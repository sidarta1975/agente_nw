// Service worker da extensão agente_nw. Recebe tarefas da página-ponte e as executa com
// chrome.tabs / chrome.scripting. Conjunto FIXO de ações: ola, abrir, estado, rolar, links, fechar.
// Nunca executa código vindo do programa e só age em linkedin, instagram, facebook e x.
const ORIGEM_PONTE = "http://127.0.0.1:8766/";
const REDES = {
  "linkedin.com": "linkedin",
  "instagram.com": "instagram",
  "facebook.com": "facebook",
  "x.com": "x",
};
const abas = {}; // rede -> id da aba (uma por rede)
const ultimaAbertura = {}; // rede -> instante da última abertura

const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

function redeDaUrl(url) {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    const achada = Object.keys(REDES).find((d) => host === d || host.endsWith("." + d));
    return achada ? REDES[achada] : null;
  } catch (e) {
    return null;
  }
}

function origemValida(remetente) {
  const url = remetente.url || (remetente.tab && remetente.tab.url) || "";
  return url.startsWith(ORIGEM_PONTE);
}

function carregada(abaId, limiteMs) {
  return new Promise((resolver) => {
    const fim = setTimeout(() => {
      chrome.tabs.onUpdated.removeListener(ouvinte);
      resolver();
    }, limiteMs);
    function ouvinte(id, mudanca) {
      if (id === abaId && mudanca.status === "complete") {
        clearTimeout(fim);
        chrome.tabs.onUpdated.removeListener(ouvinte);
        resolver();
      }
    }
    chrome.tabs.onUpdated.addListener(ouvinte);
    chrome.tabs.get(abaId).then((aba) => {
      if (aba.status === "complete") {
        clearTimeout(fim);
        chrome.tabs.onUpdated.removeListener(ouvinte);
        resolver();
      }
    });
  });
}

async function abrir({ url, ativa, pausa_s }) {
  const rede = redeDaUrl(url);
  if (!rede) throw new Error("endereço fora das redes permitidas");

  // Nunca mais de uma aba de rede social por vez.
  for (const [outra, id] of Object.entries(abas)) {
    if (outra !== rede) {
      await chrome.tabs.remove(id).catch(() => {});
      delete abas[outra];
    }
  }
  const decorrido = Date.now() - (ultimaAbertura[rede] || 0);
  if (decorrido < pausa_s * 1000) await esperar(pausa_s * 1000 - decorrido);

  let aba = null;
  if (abas[rede] !== undefined) {
    aba = await chrome.tabs.update(abas[rede], { url, active: ativa }).catch(() => null);
  }
  if (!aba) aba = await chrome.tabs.create({ url, active: ativa });
  abas[rede] = aba.id;
  ultimaAbertura[rede] = Date.now();
  await carregada(aba.id, 30000);
  return { aba_id: aba.id };
}

async function noConteudo(abaId, func, args) {
  await chrome.scripting.executeScript({ target: { tabId: abaId }, files: ["conteudo.js"] });
  const [resultado] = await chrome.scripting.executeScript({ target: { tabId: abaId }, func, args });
  return resultado.result;
}

// Uma navegação no meio da leitura (ex.: volta do login) derruba a injeção: tenta de novo uma vez.
async function comNovaTentativa(abaId, func, args) {
  try {
    return await noConteudo(abaId, func, args);
  } catch (e) {
    await carregada(abaId, 10000);
    return await noConteudo(abaId, func, args);
  }
}

async function tratar(tarefa) {
  switch (tarefa.acao) {
    case "ola":
      return { versao: chrome.runtime.getManifest().version };
    case "abrir":
      return await abrir(tarefa);
    case "estado":
      return await comNovaTentativa(tarefa.aba_id, (max) => globalThis.agenteNw.estado(max), [
        tarefa.maximo,
      ]);
    case "rolar":
      return await comNovaTentativa(
        tarefa.aba_id,
        (opcoes) => globalThis.agenteNw.rolar(opcoes),
        [
          {
            rotulos: tarefa.rotulos,
            pausa_s: tarefa.pausa_s,
            maximo_entradas: tarefa.maximo_entradas,
            pausa_pagina_s: tarefa.pausa_pagina_s,
          },
        ],
      );
    case "links":
      return { links: await comNovaTentativa(tarefa.aba_id, () => globalThis.agenteNw.links(), []) };
    case "fechar":
      await chrome.tabs.remove(tarefa.aba_id).catch(() => {});
      for (const [rede, id] of Object.entries(abas)) {
        if (id === tarefa.aba_id) delete abas[rede];
      }
      return {};
    default:
      throw new Error("ação desconhecida: " + tarefa.acao);
  }
}

function atender(mensagem, remetente, responder) {
  if (!origemValida(remetente) || !mensagem || !mensagem.tarefa) return false;
  tratar(mensagem.tarefa)
    .then((dados) => responder({ ok: true, dados }))
    .catch((erro) => responder({ ok: false, erro: String((erro && erro.message) || erro) }));
  return true; // resposta assíncrona
}

chrome.runtime.onMessageExternal.addListener(atender);
chrome.runtime.onMessage.addListener(atender);
