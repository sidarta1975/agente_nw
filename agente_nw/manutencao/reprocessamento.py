"""Dano nos dados já gravados e reprocessamento (brief 095).

`medir_dano` conta, sem gravar, o que está no banco e foi produzido pelo critério antigo, o do texto
cortado (briefs 088 a 091): itens acima dos cortes antigos, cartões, ganchos, fatos e vetores de versão
antiga, o que não tem registro de cobertura e a fila de revisão pendente. Só contagens e versões; nenhum
texto de terceiros sai daqui.

`reprocessar` refaz uma etapa com o critério novo, na ordem sugerida pelo brief (2.4), cada uma com a sua
autorização:

- `vetores`: o vetor de cada item com vetor gravado (texto inteiro, `embeddar_em_partes`), o centróide de
  cada assunto (média dos vetores novos dos seus itens, a regra do agrupador) e o vetor de cada tema
  (`texto_do_tema`). O centróide do contato não entra: o cruzamento o recalcula e regrava a cada pedido
  (`cruzamento.py`), e o `medir_dano` mostra quantos ainda são do critério anterior;
- `cartoes`: o cartão de cada assunto com cartão de versão antiga, por `cartoes.gerar_cartao`, que refaz
  também os resumos dos itens.

Em simulação (o padrão), a etapa roda numa cópia à parte do banco e o banco dado não muda: o que mudaria é
contado comparando a cópia com ele. Gravar no próprio banco é `--confirmo`, recusado dentro de uma série e,
no banco real, sem a autorização escrita da etapa no PLAN."""

from __future__ import annotations

import json
import re
import sqlite3
import struct
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from agente_nw.nucleo.agrupamento import comparar_vetores
from agente_nw.nucleo.agrupamento.agrupador import ClienteEmbeddagem, texto_do_item
from agente_nw.nucleo.agrupamento.comparar_vetores import Comparado
from agente_nw.nucleo.database.queries import assuntos, itens, temas
from agente_nw.nucleo.llm import embeddar_em_partes
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.prompts import cartao as prompt_cartao
from agente_nw.nucleo.prompts import extrair_captura_rede_social, extrair_de_texto, redigir_ganchos
from agente_nw.nucleo.relevancia import cartoes
from agente_nw.nucleo.relevancia.cartoes import ClienteCartao
from agente_nw.nucleo.vetores import centroide
from agente_nw.perfil.configurador import texto_do_tema

Etapa = Literal["vetores", "cartoes"]
ETAPAS: tuple[Etapa, ...] = ("vetores", "cartoes")

VARIAVEL_DA_SERIE = "SERIE_DENTRO_DO_CAFFEINATE"
"""A variável que o `scripts/executar_serie.sh` exporta para tudo o que roda dentro da série (brief 086)."""

AUTORIZACAO = re.compile(r"autorizado por Sidarta em \d{4}-\d{2}-\d{2}")
"""A linha do PLAN que autoriza gravar uma etapa no banco real tem `reprocessar`, o nome da etapa e isto."""

ESQUEMA_MINIMO = 22
"""Migração 022 (brief 090): sem ela não há `cartao_versao` nem resumo do item para contar."""

CORTE_ANTIGO_DO_VETOR = 2000
"""Caracteres do texto do item que iam ao embedding antes do brief 089."""

CORTE_ANTIGO_DO_CARTAO = 300
"""Caracteres de cada item que iam ao cartão e à qualificação antes do brief 090."""

VERSOES_ATUAIS_DE_FATO = frozenset({extrair_de_texto.VERSAO, extrair_captura_rede_social.VERSAO})
"""Versões de prompt das extrações que geram fato, desde o brief 088."""

_TABELAS_DE_VETOR_COM_CRITERIO = ("vetor_tema", "vetor_assunto", "vetor_perfil")


def abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    return comparar_vetores.abrir_somente_leitura(caminho)


def versao_do_esquema(conn: sqlite3.Connection) -> int:
    (versao,) = conn.execute("SELECT MAX(versao) FROM schema_version").fetchone()
    return int(versao or 0)


