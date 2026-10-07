// Mostra a versão atual (a mesma do servidor) em todos os sítios marcados
// com class="versao-site". O texto que lá está é só o valor de reserva.
(function () {
    "use strict";
    fetch("/api/versao")
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (dados) {
            if (!dados || !dados.versao) return;
            document.querySelectorAll(".versao-site").forEach(function (el) {
                el.textContent = "v" + dados.versao;
            });
        })
        .catch(function () { /* sem rede: fica o valor de reserva */ });
})();
