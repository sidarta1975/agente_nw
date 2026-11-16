"""Guarda permanente do texto por inteiro (brief 093): o gate acusa todo corte novo de texto.

O teste percorre, por AST, o código de produção (`agente_nw/**/*.py`) e acha cada lugar com cara de
corte: fatia (`x[:N]`, `x[-N:]`, `x[a:b]`), pedaço de uma divisão (`.split()[0]`), as chamadas
`shorten`/`truncate`/`truncar`/`cortar`/`islice`/`head`/`sample`/`fetchmany`, os nomes
`max_chars`/`max_len`/`maximo_caracteres`, o `LIMIT` de SQL e o teto decidido num lugar: a constante
ou a chave de configuração passada como argumento (`_FATOS_NO_PROMPT`, `limiares.teto_por_dia`), o valor
dado ao parâmetro de teto de uma função do projeto (`listar_recentes(conexao, id, 40)`, resolvida pelo
import do arquivo) e o valor padrão desse parâmetro (`limite: int = 5`). Repassar adiante a variável
`limite` recebida não conta: o achado fica em quem decidiu o valor.

A chave de cada achado é `arquivo + texto normalizado` das linhas do trecho (espaços colapsados, sem
número de linha), para que editar outra parte do arquivo não quebre o teste. Cada chave tem de estar
em um, e só um, de três estados (item 2.3 do brief):

(a) exceção aprovada: `EXCECOES_APROVADAS`, aqui, aponta a chave para um ponto `P-nnn` que tem linha
    em `docs/EXCECOES_TEXTO_INTEGRAL.md` com "Aprovado por Sidarta em AAAA-MM-DD", valor aprovado e
    condição;
(b) corte não analítico: a chave está na tabela "Cortes não analíticos" do mesmo registro;
(c) violação conhecida pendente: `VIOLACOES_PENDENTES`, aqui, com o `P-nnn` e o destino — o brief
    que vai corrigir (`brief NNN`) ou, sem brief ainda, a lacuna do PLAN que espera a decisão de
    Sidarta (`[NNN-k]`). Brief entregue (`docs/docs/doc_NNN_*.md` existe) ou lacuna marcada como
    decidida ou resolvida faz o teste falhar: o ponto tem de ser reclassificado.

Achado fora dos três estados falha. Entrada de qualquer lista sem achado correspondente também falha
(o corte saiu ou a linha mudou: a lista tem de acompanhar). Só Sidarta aprova exceção (AGENTS §4):
quem acrescenta linha em (a) aponta para uma aprovação que já existe, nunca a cria.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PASTA_PRODUCAO = "agente_nw"
REGISTRO = Path("docs") / "EXCECOES_TEXTO_INTEGRAL.md"
PLAN = Path("docs") / "PLAN_agente_nw.md"
RELATORIOS = Path("docs") / "docs"
TITULO_NAO_ANALITICOS = "## Cortes não analíticos"

Chave = tuple[str, str]

# ------------------------------------------------------------------------------------------------
# O que conta como corte
# ------------------------------------------------------------------------------------------------

_CHAMADAS_DE_CORTE = re.compile(r"^(shorten|truncate|trunc\w*|cortar\w*|islice|fetchmany|head|sample)$")
_DIVISOES = frozenset({"split", "rsplit", "splitlines", "partition", "rpartition"})
_NOMES_DE_TETO = re.compile(
    r"^(max_?chars|max_?len|maxlen|max_length|max(imo)?_caracteres\w*)$", re.IGNORECASE
)
_ARGUMENTO_DE_TETO = re.compile(
    r"((^|_)(maximo|max|limite|limit|teto)(_|$))|(_no_prompt|_no_centroide|_candidatos)$", re.IGNORECASE
)
# teto de tempo, de espera ou de tentativa não é teto de texto
_TETO_QUE_NAO_E_DE_TEXTO = re.compile(
    r"tempo|intervalo|espera|tentativa|iterac|segundos|peso|_s$", re.IGNORECASE
)
_CHAMADAS_QUE_NAO_CORTAM = frozenset({"range", "min", "max", "len", "enumerate", "sorted", "zip"})
_SQL_LIMIT = re.compile(r"\bLIMIT\b")


@dataclass(frozen=True)
class Achado:
    arquivo: str
    linha: int
    regra: str
    texto: str

    @property
    def chave(self) -> Chave:
        return (self.arquivo, self.texto)


def normalizar(texto: str) -> str:
    return " ".join(texto.split())


def _nome_da_chamada(chamada: ast.Call) -> str | None:
    if isinstance(chamada.func, ast.Name):
        return chamada.func.id
    if isinstance(chamada.func, ast.Attribute):
        return chamada.func.attr
    return None


def _e_teto_de_texto(identificador: str) -> bool:
    return (
        _ARGUMENTO_DE_TETO.search(identificador) is not None
        and _TETO_QUE_NAO_E_DE_TEXTO.search(identificador) is None
    )


def _tetos_passados(chamada: ast.Call) -> list[str]:
    """O teto decidido na chamada: constante de módulo (`_FATOS_NO_PROMPT`), chave de configuração
    (`limiares.teto_por_dia`) ou número literal (`limite=5`). Repassar a variável `limite` que veio de
    fora não é decidir teto: quem decide é quem chamou, e é lá que o achado aparece."""
    regras: list[str] = []
    for palavra in chamada.keywords:
        if (
            palavra.arg is not None
            and _e_teto_de_texto(palavra.arg)
            and isinstance(palavra.value, ast.Constant)
            and isinstance(palavra.value.value, int)
        ):
            regras.append(f"argumento {palavra.arg}={palavra.value.value}")
    for argumento in [*chamada.args, *(palavra.value for palavra in chamada.keywords)]:
        if isinstance(argumento, ast.Name) and argumento.id.isupper() and _e_teto_de_texto(argumento.id):
            regras.append(f"teto {argumento.id} como argumento")
        elif isinstance(argumento, ast.Attribute) and _e_teto_de_texto(argumento.attr):
            regras.append(f"teto {argumento.attr} como argumento")
    return regras


def _regras(no: ast.AST) -> list[str]:
    regras: list[str] = []
    if isinstance(no, ast.Subscript):
        indice = no.slice
        if isinstance(indice, ast.Slice) and (indice.lower is not None or indice.upper is not None):
            regras.append("fatia")
        elif (
            not isinstance(indice, ast.Slice)
            and isinstance(no.value, ast.Call)
            and _nome_da_chamada(no.value) in _DIVISOES
        ):
            regras.append("pedaço de divisão")
    elif isinstance(no, ast.Call):
        nome = _nome_da_chamada(no)
        if nome is not None and _CHAMADAS_DE_CORTE.match(nome):
            regras.append(f"chamada {nome}")
        if nome not in _CHAMADAS_QUE_NAO_CORTAM:
            regras.extend(_tetos_passados(no))
    elif isinstance(no, ast.Name) and _NOMES_DE_TETO.match(no.id):
        regras.append(f"nome {no.id}")
    elif isinstance(no, ast.Attribute) and _NOMES_DE_TETO.match(no.attr):
        regras.append(f"nome {no.attr}")
    elif isinstance(no, ast.arg) and _NOMES_DE_TETO.match(no.arg):
        regras.append(f"nome {no.arg}")
    elif isinstance(no, ast.keyword) and no.arg is not None and _NOMES_DE_TETO.match(no.arg):
        regras.append(f"nome {no.arg}")
    elif isinstance(no, ast.Constant) and isinstance(no.value, str) and _SQL_LIMIT.search(no.value):
        regras.append("LIMIT de SQL")
    return regras


Tetos = list[tuple[int | None, str]]
"""(posição, nome) de cada parâmetro de teto de uma função (`limite`, `maximo`, `maximo_x`)."""


@dataclass(frozen=True)
class Assinaturas:
    """As funções do código de produção que recebem um teto, por módulo e por nome. O nome sozinho só
    vale quando é único no projeto: `listar_recentes` existe em `fatos` e em `pedidos`, e a chamada é
    resolvida pelo import do arquivo (`fatos_q.listar_recentes` → `...queries.fatos`)."""

    por_modulo: dict[tuple[str, str], Tetos]
    por_nome_unico: dict[str, Tetos]


def modulo_do_arquivo(arquivo: str) -> str:
    partes = arquivo.removesuffix(".py").split("/")
    return ".".join(partes[:-1] if partes[-1] == "__init__" else partes)


def _tetos_da_funcao(funcao: ast.FunctionDef | ast.AsyncFunctionDef) -> Tetos:
    posicionais = [*funcao.args.posonlyargs, *funcao.args.args]
    if posicionais and posicionais[0].arg in ("self", "cls"):
        posicionais = posicionais[1:]
    parametros: Tetos = [(indice, a.arg) for indice, a in enumerate(posicionais)]
    parametros += [(None, a.arg) for a in funcao.args.kwonlyargs]
    return [(indice, nome) for indice, nome in parametros if _e_teto_de_texto(nome)]


def assinaturas_de_teto(fontes: Mapping[str, str]) -> Assinaturas:
    """`fontes`: arquivo relativo (`agente_nw/x.py`) → código."""
    por_modulo: dict[tuple[str, str], Tetos] = {}
    por_nome: dict[str, Tetos] = {}
    definicoes: dict[str, int] = {}
    for arquivo, fonte in fontes.items():
        modulo = modulo_do_arquivo(arquivo)
        for no in ast.walk(ast.parse(fonte)):
            if not isinstance(no, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            definicoes[no.name] = definicoes.get(no.name, 0) + 1
            tetos = _tetos_da_funcao(no)
            if tetos:
                por_modulo.setdefault((modulo, no.name), []).extend(tetos)
                por_nome.setdefault(no.name, []).extend(tetos)
    unicos = {nome: tetos for nome, tetos in por_nome.items() if definicoes[nome] == 1}
    return Assinaturas(por_modulo, unicos)


def importacoes(arvore: ast.Module) -> dict[str, str]:
    """Nome local → alvo pontuado (`fatos_q` → `agente_nw.nucleo.database.queries.fatos`)."""
    nomes: dict[str, str] = {}
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            for apelido in no.names:
                nomes[apelido.asname or apelido.name.split(".")[0]] = (
                    apelido.name if apelido.asname else apelido.name.split(".")[0]
                )
        elif isinstance(no, ast.ImportFrom) and no.module is not None and no.level == 0:
            for apelido in no.names:
                nomes[apelido.asname or apelido.name] = f"{no.module}.{apelido.name}"
    return nomes


def _tetos_da_chamada(
    chamada: ast.Call, assinaturas: Assinaturas, modulo: str, nomes: Mapping[str, str]
) -> tuple[str, Tetos] | None:
    funcao = chamada.func
    chave: tuple[str, str]
    if isinstance(funcao, ast.Name):
        nome = funcao.id
        alvo = nomes.get(nome)
        chave = (alvo.rsplit(".", 1)[0], nome) if alvo is not None else (modulo, nome)
    elif isinstance(funcao, ast.Attribute):
        nome = funcao.attr
        base = nomes.get(funcao.value.id) if isinstance(funcao.value, ast.Name) else None
        chave = (base or "", nome)
    else:
        return None
    if chave in assinaturas.por_modulo:
        return nome, assinaturas.por_modulo[chave]
    if nome in assinaturas.por_nome_unico:
        return nome, assinaturas.por_nome_unico[nome]
    return None


def _repasse(valor: ast.expr) -> bool:
    """`limite` que veio de fora e segue adiante: quem decide o valor é quem chamou."""
    return isinstance(valor, ast.Name) and not valor.id.isupper()


def _teto_decidido_na_chamada(
    chamada: ast.Call, assinaturas: Assinaturas, modulo: str, nomes: Mapping[str, str]
) -> list[str]:
    resolvida = _tetos_da_chamada(chamada, assinaturas, modulo, nomes)
    if resolvida is None:
        return []
    nome, tetos = resolvida
    regras: list[str] = []
    estrela = any(isinstance(argumento, ast.Starred) for argumento in chamada.args)
    for indice, parametro in tetos:
        valor: ast.expr | None = None
        if indice is not None and not estrela and indice < len(chamada.args):
            valor = chamada.args[indice]
        for palavra in chamada.keywords:
            if palavra.arg == parametro:
                valor = palavra.value
        if valor is not None and not _repasse(valor):
            regras.append(f"teto {parametro} decidido na chamada de {nome}")
    return regras


def _teto_padrao(funcao: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """`def f(..., limite=5)`: o valor padrão de um teto também decide quanto entra."""
    regras: list[str] = []
    posicionais = [*funcao.args.posonlyargs, *funcao.args.args]
    padroes = funcao.args.defaults
    pares = list(zip(posicionais[len(posicionais) - len(padroes) :], padroes, strict=True))
    pares += [
        (a, d) for a, d in zip(funcao.args.kwonlyargs, funcao.args.kw_defaults, strict=True) if d is not None
    ]
    for parametro, padrao in pares:
        if _e_teto_de_texto(parametro.arg) and not (
            isinstance(padrao, ast.Constant) and padrao.value is None
        ):
            regras.append(f"teto padrão {parametro.arg}")
    return regras


def achar_cortes(fonte: str, arquivo: str, assinaturas: Assinaturas | None = None) -> list[Achado]:
    """Os achados de um arquivo, cada um com o texto normalizado das linhas do trecho. `assinaturas` vem
    de todo o código de produção (`varrer`); sem ela, só as funções do próprio arquivo contam."""
    if assinaturas is None:
        assinaturas = assinaturas_de_teto({arquivo: fonte})
    modulo = modulo_do_arquivo(arquivo)
    arvore = ast.parse(fonte)
    nomes = importacoes(arvore)
    linhas = fonte.splitlines()
    achados: list[Achado] = []
    for no in ast.walk(arvore):
        regras = _regras(no)
        if isinstance(no, ast.Call):
            regras += _teto_decidido_na_chamada(no, assinaturas, modulo, nomes)
        if isinstance(no, ast.FunctionDef | ast.AsyncFunctionDef):
            # só a linha da assinatura entra na chave, não o corpo inteiro da função
            regras_padrao = _teto_padrao(no)
            if regras_padrao:
                fim_assinatura = no.body[0].lineno - 1 if no.body else no.lineno
                texto = normalizar(" ".join(linhas[no.lineno - 1 : max(fim_assinatura, no.lineno)]))
                achados.extend(Achado(arquivo, no.lineno, regra, texto) for regra in regras_padrao)
        if not regras:
            continue
        inicio = getattr(no, "lineno", None)
        if inicio is None:
            continue
        fim = getattr(no, "end_lineno", None) or inicio
        texto = normalizar(" ".join(linhas[inicio - 1 : fim]))
        achados.extend(Achado(arquivo, inicio, regra, texto) for regra in sorted(set(regras)))
    return achados


def varrer(raiz: Path) -> list[Achado]:
    caminhos = [
        caminho
        for caminho in sorted((raiz / PASTA_PRODUCAO).rglob("*.py"))
        if "__pycache__" not in caminho.parts
    ]
    fontes = {
        caminho.relative_to(raiz).as_posix(): caminho.read_text(encoding="utf-8") for caminho in caminhos
    }
    assinaturas = assinaturas_de_teto(fontes)
    achados: list[Achado] = []
    for arquivo, fonte in fontes.items():
        achados.extend(achar_cortes(fonte, arquivo, assinaturas))
    return achados


# ------------------------------------------------------------------------------------------------
# Leitura do registro, do PLAN e dos relatórios
# ------------------------------------------------------------------------------------------------

_APROVACAO = re.compile(r"Aprovado por Sidarta em \d{4}-\d{2}-\d{2}")


def _celulas(linha: str) -> list[str]:
    """Células de uma linha de tabela Markdown; `\\|` dentro da célula é barra, não divisa."""
    miolo = linha.strip()
    miolo = miolo.removeprefix("|").removesuffix("|")
    return [celula.replace("\\|", "|").strip() for celula in re.split(r"(?<!\\)\|", miolo)]


def _preenchida(celula: str) -> bool:
    return celula.strip() not in ("", "—", "-", "–")


def linhas_de_excecao(texto_registro: str) -> dict[str, str]:
    """Ponto → linha da tabela de exceções aprovadas (a que tem "Aprovado por Sidarta em")."""
    linhas: dict[str, str] = {}
    for linha in texto_registro.splitlines():
        if not linha.startswith("| P-") or _APROVACAO.search(linha) is None:
            continue
        linhas[_celulas(linha)[0]] = linha
    return linhas


def nao_analiticos(texto_registro: str) -> dict[Chave, str]:
    """Chave → identificador NA, da tabela "Cortes não analíticos" do registro.

    Colunas: `NA | Arquivo | Trecho (normalizado) | O que é cortado | Por que não é análise`."""
    tabela: dict[Chave, str] = {}
    dentro = False
    for linha in texto_registro.splitlines():
        if linha.startswith("## "):
            dentro = linha.strip() == TITULO_NAO_ANALITICOS
            continue
        if not dentro or not linha.startswith("| NA-"):
            continue
        celulas = _celulas(linha)
        if len(celulas) < 5:
            continue
        arquivo = celulas[1].strip("`")
        trecho = normalizar(celulas[2].removeprefix("`").removesuffix("`"))
        tabela[(arquivo, trecho)] = celulas[0]
    return tabela


def relatorio_entregue(raiz: Path, numero: str) -> Path | None:
    encontrados = sorted((raiz / RELATORIOS).glob(f"doc_{numero}_*.md"))
    return encontrados[0] if encontrados else None


_DESTINO_BRIEF = re.compile(r"^brief (?P<numero>\d{3})$")
_DESTINO_LACUNA = re.compile(r"^\[(?P<numero>\d{3})-(?P<indice>\d+)\]$")


def destino_vencido(raiz: Path, destino: str) -> str | None:
    """Por que o destino de uma violação pendente já não segura o ponto (None: ainda segura)."""
    if (brief := _DESTINO_BRIEF.match(destino)) is not None:
        relatorio = relatorio_entregue(raiz, brief.group("numero"))
        if relatorio is not None:
            return f"o brief {brief.group('numero')} já foi entregue ({relatorio.name})"
        return None
    if (lacuna := _DESTINO_LACUNA.match(destino)) is not None:
        plan = raiz / PLAN
        linhas_plan = plan.read_text(encoding="utf-8").splitlines() if plan.exists() else []
        no_plan = [linha for linha in linhas_plan if destino in linha]
        if no_plan:
            if any(re.search(r"\b(resolvid|decidid)", linha, re.IGNORECASE) for linha in no_plan):
                return f"a lacuna {destino} está marcada como decidida ou resolvida no PLAN"
            return None
        # A lacuna do brief em execução só chega ao PLAN na entrega (agente_lacunas.py): até lá, vale a
        # linha da tabela `## Lacunas` do relatório dele.
        relatorio = relatorio_entregue(raiz, lacuna.group("numero"))
        if relatorio is not None:
            texto = relatorio.read_text(encoding="utf-8")
            secao = texto.rsplit("## Lacunas", 1)[-1] if "## Lacunas" in texto else ""
            if re.search(rf"^\|\s*{lacuna.group('indice')}\s*\|", secao, re.MULTILINE):
                return None
        return f"a lacuna {destino} não existe no PLAN nem no relatório do brief {lacuna.group('numero')}"
    return f"destino {destino!r} não é `brief NNN` nem `[NNN-k]`"


# ------------------------------------------------------------------------------------------------
# Classificação
# ------------------------------------------------------------------------------------------------


def classificar(
    raiz: Path,
    achados: Iterable[Achado],
    aprovadas: Mapping[Chave, str],
    pendentes: Mapping[Chave, tuple[str, str]],
) -> list[str]:
    """Os erros da guarda: achado sem estado, estado duplo, aprovação inexistente, destino vencido e
    entrada sem achado. Lista vazia = tudo classificado."""
    caminho_registro = raiz / REGISTRO
    texto_registro = caminho_registro.read_text(encoding="utf-8") if caminho_registro.exists() else ""
    excecoes = linhas_de_excecao(texto_registro)
    tabela_na = nao_analiticos(texto_registro)

    por_chave: dict[Chave, list[Achado]] = {}
    for achado in achados:
        por_chave.setdefault(achado.chave, []).append(achado)

    erros: list[str] = []
    for chave in sorted(por_chave):
        arquivo, texto = chave
        primeiro = por_chave[chave][0]
        regras = ", ".join(sorted({a.regra for a in por_chave[chave]}))
        estados = [
            nome
            for nome, presente in (
                ("exceção aprovada", chave in aprovadas),
                ("não analítico", chave in tabela_na),
                ("violação pendente", chave in pendentes),
            )
            if presente
        ]
        if not estados:
            erros.append(
                f"corte sem estado em {arquivo}:{primeiro.linha} [{regras}]: {texto!r} — "
                "texto por inteiro (AGENTS §4): tire o corte, ou classifique-o (exceção aprovada por "
                "Sidarta, corte não analítico no registro, ou violação pendente com destino)"
            )
            continue
        if len(estados) > 1:
            erros.append(f"{arquivo}:{primeiro.linha} está em mais de um estado ({', '.join(estados)})")
        if chave in aprovadas:
            for ponto in aprovadas[chave].split():
                celulas = _celulas(excecoes[ponto]) if ponto in excecoes else []
                if not celulas:
                    erros.append(
                        f"{arquivo}:{primeiro.linha} aponta para {ponto}, que não tem linha aprovada por "
                        f"Sidarta em {REGISTRO.as_posix()}"
                    )
                elif len(celulas) < 7 or not _preenchida(celulas[3]) or not _preenchida(celulas[4]):
                    erros.append(
                        f"{arquivo}:{primeiro.linha} aponta para {ponto}, cuja linha no registro não tem "
                        "valor aprovado e condição"
                    )
        if chave in pendentes:
            ponto, destino = pendentes[chave]
            motivo = destino_vencido(raiz, destino)
            if motivo is not None:
                erros.append(
                    f"violação pendente {ponto} em {arquivo}:{primeiro.linha} já não está pendente: "
                    f"{motivo}; corrija o corte ou reclassifique-o"
                )

    for nome, entradas in (
        ("exceção aprovada", aprovadas.keys()),
        ("não analítico", tabela_na.keys()),
        ("violação pendente", pendentes.keys()),
    ):
        for arquivo, texto in sorted(set(entradas) - set(por_chave)):
            erros.append(
                f"entrada de {nome} sem achado no código: {arquivo}: {texto!r} — o corte saiu ou a "
                "linha mudou; atualize a lista"
            )
    return erros


# ------------------------------------------------------------------------------------------------
# Estado (a): exceções aprovadas por Sidarta. Chave → ponto do registro.
# ------------------------------------------------------------------------------------------------


def _achatar[V](por_arquivo: Mapping[str, Mapping[str, V]]) -> dict[Chave, V]:
    return {
        (arquivo, texto): valor for arquivo, linhas in por_arquivo.items() for texto, valor in linhas.items()
    }


# Mais de um ponto, separados por espaço, quando o trecho decide mais de um teto aprovado.
EXCECOES_APROVADAS: dict[Chave, str] = _achatar(
    {
        "agente_nw/cli.py": {
            (
                "entrega = orquestracao.preparar_e_redigir( canal, preparar=consulta_mo"
                "d.preparar, conexao=conn, cliente_llm=llm(), cliente_http=http(), perf"
                "il=resultado.perfil, extraido=resultado.pedido, texto=frase, limiares="
                'config.limiares, caminho_fontes=RAIZ / "fontes.yaml", caminho_sentinel'
                "a=caminho_sentinela(), abrir_pagina=abrir_pagina_extensao, pasta_naveg"
                'ador=RAIZ / "dados" / "navegador", limite_tokens=int(num_ctx * FRACAO_'
                "DO_CONTEXTO_NO_PROMPT), rodar_coleta=True, ler_redes_sociais=True, )"
            ): "P-033",
        },
        "agente_nw/coleta/capturas/extensao_backend.py": {
            (
                "def __init__( self, ponte: Ponte, limiares: ExtensaoLimiares, dorme: C"
                "allable[[float], None] = time.sleep, maximo_entradas: int = 2000, cami"
                "nho_log: Path | None = None, ) -> None:"
            ): "P-015",
            (
                "return PaginaExtensao( obter_ponte(limiares.espera_extensao_s, limiare"
                "s.navegador_app, limiares.navegador_perfil), limiares, maximo_entradas"
                "=todos.listas.maximo_entradas, caminho_log=caminho_log_chamadas_llm(),"
                " )"
            ): "P-015",
        },
        "agente_nw/coleta/capturas/leitor.py": {
            (
                "def ler_redes_sociais_do_contato( cliente_llm: ClienteExtracao, conexa"
                "o: sqlite3.Connection, perfil_id: int, abrir_pagina: Callable[[Path], "
                "Pagina], pasta_navegador: Path, agora: str, dorme: Callable[[float], N"
                "one] = time.sleep, max_esperas_login: int = 0, espera_login_s: float ="
                " 5.0, max_rolagens: int = 5, maximo_blocos: int | None = None, avisar:"
                " Callable[[str], None] | None = None, maximo_imagens: int = 0, largura"
                "_minima_imagem: int = 250, ) -> ResumoLeitura:"
            ): "P-015 P-017",
            ("else captura.blocos[: maximo_blocos * _BLOCOS_EXAMINADOS_POR_PUBLICACAO]"): "P-016",
        },
        "agente_nw/coleta/capturas/listas.py": {
            (
                "autenticado=True, motivo=None, entradas=entradas[: limiares.maximo_ent"
                "radas], truncada=truncada"
            ): "P-015",
        },
        "agente_nw/coleta/capturas/navegador.py": {
            (
                "def ler( pagina: Pagina, url: str, dorme: Callable[[float], None] = ti"
                "me.sleep, aleatorio: random.Random | None = None, max_esperas_login: i"
                "nt = _MAX_ESPERAS_LOGIN, espera_login_s: float = _ESPERA_LOGIN_S, max_"
                "rolagens: int = _MAX_ROLAGENS, intervalo_min_s: float = _INTERVALO_MIN"
                "_S, intervalo_max_s: float = _INTERVALO_MAX_S, maximo_imagens: int = 0"
                ", largura_minima_imagem: int = 250, ) -> CapturaBlocos:"
            ): "P-015 P-017",
        },
        "agente_nw/coleta/rss/google_news.py": {
            '("busca", contexto.termos_busca[:_MAXIMO_TERMOS_BUSCA]),': "P-005",
            '("contato", termos_contato[:_MAXIMO_TERMOS_CONTATO]),': "P-005",
            '("interessa", contexto.interessa[:_MAXIMO_INTERESSA]),': "P-005",
            (
                "def gerar_consultas_da_consulta( contexto: ContextoConsulta, termos_co"
                "ntato: list[str], maximo: int = _MAXIMO_CONSULTAS_PADRAO ) -> list[Fee"
                "dFonte]:"
            ): "P-005",
            "return escolhidos[:maximo]": "P-005",
            "termos = [tema.nome, *tema.sinonimos][:_MAXIMO_TERMOS_POR_TEMA]": "P-005",
        },
        "agente_nw/nucleo/agrupamento/agrupador.py": {
            (
                "def agrupar( cliente_llm: ClienteEmbeddagem, conexao: sqlite3.Connecti"
                "on, limiares: Limiares, caminho_sentinela: Path, data_referencia: str,"
                " limite: int = 100, ) -> ResumoAgrupamento:"
            ): "P-043",
        },
        "agente_nw/nucleo/agrupamento/calibracao.py": {
            (
                "amostra = gerador.sample(controle_iguais, n_iguais) + gerador.sample(c"
                "ontrole_distintos, n_distintos)"
            ): "P-008",
            'return (item.texto or "")[:_TRUNCAMENTO_TRECHO]': "P-008",
            ("return gerador.sample(dentro_da_banda, min(_MAX_PARES_BANDA, len(dentro_da_banda)))"): "P-008",
        },
        "agente_nw/nucleo/confirmacao.py": {
            "mostradas = localizacao.opcoes[:_OPCOES_MOSTRADAS]": "P-021",
        },
        "agente_nw/nucleo/consulta.py": {
            (
                "def preparar( conexao: sqlite3.Connection, cliente_llm: Any, cliente_h"
                "ttp: httpx.Client, perfil_id: int, contexto: ContextoConsulta, limiare"
                "s: Limiares, caminho_fontes: Path, caminho_sentinela: Path, abrir_pagi"
                "na: Callable[[Path], Pagina], pasta_navegador: Path, agora: str, rodar"
                "_coleta: bool = True, max_esperas_login_rede_social: int = 0, espera_l"
                "ogin_s_rede_social: float = 5.0, max_rolagens_rede_social: int = 5, av"
                "isar: Callable[[str], None] | None = None, ler_redes_sociais: bool = T"
                "rue, ) -> ResultadoConsulta:"
            ): "P-015",
            (
                "for _rotulo, termo in google_news.selecionar_termos( contexto, termos_"
                "contato, limiares.coleta.max_consultas_por_pedido )"
            ): "P-005",
            (
                "resumo_leitor = leitor_capturas.ler_redes_sociais_do_contato( cliente_"
                "llm, conexao, perfil_id, abrir_pagina, pasta_navegador, agora, max_esp"
                "eras_login=max_esperas_login_rede_social, espera_login_s=espera_login_"
                "s_rede_social, max_rolagens=max_rolagens_rede_social, maximo_blocos=li"
                "miares.coleta.maximo_blocos_por_rede, maximo_imagens=limiares.coleta.m"
                "aximo_imagens_por_rede, largura_minima_imagem=limiares.coleta.largura_"
                "minima_imagem, avisar=avisar, )"
            ): "P-016 P-017",
        },
        "agente_nw/nucleo/database/queries/conversa.py": {
            (
                '"SELECT autor, texto FROM conversa_mensagem WHERE perfil_id = ? ORDER '
                'BY enviada_em DESC LIMIT ?",'
            ): "P-023",
            "for mes in sorted(por_mes, reverse=True)[:meses_extraidos]": "P-022",
        },
        "agente_nw/nucleo/database/queries/fila_extracao.py": {
            (
                'f"SELECT {_COLUNAS} FROM fila_extracao WHERE processado = 0 AND erro I'
                'S NULL ORDER BY id LIMIT ?",'
            ): "P-043",
        },
        "agente_nw/nucleo/database/queries/fontes.py": {
            (
                '"SELECT n_itens_novos FROM fonte_execucao WHERE fonte_id = ? AND data '
                '<= ? " "ORDER BY data DESC LIMIT 2",'
            ): "P-043",
        },
        "agente_nw/nucleo/database/queries/itens.py": {
            ('f"SELECT {_COLUNAS} FROM item WHERE assunto_id IS NULL ORDER BY id LIMIT ?",'): "P-043",
        },
        "agente_nw/nucleo/database/queries/listas.py": {
            "primeiro = sem_acento_e_caixa(nome).split()[:1]": "P-045",
            "return [e for _, e in aprovadas[:maximo]]": "P-021",
        },
        "agente_nw/nucleo/fluxo.py": {
            (
                "entrega = orquestracao.preparar_e_redigir( canal, preparar=preparar, c"
                "onexao=conexao, cliente_llm=deps.fabrica_llm(conexao), cliente_http=cl"
                "iente_http, perfil=perfil, extraido=extraido, texto=pedido.texto, limi"
                "ares=deps.limiares, caminho_fontes=deps.caminho_fontes, caminho_sentin"
                "ela=deps.caminho_sentinela, abrir_pagina=deps.abrir_pagina, pasta_nave"
                "gador=deps.pasta_navegador, limite_tokens=int(deps.num_ctx_redacao * F"
                "RACAO_DO_CONTEXTO_NO_PROMPT), rodar_coleta=not reaproveita, ler_redes_"
                "sociais=not correcao, )"
            ): "P-033",
        },
        "agente_nw/nucleo/localizacao.py": {
            (
                "achadas = queries_listas.buscar_parecidos( conexao, rede, nome, limiar"
                "es.similaridade_minima, limiares.maximo_parecidas )"
            ): "P-021",
        },
        "agente_nw/nucleo/prompts/redigir_ganchos.py": {
            (
                "def construir_prompt(entrada: EntradaRedacao, limite_tokens: int = LIM"
                "ITE_TOKENS_PADRAO) -> str:"
            ): "P-033",
            (
                "def cortar_por_tamanho(entrada: EntradaRedacao, limite_tokens: int = L"
                "IMITE_TOKENS_PADRAO) -> EntradaRedacao:"
            ): "P-033",
            (
                "def fatos_nao_incluidos(entrada: EntradaRedacao, limite_tokens: int = "
                "LIMITE_TOKENS_PADRAO) -> list[str]:"
            ): "P-033",
            "historico=entrada.historico[:_HISTORICO_NO_CORTE],": "P-033",
            "mantidos = list(cortar_por_tamanho(entrada, limite_tokens).fatos)": "P-033",
            "return _montar(cortar_por_tamanho(entrada, limite_tokens))": "P-033",
            (
                "return fatos[:_FATOS_NO_CORTE] # sem data em alguma linha, vale a orde"
                "m recebida (já é a de recência)"
            ): "P-033",
            ("return sorted(fatos, key=lambda fato: fato[:10], reverse=True)[:_FATOS_NO_CORTE]"): "P-033",
        },
        "agente_nw/nucleo/redacao.py": {
            (
                "molde_origem_id = prompt_mod.cortar_por_tamanho(entrada, limite_tokens).molde_origem_id"
            ): "P-033",
        },
        "agente_nw/nucleo/relevancia/cruzamento.py": {
            "selecionados_para_menu = demais[: limiares.conector.itens_no_menu]": "P-009",
        },
        "agente_nw/perfil/extrator.py": {
            (
                "def processar_fila( cliente_llm: ClienteExtracaoPerfil, conexao: sqlit"
                "e3.Connection, limite: int = 20 ) -> ResumoProcessamento:"
            ): "P-043",
        },
    }
)

# ------------------------------------------------------------------------------------------------
# Estado (c): violações conhecidas pendentes. Chave → (ponto, destino).
# ------------------------------------------------------------------------------------------------

# Nenhum destes pontos tem brief marcado para corrigir; todos esperam uma decisão de Sidarta, registrada
# como lacuna no PLAN. Quando a decisão sair (a linha da lacuna ganha "decidido" ou "resolvido"), o teste
# falha até o trecho ser corrigido ou reclassificado.
#   [080-5] P-009  os 10 candidatos (`conector.candidatos_por_contato`), escolhidos por cosseno
#   [089-1] P-025  os 20 fatos mais recentes do centróide do contato
#   [091-1] P-034 e P-039  `interessa` com 5 itens no contrato e no ponto de apoio
#   [091-2] P-026, P-027 e P-031  10 de 40 fatos na redação, 12 de 30 nos termos, 3 itens por assunto
#   [092-3] P-032 e P-035  ganchos além do teto, contatos do prompt do pedido além dos parecidos
#   [092-5] P-021  os 200 fatos mais recentes na deduplicação da localização
#   [093-1] P-013  a página da rede social cortada em 200.000 caracteres (agora com aviso)
#   [093-2] P-009  `qualificacao.teto_por_dia` (40) assuntos por rodada na qualificação e no cartão
#   [093-3] P-028  o histórico: 5 consultas lidas, 3 na redação, mensagem anterior em 100 caracteres
#   [093-4] P-029 e P-030  5 notas e 2 moldes na redação
#   [093-5] P-034  `termos_busca` com 6 itens no contrato do pedido
VIOLACOES_PENDENTES: dict[Chave, tuple[str, str]] = _achatar(
    {
        "agente_nw/cli.py": {
            "return qualificar_cmd(args.limite)": ("P-009", "[093-2]"),
        },
        "agente_nw/coleta/capturas/extensao_backend.py": {
            "maximo = self._limiares.maximo_caracteres_pagina": ("P-013", "[093-1]"),
            "return url, texto[:maximo]": ("P-013", "[093-1]"),
            (
                '{"acao": "estado", "aba_id": self._aba_id, "maximo": self._limiares.ma'
                "ximo_caracteres_pagina}"
            ): ("P-013", "[093-1]"),
        },
        "agente_nw/nucleo/consulta.py": {
            (
                "qualificador.qualificar_pendentes( cliente_llm, conexao, limiares.qual"
                "ificacao.teto_por_dia, vetores_extras=[centroide_consulta] )"
            ): ("P-009", "[093-2]"),
        },
        "agente_nw/nucleo/database/queries/assuntos.py": {
            (
                'f"SELECT {_COLUNAS} FROM assunto " "WHERE substancial IS NOT NULL AND '
                'conversavel IS NOT NULL AND resumo_cartao IS NULL " "ORDER BY id LIMIT'
                ' ?",'
            ): ("P-009", "[093-2]"),
            "return [assunto for _, assunto in candidatos[:limite]]": ("P-009", "[093-2]"),
        },
        "agente_nw/nucleo/database/queries/consulta_contato.py": {
            "return candidatos[:1]": ("P-030", "[093-4]"),
            "return usados[:maximo]": ("P-030", "[093-4]"),
        },
        "agente_nw/nucleo/database/queries/perfis.py": {
            ("fatos_recentes = fatos.listar_recentes(conexao, perfil_id, _MAXIMO_FATOS_NO_CENTROIDE)"): (
                "P-025",
                "[089-1]",
            ),
        },
        "agente_nw/nucleo/historico.py": {
            (
                "def historico_recente_para_prompt( conexao: sqlite3.Connection, perfil"
                "_id: int, limite: int = LIMITE_PADRAO ) -> str:"
            ): ("P-028", "[093-3]"),
            (
                "trecho = f' — mensagem: \"{mensagem[:100]}\"' if isinstance(mensagem, st"
                'r) and mensagem else ""'
            ): ("P-028", "[093-3]"),
        },
        "agente_nw/nucleo/localizacao.py": {
            ("recentes = fatos.listar_recentes(conexao, perfil_id, _FATOS_NA_DEDUPLICACAO)"): (
                "P-021",
                "[092-5]",
            ),
        },
        "agente_nw/nucleo/modelos/configuracao.py": {
            "maximo_caracteres_pagina: int = Field(default=200000, ge=1000)": ("P-013", "[093-1]"),
        },
        "agente_nw/nucleo/modelos/pedido.py": {
            "return _sem_duplicatas(valor)[:_MAXIMO_INTERESSA]": ("P-034", "[091-1]"),
            "return unicos[:_MAXIMO_TERMOS_BUSCA]": ("P-034", "[093-5]"),
        },
        "agente_nw/nucleo/modelos/redacao.py": {
            "return [*base, *aceitos[:MAXIMO_GANCHOS]], motivos": ("P-032", "[092-3]"),
        },
        "agente_nw/nucleo/orquestracao.py": {
            (
                "redacao = redacao_mod.redigir( cliente_llm, conexao, extraido, consult"
                "a, perfil, pedido_mod.garantir_usuario(conexao, agora_redacao), agora_"
                "redacao, frase=texto, limite_tokens=limite_tokens, meses_fato_antigo=l"
                "imiares.redacao.meses_fato_antigo, trocas_whatsapp_no_prompt=limiares."
                "whatsapp.trocas_no_prompt, maximo_moldes=limiares.moldes.maximo, )"
            ): ("P-030", "[093-4]"),
        },
        "agente_nw/nucleo/pedido.py": {
            ("for contato in perfis.listar_contatos_recentes(conexao, _MAXIMO_CONTATOS_NO_PROMPT)"): (
                "P-035",
                "[092-3]",
            ),
            ("return [*parecidos, *completam[: max(0, _MAXIMO_CONTATOS_NO_PROMPT - len(parecidos))]]"): (
                "P-035",
                "[092-3]",
            ),
        },
        "agente_nw/nucleo/redacao.py": {
            ("candidatos = fatos_q.listar_recentes(conexao, perfil_id, _FATOS_CANDIDATOS)"): (
                "P-026",
                "[091-2]",
            ),
            (
                "def montar_entrada( conexao: sqlite3.Connection, cliente_llm: ClienteR"
                "edacao, pedido: PedidoExtraido, frase: str, resultado_consulta: Result"
                "adoConsulta, contato: Perfil, usuario: Perfil, assuntos: list[ItemMenu"
                "], meses_fato_antigo: int = 12, trocas_whatsapp_no_prompt: int = 10, m"
                "aximo_moldes: int = 2, ) -> EntradaRedacao:"
            ): ("P-030", "[093-4]"),
            (
                "def redigir( cliente_llm: ClienteRedacao, conexao: sqlite3.Connection,"
                " pedido: PedidoExtraido, resultado_consulta: ResultadoConsulta, perfil"
                ': Perfil, usuario: Perfil, agora: str, frase: str = "", limite_tokens:'
                " int = prompt_mod.LIMITE_TOKENS_PADRAO, meses_fato_antigo: int = 12, t"
                "rocas_whatsapp_no_prompt: int = 10, maximo_moldes: int = 2, ) -> Redac"
                "ao:"
            ): ("P-030", "[093-4]"),
            (
                "for c in consulta_contato_q.listar_por_perfil(conexao, perfil_id, _CON"
                "SULTAS_NO_HISTORICO + 1)"
            ): ("P-028", "[093-3]"),
            (
                "for com_dominio in itens_q.listar_por_assunto(conexao, item.assunto_id"
                ", com_corpo=True)[ :_MANCHETES_POR_ASSUNTO ]:"
            ): ("P-031", "[091-2]"),
            ("for nota in nota_contato_q.listar_por_perfil(conexao, perfil_id, _NOTAS_NO_PROMPT)"): (
                "P-029",
                "[093-4]",
            ),
            "garantidos = candidatos[:_FATOS_RECENTES_GARANTIDOS]": ("P-026", "[091-2]"),
            "resto = candidatos[_FATOS_RECENTES_GARANTIDOS:]": ("P-026", "[091-2]"),
            (
                "return [ c for c in consulta_contato_q.listar_por_perfil(conexao, perf"
                "il_id, _CONSULTAS_NO_HISTORICO + 1) if c.id != consulta_id ][:_CONSULT"
                "AS_NO_HISTORICO]"
            ): ("P-028", "[093-3]"),
            "return [*garantidos, *(resto[i] for i in sorted(ordem[:vagas]))]": ("P-026", "[091-2]"),
            "return candidatos[:_FATOS_NO_PROMPT]": ("P-026", "[091-2]"),
        },
        "agente_nw/nucleo/relevancia/candidatos.py": {
            "return [assunto for assunto, _ in ranqueados[:limite]]": ("P-009", "[080-5]"),
            "return [assunto for assunto, _ in ranqueados[:limite]], evitados": ("P-009", "[080-5]"),
        },
        "agente_nw/nucleo/relevancia/cruzamento.py": {
            (
                "restantes, evitados = candidatos.selecionar_por_consulta( conexao, per"
                "fil_id, centroide_consulta, centroide_contato, limiares.qualificacao.s"
                "ubstancial_minimo, limiares.qualificacao.conversavel_minimo, limiares."
                "conector.candidatos_por_contato, evitar_completo, limiares.conector.co"
                "nsulta, modelo_embedding, )"
            ): ("P-009", "[080-5]"),
            (
                "selecionados = candidatos.selecionar( conexao, perfil_id, centroide_co"
                "ntato, limiares.qualificacao.substancial_minimo, limiares.qualificacao"
                ".conversavel_minimo, limiares.conector.candidatos_por_contato, modelo_"
                "embedding, )"
            ): ("P-009", "[080-5]"),
            (
                "t for t in [contexto.assunto, *contexto.interessa[:_MAXIMO_INTERESSA_NO_APOIO]] if t.strip()"
            ): ("P-039", "[091-1]"),
        },
        "agente_nw/nucleo/termos_contato.py": {
            "for f in fatos.listar_recentes(conexao, perfil_id, _FATOS_LIDOS)": ("P-027", "[091-2]"),
            ("publicacoes = [f.conteudo.strip() for f in registros[:_FATOS_NO_PROMPT]]"): (
                "P-027",
                "[091-2]",
            ),
            "return termos[:MAXIMO_TERMOS]": ("P-027", "[091-2]"),
        },
    }
)


# ------------------------------------------------------------------------------------------------
# O teste de aceite: o código de produção de verdade
# ------------------------------------------------------------------------------------------------


def test_todo_corte_do_codigo_de_producao_tem_estado() -> None:
    erros = classificar(RAIZ, varrer(RAIZ), EXCECOES_APROVADAS, VIOLACOES_PENDENTES)
    assert not erros, f"{len(erros)} problema(s) na guarda do texto por inteiro:\n" + "\n".join(erros)


def test_a_varredura_enxerga_o_codigo_de_producao() -> None:
    """Uma varredura que não acha nada não guarda nada: confere que ela vê o que se sabe que existe."""
    achados = varrer(RAIZ)
    assert len({a.arquivo for a in achados}) > 20
    assert any(a.arquivo == "agente_nw/nucleo/agrupamento/calibracao.py" for a in achados)


# ------------------------------------------------------------------------------------------------
# Testes do teste: uma árvore sintética
# ------------------------------------------------------------------------------------------------

_REGISTRO_SINTETICO = """# Exceções

