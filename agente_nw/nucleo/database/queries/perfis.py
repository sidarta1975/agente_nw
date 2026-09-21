from __future__ import annotations

import json
import sqlite3
import struct

import sqlite_vec

from agente_nw.nucleo.modelos.perfil import Perfil
from agente_nw.nucleo.vetores import centroide as calcular_media_ponderada

_COLUNAS = (
    "id, tipo, nome, apelido, email, telefone, empresa, cargo, setor, cidade, naturalidade, "
    "linguas, formacao, tem_filhos, faixa_etaria, notas, ativo, gerar_agora, ultima_coleta, "
    "criado_em, atualizado_em"
)


def _para_perfil(linha: sqlite3.Row) -> Perfil:
    return Perfil(
        id=linha["id"],
        tipo=linha["tipo"],
        nome=linha["nome"],
        apelido=linha["apelido"],
        email=linha["email"],
        telefone=linha["telefone"],
        empresa=linha["empresa"],
        cargo=linha["cargo"],
        setor=linha["setor"],
        cidade=linha["cidade"],
        naturalidade=linha["naturalidade"],
        linguas=json.loads(linha["linguas"]),
        formacao=linha["formacao"],
        tem_filhos=bool(linha["tem_filhos"]) if linha["tem_filhos"] is not None else None,
        faixa_etaria=linha["faixa_etaria"],
        notas=linha["notas"],
        ativo=bool(linha["ativo"]),
        gerar_agora=bool(linha["gerar_agora"]),
        ultima_coleta=linha["ultima_coleta"],
        criado_em=linha["criado_em"],
        atualizado_em=linha["atualizado_em"],
    )


def obter_usuario(conexao: sqlite3.Connection) -> Perfil | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM perfil WHERE tipo = 'usuario'").fetchone()
    return _para_perfil(linha) if linha is not None else None


def obter_por_id(conexao: sqlite3.Connection, perfil_id: int) -> Perfil | None:
    linha = conexao.execute(f"SELECT {_COLUNAS} FROM perfil WHERE id = ?", (perfil_id,)).fetchone()
    return _para_perfil(linha) if linha is not None else None


def obter_por_telefone_ou_email(
    conexao: sqlite3.Connection, telefone: str | None, email: str | None
) -> Perfil | None:
    if telefone is None and email is None:
        return None
    linha = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil WHERE (telefone IS NOT NULL AND telefone = ?) "
        "OR (email IS NOT NULL AND email = ?)",
        (telefone, email),
    ).fetchone()
    return _para_perfil(linha) if linha is not None else None


def upsert_usuario(conexao: sqlite3.Connection, nome: str, agora: str) -> Perfil:
    existente = obter_usuario(conexao)
    if existente is None:
        conexao.execute(
            "INSERT INTO perfil (tipo, nome, linguas, ativo, gerar_agora, criado_em, atualizado_em) "
            "VALUES ('usuario', ?, '[]', 1, 0, ?, ?)",
            (nome, agora, agora),
        )
        usuario = obter_usuario(conexao)
        assert usuario is not None
        return usuario

    conexao.execute("UPDATE perfil SET nome = ?, atualizado_em = ? WHERE id = ?", (nome, agora, existente.id))
    usuario = obter_usuario(conexao)
    assert usuario is not None
    return usuario


def inserir_ou_atualizar_contato(
    conexao: sqlite3.Connection,
    nome: str,
    telefone: str | None,
    email: str | None,
    empresa: str | None,
    cargo: str | None,
    notas: str | None,
    agora: str,
) -> Perfil:
    existente = obter_por_telefone_ou_email(conexao, telefone, email)
    if existente is None:
        conexao.execute(
            "INSERT INTO perfil (tipo, nome, telefone, email, empresa, cargo, notas, linguas, "
            "ativo, gerar_agora, criado_em, atualizado_em) "
            "VALUES ('contato', ?, ?, ?, ?, ?, ?, '[]', 0, 0, ?, ?)",
            (nome, telefone, email, empresa, cargo, notas, agora, agora),
        )
        novo = obter_por_telefone_ou_email(conexao, telefone, email)
        assert novo is not None
        return novo

    conexao.execute(
        "UPDATE perfil SET nome = ?, empresa = ?, cargo = ?, notas = ?, atualizado_em = ? WHERE id = ?",
        (nome, empresa, cargo, notas, agora, existente.id),
    )
    atualizado = obter_por_telefone_ou_email(conexao, telefone, email)
    assert atualizado is not None
    return atualizado


