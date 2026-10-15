from __future__ import annotations

from pathlib import Path

import tests.test_cruzamento_por_consulta as base
from agente_nw.nucleo.database.queries import assunto_contato, fatos
from agente_nw.nucleo.modelos.configuracao import Limiares
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.relevancia.cruzamento import cruzar_contato_por_consulta

limiares = base.limiares  # a fixture do outro módulo, reaproveitada


def test_todos_abaixo_do_piso_avisa_em_vez_de_entregar(tmp_path: Path, limiares: Limiares) -> None:
    conn = base._abrir(tmp_path, "caso_sem_objetivo")
    perfil_id = base._contato(conn)
    # O que o contato publica casa com o assunto, mas o assunto não tem relação com o pedido.
    conteudo = "fato sobre manifestação"
    fatos.inserir(conn, Fato(perfil_id=perfil_id, tipo="post", conteudo=conteudo, registrado_em=base.AGORA))
    conn.commit()
    fora = base._assunto(conn, "Apoiadores de Lula ocupam Copacabana", base._vetor(0.0, 1.0))

    resumo = cruzar_contato_por_consulta(
        base._ClienteFalso(),
        conn,
        perfil_id,
        base._contexto(),
        base.CENTROIDE_CONSULTA,
        limiares,
        base.AGORA,
    )

    registros = assunto_contato.listar_do_dia(conn, perfil_id, base.DATA)
    registro = {r.assunto_id: r for r in registros}[fora]
    assert resumo.sem_assunto is True
    assert resumo.motivo == "nenhum candidato passou do piso"
    assert registro.status == "descartado"
    assert registro.motivo == "pouca relação com o pedido"
