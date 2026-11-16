"""Brief 092: pequenos ajustes de texto por inteiro, um teste por item.

1. P-032  descarte de ganchos além do teto fica visível;
2. P-035  contatos filtrados por semelhança de nome antes de montar o prompt do pedido;
3. P-036  frase de autodeclaração ignorada aparece;
4. P-005 / P-015  coleta ou leitura que para por teto avisa quanto ficou de fora;
5. P-020  o cabeçalho da pessoa na rede chega inteiro à confirmação;
6. P-044  campo longo da agenda não derruba a leitura;
7. P-009  mede quantos candidatos passam o gate;
8. P-021  teto de 200 fatos na deduplicação avisa.

Nenhum teste toca a internet, o Ollama, a extensão real ou o banco real."""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from agente_nw.coleta.capturas import busca, leitor, listas, navegador
from agente_nw.coleta.capturas.extrator import RespostaCapturaRedeSocial
from agente_nw.nucleo import localizacao, pedido
from agente_nw.nucleo.database import conexao, migracoes
from agente_nw.nucleo.database.queries import assunto_contato, assuntos, fatos, perfis, redes_sociais
from agente_nw.nucleo.modelos.assunto import Assunto
from agente_nw.nucleo.modelos.assunto_contato import AssuntoContato
from agente_nw.nucleo.modelos.configuracao import TemasUsuarioLimiares
from agente_nw.nucleo.modelos.fato import Fato
from agente_nw.nucleo.modelos.pedido import PedidoExtraido
from agente_nw.nucleo.modelos.redacao import MAXIMO_GANCHOS, Gancho, validar_ganchos
from agente_nw.perfil import agenda_google_csv, inferencia
from tests import coleta_falsa
from tests.llm_falso import ProvenienciaFalsa

AGORA = "2026-11-16T10:00:00+00:00"


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    aberta = conexao.abrir(tmp_path / "teste.db")
    migracoes.aplicar(aberta)
    return aberta


# --------------------------------------------------------------------------------------
# 1. P-032 — o descarte de ganchos aparece
# --------------------------------------------------------------------------------------


def _gancho(numero: int) -> Gancho:
    return Gancho(
        assunto_id=numero,
        titulo=f"Título {numero}",
        noticia=f"Notícia {numero}",
        por_que_para_esta_pessoa="tem relação",
        mensagem=f"Mensagem curta {numero}",
    )


def test_gancho_alem_do_teto_vira_motivo_com_a_conta() -> None:
    ganchos = [_gancho(numero) for numero in range(1, 7)]

    aceitos, motivos = validar_ganchos(ganchos, "proximo", [], set(range(1, 7)), "whatsapp", set())

    assert len(aceitos) == MAXIMO_GANCHOS == 4
    assert [g.assunto_id for g in aceitos] == [1, 2, 3, 4]  # o que é descartado não muda
    assert any("devolveu 6" in motivo and "mostro 4" in motivo for motivo in motivos)


def test_dentro_do_teto_nao_ha_motivo_de_excesso() -> None:
    ganchos = [_gancho(n) for n in range(1, 4)]

    _aceitos, motivos = validar_ganchos(ganchos, "proximo", [], {1, 2, 3}, "whatsapp", set())

    assert motivos == []


# --------------------------------------------------------------------------------------
# 2. P-035 — contatos por semelhança de nome antes do prompt
# --------------------------------------------------------------------------------------


class _ClienteQueGuardaOPrompt(ProvenienciaFalsa):
    def __init__(self) -> None:
        self.prompt = ""

    def gerar_json(
        self, tarefa_nome: str, prompt: str, esquema: type[Any], *, versao_prompt: str | None = None
    ) -> Any:
        self.prompt = prompt
        return PedidoExtraido.model_validate(
            {
                "pessoa_nome": "Beatriz Lemos",
                "pessoa_pistas": {},
                "objetivo": "retomar",
                "objetivo_texto": "retomar contato",
                "meio": "whatsapp",
                "registro": "proximo",
                "assunto_principal": "viagens",
                "interessa": [],
                "evitar": [],
                "termos_busca": ["viagens"],
                "confianca": 0.9,
            }
        )

    def embeddar(self, textos: list[str]) -> list[list[float]]:
        return [[0.0] for _ in textos]