# --- medir-dano -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Dano:
    itens: int
    itens_com_corpo: int
    itens_acima_do_corte_do_vetor: int
    itens_acima_do_corte_do_cartao: int
    itens_sem_resumo_da_versao_atual: int
    vetores_de_item_sem_versao: int
    vetores_do_criterio_anterior: tuple[tuple[str, int, int], ...]
    """(tabela, vetores de outro critério, total)."""
    cartoes: int
    cartoes_de_versao_antiga: int
    cartoes_sem_cobertura: int
    ganchos: int
    ganchos_de_versao_antiga: int
    ganchos_em_assunto_de_cartao_antigo: int
    ganchos_por_versao: tuple[tuple[str | None, int], ...]
    fatos: int
    fatos_de_versao_antiga: int
    fatos_por_versao: tuple[tuple[str | None, int], ...]
    extracoes_sem_registro_de_partes: int
    fila_revisao_pendente: int
    fila_revisao_por_tarefa: tuple[tuple[str, int], ...]


def _um(conn: sqlite3.Connection, sql: str, parametros: tuple[object, ...] = ()) -> int:
    (valor,) = conn.execute(sql, parametros).fetchone()
    return int(valor or 0)


def _por_versao(conn: sqlite3.Connection, tabela: str) -> tuple[tuple[str | None, int], ...]:
    linhas = conn.execute(
        f"SELECT gerado_por_prompt_versao, COUNT(*) FROM {tabela} "  # noqa: S608 — nomes fixos
        "GROUP BY gerado_por_prompt_versao ORDER BY gerado_por_prompt_versao"
    ).fetchall()
    return tuple((linha[0], int(linha[1])) for linha in linhas)


_CARTAO_ANTIGO = "resumo_cartao IS NOT NULL AND (cartao_versao IS NULL OR cartao_versao != ?)"


def medir_dano(conn: sqlite3.Connection, identificador_do_vetor: str) -> Dano:
    """Contagens do que foi produzido pelo critério antigo. `identificador_do_vetor`: o `modelo_embedding`
    que os vetores do critério atual gravam (`llm.identificador_do_vetor`). Não grava nada."""
    vetores_anteriores = tuple(
        (
            tabela,
            _um(
                conn,
                f"SELECT COUNT(*) FROM {tabela} WHERE modelo_embedding IS NOT ?",  # noqa: S608 — nomes fixos
                (identificador_do_vetor,),
            ),
            _um(conn, f"SELECT COUNT(*) FROM {tabela}"),  # noqa: S608 — nomes fixos
        )
        for tabela in _TABELAS_DE_VETOR_COM_CRITERIO
    )
    fatos_por_versao = _por_versao(conn, "fato")
    ganchos_por_versao = _por_versao(conn, "gancho_uso")
    fila = conn.execute(
        "SELECT tarefa, COUNT(*) FROM fila_revisao WHERE resolvido = 0 GROUP BY tarefa ORDER BY tarefa"
    ).fetchall()
    return Dano(
        itens=_um(conn, "SELECT COUNT(*) FROM item"),
        itens_com_corpo=_um(conn, "SELECT COUNT(*) FROM item WHERE texto IS NOT NULL"),
        itens_acima_do_corte_do_vetor=_um(
            conn, "SELECT COUNT(*) FROM item WHERE length(texto) > ?", (CORTE_ANTIGO_DO_VETOR,)
        ),
        itens_acima_do_corte_do_cartao=_um(
            conn, "SELECT COUNT(*) FROM item WHERE length(texto) > ?", (CORTE_ANTIGO_DO_CARTAO,)
        ),
        itens_sem_resumo_da_versao_atual=_um(
            conn,
            "SELECT COUNT(*) FROM item WHERE texto IS NOT NULL "
            "AND (resumo IS NULL OR resumo_versao IS NOT ?)",
            (prompt_cartao.VERSAO_RESUMO_ITEM,),
        ),
        vetores_de_item_sem_versao=_um(conn, "SELECT COUNT(*) FROM vetor_item"),
        vetores_do_criterio_anterior=vetores_anteriores,
        cartoes=_um(conn, "SELECT COUNT(*) FROM assunto WHERE resumo_cartao IS NOT NULL"),
        cartoes_de_versao_antiga=_um(
            conn,
            f"SELECT COUNT(*) FROM assunto WHERE {_CARTAO_ANTIGO}",
            (prompt_cartao.VERSAO,),  # noqa: S608
        ),
        cartoes_sem_cobertura=_um(
            conn, "SELECT COUNT(*) FROM assunto WHERE resumo_cartao IS NOT NULL AND cartao_itens IS NULL"
        ),
        ganchos=sum(quantidade for _versao, quantidade in ganchos_por_versao),
        ganchos_de_versao_antiga=sum(
            quantidade for versao, quantidade in ganchos_por_versao if versao != redigir_ganchos.VERSAO
        ),
        ganchos_em_assunto_de_cartao_antigo=_um(
            conn,
            f"SELECT COUNT(*) FROM gancho_uso WHERE assunto_id IN (SELECT id FROM assunto WHERE {_CARTAO_ANTIGO})",  # noqa: S608, E501
            (prompt_cartao.VERSAO,),
        ),
        ganchos_por_versao=ganchos_por_versao,
        fatos=sum(quantidade for _versao, quantidade in fatos_por_versao),
        fatos_de_versao_antiga=sum(
            quantidade for versao, quantidade in fatos_por_versao if versao not in VERSOES_ATUAIS_DE_FATO
        ),
        fatos_por_versao=fatos_por_versao,
        extracoes_sem_registro_de_partes=_um(
            conn, "SELECT COUNT(*) FROM fila_extracao WHERE processado = 1 AND partes_lidas IS NULL"
        ),
        fila_revisao_pendente=sum(int(linha[1]) for linha in fila),
        fila_revisao_por_tarefa=tuple((str(linha[0]), int(linha[1])) for linha in fila),
    )


