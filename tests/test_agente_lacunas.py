from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "agente_lacunas.py"

PLAN = """# PLAN.md — estado vivo

## Resumo

**Em execução:** nenhum.

## Doing

(nenhum)

## Backlog

- 040 · perfil do usuário inferido · não iniciado · — · 2026-10-11
- 041 · continuidade de conversa · não iniciado · — · 2026-10-11

## Done — últimos 30 dias

- 055 · documentos canônicos · concluído · `acb2a67` · 2026-10-25

## Pendências de Sidarta

- Teste real das dez frases do brief 036.

## Decisões em aberto

| # | Decisão | Situação |
|---|---|---|
| 1 | Aceitar o risco no LinkedIn | Aberta |

## Dívidas conhecidas

2. **`temas.yaml` ainda tem os dois temas fictícios.**
4. **Purga de `item.texto` não tem dono.**

---

## Armadilhas já identificadas — não redescobrir

1. **`num_ctx` padrão trunca em silêncio.**
"""

RELATORIO = """# DOC 099 — teste

Texto solto.

## Lacunas

| # | Lacuna | Destino | Impacto |
|---|---|---|---|
| 1 | Falta medir o tempo do gate | backlog | nice |
| 2 | Testar com pessoa real no console | pendência | bloqueia |
| 3 | O parser ignora data inválida | dívida | degrada |
| 4 | Escolhi `X` no lugar de `Y`; Sidarta precisa saber | decisão | degrada |
| 5 | Só registro no relatório | nenhum | nice |
"""


@pytest.fixture
def raiz(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "PLAN.md").write_text(PLAN)
    (tmp_path / "docs" / "docs" / "doc_099_teste_2026-10-25.md").write_text(RELATORIO)
    return tmp_path


def _rodar(raiz: Path, numero: str = "099") -> str:
    saida = subprocess.run(
        [sys.executable, str(SCRIPT), numero, "--raiz", str(raiz), "--data", "2026-10-26"],
        capture_output=True,
        text=True,
        check=True,
    )
    return saida.stdout


def _plan(raiz: Path) -> str:
    return (raiz / "docs" / "PLAN.md").read_text()


def _secao(plano: str, titulo: str) -> str:
    inicio = plano.index(f"## {titulo}")
    resto = plano[inicio + 1 :]
    fim = len(resto)
    for marca in ("\n## ", "\n---"):
        achado = resto.find(marca)
        if achado != -1:
            fim = min(fim, achado)
    return resto[:fim]


def test_cada_destino_vai_para_a_secao_certa(raiz: Path) -> None:
    saida = _rodar(raiz)

    plano = _plan(raiz)
    assert "- [099-1] Falta medir o tempo do gate · nice · 2026-10-26" in _secao(plano, "Backlog")
    assert "- [099-2] Testar com pessoa real no console · bloqueia · 2026-10-26" in _secao(
        plano, "Pendências de Sidarta"
    )
    assert "- [099-3] O parser ignora data inválida · degrada · 2026-10-26" in _secao(
        plano, "Dívidas conhecidas"
    )
    assert "- [099-4] Escolhi `X` no lugar de `Y`; Sidarta precisa saber · degrada · 2026-10-26" in _secao(
        plano, "Decisões em aberto"
    )
    assert "099-5" not in plano
    assert saida.strip() == "lacunas do 099: 1 no Backlog, 1 em Pendências, 1 em Dívidas, 1 em Decisões"


def test_rodar_duas_vezes_da_o_mesmo_plan(raiz: Path) -> None:
    _rodar(raiz)
    uma_vez = _plan(raiz)

    segunda = _rodar(raiz)

    assert _plan(raiz) == uma_vez
    assert segunda.strip() == "lacunas do 099: 0 no Backlog, 0 em Pendências, 0 em Dívidas, 0 em Decisões"


def test_destino_nenhum_nao_muda_o_plan(raiz: Path) -> None:
    (raiz / "docs" / "docs" / "doc_099_teste_2026-10-25.md").write_text(
        RELATORIO.split("| 1 |")[0] + "| 1 | Só no relatório | nenhum | nice |\n"
    )

    saida = _rodar(raiz)

    assert _plan(raiz) == PLAN
    assert saida.strip() == "lacunas do 099: 0 no Backlog, 0 em Pendências, 0 em Dívidas, 0 em Decisões"


def test_as_outras_linhas_do_plan_nao_mudam(raiz: Path) -> None:
    _rodar(raiz)

    antes = PLAN.splitlines()
    depois = [linha for linha in _plan(raiz).splitlines() if "[099-" not in linha]
    assert depois == antes


@pytest.mark.parametrize(
    "conteudo",
    [
        "# DOC 099\n\nSem seção nenhuma.\n",
        "# DOC 099\n\n## Lacunas\n\nTexto solto, sem tabela.\n",
        "# DOC 099\n\n## Lacunas\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
        "# DOC 099\n\n## Lacunas\n\n| # | Lacuna | Destino | Impacto |\n"
        "|---|---|---|---|\n| 1 | x | talvez | nice |\n",
    ],
)
def test_relatorio_sem_tabela_no_formato_avisa_e_deixa_o_plan_intacto(raiz: Path, conteudo: str) -> None:
    (raiz / "docs" / "docs" / "doc_099_teste_2026-10-25.md").write_text(conteudo)

    saida = _rodar(raiz)

    assert saida.strip() == "relatório sem tabela de lacunas no formato"
    assert _plan(raiz) == PLAN


def test_sem_lacunas(raiz: Path) -> None:
    (raiz / "docs" / "docs" / "doc_099_teste_2026-10-25.md").write_text(
        "# DOC 099\n\n## Lacunas\n\nSem lacunas.\n"
    )

    saida = _rodar(raiz)

    assert saida.strip() == "sem lacunas"
    assert _plan(raiz) == PLAN


def test_secao_que_so_tem_o_marcador_nenhum_troca_o_marcador_pela_linha(raiz: Path) -> None:
    vazio = PLAN.replace("- Teste real das dez frases do brief 036.", "(nenhum)")
    (raiz / "docs" / "PLAN.md").write_text(vazio)

    _rodar(raiz)

    secao = _secao(_plan(raiz), "Pendências de Sidarta")
    assert "(nenhum)" not in secao
    assert "- [099-2] Testar com pessoa real no console · bloqueia · 2026-10-26" in secao
