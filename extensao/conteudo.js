// Injetado na aba de rede social pelo background.js. Define `globalThis.agenteNw` com funções
// que só LEEM a página (texto, links) e rolam; nunca clicam em nada além de "mostrar mais".
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

  const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

  async function rolar({ rotulos, pausa_s }) {
    window.scrollTo(0, document.body.scrollHeight);
    let rolados = 0;
    for (const el of document.querySelectorAll("*")) {
      if (ehRolavel(getComputedStyle(el).overflowY, el.scrollHeight, el.clientHeight)) {
        el.scrollTop = el.scrollHeight;
        rolados += 1;
      }
    }
    let cliques = 0;
    for (const botao of document.querySelectorAll("button")) {
      if (casaTexto(botao.innerText, rotulos)) {
        botao.click();
        cliques += 1;
      }
    }
    await esperar(Math.max(0, pausa_s) * 1000);
    return { rolados, cliques };
  }

  // [(href absoluto, texto do ancestral mais próximo que pareça um cartão)]
  function links() {
    return Array.from(document.querySelectorAll("a[href]")).map((a) => {
      const cartao = a.closest("li, article, div");
      return [a.href, cartao ? cartao.innerText.trim() : a.innerText || ""];
    });
  }

  function estado(maximo) {
    const texto = document.body ? document.body.innerText : "";
    return { url: location.href, texto: texto.slice(0, maximo) };
  }

  globalThis.agenteNw = { casaTexto, ehRolavel, rolar, links, estado };
})();