def test_contato_de_nome_parecido_fora_dos_mais_recentes_chega_ao_prompt(conn: sqlite3.Connection) -> None:
    perfis.inserir_novo_contato(conn, "Beatriz Lemos", None, None, "2026-01-01T00:00:00+00:00")
    for numero in range(60):  # 60 contatos mais novos empurram a Beatriz para fora dos 50 mais recentes
        perfis.inserir_novo_contato(
            conn, f"Pessoa{numero:02d} Silva", None, None, f"2026-02-{1 + numero % 28:02d}T00:00:00+00:00"
        )
    conn.commit()
    recentes = [c.nome for c in perfis.listar_contatos_recentes(conn, 50)]
    assert "Beatriz Lemos" not in recentes  # sem o filtro, ela não chegaria

    cliente = _ClienteQueGuardaOPrompt()
    pedido.extrair(cliente, conn, "quero retomar contato com a Beatriz, falar de viagens")

    assert "Beatriz Lemos" in cliente.prompt


def test_todos_os_contatos_parecidos_chegam_ao_prompt_mesmo_passando_do_teto(
    conn: sqlite3.Connection,
) -> None:
    for numero in range(55):
        perfis.inserir_novo_contato(
            conn, f"Marcos Sobrenome{numero:02d}", None, None, f"2026-03-{1 + numero % 28:02d}T00:00:00+00:00"
        )
    conn.commit()

    cliente = _ClienteQueGuardaOPrompt()
    pedido.extrair(cliente, conn, "mensagem para o Marcos")

    assert sum(1 for numero in range(55) if f"Marcos Sobrenome{numero:02d}" in cliente.prompt) == 55


# --------------------------------------------------------------------------------------
# 3. P-036 — a frase ignorada aparece
# --------------------------------------------------------------------------------------


