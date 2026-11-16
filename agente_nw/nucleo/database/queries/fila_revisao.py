from __future__ import annotations

import sqlite3
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from agente_nw.nucleo.modelos.fila import FilaRevisao


def inserir(conexao: sqlite3.Connection, tarefa: str, entrada: str, erro: str, agora: str) -> int:
    registro = FilaRevisao(tarefa=tarefa, entrada=entrada, erro=erro, criado_em=agora, resolvido=False)
    cursor = conexao.execute(
        "INSERT INTO fila_revisao (tarefa, entrada, erro, criado_em, resolvido) VALUES (?, ?, ?, ?, ?)",
        (registro.tarefa, registro.entrada, registro.erro, registro.criado_em, int(registro.resolvido)),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


# --- Destino do que foi para a fila (brief 087) --------------------------------------------------

TAREFAS_COM_REPETICAO = frozenset({"extrair_de_texto"})
"""Tarefas que têm caminho de repetição no código: `extrair_de_texto` volta pela linha de
`fila_extracao` que falhou. `extrair_pedido` e `redigir_ganchos` guardam só o prompt montado, sem
apontar para o pedido ou para a consulta de origem; refazer a chamada com ele não gravaria nada."""

RESOLUCOES = ("descartado", "reenviado_ok", "reenviado_falhou")

Reprocessar = Callable[[int], int | None]
"""Recebe o id da linha de `fila_extracao` e devolve `None` se gravou resultado válido, ou o id da
linha que a nova falha abriu em `fila_revisao`."""


class ItemInexistente(LookupError):
    pass


class ItemJaResolvido(RuntimeError):
    pass


class SemCaminhoDeRepeticao(RuntimeError):
    pass


class ItemDaFila(BaseModel):
    """O que a listagem mostra do item: nunca a `entrada`, que é o prompt inteiro (texto de terceiros)."""

    model_config = ConfigDict(frozen=True)

    id: int
    tarefa: str
    erro: str
    classe_do_erro: str
    criado_em: str
    resolvido: bool
    resolvido_em: str | None = None
    resolucao: str | None = None
    motivo: str | None = None


class ItemCompleto(ItemDaFila):
    entrada: str


class ContagemDaFila(BaseModel):
    model_config = ConfigDict(frozen=True)

    tarefa: str
    classe_do_erro: str
    itens: int
    mais_antigo: str


def classe_do_erro(erro: str) -> str:
    """Agrupa o texto livre do erro numa classe curta. Só a classe aparece nas contagens: o texto do
    erro de validação do Pydantic pode citar pedaço da resposta do modelo."""
    minusculo = erro.lower()
    if "token repeat limit" in minusculo or "prediction aborted" in minusculo:
        return "geracao_degenerada"
    if "validation error" in minusculo or "json" in minusculo or "expecting" in minusculo:
        return "json_invalido"
    if any(marca in minusculo for marca in ("http", "connect", "timeout", "timed out", "refused")):
        return "transporte"
    return "outro"


_COLUNAS_LISTA = "id, tarefa, erro, criado_em, resolvido, resolvido_em, resolucao, motivo"


def _para_item(linha: sqlite3.Row) -> ItemDaFila:
    return ItemDaFila(
        id=linha["id"],
        tarefa=linha["tarefa"],
        erro=linha["erro"],
        classe_do_erro=classe_do_erro(linha["erro"]),
        criado_em=linha["criado_em"],
        resolvido=bool(linha["resolvido"]),
        resolvido_em=linha["resolvido_em"],
        resolucao=linha["resolucao"],
        motivo=linha["motivo"],
    )


def listar(conexao: sqlite3.Connection, incluir_resolvidos: bool = False) -> list[ItemDaFila]:
    """Itens por tarefa, depois por classe de erro, do mais velho para o mais novo. Sem a `entrada`."""
    filtro = "" if incluir_resolvidos else "WHERE resolvido = 0"
    linhas = conexao.execute(f"SELECT {_COLUNAS_LISTA} FROM fila_revisao {filtro}").fetchall()
    itens = [_para_item(linha) for linha in linhas]
    return sorted(itens, key=lambda i: (i.tarefa, i.classe_do_erro, i.criado_em, i.id))


def contar(conexao: sqlite3.Connection) -> list[ContagemDaFila]:
    """Itens ainda sem resolução, por tarefa e classe de erro."""
    grupos: dict[tuple[str, str], list[ItemDaFila]] = {}
    for item in listar(conexao):
        grupos.setdefault((item.tarefa, item.classe_do_erro), []).append(item)
    return [
        ContagemDaFila(
            tarefa=tarefa,
            classe_do_erro=classe,
            itens=len(itens),
            mais_antigo=min(i.criado_em for i in itens),
        )
        for (tarefa, classe), itens in sorted(grupos.items())
    ]


def obter(conexao: sqlite3.Connection, item_id: int) -> ItemCompleto | None:
    linha = conexao.execute(
        f"SELECT {_COLUNAS_LISTA}, entrada FROM fila_revisao WHERE id = ?", (item_id,)
    ).fetchone()
    if linha is None:
        return None
    return ItemCompleto(**_para_item(linha).model_dump(), entrada=linha["entrada"])


def _item_aberto(conexao: sqlite3.Connection, item_id: int) -> ItemCompleto:
    item = obter(conexao, item_id)
    if item is None:
        raise ItemInexistente(f"não existe item {item_id} na fila de revisão")
    if item.resolvido:
        raise ItemJaResolvido(f"o item {item_id} já foi resolvido ({item.resolucao}, em {item.resolvido_em})")
    return item


def descartar(conexao: sqlite3.Connection, item_id: int, motivo: str, agora: str) -> None:
    if not motivo.strip():
        raise ValueError("descartar exige um motivo")
    _item_aberto(conexao, item_id)
    conexao.execute(
        "UPDATE fila_revisao SET resolvido = 1, resolvido_em = ?, resolucao = 'descartado', motivo = ? "
        "WHERE id = ?",
        (agora, motivo.strip(), item_id),
    )
    conexao.commit()


def _extracao_do_item(conexao: sqlite3.Connection, item_id: int) -> int | None:
    """A linha de `fila_extracao` que apontou para este item: o `erro` dela guarda
    `(fila_revisao id=N)` (texto de `FalhaJsonInvalido`)."""
    linha = conexao.execute(
        "SELECT id FROM fila_extracao WHERE erro LIKE ? ORDER BY id DESC LIMIT 1",
        (f"%(fila_revisao id={item_id})%",),
    ).fetchone()
    return int(linha["id"]) if linha is not None else None


def reenviar(conexao: sqlite3.Connection, item_id: int, agora: str, reprocessar: Reprocessar) -> str:
    """Refaz a tarefa do item. Devolve `reenviado_ok` (resolvido) ou `reenviado_falhou` (continua na
    fila). Só marca resolvido depois de `reprocessar` gravar resultado válido; a linha que uma nova
    falha abre em `fila_revisao` é removida, para o mesmo texto não entrar duas vezes."""
    item = _item_aberto(conexao, item_id)
    if item.tarefa not in TAREFAS_COM_REPETICAO:
        raise SemCaminhoDeRepeticao(
            f"a tarefa '{item.tarefa}' não tem caminho de repetição no código; nada foi feito"
        )
    extracao_id = _extracao_do_item(conexao, item_id)
    if extracao_id is None:
        raise SemCaminhoDeRepeticao(
            f"nenhuma linha de fila_extracao aponta para o item {item_id} (item anterior ao vínculo); "
            "nada foi feito"
        )
    conexao.execute("UPDATE fila_extracao SET processado = 0, erro = NULL WHERE id = ?", (extracao_id,))
    conexao.commit()

    nova_falha = reprocessar(extracao_id)

    if nova_falha is None:
        conexao.execute(
            "UPDATE fila_revisao SET resolvido = 1, resolvido_em = ?, resolucao = 'reenviado_ok' "
            "WHERE id = ?",
            (agora, item_id),
        )
        conexao.commit()
        return "reenviado_ok"

    novo = conexao.execute("SELECT erro FROM fila_revisao WHERE id = ?", (nova_falha,)).fetchone()
    erro_novo = novo["erro"] if novo is not None else item.erro
    if nova_falha != item_id:
        conexao.execute("DELETE FROM fila_revisao WHERE id = ?", (nova_falha,))
    conexao.execute(
        "UPDATE fila_extracao SET erro = ? WHERE id = ?",
        (f"tarefa '{item.tarefa}' falhou de novo (fila_revisao id={item_id}): {erro_novo}", extracao_id),
    )
    conexao.execute(
        "UPDATE fila_revisao SET erro = ?, resolucao = 'reenviado_falhou', resolvido_em = ? WHERE id = ?",
        (erro_novo, agora, item_id),
    )
    conexao.commit()
    return "reenviado_falhou"