def linhas_do_dano(dano: Dano) -> list[str]:
    """A saída do `medir-dano`: rótulo e contagem, uma por linha. Versão de prompt não é texto de terceiro."""
    linhas = [
        f"Itens: {dano.itens}",
        f"Itens com corpo: {dano.itens_com_corpo}",
        f"Itens com texto acima de {CORTE_ANTIGO_DO_VETOR} caracteres (corte antigo do vetor do item): "
        f"{dano.itens_acima_do_corte_do_vetor}",
        f"Itens com texto acima de {CORTE_ANTIGO_DO_CARTAO} caracteres (corte antigo do cartão e da "
        f"qualificação): {dano.itens_acima_do_corte_do_cartao}",
        f"Itens com corpo sem resumo da versão atual: {dano.itens_sem_resumo_da_versao_atual}",
        f"vetor_item: {dano.vetores_de_item_sem_versao} vetores, sem versão gravada "
        "(o critério não se distingue)",
    ]
    linhas += [
        f"{tabela}: {outros} de {total} do critério anterior"
        for tabela, outros, total in dano.vetores_do_criterio_anterior
    ]
    linhas += [
        f"Cartões: {dano.cartoes}",
        f"Cartões de versão antiga: {dano.cartoes_de_versao_antiga}",
        f"Cartões sem registro de cobertura: {dano.cartoes_sem_cobertura}",
        f"Ganchos: {dano.ganchos}",
        f"Ganchos de versão antiga do prompt: {dano.ganchos_de_versao_antiga}",
        f"Ganchos em assunto de cartão antigo: {dano.ganchos_em_assunto_de_cartao_antigo}",
    ]
    linhas += [f"  ganchos da versão {versao or 'sem versão'}: {n}" for versao, n in dano.ganchos_por_versao]
    linhas += [
        f"Fatos: {dano.fatos}",
        f"Fatos de versão antiga ou sem versão: {dano.fatos_de_versao_antiga}",
    ]
    linhas += [f"  fatos da versão {versao or 'sem versão'}: {n}" for versao, n in dano.fatos_por_versao]
    linhas += [
        f"Extrações processadas sem registro de partes lidas: {dano.extracoes_sem_registro_de_partes}",
        f"Fila de revisão pendente: {dano.fila_revisao_pendente}",
    ]
    linhas += [f"  fila de revisão, {tarefa}: {n}" for tarefa, n in dano.fila_revisao_por_tarefa]
    return linhas