def inserir_novo_contato(
    conexao: sqlite3.Connection,
    nome: str,
    telefone: str | None,
    email: str | None,
    agora: str,
) -> Perfil:
    """INSERT direto de um novo contato, sem lookup por telefone/email. Usado
    quando o chamador já sabe que é um contato novo (formulário do console),
    inclusive quando não há telefone nem email."""
    cursor = conexao.execute(
        "INSERT INTO perfil (tipo, nome, telefone, email, linguas, ativo, gerar_agora, "
        "criado_em, atualizado_em) VALUES ('contato', ?, ?, ?, '[]', 0, 0, ?, ?)",
        (nome, telefone, email, agora, agora),
    )
    assert cursor.lastrowid is not None
    novo = obter_por_id(conexao, cursor.lastrowid)
    assert novo is not None
    return novo


def ativar(conexao: sqlite3.Connection, perfil_id: int) -> None:
    conexao.execute("UPDATE perfil SET ativo = 1 WHERE id = ?", (perfil_id,))


def contagem_historico_protegido(conexao: sqlite3.Connection, perfil_id: int) -> tuple[int, int]:
    """Devolve (n_fatos, n_consultas) — as duas tabelas cuja imutabilidade
    impede apagar o perfil por caminho direto."""
    (n_fatos,) = conexao.execute("SELECT COUNT(*) FROM fato WHERE perfil_id = ?", (perfil_id,)).fetchone()
    (n_consultas,) = conexao.execute(
        "SELECT COUNT(*) FROM consulta_contato WHERE perfil_id = ?", (perfil_id,)
    ).fetchone()
    return int(n_fatos), int(n_consultas)


