// Monitor de Vagas & Notícias — frontend puro (sem framework), tal como o
// resto do portefólio. Sem autenticação: é um painel pessoal.

const ESTADOS_LABEL = {
    por_candidatar: 'Por candidatar',
    candidatei_me: 'Já me candidatei',
    resposta_recebida: 'Com resposta',
    arquivada: 'Arquivada',
};

function formatarData(isoString) {
    if (!isoString) return 'Data não indicada';
    const data = new Date(isoString);
    if (Number.isNaN(data.getTime())) return 'Data não indicada';
    return data.toLocaleDateString('pt-PT', { day: '2-digit', month: 'short', year: 'numeric' });
}

async function pedirJSON(url, opcoes) {
    const resposta = await fetch(url, opcoes);
    if (!resposta.ok) {
        throw new Error(`Pedido falhou (${resposta.status}) a ${url}`);
    }
    return resposta.json();
}

// ---------- Resumo ----------

async function carregarResumo() {
    try {
        const resumo = await pedirJSON('/api/resumo');
        document.getElementById('resumoTotalVagas').textContent = resumo.total_vagas;
        document.getElementById('resumoPorCandidatar').textContent = resumo.vagas_por_candidatar;
        document.getElementById('resumoCandidateiMe').textContent = resumo.vagas_candidatei_me;
        document.getElementById('resumoRespostaRecebida').textContent = resumo.vagas_resposta_recebida;
        document.getElementById('resumoTotalNoticias').textContent = resumo.total_noticias;
    } catch (erro) {
        console.error('Não foi possível carregar o resumo', erro);
    }
}

// ---------- Vagas ----------

function construirCartaoVaga(vaga) {
    const modelo = document.getElementById('modeloVaga').content.cloneNode(true);
    const cartao = modelo.querySelector('.cartao-vaga');

    cartao.querySelector('h3').textContent = vaga.titulo;

    const etiqueta = cartao.querySelector('.etiqueta-estado');
    etiqueta.textContent = ESTADOS_LABEL[vaga.estado] || vaga.estado;
    etiqueta.dataset.estado = vaga.estado;

    cartao.querySelector('.cartao-vaga-empresa').textContent = vaga.empresa;

    const localizacoes = (vaga.localizacoes || []).join(', ') || 'Localização não indicada';
    const salario = vaga.salario_min && vaga.salario_max
        ? `${vaga.salario_min}€ – ${vaga.salario_max}€`
        : 'Salário não indicado';
    cartao.querySelector('.cartao-vaga-detalhes').textContent =
        `${localizacoes} · ${salario} · publicada em ${formatarData(vaga.publicado_em)}`;

    const link = cartao.querySelector('.cartao-vaga-link');
    link.href = vaga.link;

    const seletor = cartao.querySelector('.seletor-estado');
    seletor.value = vaga.estado;
    seletor.addEventListener('change', () => atualizarEstadoVaga(vaga.id, seletor.value, etiqueta));

    return cartao;
}

async function atualizarEstadoVaga(vagaId, novoEstado, elementoEtiqueta) {
    try {
        await pedirJSON(`/api/vagas/${vagaId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: novoEstado }),
        });
        elementoEtiqueta.textContent = ESTADOS_LABEL[novoEstado] || novoEstado;
        elementoEtiqueta.dataset.estado = novoEstado;
        carregarResumo();
    } catch (erro) {
        console.error('Não foi possível atualizar o estado da vaga', erro);
        alert('Não foi possível guardar esta alteração. Tenta novamente.');
    }
}

async function carregarVagas() {
    const lista = document.getElementById('listaVagas');
    const texto = document.getElementById('filtroTextoVagas').value.trim();
    const estado = document.getElementById('filtroEstadoVagas').value;

    const parametros = new URLSearchParams();
    if (texto) parametros.set('texto', texto);
    if (estado) parametros.set('estado', estado);

    try {
        const vagas = await pedirJSON(`/api/vagas?${parametros.toString()}`);
        lista.innerHTML = '';
        if (vagas.length === 0) {
            lista.innerHTML = '<p class="estado-vazio">Nenhuma vaga encontrada com estes filtros.</p>';
            return;
        }
        vagas.forEach((vaga) => lista.appendChild(construirCartaoVaga(vaga)));
    } catch (erro) {
        console.error('Não foi possível carregar as vagas', erro);
        lista.innerHTML = '<p class="estado-vazio">Não foi possível carregar as vagas agora.</p>';
    }
}

// ---------- Notícias ----------

function construirCartaoNoticia(noticia) {
    const modelo = document.getElementById('modeloNoticia').content.cloneNode(true);
    const cartao = modelo.querySelector('.cartao-noticia');

    cartao.querySelector('.cartao-noticia-fonte').textContent = noticia.fonte;

    const link = cartao.querySelector('h3 a');
    link.textContent = noticia.titulo;
    link.href = noticia.link;

    const resumo = cartao.querySelector('.cartao-noticia-resumo');
    if (noticia.resumo) {
        resumo.textContent = noticia.resumo.replace(/<[^>]*>/g, '');
    } else {
        resumo.remove();
    }

    cartao.querySelector('.cartao-noticia-data').textContent = formatarData(noticia.publicado_em);

    return cartao;
}

async function carregarNoticias() {
    const lista = document.getElementById('listaNoticias');
    const texto = document.getElementById('filtroTextoNoticias').value.trim();

    const parametros = new URLSearchParams();
    if (texto) parametros.set('texto', texto);

    try {
        const noticias = await pedirJSON(`/api/noticias?${parametros.toString()}`);
        lista.innerHTML = '';
        if (noticias.length === 0) {
            lista.innerHTML = '<p class="estado-vazio">Nenhuma notícia encontrada.</p>';
            return;
        }
        noticias.forEach((noticia) => lista.appendChild(construirCartaoNoticia(noticia)));
    } catch (erro) {
        console.error('Não foi possível carregar as notícias', erro);
        lista.innerHTML = '<p class="estado-vazio">Não foi possível carregar as notícias agora.</p>';
    }
}

// ---------- Abas ----------

function configurarAbas() {
    const abas = document.querySelectorAll('.aba');
    abas.forEach((aba) => {
        aba.addEventListener('click', () => {
            abas.forEach((a) => {
                a.classList.remove('aba-ativa');
                a.setAttribute('aria-selected', 'false');
            });
            aba.classList.add('aba-ativa');
            aba.setAttribute('aria-selected', 'true');

            document.querySelectorAll('.painel').forEach((painel) => {
                painel.hidden = painel.dataset.painel !== aba.dataset.aba;
            });
        });
    });
}

// ---------- Filtros (com debounce simples) ----------

function comAtraso(fn, atrasoMs = 300) {
    let temporizador;
    return (...args) => {
        clearTimeout(temporizador);
        temporizador = setTimeout(() => fn(...args), atrasoMs);
    };
}

function configurarFiltros() {
    document.getElementById('filtroTextoVagas').addEventListener('input', comAtraso(carregarVagas));
    document.getElementById('filtroEstadoVagas').addEventListener('change', carregarVagas);
    document.getElementById('filtroTextoNoticias').addEventListener('input', comAtraso(carregarNoticias));
}

document.addEventListener('DOMContentLoaded', () => {
    configurarAbas();
    configurarFiltros();
    carregarResumo();
    carregarVagas();
    carregarNoticias();
});