# --- reprocessar: travas -----------------------------------------------------------------------------------


def autorizado_no_plan(plan: Path, etapa: Etapa) -> bool:
    if not plan.is_file():
        return False
    return any(
        "reprocessar" in linha and etapa in linha and AUTORIZACAO.search(linha)
        for linha in plan.read_text(encoding="utf-8").splitlines()
    )


def recusa_para_gravar(
    banco: Path, banco_real: Path, plan: Path, etapa: Etapa, ambiente: Mapping[str, str]
) -> str | None:
    """Por que `--confirmo` não pode gravar, ou None. Dentro de uma série nunca grava (ninguém autoriza);
    no banco real, só com a linha da etapa no PLAN."""
    if ambiente.get(VARIAVEL_DA_SERIE):
        return "reprocessar --confirmo não grava dentro de uma série: gravação só por Sidarta, acompanhada"
    if banco.resolve() == banco_real.resolve() and not autorizado_no_plan(plan, etapa):
        return (
            f"gravar a etapa {etapa} no banco real exige, no PLAN, uma linha com 'reprocessar {etapa}' e "
            "'autorizado por Sidarta em AAAA-MM-DD'"
        )
    return None


def copiar_consistente(origem: Path, destino: Path) -> None:
    """Cópia do banco pela API de backup do SQLite, lida em `mode=ro` (inclui o que está no WAL)."""
    if destino.exists():
        raise FileExistsError(f"{destino} já existe")
    leitura = abrir_somente_leitura(origem)
    try:
        escrita = sqlite3.connect(str(destino))
        try:
            leitura.backup(escrita)
        finally:
            escrita.close()
    finally:
        leitura.close()


# --- reprocessar: etapas -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoReprocessamento:
    etapa: Etapa
    linhas: tuple[str, ...]
    """Contagens, na ordem em que o CLI as mostra."""


