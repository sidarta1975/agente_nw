from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from agente_nw.coleta.capturas import busca, listas
from agente_nw.coleta.capturas.busca import redes_automaticas
from agente_nw.coleta.capturas.listas import PaginaLista, ResultadoAtualizacao
from agente_nw.nucleo.database.queries import fatos, perfis, rede_sem_perfil, redes_sociais
from agente_nw.nucleo.database.queries import listas as queries_listas
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.configuracao import ListasLimiares
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.lista_rede_social import EntradaGravada
from agente_nw.nucleo.modelos.localizacao import Localizacao, Opcao, RespostaDesempate
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.prompts import desempatar_perfil
from agente_nw.nucleo.texto import sem_acento_e_caixa, variantes_do_nome

_EsquemaT = TypeVar("_EsquemaT", bound=BaseModel)
_CONFIANCA_MINIMA = 0.7
TIPO_FATO_LISTA = "lista_rede_social"
_HOSTS_POR_REDE: dict[str, str] = {
    "linkedin.com": "linkedin",
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "x.com": "x",
    "twitter.com": "x",
}


class ClienteDesempate(Protocol):
    def gerar_json(self, tarefa_nome: str, prompt: str, esquema: type[_EsquemaT]) -> _EsquemaT: ...


@dataclass
class ContextoNavegacao:
    """Tudo de que a localização precisa para abrir o navegador do usuário e guardar o que aprende."""

    abrir_pagina: Callable[[Path], PaginaLista]
    pasta_navegador: Path
    limiares: ListasLimiares
    usuarios_rede: dict[str, str]
    gravar_usuario: Callable[[str, str], None] | None = None
    perguntar_usuario: Callable[[str], str | None] | None = None
    avisar: Callable[[str], None] | None = None
    dorme: Callable[[float], None] = time.sleep


def canonicalizar_link(link: str) -> str:
    """Sem parâmetros de rastreio nem barra final, para o mesmo perfil ter sempre o mesmo link."""
    bruto = link.strip()
    base = bruto if "profile.php" in bruto else bruto.split("?")[0]
    return base.rstrip("/")


def rede_do_link(link: str) -> str | None:
    host = (urlparse(link.strip()).hostname or "").lower().removeprefix("www.")
    return _HOSTS_POR_REDE.get(host)


def ordem_das_redes(registro: str, pistas: dict[str, str], so_por_link: Iterable[str] = ()) -> list[str]:
    """LinkedIn primeiro para registro cordial/formal ou pista de profissão/empresa; Instagram
    primeiro para registro próximo; as demais na ordem das redes automáticas (as de
    `redes_so_por_link` só entram por link)."""
    profissional = registro in ("cordial", "formal") or "profissao" in pistas or "empresa" in pistas
    primeira = "linkedin" if profissional else ("instagram" if registro == "proximo" else None)
    restantes = [r for r in redes_automaticas(so_por_link) if r != primeira]
    return ([primeira] if primeira else []) + restantes


def opcao_da_entrada(entrada: EntradaGravada) -> Opcao:
    return Opcao(
        rede=entrada.rede,
        nome=entrada.nome,
        cabecalho=entrada.cabecalho,
        link=entrada.link,
        fonte="lista",
        foto_url=entrada.foto_url,
    )


def _pontuar(opcao: Opcao, pistas: dict[str, str]) -> int:
    cabecalho = sem_acento_e_caixa(opcao.cabecalho)
    return sum(
        1
        for chave in ("profissao", "empresa", "cidade")
        if chave in pistas and sem_acento_e_caixa(pistas[chave]) in cabecalho
    )


def _desempatar(
    cliente_llm: ClienteDesempate, nome: str, pistas: dict[str, str], empatadas: list[Opcao]
) -> Opcao | None:
    prompt = desempatar_perfil.construir_prompt(nome, pistas, [o.cabecalho for o in empatadas])
    try:
        resposta = cliente_llm.gerar_json("desempatar_perfil", prompt, RespostaDesempate)
    except FalhaJsonInvalido:
        return None
    indice = resposta.indice_escolhido
    if indice is None or not 1 <= indice <= len(empatadas) or resposta.confianca < _CONFIANCA_MINIMA:
        return None
    return empatadas[indice - 1]


