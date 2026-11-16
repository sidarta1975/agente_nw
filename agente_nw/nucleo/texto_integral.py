"""Texto que não cabe numa chamada: dividido em partes que somam exatamente o texto todo (brief 088).

Uma só peça para todo o projeto, como no sergio (`texto_integral.py`) e no trf6:

- **Texto que cabe vai inteiro, sem marcação**: uma parte só, e o prompt de quem chama fica idêntico ao
  de antes deste brief.
- **Texto que não cabe** é dividido em partes consecutivas, preferindo fim de parágrafo, depois de linha,
  de frase e de espaço; só em último caso, no limite exato. Vizinhas se sobrepõem em `SOBREPOSICAO`
  caracteres. `reconstruir` devolve o original byte a byte, e `dividir` confere isso antes de devolver.
- **O orçamento** de cada parte é em tokens, pelo estimador compartilhado do brief 082
  (`estimar_tokens_conservador`): `orcamento_do_texto` desconta do `num_ctx` da tarefa o prompt sem o
  texto. Se o servidor recusar por tamanho, `processar_dividindo` divide o orçamento ao meio, até
  `MAX_DIVISOES` vezes.
- **A consolidação** é de quem chama, com uma regra escrita para cada uso; aqui moram as peças comuns:
  média ponderada de vetores, união ordenada de fatos e conferência de campo único sem voto.

Nenhuma função daqui corta texto: o que não se consegue dividir para caber falha em voz alta.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from agente_nw.nucleo.estimativa_tokens import estimar_tokens_conservador

SOBREPOSICAO = 500
"""Caracteres repetidos do fim de uma parte no começo da seguinte (sergio): um fato escrito em cima do
ponto de divisão aparece inteiro em pelo menos uma das duas partes."""

MAX_DIVISOES = 4
"""Quantas vezes o orçamento cai à metade quando o servidor recusa o prompt por tamanho."""

_FOLGA_TOKENS = 2
"""O estimador não é exatamente aditivo (arredonda cada metade para baixo): prompt sem o texto + parte
pode estimar até 2 tokens a mais do que a soma das duas estimativas."""

_AVISO_MAIOR = "[parte 999 de 999 de um documento maior]\n"
"""O aviso mais longo que uma parte pode receber, para o orçamento já contar com ele."""

_FIM_DE_FRASE = re.compile(r"[.!?…][\"')\]»”’]*\s")


@dataclass(frozen=True)
class Parte:
    """Um trecho consecutivo do texto: `texto == original[inicio:fim]`. `sobreposicao` é quantos
    caracteres do começo repetem o fim da parte anterior (0 na primeira e na parte única)."""

    indice: int
    total: int
    inicio: int
    fim: int
    sobreposicao: int
    texto: str

    @property
    def dividida(self) -> bool:
        return self.total > 1


def aviso(parte: Parte) -> str:
    """ "[parte K de N de um documento maior]" — vai na primeira linha do texto cercado da parte."""
    return f"[parte {parte.indice} de {parte.total} de um documento maior]"


def texto_para_o_prompt(parte: Parte) -> str:
    """O texto da parte como entra no cerco do dado externo: inteiro e sem marcação quando o texto
    coube numa parte só; com o aviso "parte K de N" na primeira linha quando foi dividido."""
    return f"{aviso(parte)}\n{parte.texto}" if parte.dividida else parte.texto


def orcamento_do_texto(janela: int, prompt_sem_texto: str) -> int:
    """Tokens que sobram para o texto de uma parte: o `num_ctx` da tarefa menos o prompt montado com o
    texto vazio, menos o maior aviso "parte K de N" e a folga do estimador. Pode dar zero ou menos
    (o prompt sozinho já não cabe): quem chama manda o texto inteiro e o cliente recusa (brief 082)."""
    return janela - estimar_tokens_conservador(prompt_sem_texto + _AVISO_MAIOR) - _FOLGA_TOKENS


def _maior_prefixo(texto: str, inicio: int, orcamento: int) -> int:
    """Maior `n` com `estimar_tokens_conservador(texto[inicio:inicio + n]) <= orcamento`. A estimativa
    só cresce com o prefixo (caracteres e palavras nunca diminuem), então a busca é binária; como o
    estimador conta caracteres ÷ 3, nenhum prefixo acima de `3 × orcamento + 2` cabe."""
    baixo, alto = 0, min(len(texto) - inicio, 3 * orcamento + 2)
    while baixo < alto:
        meio = (baixo + alto + 1) // 2
        if estimar_tokens_conservador(texto[inicio : inicio + meio]) <= orcamento:
            baixo = meio
        else:
            alto = meio - 1
    return baixo


def _melhor_corte(texto: str, novo: int, limite: int) -> int:
    """Onde termina a parte, em `(novo, limite]`: depois do último fim de parágrafo, de linha, de frase
    ou espaço da segunda metade do trecho novo (para nenhuma parte sair minúscula); sem nenhum, `limite`."""
    piso = novo + (limite - novo) // 2
    janela = texto[piso:limite]
    for separador in ("\n\n", "\n"):
        posicao = janela.rfind(separador)
        if posicao >= 0:
            return piso + posicao + len(separador)
    frases = list(_FIM_DE_FRASE.finditer(janela))
    if frases:
        return piso + frases[-1].end()
    posicao = janela.rfind(" ")
    if posicao >= 0:
        return piso + posicao + 1
    return limite


def dividir(texto: str, orcamento: int) -> list[Parte]:
    """Partes consecutivas de `texto`, cada uma com estimativa de até `orcamento` tokens, que somam o
    texto todo. Texto que cabe (vazio inclusive) volta numa parte só, idêntica ao original.

    A sobreposição é `SOBREPOSICAO`, menor só quando a parte é curta demais para ela (metade da parte) ou
    quando o orçamento não deixa espaço para texto novo depois dela (aí a parte começa sem sobreposição).
    Levanta `ValueError` com orçamento abaixo de 1, ou se a reconstrução não reproduzir o original."""
    if orcamento < 1:
        raise ValueError(f"orçamento de {orcamento} tokens: nenhuma parte cabe")
    trechos: list[tuple[int, int, int]] = []
    inicio, novo = 0, 0
    while True:
        limite = inicio + _maior_prefixo(texto, inicio, orcamento)
        if limite <= novo:
            inicio = novo
            limite = max(inicio + _maior_prefixo(texto, inicio, orcamento), novo + 1)
        if limite >= len(texto):
            trechos.append((inicio, len(texto), novo - inicio))
            break
        fim = _melhor_corte(texto, novo, limite)
        trechos.append((inicio, fim, novo - inicio))
        novo = fim
        inicio = fim - min(SOBREPOSICAO, (fim - inicio) // 2)

    total = len(trechos)
    partes = [
        Parte(indice, total, ini, fim, sobre, texto[ini:fim])
        for indice, (ini, fim, sobre) in enumerate(trechos, start=1)
    ]
    if reconstruir(partes) != texto:
        raise ValueError("as partes não reproduzem o texto original")
    return partes


def reconstruir(partes: Sequence[Parte]) -> str:
    """O texto original a partir das partes, descontada a sobreposição de cada uma."""
    return "".join(parte.texto[parte.sobreposicao :] for parte in partes)


def processar_dividindo[R](
    texto: str,
    orcamento: int,
    processar: Callable[[list[Parte]], R],
    recusa: type[BaseException],
    ao_refazer: Callable[[BaseException], None] | None = None,
) -> tuple[R, list[Parte]]:
    """Divide `texto` com `orcamento` e chama `processar(partes)`. Se `processar` levantar `recusa` (o
    servidor recusou um prompt por tamanho), o orçamento cai à metade e o texto é dividido e processado
    de novo, do começo, até `MAX_DIVISOES` vezes. Para antes, relançando a recusa, quando a metade não
    muda a divisão (o texto já cabia numa parte menor que ela: quem estoura é o resto do prompt) ou fica
    abaixo de 1 token. `ao_refazer` recebe cada recusa que foi superada por uma nova divisão.

    Orçamento abaixo de 1 (o prompt sem o texto já não cabe): o texto vai inteiro, numa parte só, para o
    cliente recusar em voz alta (brief 082)."""
    if orcamento < 1:
        unica = [Parte(1, 1, 0, len(texto), 0, texto)]
        return processar(unica), unica
    partes = dividir(texto, orcamento)
    for divisao in range(MAX_DIVISOES + 1):
        try:
            return processar(partes), partes
        except recusa as erro:
            orcamento //= 2
            if divisao == MAX_DIVISOES or orcamento < 1:
                raise
            novas = dividir(texto, orcamento)
            if [(p.inicio, p.fim) for p in novas] == [(p.inicio, p.fim) for p in partes]:
                raise
            if ao_refazer is not None:
                ao_refazer(erro)
            partes = novas
    raise AssertionError("inalcançável")  # pragma: no cover


# --- consolidação -----------------------------------------------------------------------------------


def consolidar_vetores(vetores: Sequence[Sequence[float]], pesos: Sequence[int]) -> list[float]:
    """Média dos vetores ponderada por `pesos` (o número de caracteres de cada parte), normalizada para
    norma 1 (trf6). Vetor nulo é erro: não há direção para devolver."""
    if not vetores or len(vetores) != len(pesos):
        raise ValueError("consolidar_vetores pede um peso por vetor, e pelo menos um vetor")
    dimensao = len(vetores[0])
    if any(len(vetor) != dimensao for vetor in vetores):
        raise ValueError("vetores de tamanhos diferentes")
    soma = [
        math.fsum(peso * vetor[i] for vetor, peso in zip(vetores, pesos, strict=True))
        for i in range(dimensao)
    ]
    norma = math.sqrt(math.fsum(valor * valor for valor in soma))
    if norma == 0:
        raise ValueError("média ponderada nula")
    return [valor / norma for valor in soma]


@dataclass(frozen=True)
class DeParte[T]:
    """Um valor consolidado e a parte (1 a N) onde ele apareceu primeiro."""

    parte: int
    valor: T


def consolidar_fatos[T](por_parte: Sequence[Sequence[T]]) -> list[DeParte[T]]:
    """União ordenada das listas de cada parte (ordem das partes, depois a ordem dentro de cada uma),
    sem repetição exata (`==`), guardando a parte de origem. Valores parecidos mas não iguais ficam os
    dois: decidir que são o mesmo fato seria adivinhar."""
    unidos: list[DeParte[T]] = []
    for numero, valores in enumerate(por_parte, start=1):
        for valor in valores:
            if not any(existente.valor == valor for existente in unidos):
                unidos.append(DeParte(numero, valor))
    return unidos


@dataclass(frozen=True)
class Divergencia:
    """Campo único (como "cidade") com valores diferentes em partes diferentes."""

    campo: str
    valores: tuple[DeParte[object], ...]

    def descrever(self) -> str:
        """Só o campo e as partes, sem os valores (o texto do erro aparece na listagem da revisão)."""
        partes = ", ".join(str(valor.parte) for valor in self.valores)
        return f"campo {self.campo} (partes {partes})"

    def descrever_com_valores(self) -> str:
        valores = "; ".join(f"parte {valor.parte} = {valor.valor!r}" for valor in self.valores)
        return f"- {self.campo}: {valores}"


def consolidar_unicos(
    por_parte: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], list[Divergencia]]:
    """Campos de valor único de cada parte (sem os ausentes). O valor que todas as partes que falaram do
    campo dão igual é aceito; valores diferentes **não são decididos por voto**: o campo sai do resultado
    e vira uma `Divergencia`, para a revisão humana."""
    vistos: dict[str, list[DeParte[object]]] = {}
    for numero, campos in enumerate(por_parte, start=1):
        for campo, valor in campos.items():
            lista = vistos.setdefault(campo, [])
            if not any(existente.valor == valor for existente in lista):
                lista.append(DeParte(numero, valor))
    valores = {campo: lista[0].valor for campo, lista in vistos.items() if len(lista) == 1}
    divergencias = [Divergencia(campo, tuple(lista)) for campo, lista in vistos.items() if len(lista) > 1]
    return valores, divergencias
