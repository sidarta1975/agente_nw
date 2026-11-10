"""`scripts/verificar_auditoria_texto.py` (brief 079): confere que o relatório de auditoria de
"texto por inteiro" cobre todo arquivo do universo uma vez, que nada foi certificado sem leitura
registrada, que cada ocorrência da varredura mecânica tem destino e que nenhuma exceção foi dada
por quem não pode. Tudo em árvores sintéticas em `tmp_path`: nenhum teste lê o repositório real."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "verificar_auditoria_texto.py"

ESTADO_ABERTO = "AGUARDANDO DECISÃO DE SIDARTA"

EXCECOES_VAZIO = """\
# Exceções aprovadas ao princípio do texto por inteiro

| Ponto | Arquivo:função | O que é cortado | Justificativa aprovada | Aprovado por Sidarta em |
|---|---|---|---|---|
"""


def _arvore(raiz: Path, arquivos: dict[str, str]) -> None:
    for caminho_relativo, conteudo in arquivos.items():
        caminho = raiz / caminho_relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")


def _linhas(raiz: Path, caminho_relativo: str) -> int:
    return len((raiz / caminho_relativo).read_text(encoding="utf-8").splitlines())


def _linha_tabela(arquivo: str, total: int, resultado: str, evidencia: str, ponto: str = "—") -> str:
    return f"| {arquivo} | {total}/{total} | {resultado} | {evidencia} | {ponto} |"


def _ponto(
    identificador: str,
    local: str,
    classe: str,
    estado: str = ESTADO_ABERTO,
    sem: str = "",
) -> str:
    campos = {
        "Classe": classe,
        "O que é cortado e quanto": "os 200 primeiros caracteres",
        "Qual decisão do produto depende desse corte": "prompt `qualificar`",
        "Commit que introduziu": "abc1234",
        "Justificativa existente": "nenhuma",
        "Proposta do executor": "manter; corrigir custa um brief",
        "Estado": estado,
    }
    if sem:
        campos.pop(sem)
    linhas = [f"#### {identificador} — {local} — `funcao`"]
    linhas.extend(f"- {rotulo}: {valor}" for rotulo, valor in campos.items())
    return "\n".join(linhas)


def _relatorio(tabela: list[str], pontos: list[str] | None = None, apendice: list[str] | None = None) -> str:
    return "\n".join(
        [
            "# DOC 079 — auditoria",
            "",
            "## 3. Pontos que cortam o texto — aguardando decisão",
            "",
            *(pontos or []),
            "",
            "## 6. Certificação por arquivo",
            "",
            "| Arquivo | Linhas lidas/total | Resultado | Evidência | Ponto |",
            "|---|---|---|---|---|",
            *tabela,
            "",
            "## Apêndice A — varredura mecânica",
            "",
            *(apendice or []),
            "",
        ]
    )


def _rodar(raiz: Path, relatorio: str, excecoes: str = EXCECOES_VAZIO) -> subprocess.CompletedProcess[str]:
    (raiz / "docs" / "docs").mkdir(parents=True, exist_ok=True)
    (raiz / "docs" / "docs" / "doc_079_auditoria_2026-11-07.md").write_text(relatorio, encoding="utf-8")
    (raiz / "docs" / "EXCECOES_TEXTO_INTEGRAL.md").write_text(excecoes, encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(raiz)], capture_output=True, text=True)


@pytest.fixture
def arvore(tmp_path: Path) -> Path:
    """Universo mínimo e limpo: nada nestes arquivos casa com a varredura mecânica."""
    _arvore(
        tmp_path,
        {
            "agente_nw/alfa.py": "def alfa(texto: str) -> str:\n    return texto\n",
            "agente_nw/beta.py": "VALOR = 1\n",
            "extensao/gama.js": "const x = 1;\n",
            "config/limites.yaml": "chave: valor\n",
            "tests/test_alfa.py": "def test_alfa() -> None:\n    assert True\n",
        },
    )
    return tmp_path


def _tabela_limpa(raiz: Path) -> list[str]:
    return [
        _linha_tabela(
            "agente_nw/alfa.py", _linhas(raiz, "agente_nw/alfa.py"), "CERTIFICADO", "devolve o texto"
        ),
        _linha_tabela(
            "agente_nw/beta.py", _linhas(raiz, "agente_nw/beta.py"), "CERTIFICADO", "só uma constante"
        ),
        _linha_tabela(
            "extensao/gama.js", _linhas(raiz, "extensao/gama.js"), "CERTIFICADO", "só uma constante"
        ),
        _linha_tabela(
            "config/limites.yaml", _linhas(raiz, "config/limites.yaml"), "CERTIFICADO", "sem chave de limite"
        ),
        _linha_tabela(
            "tests/test_alfa.py", _linhas(raiz, "tests/test_alfa.py"), "CERTIFICADO", "só exercita"
        ),
    ]


# --------------------------------------------------------------------------------------
# 1. Relatório completo e correto
# --------------------------------------------------------------------------------------


def test_relatorio_completo_e_correto_devolve_zero(arvore: Path) -> None:
    resultado = _rodar(arvore, _relatorio(_tabela_limpa(arvore)))

    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
    assert "5 arquivos" in resultado.stdout
    assert "5 certificados" in resultado.stdout


# --------------------------------------------------------------------------------------
# 2 e 3. Arquivo ausente e arquivo repetido
# --------------------------------------------------------------------------------------


def test_arquivo_do_universo_ausente_do_relatorio_falha_citando_o_arquivo(arvore: Path) -> None:
    tabela = [linha for linha in _tabela_limpa(arvore) if "beta.py" not in linha]

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "agente_nw/beta.py" in resultado.stdout


def test_arquivo_repetido_na_tabela_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela.append(tabela[0])

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "mais de uma vez" in resultado.stdout
    assert "agente_nw/alfa.py" in resultado.stdout


def test_arquivo_fora_do_universo_na_tabela_falha(arvore: Path) -> None:
    tabela = [*_tabela_limpa(arvore), _linha_tabela("agente_nw/inexistente.py", 3, "CERTIFICADO", "nada")]

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "agente_nw/inexistente.py" in resultado.stdout


# --------------------------------------------------------------------------------------
# 4. Contagem de linhas errada
# --------------------------------------------------------------------------------------


def test_contagem_de_linhas_errada_falha_citando_o_arquivo(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela("agente_nw/alfa.py", 99, "CERTIFICADO", "devolve o texto")

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "agente_nw/alfa.py" in resultado.stdout
    assert "99" in resultado.stdout


def test_lidas_menor_que_o_total_sem_nao_conferido_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    total = _linhas(arvore, "agente_nw/alfa.py")
    tabela[0] = f"| agente_nw/alfa.py | 1/{total} | CERTIFICADO | devolve o texto | — |"

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "agente_nw/alfa.py" in resultado.stdout


# --------------------------------------------------------------------------------------
# 5. CERTIFICADO sem evidência
# --------------------------------------------------------------------------------------


def test_certificado_sem_evidencia_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela("agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CERTIFICADO", "—")

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "sem evidência" in resultado.stdout


# --------------------------------------------------------------------------------------
# 6. CORTA sem o ponto correspondente
# --------------------------------------------------------------------------------------


def test_corta_sem_o_ponto_na_secao_3_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "P-001" in resultado.stdout


def test_corta_com_o_ponto_na_secao_3_passa(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )
    pontos = [_ponto("P-001", "agente_nw/alfa.py:2", "T")]

    resultado = _rodar(arvore, _relatorio(tabela, pontos))

    assert resultado.returncode == 0, resultado.stdout
    assert "1 ponto(s) aguardando" in resultado.stdout


def test_corta_sem_nenhum_ponto_citado_na_linha_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "—"
    )

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert "sem ponto" in resultado.stdout


# --------------------------------------------------------------------------------------
# 7. Ponto sem campo obrigatório
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "campo",
    [
        "Classe",
        "O que é cortado e quanto",
        "Qual decisão do produto depende desse corte",
        "Commit que introduziu",
        "Justificativa existente",
        "Proposta do executor",
        "Estado",
    ],
)
def test_ponto_sem_campo_obrigatorio_falha(campo: str, arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )
    pontos = [_ponto("P-001", "agente_nw/alfa.py:2", "T", sem=campo)]

    resultado = _rodar(arvore, _relatorio(tabela, pontos))

    assert resultado.returncode == 1
    assert "P-001" in resultado.stdout


def test_ponto_sem_arquivo_e_linha_no_titulo_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )
    pontos = [_ponto("P-001", "agente_nw/alfa.py", "T")]  # sem `:linha`

    resultado = _rodar(arvore, _relatorio(tabela, pontos))

    assert resultado.returncode == 1
    assert "P-001" in resultado.stdout


# --------------------------------------------------------------------------------------
# 8. Exceção aprovada só com linha no registro
# --------------------------------------------------------------------------------------


def test_excecao_aprovada_sem_linha_no_registro_falha(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )
    pontos = [_ponto("P-001", "agente_nw/alfa.py:2", "T", estado="EXCEÇÃO APROVADA")]

    resultado = _rodar(arvore, _relatorio(tabela, pontos))

    assert resultado.returncode == 1
    assert "P-001" in resultado.stdout
    assert "registro de exceções" in resultado.stdout


def test_excecao_aprovada_com_linha_no_registro_passa(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    tabela[0] = _linha_tabela(
        "agente_nw/alfa.py", _linhas(arvore, "agente_nw/alfa.py"), "CORTA", "corta o texto", "P-001"
    )
    pontos = [_ponto("P-001", "agente_nw/alfa.py:2", "T", estado="EXCEÇÃO APROVADA")]
    excecoes = EXCECOES_VAZIO + (
        "| P-001 | agente_nw/alfa.py:alfa | 200 caracteres | amostra basta | "
        "Aprovado por Sidarta em 2026-11-08 |\n"
    )

    resultado = _rodar(arvore, _relatorio(tabela, pontos), excecoes)

    assert resultado.returncode == 0, resultado.stdout
    assert "0 ponto(s) aguardando" in resultado.stdout


# --------------------------------------------------------------------------------------
# 9 e 11. A varredura mecânica não deixa escapar
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("arquivo", "linha_de_codigo"),
    [
        ("agente_nw/padrao.py", "resumo = texto[:200]"),
        ("agente_nw/padrao.py", "ultimos = itens[-5:]"),
        ("agente_nw/padrao.py", "faixa = texto[10:20]"),
        ("agente_nw/padrao.py", "cabeca = linhas[2:]"),
        ("agente_nw/padrao.py", "corpo = {'max_chars': 300}"),
        ("agente_nw/padrao.py", "opcoes = {'num_ctx': 2048}"),
        ("agente_nw/padrao.py", "corpo = {'num_predict': 256}"),
        ("agente_nw/padrao.py", "def truncar(texto: str) -> str: return texto"),
        ("agente_nw/padrao.py", "def cortar_por_tamanho(x: int) -> int: return x"),
        ("agente_nw/padrao.py", "trecho = textwrap.shorten(texto, 80)"),
        ("agente_nw/padrao.py", "primeiros = list(itertools.islice(itens, 5))"),
        ("agente_nw/padrao.py", "linhas = cursor.fetchmany(10)"),
        ("agente_nw/padrao.py", 'SQL = "SELECT texto FROM item LIMIT 5"'),
        ("agente_nw/padrao.py", "escolhidos = random.sample(pares, 35)"),
        ("agente_nw/padrao.py", "primeira = corpo.splitlines()[0]"),
        ("agente_nw/padrao.py", "corpo = trafilatura.extract(pagina)"),
        ("agente_nw/padrao.py", "pedaco = arquivo.read(1024)"),
        ("agente_nw/padrao.py", "meses = chaves[:meses_extraidos]"),
        ("extensao/padrao.js", "const curto = texto.slice(0, maximo);"),
        ("extensao/padrao.js", "const curto = texto.substring(0, 100);"),
        ("extensao/padrao.js", "const curto = texto.substr(0, 100);"),
        ("extensao/padrao.js", "const texto = document.body.innerText;"),
        ("extensao/padrao.js", "const texto = el.textContent;"),
        ("config/padrao.yaml", "maximo_entradas: 2000"),
        ("config/padrao.yaml", "limite_de_blocos: 10"),
    ],
)
def test_ocorrencia_da_varredura_sem_destino_falha(arquivo: str, linha_de_codigo: str, arvore: Path) -> None:
    """Cada padrão do passo 3 do brief é detectado: certificar o arquivo sem citar a linha falha."""
    _arvore(arvore, {arquivo: f"{linha_de_codigo}\n"})
    tabela = [*_tabela_limpa(arvore), _linha_tabela(arquivo, 1, "CERTIFICADO", "não corta nada")]

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1
    assert f"{arquivo}:1" in resultado.stdout
    assert "sem destino" in resultado.stdout


def test_ocorrencia_da_varredura_listada_na_secao_4_passa(arvore: Path) -> None:
    _arvore(arvore, {"agente_nw/padrao.py": "rotulo = texto[:200]\n"})
    tabela = [
        *_tabela_limpa(arvore),
        _linha_tabela("agente_nw/padrao.py", 1, "NÃO ANALÍTICO", "corte só de rótulo de tela", "NA-001"),
    ]
    pontos = [
        "#### NA-001 — agente_nw/padrao.py:1 — `rotulo`",
        "- Classe: NA",
        "- O que é cortado e quanto: 200 caracteres do rótulo mostrado na tela",
        "- Prova de que não entra em decisão: o valor só vai para o template, nunca para prompt ou vetor",
    ]

    resultado = _rodar(arvore, _relatorio(tabela, pontos))

    assert resultado.returncode == 0, resultado.stdout
    assert "1 não analítico" in resultado.stdout


def test_ocorrencia_citada_no_apendice_com_destino_passa(arvore: Path) -> None:
    _arvore(arvore, {"agente_nw/padrao.py": "data = quando[:10]\n"})
    tabela = [*_tabela_limpa(arvore), _linha_tabela("agente_nw/padrao.py", 1, "CERTIFICADO", "só a data ISO")]
    apendice = ["descartada: `[:10]` sobre data ISO é o dia, não corte de texto", "", "agente_nw/padrao.py:1"]

    resultado = _rodar(arvore, _relatorio(tabela, [], apendice))

    assert resultado.returncode == 0, resultado.stdout


def test_citacao_de_linha_parecida_nao_vale_pela_outra(arvore: Path) -> None:
    """`arquivo.py:1` não pode valer por `arquivo.py:12`: a conferência casa a linha exata."""
    _arvore(arvore, {"agente_nw/padrao.py": "\n" * 11 + "resumo = texto[:200]\n"})
    tabela = [*_tabela_limpa(arvore), _linha_tabela("agente_nw/padrao.py", 12, "CERTIFICADO", "nada")]
    apendice = ["agente_nw/padrao.py:1"]

    resultado = _rodar(arvore, _relatorio(tabela, [], apendice))

    assert resultado.returncode == 1
    assert "agente_nw/padrao.py:12" in resultado.stdout


# --------------------------------------------------------------------------------------
# 10. NÃO CONFERIDO é aceito, mas sai com 2
# --------------------------------------------------------------------------------------


def test_nao_conferido_e_aceito_com_codigo_2(arvore: Path) -> None:
    tabela = _tabela_limpa(arvore)
    total = _linhas(arvore, "agente_nw/alfa.py")
    tabela[0] = f"| agente_nw/alfa.py | 1/{total} | NÃO CONFERIDO | não consegui ler até o fim | — |"

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 2
    assert "1 não conferido" in resultado.stdout


def test_nao_conferido_nao_apaga_inconsistencia(arvore: Path) -> None:
    """Código 1 manda: com inconsistência **e** `NÃO CONFERIDO`, o verificador falha."""
    tabela = [linha for linha in _tabela_limpa(arvore) if "beta.py" not in linha]
    total = _linhas(arvore, "agente_nw/alfa.py")
    tabela[0] = f"| agente_nw/alfa.py | 1/{total} | NÃO CONFERIDO | não li | — |"

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 1


# --------------------------------------------------------------------------------------
# O universo enumerado é o do brief (item 3.7)
# --------------------------------------------------------------------------------------


def test_pastas_ignoradas_ficam_fora_do_universo(arvore: Path) -> None:
    _arvore(
        arvore,
        {
            ".venv/lib/pacote.py": "x = 1\n",
            "node_modules/pacote/indice.js": "const x = 1;\n",
            "agente_nw/__pycache__/alfa.cpython-312.pyc": "lixo\n",
            "dados/despejo.py": "x = 1\n",
            "logs/arquivos_079.py": "x = 1\n",
            "docs/PLAN_agente_nw.md": "# plano\n",
            "docs/exemplo.py": "x = 1\n",
        },
    )

    resultado = _rodar(arvore, _relatorio(_tabela_limpa(arvore)))

    assert resultado.returncode == 0, resultado.stdout
    assert "5 arquivos" in resultado.stdout


def test_sql_sh_e_json_da_extensao_entram_no_universo(arvore: Path) -> None:
    _arvore(
        arvore,
        {
            "scripts/migracoes/001_inicial.sql": "CREATE TABLE item (texto TEXT);\n",
            "scripts/verificar.sh": "#!/usr/bin/env bash\necho ok\n",
            "extensao/manifest.json": '{"manifest_version": 3}\n',
        },
    )
    tabela = [
        *_tabela_limpa(arvore),
        _linha_tabela("scripts/migracoes/001_inicial.sql", 1, "CERTIFICADO", "TEXT sem limite"),
        _linha_tabela("scripts/verificar.sh", 2, "CERTIFICADO", "só roda o gate"),
        _linha_tabela("extensao/manifest.json", 1, "CERTIFICADO", "só declaração"),
    ]

    resultado = _rodar(arvore, _relatorio(tabela))

    assert resultado.returncode == 0, resultado.stdout
    assert "8 arquivos" in resultado.stdout
