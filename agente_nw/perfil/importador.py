from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime

from agente_nw.nucleo.database.queries import fila_extracao
from agente_nw.nucleo.database.queries import perfil_tema as queries_perfil_tema
from agente_nw.nucleo.database.queries import perfis as queries_perfis
from agente_nw.nucleo.database.queries import temas as queries_temas
from agente_nw.perfil.normalizacao import telefone_e164

PESO_TAG_IMPORTADA = 3


@dataclass
class ContatoBruto:
    nome: str
    telefone: str | None = None
    email: str | None = None
    empresa: str | None = None
    cargo: str | None = None
    notas: str | None = None
    marcadores: list[str] = field(default_factory=list)


@dataclass
class ResumoImportacao:
    contatos_lidos: int = 0
    contatos_ignorados: int = 0
    perfis_criados: int = 0
    perfis_atualizados: int = 0
    tags_vinculadas: int = 0
    notas_enfileiradas: int = 0


def _vincular_marcador(
    conexao: sqlite3.Connection,
    perfil_id: int,
    marcador: str,
    vinculados_existentes: dict[int, bool],
    agora: str,
) -> bool:
    marcador_limpo = marcador.strip()
    if not marcador_limpo:
        return False

    tema = queries_temas.obter_por_nome(conexao, marcador_limpo)
    if tema is None:
        tema = queries_temas.obter_ou_criar(conexao, marcador_limpo, marcador_limpo, [], agora)
    assert tema.id is not None

    # Um vínculo já confirmado pelo usuário (via `agente_nw confirmar-tags`) nunca é
    # tocado de novo aqui — `perfil_tema.vincular` reseta `confirmado` para False em
    # cada chamada (é um upsert completo), e reimportar a agenda não pode desfazer
    # uma confirmação que já aconteceu.
    if vinculados_existentes.get(tema.id):
        return False

    queries_perfil_tema.vincular(
        conexao, perfil_id, tema.id, PESO_TAG_IMPORTADA, "importada", None, False, agora
    )
    return True


def importar(contatos: list[ContatoBruto], conexao: sqlite3.Connection) -> ResumoImportacao:
    resumo = ResumoImportacao()

    for bruto in contatos:
        resumo.contatos_lidos += 1
        agora = datetime.now(UTC).isoformat()

        telefone_normalizado = telefone_e164(bruto.telefone)
        if not bruto.nome.strip() or (telefone_normalizado is None and not bruto.email):
            resumo.contatos_ignorados += 1
            continue

        existente_antes = queries_perfis.obter_por_telefone_ou_email(
            conexao, telefone_normalizado, bruto.email
        )
        perfil = queries_perfis.inserir_ou_atualizar_contato(
            conexao,
            bruto.nome.strip(),
            telefone_normalizado,
            bruto.email,
            bruto.empresa,
            bruto.cargo,
            bruto.notas,
            agora,
        )
        assert perfil.id is not None

        if existente_antes is None:
            resumo.perfis_criados += 1
        else:
            resumo.perfis_atualizados += 1

        vinculados_existentes = {
            pt.tema_id: pt.confirmado for pt in queries_perfil_tema.listar_por_perfil(conexao, perfil.id)
        }
        for marcador in bruto.marcadores:
            if _vincular_marcador(conexao, perfil.id, marcador, vinculados_existentes, agora):
                resumo.tags_vinculadas += 1

        if bruto.notas and bruto.notas.strip():
            fila_extracao.inserir(conexao, perfil.id, bruto.notas, "notas_agenda", agora)
            resumo.notas_enfileiradas += 1

        conexao.commit()

    return resumo