def _avaliar(
    cliente_llm: ClienteDesempate, pedido: PedidoExtraido, candidatas: list[Opcao]
) -> tuple[Opcao | None, list[Opcao]]:
    """Devolve (escolhido claro ou None, candidatas ordenadas da mais para a menos provável)."""
    pistas = pedido.pessoa_pistas
    tem_pistas = any(chave in pistas for chave in ("profissao", "empresa", "cidade"))
    pontuadas = sorted(((_pontuar(o, pistas), o) for o in candidatas), key=lambda par: -par[0])
    ordenadas = [o for _, o in pontuadas]
    melhor = pontuadas[0][0]
    empatadas = [o for pontos, o in pontuadas if pontos == melhor]

    if len(empatadas) == 1:
        claro = not tem_pistas or melhor >= 1
        return (empatadas[0] if claro else None), ordenadas
    if tem_pistas:
        escolhida = _desempatar(cliente_llm, pedido.pessoa_nome, pistas, empatadas)
        if escolhida is not None:
            resto = [o for o in ordenadas if o != escolhida]
            return escolhida, [escolhida, *resto]
    return None, ordenadas


def atualizar_lista(
    conexao: sqlite3.Connection,
    rede: str,
    contexto: ContextoNavegacao,
    agora: str,
    forcar: bool = False,
) -> ResultadoAtualizacao:
    """Garante a lista de `rede` no cache: usa o cache válido, ou lê a lista do navegador do usuário."""
    if not forcar and queries_listas.cache_valido(conexao, rede, contexto.limiares.validade_dias, agora):
        return ResultadoAtualizacao(
            rede=rede, lida=False, usou_cache=True, total=queries_listas.contar_por_rede(conexao, rede)
        )

    usuario = listas.resolver_usuario(
        rede,
        contexto.usuarios_rede.get(rede),
        contexto.abrir_pagina,
        contexto.pasta_navegador,
        contexto.gravar_usuario,
        contexto.perguntar_usuario,
        dorme=contexto.dorme,
    )
    if contexto.avisar is not None:
        contexto.avisar(f"Lendo a lista de {rede} no seu Chrome — vai demorar; deixe a aba da ponte aberta.")
    pagina = contexto.abrir_pagina(contexto.pasta_navegador / rede)
    try:
        resultado = listas.ler_lista(
            pagina,
            rede,
            usuario,
            contexto.limiares,
            dorme=contexto.dorme,
        )
        vista = _o_que_a_pagina_mostra(pagina) if resultado.autenticado and not resultado.entradas else ""
    finally:
        pagina.fechar()

    if not resultado.autenticado:
        return ResultadoAtualizacao(rede=rede, lida=False, usou_cache=False, total=0, motivo=resultado.motivo)
    if not resultado.entradas:
        return ResultadoAtualizacao(
            rede=rede,
            lida=False,
            usou_cache=False,
            total=0,
            motivo=f"abri a lista de {rede} mas não achei ninguém nela (a página pode ter mudado){vista}",
        )
    queries_listas.substituir_lista(conexao, rede, resultado.entradas, agora)
    conexao.commit()
    return ResultadoAtualizacao(rede=rede, lida=True, usou_cache=False, total=len(resultado.entradas))


def _o_que_a_pagina_mostra(pagina: PaginaLista) -> str:
    """Endereço e começo do texto da página, para o usuário ver por que a lista veio vazia."""
    try:
        url, texto = pagina.estado()
    except Exception:
        return ""
    resumo = " ".join(str(texto).split())[:160]
    return f' — a aba estava em {url}: "{resumo}"'


_PISTAS_DA_DESCRICAO = ("profissao", "empresa", "cidade")


def _casamento_com_pistas(descricao: str, pistas: dict[str, str]) -> int:
    """Quantas palavras (de 4 letras ou mais) da profissão, empresa e cidade informadas pelo usuário
    aparecem na descrição do candidato. Só ordena: a informação do usuário vem primeiro."""
    texto = sem_acento_e_caixa(descricao)
    achadas = 0
    for chave in _PISTAS_DA_DESCRICAO:
        for palavra in sem_acento_e_caixa(pistas.get(chave, "")).split():
            if len(palavra) >= 4 and palavra in texto:
                achadas += 1
    return achadas