def test_frase_sem_padrao_e_devolvida_e_avisada(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None
    avisos: list[str] = []

    ignoradas = inferencia.aplicar_declaracoes(
        conn,
        ProvenienciaFalsa(),  # sem `embeddar`: a positiva também é ignorada, a frase abaixo não casa
        usuario.id,
        ["o céu amanheceu estranho hoje"],
        AGORA,
        TemasUsuarioLimiares(),
        avisar=avisos.append,
    )

    assert ignoradas == ["o céu amanheceu estranho hoje"]
    assert len(avisos) == 1 and "o céu amanheceu estranho hoje" in avisos[0]


def test_frase_com_padrao_nao_e_ignorada(conn: sqlite3.Connection) -> None:
    usuario = perfis.upsert_usuario(conn, "Rafael", AGORA)
    assert usuario.id is not None

    ignoradas = inferencia.aplicar_declaracoes(
        conn, ProvenienciaFalsa(), usuario.id, ["não me interessa futebol"], AGORA, TemasUsuarioLimiares()
    )

    assert ignoradas == []


# --------------------------------------------------------------------------------------
# 4. P-005 / P-015 — o teto avisa quanto ficou de fora
# --------------------------------------------------------------------------------------


def test_coleta_que_para_por_candidatos_suficientes_conta_as_buscas_que_ficaram_de_fora(
    tmp_path: Path,
) -> None:
    rede = coleta_falsa.RedeFalsa(por_busca=6)
    conn = coleta_falsa.banco(tmp_path)

    resumo = coleta_falsa.coletar(rede, conn, tmp_path, ["a1", "b2", "c3", "d4"], candidatos_suficientes=10)

    assert resumo.termos_nao_buscados == 2


def test_coleta_que_rodou_todas_as_buscas_nao_avisa_de_teto(tmp_path: Path) -> None:
    rede = coleta_falsa.RedeFalsa(por_busca=1)
    conn = coleta_falsa.banco(tmp_path)

    resumo = coleta_falsa.coletar(rede, conn, tmp_path, ["a1", "b2"], candidatos_suficientes=10)

    assert resumo.termos_nao_buscados == 0


@dataclass
class _PaginaQueRola:
    """Cada rolagem traz um bloco novo (`blocos_por_rolagem`) ou nenhum."""

    blocos: list[str]
    rolagens_com_novidade: int
    rolagens: int = 0
    estados: list[tuple[str, str]] = field(default_factory=list)

    def ir_para(self, url: str) -> None:
        pass

    def _texto(self) -> str:
        visiveis = self.blocos[: 1 + min(self.rolagens, self.rolagens_com_novidade)]
        return "feed\n\n" + "\n\n".join(visiveis) + "\n\n" + "conteúdo variado suficiente para passar. " * 30

    def estado(self) -> tuple[str, str]:
        return ("https://exemplo.com/feed", self._texto())

    def rolar(self) -> None:
        self.rolagens += 1

    def fechar(self) -> None:
        pass


def _blocos(total: int) -> list[str]:
    return [
        f"Publicação número {n} com texto longo o bastante para valer como bloco extraído."
        for n in range(total)
    ]


def test_leitura_cuja_ultima_rolagem_ainda_trouxe_texto_novo_marca_o_teto() -> None:
    pagina = _PaginaQueRola(_blocos(10), rolagens_com_novidade=99)

    captura = navegador.ler(
        pagina, "https://exemplo.com/feed", dorme=lambda _s: None, aleatorio=random.Random(0), max_rolagens=3
    )

    assert captura.parou_no_teto_de_rolagens is True
    assert captura.teto_de_rolagens == 3


def test_leitura_que_acabou_antes_do_teto_nao_marca() -> None:
    pagina = _PaginaQueRola(_blocos(10), rolagens_com_novidade=1)

    captura = navegador.ler(
        pagina, "https://exemplo.com/feed", dorme=lambda _s: None, aleatorio=random.Random(0), max_rolagens=4
    )

    assert captura.parou_no_teto_de_rolagens is False


class _ClienteExtracao:
    def num_ctx(self, tarefa_nome: str) -> int:
        return 4096

    def gerar_json(
        self, tarefa: str, prompt: str, esquema: type[BaseModel], versao_prompt: str | None = None
    ) -> Any:
        return RespostaCapturaRedeSocial(descartar=True)


def test_leitor_avisa_teto_de_rolagens_e_blocos_que_ficaram_de_fora(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    contato = perfis.inserir_novo_contato(conn, "Beto", None, None, AGORA)
    assert contato.id is not None
    redes_sociais.inserir(conn, contato.id, "linkedin", "https://linkedin.com/in/beto", AGORA)
    conn.commit()
    avisos: list[str] = []

    resumo = leitor.ler_redes_sociais_do_contato(
        _ClienteExtracao(),
        conn,
        contato.id,
        lambda _pasta: _PaginaQueRola(_blocos(12), rolagens_com_novidade=99),  # type: ignore[arg-type,return-value]
        tmp_path / "navegador",
        AGORA,
        dorme=lambda _s: None,
        max_rolagens=5,
        maximo_blocos=1,  # examina no máximo 4 blocos; os outros ficam de fora
        avisar=avisos.append,
    )

    textos = " ".join(resumo.avisos)
    assert "5 rolagens" in textos
    assert "ficaram de fora" in textos
    assert any("5 rolagens" in aviso for aviso in avisos)


def test_lista_truncada_chega_ao_resultado_da_atualizacao_com_o_motivo(
    conn: sqlite3.Connection,
) -> None:
    resultado = localizacao.ResultadoAtualizacao(
        rede="instagram", lida=True, usou_cache=False, total=2000, truncada=True
    )

    assert "2000" in localizacao.aviso_de_lista_truncada(resultado)
    assert "instagram" in localizacao.aviso_de_lista_truncada(resultado)


# --------------------------------------------------------------------------------------
# 5. P-020 — o cabeçalho inteiro
# --------------------------------------------------------------------------------------


def test_cabecalho_da_lista_traz_todas_as_linhas_da_rede() -> None:
    texto = "Ana Souza\nEngenheira de dados\nSão Paulo\nAcme S.A.\nEx-Banco X\nMentora voluntária"

    (entrada,) = listas.parse_links("linkedin", [("https://www.linkedin.com/in/anasouza", texto)])

    assert (
        entrada.cabecalho == "Engenheira de dados · São Paulo · Acme S.A. · Ex-Banco X · Mentora voluntária"
    )


def test_cabecalho_da_busca_geral_traz_todas_as_linhas_da_rede() -> None:
    texto = "Ana Souza\nlinha 1\nlinha 2\nlinha 3\nlinha 4\nlinha 5\nlinha 6"

    (candidato,) = busca._filtrar_candidatos("linkedin", [("https://www.linkedin.com/in/anasouza", texto)])

    assert candidato.descricao == "linha 1 · linha 2 · linha 3 · linha 4 · linha 5 · linha 6"


# --------------------------------------------------------------------------------------
# 6. P-044 — campo longo da agenda
# --------------------------------------------------------------------------------------


def test_agenda_com_campo_de_300000_caracteres_e_lida(tmp_path: Path) -> None:
    arquivo = tmp_path / "contatos.csv"
    notas = "x" * 300_000
    arquivo.write_text(f"Name,Notes\nAna,{notas}\nBeto,curta\n", encoding="utf-8")

    contatos = agenda_google_csv.ler_contatos(arquivo)

    assert [c.nome for c in contatos] == ["Ana", "Beto"]
    assert contatos[0].notas == notas


# --------------------------------------------------------------------------------------
# 7. P-009 — quantos dos candidatos passam o gate
# --------------------------------------------------------------------------------------


def _assunto(conn: sqlite3.Connection) -> int:
    return assuntos.inserir(conn, Assunto(primeiro_visto=AGORA, ultimo_visto=AGORA, n_itens=1, status="novo"))


def test_medicao_do_gate_conta_candidatos_e_os_que_passaram(conn: sqlite3.Connection) -> None:
    contato = perfis.inserir_novo_contato(conn, "Ana", None, None, AGORA)
    assert contato.id is not None
    for numero in range(10):
        passou = numero < 3
        assunto_contato.inserir(
            conn,
            AssuntoContato(
                assunto_id=_assunto(conn),
                perfil_id=contato.id,
                gerado_em="2026-11-16",
                tipo="conector" if passou else "fora_do_dominio",
                aderencia_contato=0.5,
                aderencia_usuario=0.5,
                conversavel=0.5,
                score=50.0,
                status="novo" if passou else "descartado",
            ),
        )
    conn.commit()

    medicao = assunto_contato.medir_passagem_do_gate(conn)

    assert (medicao.rodadas, medicao.candidatos, medicao.passaram) == (1, 10, 3)


def test_medicao_do_gate_sem_dados_devolve_zeros(conn: sqlite3.Connection) -> None:
    medicao = assunto_contato.medir_passagem_do_gate(conn)

    assert (medicao.rodadas, medicao.candidatos, medicao.passaram) == (0, 0, 0)


# --------------------------------------------------------------------------------------
# 8. P-021 — teto de 200 na deduplicação
# --------------------------------------------------------------------------------------


def _opcao() -> localizacao.Opcao:
    return localizacao.Opcao(
        rede="instagram",
        nome="Ana",
        cabecalho="Engenheira",
        link="https://www.instagram.com/ana",
        fonte="lista",
    )


def _contato_com_fatos(conn: sqlite3.Connection, quantos: int) -> int:
    contato = perfis.inserir_novo_contato(conn, "Ana", None, None, AGORA)
    assert contato.id is not None
    for numero in range(quantos):
        fatos.inserir(
            conn,
            Fato(
                perfil_id=contato.id, tipo="outro", conteudo=f"fato {numero}", fonte="x", registrado_em=AGORA
            ),
        )
    conn.commit()
    return contato.id


def test_contato_com_200_fatos_avisa_que_a_deduplicacao_olhou_so_os_200_mais_recentes(
    conn: sqlite3.Connection,
) -> None:
    perfil_id = _contato_com_fatos(conn, 200)
    avisos: list[str] = []

    localizacao.confirmar(conn, perfil_id, _opcao(), AGORA, avisar=avisos.append)

    assert len(avisos) == 1 and "200" in avisos[0]


def test_contato_com_poucos_fatos_nao_avisa(conn: sqlite3.Connection) -> None:
    perfil_id = _contato_com_fatos(conn, 5)
    avisos: list[str] = []

    localizacao.confirmar(conn, perfil_id, _opcao(), AGORA, avisar=avisos.append)

    assert avisos == []