| Ponto | Arquivo:função | O que | Valor | Condição | Justificativa | Aprovado por Sidarta em |
|---|---|---|---|---|---|---|
| P-900 | agente_nw/aprovado.py:1 | 2.000 | 2000 | sempre | — | Aprovado por Sidarta em 2026-11-08 |
| P-901 | agente_nw/sem_aprovacao.py:1 | 50 caracteres | 50 | — | — | aguardando |
| P-902 | agente_nw/sem_condicao.py:1 | 80 | 80 | — | — | Aprovado por Sidarta em 2026-11-08 |
| P-903 | agente_nw/dois.py:1 | 8 | 8 | sempre | — | Aprovado por Sidarta em 2026-11-08 |

## Cortes não analíticos

| NA | Arquivo | Trecho (normalizado) | O que é cortado | Por que não é análise |
|---|---|---|---|---|
| NA-001 | `agente_nw/data.py` | `dia = agora[:10]` | o dia de uma data ISO | é data, não texto |
| NA-002 | `agente_nw/barra.py` | `aviso = " \\| ".join(x[:40] for x in fora)` | rótulo | é aviso |
"""

_PLAN_SINTETICO = """# PLAN

## Decisões em aberto

- [091-2] P-026: teto de 10 fatos sem aprovação · degrada · 2026-11-16
- [080-4] P-021: teto de 200 fatos · degrada · 2026-11-16 · **decidido em 2026-11-20:** aprovar
"""


_DATA = "def f(agora: str) -> str:\n    dia = agora[:10]\n    return dia\n"
_BARRA = 'def f(fora: list[str]) -> str:\n    aviso = " | ".join(x[:40] for x in fora)\n    return aviso\n'


@pytest.fixture
def arvore(tmp_path: Path) -> Path:
    (tmp_path / "docs" / "docs").mkdir(parents=True)
    (tmp_path / PASTA_PRODUCAO).mkdir()
    (tmp_path / REGISTRO).write_text(_REGISTRO_SINTETICO, encoding="utf-8")
    (tmp_path / PLAN).write_text(_PLAN_SINTETICO, encoding="utf-8")
    # o código das duas linhas da tabela não analítica: a árvore de partida não tem erro nenhum
    _codigo(tmp_path, "data.py", _DATA)
    _codigo(tmp_path, "barra.py", _BARRA)
    return tmp_path


def _codigo(raiz: Path, nome: str, fonte: str) -> None:
    (raiz / PASTA_PRODUCAO / nome).write_text(fonte, encoding="utf-8")


def _erros(
    raiz: Path,
    aprovadas: Mapping[Chave, str] | None = None,
    pendentes: Mapping[Chave, tuple[str, str]] | None = None,
) -> list[str]:
    return classificar(raiz, varrer(raiz), aprovadas or {}, pendentes or {})


@pytest.mark.parametrize(
    ("fonte", "regra"),
    [
        ("def f(x: str) -> str:\n    return x[:100]\n", "fatia"),
        ("def f(x: str) -> str:\n    return x[-300:]\n", "fatia"),
        ("def f(x: str) -> str:\n    return x[10:500]\n", "fatia"),
        ("def f(x: str) -> list[str]:\n    return x.split()[:5]\n", "fatia"),
        ("def f(x: str) -> str:\n    return x.split('\\n')[0]\n", "pedaço de divisão"),
        ("import textwrap\n\ndef f(x: str) -> str:\n    return textwrap.shorten(x, 80)\n", "chamada shorten"),
        ("def f(x: str) -> str:\n    return truncate(x)\n", "chamada truncate"),
        ("def f(x: str, max_chars: int) -> str:\n    return x\n", "nome max_chars"),
        (
            "def f(c: object) -> object:\n    return c.execute('SELECT texto FROM item LIMIT 5')\n",
            "LIMIT de SQL",
        ),
        ("def f(q: object) -> object:\n    return q.listar(limite=5)\n", "argumento limite=5"),
        (
            "def f(q: object) -> object:\n    return q.listar(1, _FATOS_NO_PROMPT)\n",
            "teto _FATOS_NO_PROMPT como argumento",
        ),
    ],
)
def test_fatiamento_novo_e_acusado(arvore: Path, fonte: str, regra: str) -> None:
    _codigo(arvore, "novo.py", fonte)
    achados = varrer(arvore)
    assert regra in {a.regra for a in achados}
    erros = _erros(arvore)
    assert len(erros) == 1
    assert erros[0].startswith("corte sem estado em agente_nw/novo.py:")


def test_x_100_inserido_num_arquivo_limpo_faz_o_teste_falhar(arvore: Path) -> None:
    _codigo(arvore, "limpo.py", "def f(x: str) -> str:\n    return x\n")
    assert _erros(arvore) == []
    _codigo(arvore, "limpo.py", "def f(x: str) -> str:\n    return x[:100]\n")
    assert len(_erros(arvore)) == 1


def test_fatia_sem_limite_e_inversao_nao_sao_corte(arvore: Path) -> None:
    _codigo(arvore, "inteiro.py", "def f(x: str) -> tuple[str, str]:\n    return x[:], x[::-1]\n")
    assert [a for a in varrer(arvore) if a.arquivo == "agente_nw/inteiro.py"] == []


def test_a_chave_nao_depende_do_numero_da_linha(arvore: Path) -> None:
    _codigo(arvore, "aprovado.py", "def trecho(x: str) -> str:\n    return x[:2000]\n")
    chave = ("agente_nw/aprovado.py", "return x[:2000]")
    assert _erros(arvore, aprovadas={chave: "P-900"}) == []
    _codigo(arvore, "aprovado.py", '"""Doc."""\n\n\ndef trecho(x: str) -> str:\n    return   x[:2000]\n')
    assert _erros(arvore, aprovadas={chave: "P-900"}) == []


def test_trecho_de_varias_linhas_vira_uma_chave_so(arvore: Path) -> None:
    _codigo(
        arvore,
        "longo.py",
        "def f(xs: list[str], n: int) -> list[str]:\n    return [\n        x for x in xs\n    ][:n]\n",
    )
    (achado,) = [a for a in varrer(arvore) if a.arquivo == "agente_nw/longo.py"]
    assert achado.texto == "return [ x for x in xs ][:n]"


def test_fatiamento_em_excecao_aprovada_passa(arvore: Path) -> None:
    _codigo(arvore, "aprovado.py", "def trecho(x: str) -> str:\n    return x[:2000]\n")
    assert _erros(arvore, aprovadas={("agente_nw/aprovado.py", "return x[:2000]"): "P-900"}) == []


def test_excecao_sem_aprovacao_no_registro_falha(arvore: Path) -> None:
    _codigo(arvore, "sem_aprovacao.py", "def f(x: str) -> str:\n    return x[:50]\n")
    erros = _erros(arvore, aprovadas={("agente_nw/sem_aprovacao.py", "return x[:50]"): "P-901"})
    assert len(erros) == 1
    assert "não tem linha aprovada por Sidarta" in erros[0]


def test_excecao_sem_valor_ou_condicao_falha(arvore: Path) -> None:
    _codigo(arvore, "sem_condicao.py", "def f(x: str) -> str:\n    return x[:80]\n")
    erros = _erros(arvore, aprovadas={("agente_nw/sem_condicao.py", "return x[:80]"): "P-902"})
    assert len(erros) == 1
    assert "não tem valor aprovado e condição" in erros[0]


def test_um_achado_pode_apontar_para_dois_pontos_aprovados(arvore: Path) -> None:
    _codigo(arvore, "dois.py", "def f(a: list[str], b: list[str]) -> list[str]:\n    return a[:5] + b[:8]\n")
    chave = ("agente_nw/dois.py", "return a[:5] + b[:8]")
    assert _erros(arvore, aprovadas={chave: "P-900 P-903"}) == []
    erros = _erros(arvore, aprovadas={chave: "P-900 P-901"})
    assert len(erros) == 1
    assert "P-901, que não tem linha aprovada" in erros[0]


def test_fatiamento_nao_analitico_passa(arvore: Path) -> None:
    """A árvore de partida tem `agora[:10]` e `x[:40]` num aviso com `|`, os dois na tabela não analítica
    (o segundo com a barra escapada na célula)."""
    assert {a.arquivo for a in varrer(arvore)} == {"agente_nw/data.py", "agente_nw/barra.py"}
    assert _erros(arvore) == []


def test_violacao_pendente_com_brief_ainda_nao_entregue_passa(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: str) -> str:\n    return x[:300]\n")
    pendentes = {("agente_nw/pendente.py", "return x[:300]"): ("P-007", "brief 999")}
    assert _erros(arvore, pendentes=pendentes) == []


def test_violacao_pendente_com_brief_entregue_falha(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: str) -> str:\n    return x[:300]\n")
    (arvore / RELATORIOS / "doc_999_correcao_2026-11-20.md").write_text("# DOC 999\n", encoding="utf-8")
    pendentes = {("agente_nw/pendente.py", "return x[:300]"): ("P-007", "brief 999")}
    erros = _erros(arvore, pendentes=pendentes)
    assert len(erros) == 1
    assert "o brief 999 já foi entregue" in erros[0]


def test_violacao_pendente_com_lacuna_aberta_no_plan_passa(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: list[str]) -> list[str]:\n    return x[:10]\n")
    pendentes = {("agente_nw/pendente.py", "return x[:10]"): ("P-026", "[091-2]")}
    assert _erros(arvore, pendentes=pendentes) == []


def test_violacao_pendente_com_lacuna_decidida_falha(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: list[str]) -> list[str]:\n    return x[:200]\n")
    pendentes = {("agente_nw/pendente.py", "return x[:200]"): ("P-021", "[080-4]")}
    erros = _erros(arvore, pendentes=pendentes)
    assert len(erros) == 1
    assert "decidida ou resolvida" in erros[0]


def test_violacao_pendente_com_lacuna_do_brief_em_execucao_vale_pelo_relatorio(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: str) -> str:\n    return x[:100]\n")
    pendentes = {("agente_nw/pendente.py", "return x[:100]"): ("P-028", "[998-1]")}
    erros = _erros(arvore, pendentes=pendentes)
    assert len(erros) == 1
    assert "não existe no PLAN" in erros[0]
    (arvore / RELATORIOS / "doc_998_guarda_2026-11-16.md").write_text(
        "# DOC 998\n\n## Lacunas\n\n| # | Lacuna | Destino | Impacto |\n|---|---|---|---|\n"
        "| 1 | P-028: 100 caracteres | decisão | nice |\n",
        encoding="utf-8",
    )
    assert _erros(arvore, pendentes=pendentes) == []


def test_destino_fora_do_formato_falha(arvore: Path) -> None:
    _codigo(arvore, "pendente.py", "def f(x: str) -> str:\n    return x[:300]\n")
    pendentes = {("agente_nw/pendente.py", "return x[:300]"): ("P-007", "algum dia")}
    erros = _erros(arvore, pendentes=pendentes)
    assert len(erros) == 1
    assert "não é `brief NNN` nem `[NNN-k]`" in erros[0]


def test_entrada_sem_achado_falha(arvore: Path) -> None:
    _codigo(arvore, "data.py", "def f(agora: str) -> str:\n    return agora\n")
    erros = _erros(arvore, aprovadas={("agente_nw/aprovado.py", "return x[:2000]"): "P-900"})
    assert len(erros) == 2  # a aprovada e a linha `agora[:10]` da tabela não analítica, as duas sem código
    assert all("sem achado no código" in erro for erro in erros)


def test_achado_em_dois_estados_falha(arvore: Path) -> None:
    pendentes = {("agente_nw/data.py", "dia = agora[:10]"): ("P-026", "[091-2]")}
    erros = _erros(arvore, pendentes=pendentes)
    assert any("mais de um estado" in erro for erro in erros)


def test_teto_decidido_na_chamada_de_funcao_de_outro_modulo_e_acusado(arvore: Path) -> None:
    _codigo(
        arvore, "consultas.py", "def listar(itens: list[str], limite: int) -> list[str]:\n    return itens\n"
    )
    _codigo(
        arvore,
        "uso.py",
        "from agente_nw import consultas as q\n\n_FATOS = 40\n\n\n"
        "def decide(x: list[str]) -> list[str]:\n    return q.listar(x, _FATOS)\n\n\n"
        "def repassa(x: list[str], limite: int) -> list[str]:\n    return q.listar(x, limite)\n",
    )
    achados = [a for a in varrer(arvore) if a.arquivo == "agente_nw/uso.py"]
    assert [(a.texto, a.regra) for a in achados] == [
        ("return q.listar(x, _FATOS)", "teto limite decidido na chamada de listar")
    ]


def test_mesmo_nome_em_outro_modulo_sem_teto_nao_e_acusado(arvore: Path) -> None:
    _codigo(
        arvore, "consultas.py", "def listar(itens: list[str], limite: int) -> list[str]:\n    return itens\n"
    )
    _codigo(arvore, "outro.py", "def listar(itens: list[str], ordem: int) -> list[str]:\n    return itens\n")
    _codigo(
        arvore,
        "uso.py",
        "from agente_nw import outro\n\n\ndef f(x: list[str]) -> list[str]:\n    return outro.listar(x, 5)\n",
    )
    assert [a for a in varrer(arvore) if a.arquivo == "agente_nw/uso.py"] == []


def test_valor_padrao_de_teto_e_acusado_e_none_nao(arvore: Path) -> None:
    _codigo(
        arvore,
        "padrao.py",
        "def f(x: list[str], limite: int = 5) -> list[str]:\n    return x\n\n\n"
        "def g(x: list[str], limite: int | None = None) -> list[str]:\n    return x\n",
    )
    achados = [a for a in varrer(arvore) if a.arquivo == "agente_nw/padrao.py"]
    assert [(a.texto, a.regra) for a in achados] == [
        ("def f(x: list[str], limite: int = 5) -> list[str]:", "teto padrão limite")
    ]


def test_teto_de_tempo_ou_de_tentativas_nao_e_teto_de_texto(arvore: Path) -> None:
    _codigo(
        arvore,
        "tempo.py",
        "def f(p: object, limiares: object) -> object:\n"
        "    return p.esperar(limiares.tempo_limite_s, limiares.max_tentativas)\n",
    )
    assert [a for a in varrer(arvore) if a.arquivo == "agente_nw/tempo.py"] == []