def _busca_geral(
    rede: str, pedido: PedidoExtraido, contexto: ContextoNavegacao, nome: str
) -> tuple[list[Opcao], str | None]:
    pagina = contexto.abrir_pagina(contexto.pasta_navegador / rede)
    try:
        resultado = busca.buscar(
            pagina,
            rede,
            nome,
            pedido.pessoa_pistas.get("empresa"),
            refino=pedido.pessoa_pistas.get("profissao"),
        )
    finally:
        pagina.fechar()
    if not resultado.autenticado:
        return [], resultado.motivo
    resultado.candidatos.sort(key=lambda c: -_casamento_com_pistas(c.descricao, pedido.pessoa_pistas))
    opcoes = [
        Opcao(
            rede=rede,
            nome=c.nome_exibido,
            cabecalho=c.descricao,
            link=canonicalizar_link(c.link),
            fonte="busca_geral",
        )
        for c in resultado.candidatos
    ]
    return opcoes, None


def _candidatas_da_lista(
    conexao: sqlite3.Connection, rede: str, nomes: list[str], limiares: ListasLimiares
) -> list[Opcao]:
    """Entradas da lista da rede que casam com algum dos nomes (exato primeiro; só se nenhum casar,
    por semelhança). Cada pessoa usa o nome que quer na conta, então vale qualquer variante."""
    exatas: dict[str, Opcao] = {}
    for nome in nomes:
        for entrada in queries_listas.buscar_por_nome(conexao, rede, nome):
            exatas.setdefault(entrada.link, opcao_da_entrada(entrada))
    if exatas:
        return list(exatas.values())
    parecidas: dict[str, Opcao] = {}
    for nome in nomes:
        achadas = queries_listas.buscar_parecidos(
            conexao, rede, nome, limiares.similaridade_minima, limiares.maximo_parecidas
        )
        for entrada in achadas:
            parecidas.setdefault(entrada.link, opcao_da_entrada(entrada))
    return list(parecidas.values())


def localizar(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteDesempate,
    pedido: PedidoExtraido,
    contexto: ContextoNavegacao,
    agora: str,
    nomes_extras: Iterable[str] = (),
) -> Localizacao:
    """Procura a pessoa do pedido nas listas do próprio usuário (cache local) e, não achando,
    na busca geral de cada rede com sessão. Nunca decide sozinho nem grava: devolve `Localizacao`."""
    avisos: list[str] = []
    sem_sessao: set[str] = set()
    acumuladas: list[Opcao] = []
    nomes = variantes_do_nome([pedido.pessoa_nome, *nomes_extras])

    for rede in ordem_das_redes(pedido.registro, pedido.pessoa_pistas, contexto.limiares.redes_so_por_link):
        atualizacao = atualizar_lista(conexao, rede, contexto, agora)
        if atualizacao.motivo:
            avisos.append(f"{rede}: {atualizacao.motivo}")
            sem_sessao.add(rede)
            continue
        candidatas = _candidatas_da_lista(conexao, rede, nomes, contexto.limiares)
        if not candidatas:
            continue
        escolhido, ordenadas = _avaliar(cliente_llm, pedido, candidatas)
        if escolhido is not None:
            return Localizacao(
                status="claro", escolhido=escolhido, opcoes=ordenadas, fonte="lista", avisos=avisos
            )
        acumuladas.extend(ordenadas)

    if acumuladas:
        return Localizacao(status="ambiguo", opcoes=acumuladas, fonte="lista", avisos=avisos)

    nomes_da_busca = list(dict.fromkeys([pedido.pessoa_nome, *nomes_extras]))
    opcoes_busca: dict[str, Opcao] = {}
    for rede in ordem_das_redes(pedido.registro, pedido.pessoa_pistas, contexto.limiares.redes_so_por_link):
        if rede in sem_sessao:
            continue
        for nome in nomes_da_busca:
            achadas, motivo = _busca_geral(rede, pedido, contexto, nome)
            if motivo:
                avisos.append(f"{rede}: {motivo}")
                break
            for opcao in achadas:
                opcoes_busca.setdefault(opcao.link, opcao)
    return Localizacao(
        status="nenhum", opcoes=list(opcoes_busca.values()), fonte="busca_geral", avisos=avisos
    )


