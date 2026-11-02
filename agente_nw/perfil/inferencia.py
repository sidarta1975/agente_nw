"""Perfil do usuário inferido, não cadastrado (brief 040).

Os temas do usuário deixam de depender de formulário ou de `temas.yaml`: `atualizar_temas_do_usuario`
lê o que o pedido buscou e reforça ou cria temas; `aplicar_declaracoes` lê o que o próprio usuário disse
sobre si (`PedidoExtraido.sobre_o_usuario`) e vira tema `declarada`, atualização de nome ou entrada em
"não me interessa"; `decair` reduz o peso de tema sem uso há muito tempo. Tudo chamado de
`nucleo/pedido.py::processar`.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from typing import Protocol

from agente_nw.nucleo.database.queries import perfil_tema as perfil_tema_q
from agente_nw.nucleo.database.queries import perfis as perfis_q
from agente_nw.nucleo.database.queries import temas as temas_q
from agente_nw.nucleo.llm import FalhaJsonInvalido
from agente_nw.nucleo.modelos.configuracao import NivelTema, TemasUsuarioLimiares
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.perfil_tema import OrigemTema
from agente_nw.nucleo.modelos.tema import RespostaDescreverTema, Tema
from agente_nw.nucleo.prompts import descrever_tema
from agente_nw.nucleo.texto import sem_acento_e_caixa
from agente_nw.nucleo.vetores import cosseno

_PESO_MAXIMO = 5
_PESO_DECLARADA = 5
_RANQUE_NIVEL: dict[NivelTema, int] = {"curiosidade": 0, "interesse": 1, "dominio": 2}

# As frases de `sobre_o_usuario` chegam curtas e separadas (o prompt de extrair_pedido já pede isso);
# aqui só classificamos cada uma em nome / negativa / positiva por palavras-chave comuns em português.
_PADRAO_NOME = re.compile(r"^(?:me\s+chamo|sou\s+o|sou\s+a)\s+(.+)$", re.IGNORECASE)
_PADRAO_NEGATIVO = re.compile(
    r"^n[aã]o\s+(?:me\s+interessa|entendo\s+nada\s+de|gosto\s+de|tenho\s+mais\s+interesse\s+em)\s+(.+)$",
    re.IGNORECASE,
)
_PADRAO_POSITIVO = re.compile(r"^(?:sou\s+|gosto\s+de\s+|curto\s+|pratico\s+)(.+)$", re.IGNORECASE)


class ClienteInferencia(Protocol):
    def gerar_json(
        self,
        tarefa_nome: str,
        prompt: str,
        esquema: type[RespostaDescreverTema],
        *,
        versao_prompt: str | None = None,
    ) -> RespostaDescreverTema: ...

    def embeddar(self, textos: list[str]) -> list[list[float]]: ...

    @property
    def modelo_embedding(self) -> str: ...


def _termos_do_pedido(pedido: PedidoExtraido) -> list[str]:
    vistos: set[str] = set()
    termos: list[str] = []
    for termo in (pedido.assunto_principal, *pedido.interessa, *pedido.termos_busca):
        limpo = termo.strip()
        chave = sem_acento_e_caixa(limpo)
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        termos.append(limpo)
    return termos


def _tema_por_nome_ou_sinonimo(temas_existentes: list[Tema], termo: str) -> Tema | None:
    alvo = sem_acento_e_caixa(termo)
    for tema in temas_existentes:
        if sem_acento_e_caixa(tema.nome) == alvo:
            return tema
        if alvo in (sem_acento_e_caixa(sinonimo) for sinonimo in tema.sinonimos):
            return tema
    return None


def _tema_parecido(
    conexao: sqlite3.Connection, cliente_llm: ClienteInferencia, termo: str, limiar: float
) -> Tema | None:
    """Casa um termo com um tema já existente, do catálogo todo (não só os do usuário) — nome,
    sinônimo, ou cosseno do embedding acima do limiar (brief 040, decisão 3.1)."""
    por_nome = _tema_por_nome_ou_sinonimo(temas_q.listar(conexao), termo)
    if por_nome is not None:
        return por_nome
    candidatos = temas_q.listar_com_embedding(conexao, cliente_llm.modelo_embedding)
    if not candidatos:
        return None
    vetor_termo = cliente_llm.embeddar([termo])[0]
    melhor: tuple[float, Tema] | None = None
    for tema, vetor in candidatos:
        similaridade = cosseno(vetor_termo, vetor)
        if melhor is None or similaridade > melhor[0]:
            melhor = (similaridade, tema)
    if melhor is not None and melhor[0] >= limiar:
        return melhor[1]
    return None


def _criar_tema(conexao: sqlite3.Connection, cliente_llm: ClienteInferencia, termo: str, agora: str) -> Tema:
    try:
        resposta = cliente_llm.gerar_json(
            "descrever_tema",
            descrever_tema.construir_prompt(termo),
            RespostaDescreverTema,
            versao_prompt=descrever_tema.VERSAO,
        )
        descricao, sinonimos = resposta.descricao, resposta.sinonimos
    except FalhaJsonInvalido:
        # Sem descrição boa do modelo, o próprio termo vira a descrição — o tema nasce assim mesmo;
        # não há tentativa de qualificar a interrupção, igual a `_escolher_fatos` com embeddagem.
        descricao, sinonimos = termo, []
    tema = temas_q.obter_ou_criar(conexao, termo, descricao, sinonimos, agora)
    assert tema.id is not None
    try:
        vetor = cliente_llm.embeddar([f"{termo}: {descricao}"])[0]
        temas_q.gravar_embedding(conexao, tema.id, vetor, cliente_llm.modelo_embedding)
    except Exception:
        pass
    return tema


def _nivel_por_frequencia(
    usos_janela_interesse: int, usos_janela_dominio: int, limiares: TemasUsuarioLimiares
) -> NivelTema:
    if usos_janela_dominio >= limiares.usos_para_dominio:
        return "dominio"
    if usos_janela_interesse >= limiares.usos_para_interesse:
        return "interesse"
    return "curiosidade"


def _tocar_tema(
    conexao: sqlite3.Connection,
    usuario_id: int,
    tema: Tema,
    forcar_dominio: bool,
    agora: str,
    limiares: TemasUsuarioLimiares,
) -> None:
    """Reforça o vínculo do usuário com o tema: soma o uso, sobe o peso (teto 5) e deixa o nível subir
    conforme a frequência (nunca desce aqui — decair() é quem reduz por inatividade)."""
    assert tema.id is not None
    perfil_tema_q.registrar_uso(conexao, usuario_id, tema.id, agora)

    existente = next(
        (pt for pt in perfil_tema_q.listar_por_perfil(conexao, usuario_id) if pt.tema_id == tema.id), None
    )
    novo_peso = min(_PESO_MAXIMO, (existente.peso if existente else 0) + 1)
    origem: OrigemTema = (
        "declarada" if existente is not None and existente.origem == "declarada" else "conversa"
    )

    hoje = datetime.fromisoformat(agora).date()
    desde_interesse = (hoje - timedelta(days=limiares.janela_dias_interesse)).isoformat()
    desde_dominio = (hoje - timedelta(days=limiares.janela_dias_dominio)).isoformat()
    usos_interesse = perfil_tema_q.contar_usos_desde(conexao, usuario_id, tema.id, desde_interesse)
    usos_dominio = perfil_tema_q.contar_usos_desde(conexao, usuario_id, tema.id, desde_dominio)

    nivel_calculado: NivelTema = (
        "dominio" if forcar_dominio else _nivel_por_frequencia(usos_interesse, usos_dominio, limiares)
    )
    nivel_atual: NivelTema = existente.nivel if existente is not None and existente.nivel else "curiosidade"
    nivel_final = (
        nivel_calculado if _RANQUE_NIVEL[nivel_calculado] > _RANQUE_NIVEL[nivel_atual] else nivel_atual
    )

    perfil_tema_q.vincular(conexao, usuario_id, tema.id, novo_peso, origem, nivel_final, True, agora)


def atualizar_temas_do_usuario(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteInferencia,
    pedido: PedidoExtraido,
    agora: str,
    limiares: TemasUsuarioLimiares,
) -> None:
    """Após o pedido, reforça ou cria os temas do usuário a partir do que ele buscou (brief 040, 3.1).
    Pedido com `objetivo='apresentar'` leva o tema direto a `dominio` (alguém já apresentado domina o
    assunto, por definição do próprio objetivo). Sem `embeddar` não há como casar tema por
    similaridade nem gravar o embedding de um tema novo — a rodada é pulada, sem derrubar o pedido
    (mesma resiliência de `redacao._escolher_fatos`)."""
    if getattr(cliente_llm, "embeddar", None) is None:
        return
    usuario = perfis_q.obter_usuario(conexao)
    if usuario is None or usuario.id is None:
        return
    forcar_dominio = pedido.objetivo == "apresentar"
    for termo in _termos_do_pedido(pedido):
        tema = _tema_parecido(conexao, cliente_llm, termo, limiares.similaridade_mesmo_tema)
        if tema is None:
            tema = _criar_tema(conexao, cliente_llm, termo, agora)
        _tocar_tema(conexao, usuario.id, tema, forcar_dominio, agora, limiares)
    conexao.commit()


def _remover_tema_parecido(conexao: sqlite3.Connection, usuario_id: int, termo: str) -> None:
    """Remoção conservadora: só por nome/sinônimo exato, nunca por similaridade de embedding — não
    convém apagar um tema por aproximação."""
    tema = _tema_por_nome_ou_sinonimo(temas_q.listar(conexao), termo)
    if tema is not None and tema.id is not None:
        perfil_tema_q.desvincular(conexao, usuario_id, tema.id)


def aplicar_declaracoes(
    conexao: sqlite3.Connection,
    cliente_llm: ClienteInferencia,
    usuario_id: int,
    frases: list[str],
    agora: str,
    limiares: TemasUsuarioLimiares,
) -> None:
    """O que o usuário disse sobre si vale mais (brief 040, 3.2/3.3): nome, autodeclaração positiva
    (tema `declarada`/`dominio`) ou negativa (`nao_me_interessa`, e remove o tema se ele já existia).
    Cada frase de `frases` é tratada sozinha; frase sem padrão reconhecido é ignorada."""
    for frase in frases:
        limpa = frase.strip()
        if not limpa:
            continue

        casamento_nome = _PADRAO_NOME.match(limpa)
        if casamento_nome is not None:
            nome = casamento_nome.group(1).strip()
            if nome:
                perfis_q.upsert_usuario(conexao, nome, agora)
            continue

        casamento_negativo = _PADRAO_NEGATIVO.match(limpa)
        if casamento_negativo is not None:
            termo = casamento_negativo.group(1).strip()
            if termo:
                perfis_q.adicionar_nao_me_interessa(conexao, usuario_id, termo, agora)
                _remover_tema_parecido(conexao, usuario_id, termo)
            continue

        casamento_positivo = _PADRAO_POSITIVO.match(limpa)
        termo = casamento_positivo.group(1).strip() if casamento_positivo is not None else ""
        if not termo or getattr(cliente_llm, "embeddar", None) is None:
            continue
        tema = _tema_parecido(conexao, cliente_llm, termo, limiares.similaridade_mesmo_tema)
        if tema is None:
            tema = _criar_tema(conexao, cliente_llm, termo, agora)
        assert tema.id is not None
        perfil_tema_q.vincular(
            conexao, usuario_id, tema.id, _PESO_DECLARADA, "declarada", "dominio", True, agora
        )
        perfil_tema_q.registrar_uso(conexao, usuario_id, tema.id, agora)
    conexao.commit()


def decair(conexao: sqlite3.Connection, hoje: date, limiares: TemasUsuarioLimiares) -> None:
    """Tema sem uso há `dias_para_decair` perde 1 de peso por mês, nunca abaixo de 1; `declarada` não
    decai (brief 040, 3.1). Idempotente: no máximo um decaimento por tema por mês de calendário, então
    chamar de novo no mesmo pedido ou no mesmo dia não acumula."""
    usuario = perfis_q.obter_usuario(conexao)
    if usuario is None or usuario.id is None:
        return
    mes_atual = hoje.strftime("%Y-%m")
    for item in perfil_tema_q.listar_por_perfil(conexao, usuario.id):
        if item.origem == "declarada" or item.peso <= 1 or item.peso_decaido_em == mes_atual:
            continue
        ultimo_uso_texto = (
            perfil_tema_q.ultima_mencao(conexao, usuario.id, item.tema_id) or item.registrado_em
        )
        ultimo_uso = datetime.fromisoformat(ultimo_uso_texto[:10]).date()
        if (hoje - ultimo_uso).days <= limiares.dias_para_decair:
            continue
        perfil_tema_q.atualizar_peso_por_decaimento(
            conexao, usuario.id, item.tema_id, max(1, item.peso - 1), mes_atual
        )
    conexao.commit()


def esquecer_inferidos(conexao: sqlite3.Connection, usuario_id: int) -> int:
    """'Esquecer tudo o que você inferiu sobre mim' (brief 040, 3.4): zera só `origem='conversa'`;
    temas `declarada` sobrevivem. Devolve quantos vínculos foram removidos."""
    removidos = perfil_tema_q.remover_por_origem(conexao, usuario_id, "conversa")
    conexao.commit()
    return removidos
