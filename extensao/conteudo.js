// Injetado na aba de rede social pelo background.js. Define `globalThis.agenteNw` com funções
// que só LEEM a página (texto, links) e rolam; nunca clicam em nada além de "mostrar mais" e do link que abre a própria lista (…/following/).
// As funções de decisão (casaTexto, ehRolavel) são puras e não tocam o DOM.
(() => {
  if (globalThis.agenteNw) return;

  // Puro: o texto do botão começa com algum dos rótulos de "mostrar mais"?
  function casaTexto(texto, rotulos) {
    const baixo = (texto || "").trim().toLowerCase();
    return baixo.length > 0 && rotulos.some((r) => baixo.startsWith(r.toLowerCase()));
  }

  // Puro: um elemento com rolagem própria (painel, janela sobreposta, lista interna).
  function ehRolavel(overflowY, scrollHeight, clientHeight) {
    return (overflowY === "auto" || overflowY === "scroll") && scrollHeight > clientHeight + 20;
  }

  // Puro: o caminho termina em /following ou /followers (uma lista de pessoas)?
  function ehCaminhoDeLista(caminho) {
    return /\/(following|followers)\/?$/.test(caminho || "");
  }

  // Instagram: abrir /usuario/following/ mostra o perfil; a lista só aparece (em janela) ao clicar
  // no link da mesma lista. Clica apenas num link cujo caminho é o da página atual (navegação, sem
  // efeito na conta) e só se ainda não houver janela aberta.
  let jaTentouAbrirJanela = false;
  function abrirJanelaDaLista() {
    if (jaTentouAbrirJanela || !/(^|\.)instagram\.com$/.test(location.hostname)) return 0;
    if (!ehCaminhoDeLista(location.pathname) || document.querySelector('[role="dialog"]')) return 0;
    jaTentouAbrirJanela = true;
    const alvo = location.pathname.replace(/\/$/, "");
    for (const a of document.querySelectorAll("a[href]")) {
      if (new URL(a.href, location.href).pathname.replace(/\/$/, "") === alvo) {
        a.click();
        return 1;
      }
    }
    return 0;
  }

  const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

  // Tudo o que já apareceu na página: listas que reciclam as linhas (Instagram) perdem as pessoas
  // que saem da tela, então cada passo da rolagem guarda os links antes de seguir.
  const vistos = new Map(); // href absoluto -> texto do cartão mais longo
  function coletar() {
    for (const a of document.querySelectorAll("a[href]")) {
      const cartao = a.closest("li, article, div");
      const texto = cartao ? cartao.innerText.trim() : a.innerText || "";
      const antes = vistos.get(a.href);
      if (antes === undefined || texto.length > antes.length) vistos.set(a.href, texto);
    }
  }

  // Instagram: a janela de seguidos não busca a página seguinte ao rolar (spinner eterno, nenhuma
  // requisição). A lista vem do mesmo endereço que a própria página usa, chamado de dentro da aba
  // logada: só LEITURA (GET), 12 por página, com pausa entre páginas. Guarda o ponto em que parou,
  // então cada chamada de `rolar` avança algumas páginas (a tarefa tem tempo limite).
  const IG_APP_ID = "936619743392459";
  const IG_PAGINAS_POR_CHAMADA = 8;
  const ig = { id: null, cursor: "", fim: false, falhou: false, total: 0 };

  async function igJson(url) {
    const resposta = await fetch(url, {
      credentials: "include",
      headers: { "x-ig-app-id": IG_APP_ID, "x-requested-with": "XMLHttpRequest" },
    });
    if (!resposta.ok) throw new Error("HTTP " + resposta.status);
    return resposta.json();
  }

  async function igIdDoUsuario(usuario) {
    try {
      const dados = await igJson("/api/v1/users/web_profile_info/?username=" + encodeURIComponent(usuario));
      const id = dados && dados.data && dados.data.user && dados.data.user.id;
      if (id) return String(id);
    } catch (e) {
      // cai para o HTML do perfil
    }
    const achado = /"profile_id":"(\d+)"/.exec(document.documentElement.innerHTML);
    return achado ? achado[1] : null;
  }

  // true = a lista está sendo lida pela API (não precisa rolar); false = usar a rolagem normal.
  async function paginarSeguidosInstagram({ maximo_entradas, pausa_pagina_s }) {
    const caminho = location.pathname;
    if (!/(^|\.)instagram\.com$/.test(location.hostname) || !/\/following\/?$/.test(caminho)) return false;
    if (ig.falhou) return false;
    if (ig.fim) return true;
    try {
      if (!ig.id) {
        const usuario = caminho.split("/").filter(Boolean)[0];
        ig.id = await igIdDoUsuario(usuario);
        if (!ig.id) throw new Error("id do usuário não encontrado");
      }
      const limite = maximo_entradas || 2000;
      for (let i = 0; i < IG_PAGINAS_POR_CHAMADA && !ig.fim && ig.total < limite; i += 1) {
        const url =
          "/api/v1/friendships/" + ig.id + "/following/?count=12" +
          (ig.cursor ? "&max_id=" + encodeURIComponent(ig.cursor) : "");
        const dados = await igJson(url);
        for (const u of dados.users || []) {
          vistos.set("https://www.instagram.com/" + u.username + "/", (u.username + "\n" + (u.full_name || "")).trim());
          ig.total += 1;
        }
        ig.cursor = dados.next_max_id ? String(dados.next_max_id) : "";
        ig.fim = !dados.has_more || !ig.cursor || ig.total >= limite;
        if (!ig.fim) await esperar(Math.max(0, pausa_pagina_s || 0) * 1000);
      }
      return true;
    } catch (e) {
      ig.falhou = true; // volta para a rolagem da janela
      return false;
    }
  }

  const MAX_PASSOS = 40;
  async function rolarPainel(el) {
    for (let passo = 0; passo < MAX_PASSOS; passo += 1) {
      const fim = el.scrollHeight - el.clientHeight;
      if (el.scrollTop >= fim - 2) break;
      el.scrollTop = Math.min(fim, el.scrollTop + el.clientHeight * 0.8);
      await esperar(250);
      coletar();
    }
    el.scrollTop = el.scrollHeight;
  }

  async function rolar({ rotulos, pausa_s, maximo_entradas, pausa_pagina_s }) {
    coletar();
    if (await paginarSeguidosInstagram({ maximo_entradas, pausa_pagina_s })) {
      return { rolados: 0, cliques: 0 };
    }
    window.scrollTo(0, document.body.scrollHeight);
    let rolados = 0;
    for (const el of Array.from(document.querySelectorAll("*"))) {
      if (ehRolavel(getComputedStyle(el).overflowY, el.scrollHeight, el.clientHeight)) {
        await rolarPainel(el);
        rolados += 1;
      }
    }
    let cliques = abrirJanelaDaLista();
    for (const botao of document.querySelectorAll("button")) {
      if (casaTexto(botao.innerText, rotulos)) {
        botao.click();
        cliques += 1;
      }
    }
    await esperar(Math.max(0, pausa_s) * 1000);
    coletar();
    return { rolados, cliques };
  }

  // [(href absoluto, texto do ancestral mais próximo que pareça um cartão)]
  function links() {
    coletar();
    return Array.from(vistos.entries());
  }

  function estado(maximo) {
    const texto = document.body ? document.body.innerText : "";
    return { url: location.href, texto: texto.slice(0, maximo) };
  }

  globalThis.agenteNw = { casaTexto, ehRolavel, ehCaminhoDeLista, rolar, links, estado };
})();
