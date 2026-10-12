// Roda só na página-ponte (http://127.0.0.1:8766). Repassa à extensão as tarefas que a página
// recebe do programa e devolve a resposta. Serve de via alternativa quando o Chrome não expõe
// `chrome.runtime` à página (externally_connectable).
window.addEventListener("message", (evento) => {
  const dados = evento.data;
  if (evento.source !== window || !dados || dados.tipo !== "agente_nw_tarefa") return;
  chrome.runtime.sendMessage({ tarefa: dados.tarefa }, (resposta) => {
    const erro = chrome.runtime.lastError ? chrome.runtime.lastError.message : null;
    window.postMessage(
      {
        tipo: "agente_nw_resposta",
        id: dados.id,
        resposta: resposta || { ok: false, erro: erro || "a extensão não respondeu" },
      },
      "*",
    );
  });
});