def localizar_rede(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteDesempate,
    pedido: PedidoExtraido,
    contexto: ContextoNavegacao,
    agora: str,
    rede: str,
    nomes_extras: Iterable[str] = (),
) -> Localizacao:
    """Curadoria de uma rede: procura a pessoa na lista do usuário nessa rede (todas as variantes do
    nome) e, não achando, na busca geral dela. Nunca decide nem grava: devolve `Localizacao`."""
    atualizacao = atualizar_lista(conexao, rede, contexto, agora)
    if atualizacao.motivo:
        return Localizacao(status="nenhum", rede=rede, avisos=[f"{rede}: {atualizacao.motivo}"])
    nomes = variantes_do_nome([pedido.pessoa_nome, *nomes_extras])
    candidatas = _candidatas_da_lista(conexao, rede, nomes, contexto.limiares)
    if candidatas:
        escolhido, ordenadas = _avaliar(cliente_llm, pedido, candidatas)
        return Localizacao(
            status="claro" if escolhido is not None else "ambiguo",
            escolhido=escolhido,
            opcoes=ordenadas,
            fonte="lista",
            rede=rede,
        )
    opcoes: dict[str, Opcao] = {}
    for nome in dict.fromkeys([pedido.pessoa_nome, *nomes_extras]):
        achadas, motivo = _busca_geral(rede, pedido, contexto, nome)
        if motivo:
            return Localizacao(status="nenhum", fonte="busca_geral", rede=rede, avisos=[f"{rede}: {motivo}"])
        for opcao in achadas:
            opcoes.setdefault(opcao.link, opcao)
    return Localizacao(status="nenhum", opcoes=list(opcoes.values()), fonte="busca_geral", rede=rede)


def confirmar(
    conexao: sqlite3.Connection,
    perfil_id: int,
    opcao: Opcao,
    agora: str,
    substituir: bool = False,
) -> None:
    """Grava a escolha confirmada no contato: rede social, notas (se vazias), vínculo na lista e fato."""
    atuais = redes_sociais.listar_por_perfil(conexao, perfil_id)
    if substituir:
        for existente in atuais:
            if existente.rede == opcao.rede:
                if existente.id is not None:
                    redes_sociais.remover(conexao, existente.id)
        atuais = redes_sociais.listar_por_perfil(conexao, perfil_id)
    if not any(r.link == opcao.link for r in atuais):
        redes_sociais.inserir(conexao, perfil_id, opcao.rede, opcao.link, agora)
    rede_sem_perfil.remover(conexao, perfil_id, opcao.rede)

    if opcao.cabecalho:
        perfis.preencher_lacunas(conexao, perfil_id, {"notas": opcao.cabecalho}, agora)
        ja_tem = any(
            f.conteudo == opcao.cabecalho and f.tipo == TIPO_FATO_LISTA
            for f in fatos.listar_recentes(conexao, perfil_id, 200)
        )
        if not ja_tem:
            fatos.inserir(
                conexao,
                Fato(
                    perfil_id=perfil_id,
                    tipo=TIPO_FATO_LISTA,
                    conteudo=opcao.cabecalho,
                    fonte=opcao.link,
                    registrado_em=agora,
                ),
            )
    queries_listas.vincular(conexao, opcao.link, perfil_id)
    conexao.commit()


def opcao_do_link(conexao: sqlite3.Connection, link: str) -> Opcao | None:
    """Opção a partir de um link colado pelo usuário; usa o cabeçalho da lista se o link estiver nela."""
    bruto = link.strip()
    rede = rede_do_link(bruto)
    if rede is None:
        return None
    canonico = canonicalizar_link(bruto)
    nome, cabecalho = queries_listas.nome_e_cabecalho_do_link(conexao, canonico) or (canonico, "")
    return Opcao(rede=rede, nome=nome, cabecalho=cabecalho, link=canonico, fonte="link_colado")


def gravar_link_do_pedido(
    conexao: sqlite3.Connection, perfil_id: int, link: str, agora: str, substituir: bool = False
) -> Opcao | None:
    """O pedido trouxe o link da pessoa: grava direto, sem perguntar."""
    opcao = opcao_do_link(conexao, link)
    if opcao is None:
        return None
    confirmar(conexao, perfil_id, opcao, agora, substituir=substituir)
    return opcao