def _desserializar(blob: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(blob) // 4}f", blob))


def _ganchos_em(conn: sqlite3.Connection, assunto_ids: set[int]) -> int:
    if not assunto_ids:
        return 0
    marcas = ", ".join("?" for _ in assunto_ids)
    return _um(
        conn,
        f"SELECT COUNT(*) FROM gancho_uso WHERE assunto_id IN ({marcas})",  # noqa: S608 — só marcadores
        tuple(sorted(assunto_ids)),
    )


def reprocessar_vetores(
    cliente: ClienteEmbeddagem, leitura: sqlite3.Connection, escrita: sqlite3.Connection, limiares: Limiares
) -> ResultadoReprocessamento:
    """Regrava vetores de item, centróides de assunto e vetores de tema em `escrita` com o critério novo.
    `leitura` é o banco antes da regravação: dele vêm os vetores antigos e os centróides contra os quais se
    conta quem trocaria de assunto (a regra de `comparar_vetores.contar`)."""
    linhas_item = leitura.execute(
        "SELECT i.id, i.titulo, i.texto, i.assunto_id, v.embedding AS embedding "
        "FROM item i JOIN vetor_item v ON v.item_id = i.id ORDER BY i.id"
    ).fetchall()
    centroides_antigos = {
        int(linha["assunto_id"]): _desserializar(linha["centroide"])
        for linha in leitura.execute("SELECT assunto_id, centroide FROM vetor_assunto")
    }

    comparados: list[Comparado] = []
    falhas = 0
    novos_por_assunto: dict[int, list[list[float]]] = defaultdict(list)
    for linha in linhas_item:
        try:
            novo = embeddar_em_partes(cliente, texto_do_item(linha["titulo"], linha["texto"]))
        except ValueError:  # falha numa parte: o item fica com o vetor de antes, nunca com um parcial
            falhas += 1
            continue
        itens.gravar_embedding(escrita, int(linha["id"]), novo)
        comparados.append(
            Comparado(int(linha["id"]), linha["assunto_id"], _desserializar(linha["embedding"]), novo)
        )
        if linha["assunto_id"] is not None:
            novos_por_assunto[int(linha["assunto_id"])].append(novo)

    for assunto_id, vetores in novos_por_assunto.items():
        assuntos.gravar_centroide(escrita, assunto_id, centroide(vetores), cliente.modelo_embedding)

    temas_regravados = 0
    for linha in leitura.execute(
        "SELECT t.id, t.nome, t.descricao, t.sinonimos FROM tema t JOIN vetor_tema v ON v.tema_id = t.id"
    ).fetchall():
        sinonimos = [str(s) for s in _lista_json(linha["sinonimos"])]
        try:
            vetor = embeddar_em_partes(cliente, texto_do_tema(linha["nome"], linha["descricao"], sinonimos))
        except ValueError:
            falhas += 1
            continue
        temas.gravar_embedding(escrita, int(linha["id"]), vetor, cliente.modelo_embedding)
        temas_regravados += 1
    escrita.commit()

    contagem = comparar_vetores.contar(comparados, centroides_antigos, limiares)
    por_assunto: dict[int, list[Comparado]] = defaultdict(list)
    for comparado in comparados:
        if comparado.assunto_id is not None:
            por_assunto[comparado.assunto_id].append(comparado)
    assuntos_que_mudariam = {
        assunto_id
        for assunto_id, grupo in por_assunto.items()
        if comparar_vetores.contar(grupo, centroides_antigos, limiares).itens_que_trocariam_de_assunto
    }
    return ResultadoReprocessamento(
        "vetores",
        (
            f"Itens com vetor novo: {len(comparados)} de {len(linhas_item)}",
            f"Centróides de assunto regravados: {len(novos_por_assunto)}",
            f"Vetores de tema regravados: {temas_regravados}",
            f"Falhas (o vetor de antes fica): {falhas}",
            f"Itens que trocariam de assunto: {contagem.itens_que_trocariam_de_assunto}",
            f"Assuntos que se fundiriam: {contagem.assuntos_que_se_fundiriam}",
            f"Assuntos que se separariam: {contagem.assuntos_que_se_separariam}",
            f"Republicados que deixariam de ser: {contagem.republicacoes_que_mudariam}",
            f"Itens que passariam a ser republicação: {contagem.passariam_a_republicacao}",
            f"Assuntos com item que trocaria: {len(assuntos_que_mudariam)}",
            f"Ganchos em assunto que mudaria: {_ganchos_em(leitura, assuntos_que_mudariam)}",
        ),
    )


def _lista_json(valor: str | None) -> list[object]:
    carregado = json.loads(valor or "[]")
    return list(carregado) if isinstance(carregado, list) else []


def reprocessar_cartoes(
    cliente: ClienteCartao, leitura: sqlite3.Connection, escrita: sqlite3.Connection
) -> ResultadoReprocessamento:
    """Refaz em `escrita` o cartão de cada assunto com cartão de versão antiga (`cartoes.gerar_cartao`,
    que também refaz os resumos dos itens). `leitura` guarda o cartão de antes, para contar o que mudou."""
    antigos = {
        int(linha["id"]): str(linha["resumo_cartao"])
        for linha in leitura.execute(
            f"SELECT id, resumo_cartao FROM assunto WHERE {_CARTAO_ANTIGO} ORDER BY id",  # noqa: S608
            (prompt_cartao.VERSAO,),
        )
    }
    regravados = falhas = 0
    mudariam: set[int] = set()
    for assunto_id, cartao_antigo in antigos.items():
        novo = cartoes.gerar_cartao(cliente, escrita, assunto_id)
        if novo is None:
            falhas += 1
            continue
        regravados += 1
        if novo != cartao_antigo:
            mudariam.add(assunto_id)
    escrita.commit()
    return ResultadoReprocessamento(
        "cartoes",
        (
            f"Cartões de versão antiga: {len(antigos)}",
            f"Cartões regravados: {regravados}",
            f"Falhas (o cartão de antes fica, motivo na fila de revisão): {falhas}",
            f"Cartões que mudariam: {len(mudariam)}",
            f"Ganchos em assunto que mudaria: {_ganchos_em(leitura, mudariam)}",
        ),
    )
