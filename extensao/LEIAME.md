# Extensão do Chrome — agente_nw

O agente_nw lê listas, buscas e perfis de rede social **no seu Chrome**, já logado, por esta
extensão. Não existe navegador separado nem segundo login.

## Instalar (uma vez)

1. Rode `agente_nw extensao instalar` (mostra o caminho desta pasta).
2. No Chrome (ou Brave, Edge, Arc, Vivaldi), abra `chrome://extensions`.
3. Ligue o **Modo do desenvolvedor** (canto superior direito).
4. Clique em **Carregar sem compactação** e escolha esta pasta (`extensao/`).
5. Confira com `agente_nw extensao testar`: deve responder OK com a versão.

O ID da extensão é fixo (a `key` do `manifest.json`), por isso a página-ponte sabe com quem falar.
Firefox e Safari não são suportados.

## Como funciona

- O programa sobe uma **ponte** local em `127.0.0.1:8766` e abre no navegador a página
  "agente_nw — ponte". **Deixe essa aba aberta enquanto o programa estiver lendo.**
- A página-ponte busca as tarefas no programa e as passa à extensão; a extensão abre uma aba da
  rede **em segundo plano**, rola, lê o texto e os links e devolve tudo.
- Só estas ações existem: `ola`, `abrir`, `estado`, `rolar`, `links`, `fechar`. Nada de curtir,
  seguir ou enviar. A extensão só atua em linkedin.com, instagram.com, facebook.com e x.com.
- Nunca mais de uma aba de rede social por vez, com pausa entre páginas da mesma rede.
- Nada roda sem um comando seu (`pedir`, `listas atualizar`, console).

## Se algo não responder

- `agente_nw extensao testar` diz se a extensão respondeu.
- Se a aba da ponte não abriu no Chrome (navegador padrão diferente), copie o endereço que o
  programa imprime (`Ponte do navegador: …`) e cole no Chrome.
- Sem sessão numa rede: entre nela no seu Chrome normalmente e repita o comando.
- Se uma rede carregar pela metade com a aba em segundo plano, ponha
  `extensao.aba_em_segundo_plano: false` em `config/limiares.yaml`.
- Se uma rede passar a bloquear, ponha o nome dela em `listas.redes_so_por_link` (ex.: `[x]`):
  ela volta a entrar só por link colado.
