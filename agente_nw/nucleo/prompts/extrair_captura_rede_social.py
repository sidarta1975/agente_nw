"""Prompt da tarefa `extrair_captura_rede_social`: um bloco de texto capturado da página de uma rede social.

Saiu de `coleta/capturas/extrator.py` no brief 088, com o texto do prompt sem mudança nenhuma, para ter
`VERSAO` como todo módulo deste pacote (brief 066). O bloco inteiro continua entre aspas, sem o cerco do
dado externo (dívida [068-2], fora deste brief); só a parte de um bloco dividido entra cercada, com o
aviso "parte K de N" dentro do cerco.
"""

from __future__ import annotations

from agente_nw.nucleo.prompts.seguranca import INSTRUCAO_DADO_EXTERNO, cercar_dado_externo
from agente_nw.nucleo.texto_integral import Parte, texto_para_o_prompt

VERSAO = "2026-11-16-1"
"""Brief 088: bloco que não cabe numa chamada chega em partes. Bloco que cabe produz o mesmo prompt de
antes (o módulo antigo não tinha versão), caractere por caractere."""


def construir_prompt(bloco: str, rede: str) -> str:
    return f"""\
Você recebe um bloco de texto capturado da página de uma rede social ({rede}).
O bloco pode ser uma publicação, uma curtida, um comentário, uma reação — ou
pode ser texto de interface (menu, rodapé, propaganda, sugestão de conexão,
notificação do sistema).

Responda só com um objeto JSON, sem texto antes ou depois, com este formato:
{{"descartar": bool, "data_do_fato": "AAAA-MM-DD" ou null, "tipo": "...", "conteudo": "..."}}

Se o bloco NÃO for uma publicação/curtida/comentário atribuível a alguém
(por exemplo: menu de navegação, botão, propaganda, sugestão, texto de
sistema, campo vazio), devolva {{"descartar": true, "data_do_fato": null,
"tipo": "", "conteudo": ""}}.

Se for uma publicação/curtida/comentário, devolva descartar=false e preencha:
- data_do_fato: só se houver data explícita no texto (formato AAAA-MM-DD).
  Datas relativas ("2 dias atrás", "há 3 horas") devem devolver null.
- tipo: uma palavra curta que classifique — "publicacao", "curtida",
  "comentario", "reacao", "repost".
- conteudo: o texto essencial da publicação, limpo, sem sugestões laterais
  nem prompts de interface. Sem chamar atenção do modelo para nada que não
  esteja no bloco.

Bloco a processar:
"{bloco}"
"""


def construir_prompt_de_parte(parte: Parte, rede: str) -> str:
    """O mesmo prompt para uma parte de um bloco dividido: a parte vai cercada como dado externo, com o
    aviso "parte K de N" na primeira linha do cerco. Parte única é o bloco inteiro: prompt de antes."""
    if not parte.dividida:
        return construir_prompt(parte.texto, rede)
    inteiro = construir_prompt(parte.texto, rede)
    final = f'Bloco a processar:\n"{parte.texto}"\n'
    assert inteiro.endswith(final)
    cerco = cercar_dado_externo(texto_para_o_prompt(parte))
    return f"{inteiro[: -len(final)]}{INSTRUCAO_DADO_EXTERNO}\n\nBloco a processar:\n{cerco}\n"