def apagar_contato_completo(conexao: sqlite3.Connection, perfil_id: int) -> None:
    """Apaga o perfil e todas as tabelas dependentes sem imutabilidade.
    Chamador é responsável por checar antes que `contagem_historico_protegido`
    devolveu (0, 0). Falha por FK se houver linha remanescente em fato ou
    consulta_contato — o gatilho continua bloqueando DELETE em ambas."""
    conexao.execute("DELETE FROM assunto_contato WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM rede_social WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM perfil_tema WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM fila_extracao WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM descarte_sensivel WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM vetor_perfil WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("DELETE FROM perfil WHERE id = ?", (perfil_id,))


_CAMPOS_MERGE_UNIAO: tuple[str, ...] = (
    "apelido",
    "email",
    "telefone",
    "empresa",
    "cargo",
    "setor",
    "cidade",
    "naturalidade",
    "formacao",
    "tem_filhos",
    "faixa_etaria",
    "notas",
)


def _campos_para_preencher_do_outro(canonico: Perfil, duplicado: Perfil) -> dict[str, object]:
    campos: dict[str, object] = {}
    for campo in _CAMPOS_MERGE_UNIAO:
        valor_canonico = getattr(canonico, campo)
        valor_duplicado = getattr(duplicado, campo)
        if valor_canonico is None and valor_duplicado is not None:
            campos[campo] = valor_duplicado
    if not canonico.linguas and duplicado.linguas:
        campos["linguas"] = list(duplicado.linguas)
    return campos


def unir_contatos(conexao: sqlite3.Connection, canonico_id: int, duplicado_id: int) -> None:
    """Reatribui ao canônico tudo que estava no duplicado e apaga o duplicado.
    Preenche campos vazios do canônico com valores do duplicado, sem sobrescrever.
    Assume que a migração 005 já ajustou os gatilhos de fato e consulta_contato
    para permitir UPDATE de `perfil_id`.

    Não permite unir o perfil de usuário nem unir consigo mesmo."""
    if canonico_id == duplicado_id:
        raise ValueError("canônico e duplicado precisam ser contatos diferentes")

    canonico = obter_por_id(conexao, canonico_id)
    duplicado = obter_por_id(conexao, duplicado_id)
    if canonico is None or duplicado is None:
        raise ValueError("canônico ou duplicado não encontrado")
    if canonico.tipo != "contato" or duplicado.tipo != "contato":
        raise ValueError("unir só se aplica a perfis de contato")

    agora = duplicado.atualizado_em
    campos_para_completar = _campos_para_preencher_do_outro(canonico, duplicado)
    if campos_para_completar:
        atualizar_ficha_manual(conexao, canonico_id, campos_para_completar, agora)

    # perfil_tema: DELETE do duplicado quando canonico já tem o mesmo tema;
    # UPDATE do restante.
    temas_do_canonico = {
        linha["tema_id"]
        for linha in conexao.execute(
            "SELECT tema_id FROM perfil_tema WHERE perfil_id = ?", (canonico_id,)
        ).fetchall()
    }
    for linha in conexao.execute(
        "SELECT tema_id FROM perfil_tema WHERE perfil_id = ?", (duplicado_id,)
    ).fetchall():
        if linha["tema_id"] in temas_do_canonico:
            conexao.execute(
                "DELETE FROM perfil_tema WHERE perfil_id = ? AND tema_id = ?",
                (duplicado_id, linha["tema_id"]),
            )
        else:
            conexao.execute(
                "UPDATE perfil_tema SET perfil_id = ? WHERE perfil_id = ? AND tema_id = ?",
                (canonico_id, duplicado_id, linha["tema_id"]),
            )

    # assunto_contato: UNIQUE (assunto_id, perfil_id, gerado_em). Mesma estratégia.
    ja_no_canonico = {
        (linha["assunto_id"], linha["gerado_em"])
        for linha in conexao.execute(
            "SELECT assunto_id, gerado_em FROM assunto_contato WHERE perfil_id = ?", (canonico_id,)
        ).fetchall()
    }
    for linha in conexao.execute(
        "SELECT id, assunto_id, gerado_em FROM assunto_contato WHERE perfil_id = ?", (duplicado_id,)
    ).fetchall():
        chave = (linha["assunto_id"], linha["gerado_em"])
        if chave in ja_no_canonico:
            conexao.execute("DELETE FROM assunto_contato WHERE id = ?", (linha["id"],))
        else:
            conexao.execute(
                "UPDATE assunto_contato SET perfil_id = ? WHERE id = ?", (canonico_id, linha["id"])
            )

    # Reatribuições simples nas demais tabelas.
    conexao.execute("UPDATE rede_social SET perfil_id = ? WHERE perfil_id = ?", (canonico_id, duplicado_id))
    conexao.execute("UPDATE fila_extracao SET perfil_id = ? WHERE perfil_id = ?", (canonico_id, duplicado_id))
    conexao.execute(
        "UPDATE descarte_sensivel SET perfil_id = ? WHERE perfil_id = ?", (canonico_id, duplicado_id)
    )
    conexao.execute("UPDATE fato SET perfil_id = ? WHERE perfil_id = ?", (canonico_id, duplicado_id))
    conexao.execute(
        "UPDATE consulta_contato SET perfil_id = ? WHERE perfil_id = ?", (canonico_id, duplicado_id)
    )

    # Centróide do canônico pode ficar defasado; deixamos para o próximo cruzar_contato
    # recalcular. Apagamos o do duplicado explicitamente antes do DELETE do perfil.
    conexao.execute("DELETE FROM vetor_perfil WHERE perfil_id = ?", (duplicado_id,))
    conexao.execute("DELETE FROM perfil WHERE id = ?", (duplicado_id,))


def listar_ativos(conexao: sqlite3.Connection) -> list[Perfil]:
    linhas = conexao.execute(
        f"SELECT {_COLUNAS} FROM perfil WHERE ativo = 1 AND tipo = 'contato' ORDER BY nome"
    ).fetchall()
    return [_para_perfil(linha) for linha in linhas]


def listar_todos(conexao: sqlite3.Connection) -> list[Perfil]:
    linhas = conexao.execute(f"SELECT {_COLUNAS} FROM perfil WHERE tipo = 'contato' ORDER BY nome").fetchall()
    return [_para_perfil(linha) for linha in linhas]


_CAMPOS_GUIADOS = (
    "cidade",
    "naturalidade",
    "linguas",
    "formacao",
    "cargo",
    "setor",
    "empresa",
    "tem_filhos",
    "faixa_etaria",
)


def atualizar_campos_guiados(
    conexao: sqlite3.Connection, perfil_id: int, campos: dict[str, object], agora: str
) -> None:
    """Grava, um de cada vez, só os campos guiados presentes em ``campos`` —
    e só se estiverem vazios hoje. Nunca sobrescreve um valor já preenchido
    (o dado que a pessoa digitou é sempre mais confiável do que o inferido).

    ``linguas`` é tratado separado dos demais: a coluna nunca é NULL (default
    '[]' na migração), então "vazio" para ela é `linguas = '[]'`, não
    `IS NULL` como para as colunas escalares.
    """
    for campo, valor in campos.items():
        if campo not in _CAMPOS_GUIADOS or valor is None:
            continue

        if campo == "linguas":
            assert isinstance(valor, list)
            conexao.execute(
                "UPDATE perfil SET linguas = CASE WHEN linguas = '[]' THEN ? ELSE linguas END, "
                "atualizado_em = CASE WHEN linguas = '[]' THEN ? ELSE atualizado_em END "
                "WHERE id = ?",
                (json.dumps(valor, ensure_ascii=False), agora, perfil_id),
            )
            continue

        valor_coluna = int(valor) if campo == "tem_filhos" and isinstance(valor, bool) else valor
        conexao.execute(
            f"UPDATE perfil SET {campo} = COALESCE({campo}, ?), "  # noqa: S608 — campo vem de _CAMPOS_GUIADOS, allowlist fechada acima
            f"atualizado_em = CASE WHEN {campo} IS NULL THEN ? ELSE atualizado_em END "
            "WHERE id = ?",
            (valor_coluna, agora, perfil_id),
        )


_CAMPOS_EDITAVEIS_MANUAL = (
    "nome",
    "apelido",
    "email",
    "telefone",
    "empresa",
    "cargo",
    "setor",
    "cidade",
    "naturalidade",
    "linguas",
    "formacao",
    "tem_filhos",
    "faixa_etaria",
    "notas",
)


def atualizar_ficha_manual(
    conexao: sqlite3.Connection, perfil_id: int, campos: dict[str, object], agora: str
) -> None:
    """Edição manual de campos da ficha do contato pelo usuário no console.

    Sobrescreve o valor atual, mesmo se já preenchido — o oposto de
    ``atualizar_campos_guiados`` (LLM-assistida), que só completa lacunas.
    Chave `linguas` deve vir como lista; `tem_filhos` como bool ou None; os
    demais como str ou None. Chaves fora de ``_CAMPOS_EDITAVEIS_MANUAL`` são
    silenciosamente ignoradas.
    """
    for campo, valor in campos.items():
        if campo not in _CAMPOS_EDITAVEIS_MANUAL:
            continue

        if campo == "linguas":
            assert valor is None or isinstance(valor, list)
            serializado = json.dumps(valor or [], ensure_ascii=False)
            conexao.execute(
                "UPDATE perfil SET linguas = ?, atualizado_em = ? WHERE id = ?",
                (serializado, agora, perfil_id),
            )
            continue

        valor_coluna = int(valor) if campo == "tem_filhos" and isinstance(valor, bool) else valor
        conexao.execute(
            f"UPDATE perfil SET {campo} = ?, atualizado_em = ? WHERE id = ?",  # noqa: S608 — allowlist acima
            (valor_coluna, agora, perfil_id),
        )


def _desserializar(blob: bytes) -> list[float]:
    quantidade = len(blob) // 4
    return list(struct.unpack(f"<{quantidade}f", blob))


def calcular_centroide(
    conexao: sqlite3.Connection, perfil_id: int, peso_nivel: dict[str, float]
) -> list[float] | None:
    linhas = conexao.execute(
        "SELECT pt.peso, pt.nivel, vt.embedding AS embedding FROM perfil_tema pt "
        "JOIN vetor_tema vt ON vt.tema_id = pt.tema_id "
        "WHERE pt.perfil_id = ? AND pt.confirmado = 1",
        (perfil_id,),
    ).fetchall()
    if not linhas:
        return None

    vetores: list[list[float]] = []
    pesos: list[float] = []
    for linha in linhas:
        peso_do_nivel = peso_nivel[linha["nivel"]] if linha["nivel"] is not None else 1.0
        vetores.append(_desserializar(linha["embedding"]))
        pesos.append(linha["peso"] * peso_do_nivel)

    return calcular_media_ponderada(vetores, pesos)


def gravar_centroide(conexao: sqlite3.Connection, perfil_id: int, centroide: list[float]) -> None:
    vetor = sqlite_vec.serialize_float32(centroide)
    conexao.execute("DELETE FROM vetor_perfil WHERE perfil_id = ?", (perfil_id,))
    conexao.execute("INSERT INTO vetor_perfil (perfil_id, centroide) VALUES (?, ?)", (perfil_id, vetor))


def obter_centroide(conexao: sqlite3.Connection, perfil_id: int) -> list[float] | None:
    linha = conexao.execute("SELECT centroide FROM vetor_perfil WHERE perfil_id = ?", (perfil_id,)).fetchone()
    return _desserializar(linha["centroide"]) if linha is not None else None
