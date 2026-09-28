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

const prefereMenosMovimento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function animarNumero(elemento, valorFinal) {
    if (!elemento) return;
    const alvo = Number(valorFinal);
    if (!Number.isFinite(alvo) || prefereMenosMovimento) {
        elemento.textContent = valorFinal;
        return;
    }
    const duracao = 700;
    const inicio = performance.now();
    function passo(agora) {
        const progresso = Math.min((agora - inicio) / duracao, 1);
        const suavizado = 1 - Math.pow(1 - progresso, 3);
        elemento.textContent = Math.round(alvo * suavizado);
        if (progresso < 1) requestAnimationFrame(passo);
        else elemento.textContent = alvo;
    }
    requestAnimationFrame(passo);
}

async function carregarResumo() {
    try {
        const resumo = await pedirJSON('/api/resumo');
        animarNumero(document.getElementById('resumoTotalVagas'), resumo.total_vagas);
        animarNumero(document.getElementById('resumoPorCandidatar'), resumo.vagas_por_candidatar);
        animarNumero(document.getElementById('resumoCandidateiMe'), resumo.vagas_candidatei_me);
        animarNumero(document.getElementById('resumoRespostaRecebida'), resumo.vagas_resposta_recebida);
        animarNumero(document.getElementById('resumoTotalNoticias'), resumo.total_noticias);
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
    cartao.querySelector('.etiqueta-fonte').textContent = vaga.fonte || 'Fonte não indicada';

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
    seletor.addEventListener('change', () => atualizarEstadoVaga(vaga.id, seletor.value, etiqueta, cartao));

    return cartao;
}

async function atualizarEstadoVaga(vagaId, novoEstado, elementoEtiqueta, elementoCartao) {
    try {
        await pedirJSON(`/api/vagas/${vagaId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ estado: novoEstado }),
        });
        elementoEtiqueta.textContent = ESTADOS_LABEL[novoEstado] || novoEstado;
        elementoEtiqueta.dataset.estado = novoEstado;
        carregarResumo();

        // Uma resposta a uma candidatura é a melhor notícia deste painel —
        // merece um pequeno destaque, não só uma mudança silenciosa de cor.
        if (novoEstado === 'resposta_recebida' && elementoCartao) {
            elementoCartao.classList.add('a-celebrar');
            elementoEtiqueta.classList.add('a-celebrar');
            setTimeout(() => {
                elementoCartao.classList.remove('a-celebrar');
                elementoEtiqueta.classList.remove('a-celebrar');
            }, 1000);
        }
    } catch (erro) {
        console.error('Não foi possível atualizar o estado da vaga', erro);
        alert('Não foi possível guardar esta alteração. Tenta novamente.');
    }
}

function preencherOpcoes(seletor, valores) {
    const atual = seletor.value;
    // remove todas as opções exceto a primeira ("Todos/Todas...")
    while (seletor.options.length > 1) {
        seletor.remove(1);
    }
    valores.forEach((valor) => {
        const opcao = document.createElement('option');
        opcao.value = valor;
        opcao.textContent = valor;
        seletor.appendChild(opcao);
    });
    // mantém a seleção anterior se ainda for válida
    if (valores.includes(atual)) {
        seletor.value = atual;
    }
}

async function carregarOpcoesVagas() {
    try {
        const opcoes = await pedirJSON('/api/opcoes/vagas');
        preencherOpcoes(document.getElementById('filtroLocalizacaoVagas'), opcoes.localizacoes);
        preencherOpcoes(document.getElementById('filtroTermoVagas'), opcoes.termos_origem);
        preencherOpcoes(document.getElementById('filtroFonteVagas'), opcoes.fontes);
    } catch (erro) {
        console.error('Não foi possível carregar as opções de filtro das vagas', erro);
    }
}

async function carregarVagas() {
    const lista = document.getElementById('listaVagas');
    const texto = document.getElementById('filtroTextoVagas').value.trim();
    const estado = document.getElementById('filtroEstadoVagas').value;
    const localizacao = document.getElementById('filtroLocalizacaoVagas').value;
    const termoOrigem = document.getElementById('filtroTermoVagas').value;
    const fonte = document.getElementById('filtroFonteVagas').value;
    const periodo = document.getElementById('filtroPeriodoVagas').value;

    const parametros = new URLSearchParams();
    if (texto) parametros.set('texto', texto);
    if (estado) parametros.set('estado', estado);
    if (localizacao) parametros.set('localizacao', localizacao);
    if (termoOrigem) parametros.set('termo_origem', termoOrigem);
    if (fonte) parametros.set('fonte', fonte);
    if (periodo) parametros.set('periodo', periodo);

    try {
        const vagas = await pedirJSON(`/api/vagas?${parametros.toString()}`);
        lista.innerHTML = '';
        if (vagas.length === 0) {
            lista.innerHTML = '<p class="estado-vazio">Nenhuma vaga encontrada com estes filtros.</p>';
        } else {
            vagas.forEach((vaga) => lista.appendChild(construirCartaoVaga(vaga)));
        }
        // O contador de "novas" só faz sentido em relação ao conjunto todo,
        // não a uma lista já filtrada.
        const semFiltros = !texto && !estado && !localizacao && !termoOrigem && !fonte && !periodo;
        if (semFiltros) {
            atualizarContadorVagasNovas(vagas);
        }
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

async function carregarOpcoesNoticias() {
    try {
        const opcoes = await pedirJSON('/api/opcoes/noticias');
        preencherOpcoes(document.getElementById('filtroFonteNoticias'), opcoes.fontes);
    } catch (erro) {
        console.error('Não foi possível carregar as opções de filtro das notícias', erro);
    }
}

async function carregarNoticias() {
    const lista = document.getElementById('listaNoticias');
    const texto = document.getElementById('filtroTextoNoticias').value.trim();
    const fonte = document.getElementById('filtroFonteNoticias').value;
    const periodo = document.getElementById('filtroPeriodoNoticias').value;

    const parametros = new URLSearchParams();
    if (texto) parametros.set('texto', texto);
    if (fonte) parametros.set('fonte', fonte);
    if (periodo) parametros.set('periodo', periodo);

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

// ---------- Vagas novas desde a última visita ----------

const CHAVE_ULTIMA_VISITA = 'monitor_ultima_visita_vagas';

function lerUltimaVisita() {
    try {
        return localStorage.getItem(CHAVE_ULTIMA_VISITA);
    } catch (erro) {
        return null;
    }
}

function gravarUltimaVisita(valorIso) {
    try {
        localStorage.setItem(CHAVE_ULTIMA_VISITA, valorIso);
    } catch (erro) {
        // localStorage pode não estar disponível (ex: navegação privada) —
        // sem drama, o contador de "novas" simplesmente não persiste.
    }
}

function atualizarContadorVagasNovas(vagas) {
    const contador = document.getElementById('contadorVagasNovas');
    if (!contador) return;

    const ultimaVisita = lerUltimaVisita();
    if (!ultimaVisita) {
        contador.hidden = true;
        return;
    }
    const limite = new Date(ultimaVisita).getTime();
    const novas = vagas.filter(
        (v) => v.publicado_em && new Date(v.publicado_em).getTime() > limite
    ).length;

    if (novas > 0) {
        contador.textContent = novas > 99 ? '99+' : String(novas);
        contador.hidden = false;
    } else {
        contador.hidden = true;
    }
}

function marcarVagasComoVistas() {
    gravarUltimaVisita(new Date().toISOString());
    const contador = document.getElementById('contadorVagasNovas');
    if (contador) contador.hidden = true;
}

// ---------- Estatísticas ----------

let ultimosDadosEstatisticas = null;

function corVar(nome) {
    return getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
}

function retangulaArredondado(ctx, x, y, largura, altura, raio) {
    ctx.beginPath();
    if (ctx.roundRect) {
        ctx.roundRect(x, y, largura, Math.max(altura, 0), raio);
    } else {
        ctx.rect(x, y, largura, Math.max(altura, 0));
    }
}

function larguraDisponivel(elemento) {
    const estilo = getComputedStyle(elemento);
    const preenchimento = parseFloat(estilo.paddingLeft) + parseFloat(estilo.paddingRight);
    return Math.max(1, elemento.clientWidth - preenchimento);
}

function prepararCanvas(canvas, alturaCss) {
    const dpr = window.devicePixelRatio || 1;
    const largura = larguraDisponivel(canvas.parentElement);
    canvas.style.width = largura + 'px';
    canvas.style.height = alturaCss + 'px';
    canvas.width = Math.max(1, Math.round(largura * dpr));
    canvas.height = Math.max(1, Math.round(alturaCss * dpr));
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, largura };
}

function desenharEvolucao(canvas, serie) {
    const altura = 220;
    const { ctx, largura } = prepararCanvas(canvas, altura);
    ctx.clearRect(0, 0, largura, altura);
    if (!serie || !serie.length) return;

    const margem = { topo: 12, baixo: 24, esquerda: 4, direita: 4 };
    const areaLargura = largura - margem.esquerda - margem.direita;
    const areaAltura = altura - margem.topo - margem.baixo;
    const maiorValor = Math.max(1, ...serie.map((p) => Math.max(p.vagas, p.noticias)));
    const passoX = areaLargura / Math.max(1, serie.length - 1);

    ctx.strokeStyle = corVar('--borda');
    ctx.lineWidth = 1;
    for (let i = 0; i <= 2; i++) {
        const y = margem.topo + (areaAltura / 2) * i;
        ctx.beginPath();
        ctx.moveTo(margem.esquerda, y);
        ctx.lineTo(margem.esquerda + areaLargura, y);
        ctx.stroke();
    }

    function tracarLinha(chave, cor) {
        ctx.beginPath();
        serie.forEach((ponto, i) => {
            const x = margem.esquerda + passoX * i;
            const y = margem.topo + areaAltura - (ponto[chave] / maiorValor) * areaAltura;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.strokeStyle = cor;
        ctx.lineWidth = 2;
        ctx.lineJoin = 'round';
        ctx.stroke();

        serie.forEach((ponto, i) => {
            const x = margem.esquerda + passoX * i;
            const y = margem.topo + areaAltura - (ponto[chave] / maiorValor) * areaAltura;
            ctx.beginPath();
            ctx.arc(x, y, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = cor;
            ctx.fill();
        });
    }

    tracarLinha('noticias', corVar('--acento'));
    tracarLinha('vagas', corVar('--azul-700'));

    ctx.fillStyle = corVar('--texto-fraco');
    ctx.font = '11px "Public Sans", sans-serif';
    const indices = [0, Math.floor((serie.length - 1) / 2), serie.length - 1];
    indices.forEach((i, posicao) => {
        const ponto = serie[i];
        if (!ponto) return;
        const x = margem.esquerda + passoX * i;
        const partes = ponto.data.split('-');
        // Alinha a 1a etiqueta à esquerda e a última à direita, para nenhuma
        // delas ficar cortada pela borda do canvas.
        if (posicao === 0) ctx.textAlign = 'left';
        else if (posicao === indices.length - 1) ctx.textAlign = 'right';
        else ctx.textAlign = 'center';
        ctx.fillText(`${partes[2]}/${partes[1]}`, x, altura - 6);
    });
}

function desenharBarras(canvas, dados) {
    const alturaLinha = 28;
    const altura = Math.max(alturaLinha, (dados ? dados.length : 0) * alturaLinha) + 8;
    const { ctx, largura } = prepararCanvas(canvas, altura);
    ctx.clearRect(0, 0, largura, altura);

    if (!dados || !dados.length) {
        ctx.fillStyle = corVar('--texto-suave');
        ctx.font = '13px "Public Sans", sans-serif';
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.fillText('Ainda não há dados suficientes.', 0, altura / 2);
        return;
    }

    const maiorValor = Math.max(...dados.map((d) => d.total));
    const larguraRotulo = 108;
    const larguraValor = 34;
    const areaBarra = Math.max(20, largura - larguraRotulo - larguraValor);

    dados.forEach((item, i) => {
        const y = i * alturaLinha;
        const centroY = y + alturaLinha / 2;

        ctx.fillStyle = corVar('--texto-suave');
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.font = '12px "Public Sans", sans-serif';
        const chave = String(item.chave);
        const rotulo = chave.length > 16 ? chave.slice(0, 15) + '…' : chave;
        ctx.fillText(rotulo, 0, centroY);

        const comprimentoBarra = Math.max(4, (item.total / maiorValor) * areaBarra);
        ctx.fillStyle = corVar('--azul-700');
        retangulaArredondado(ctx, larguraRotulo, y + 5, comprimentoBarra, alturaLinha - 10, 5);
        ctx.fill();

        ctx.fillStyle = corVar('--texto');
        ctx.font = '12px "JetBrains Mono", monospace';
        ctx.fillText(String(item.total), larguraRotulo + comprimentoBarra + 8, centroY);
    });
}

function desenharTaxaResposta(dados) {
    const contentor = document.getElementById('taxaResposta');
    if (!contentor) return;
    if (!dados || dados.candidatadas === 0) {
        contentor.innerHTML = '<p class="estado-vazio">Ainda não te candidataste a nenhuma vaga.</p>';
        return;
    }
    contentor.innerHTML = `
        <div class="taxa-resposta-numero">${dados.percentagem}%</div>
        <div class="taxa-resposta-barra">
            <div class="taxa-resposta-preenchimento" style="width: ${dados.percentagem}%"></div>
        </div>
        <p class="taxa-resposta-legenda">${dados.com_resposta} de ${dados.candidatadas} candidaturas tiveram resposta</p>
    `;
}

function desenharGraficosEstatisticas() {
    if (!ultimosDadosEstatisticas) return;
    const painel = document.querySelector('[data-painel="estatisticas"]');
    if (!painel || painel.hidden) return;
    desenharEvolucao(document.getElementById('graficoEvolucao'), ultimosDadosEstatisticas.evolucao);
    desenharBarras(document.getElementById('graficoTermos'), ultimosDadosEstatisticas.por_termo);
    desenharBarras(document.getElementById('graficoLocalizacoes'), ultimosDadosEstatisticas.por_localizacao);
    desenharBarras(document.getElementById('graficoFontes'), ultimosDadosEstatisticas.por_fonte);
    desenharTaxaResposta(ultimosDadosEstatisticas.taxa_resposta);
}

async function carregarEstatisticas() {
    try {
        ultimosDadosEstatisticas = await pedirJSON('/api/estatisticas');
        desenharGraficosEstatisticas();
    } catch (erro) {
        console.error('Não foi possível carregar as estatísticas', erro);
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

            if (aba.dataset.aba === 'estatisticas') {
                desenharGraficosEstatisticas();
            }
            if (aba.dataset.aba === 'vagas') {
                marcarVagasComoVistas();
            }
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
    document.getElementById('filtroLocalizacaoVagas').addEventListener('change', carregarVagas);
    document.getElementById('filtroTermoVagas').addEventListener('change', carregarVagas);
    document.getElementById('filtroFonteVagas').addEventListener('change', carregarVagas);
    document.getElementById('filtroPeriodoVagas').addEventListener('change', carregarVagas);
    document.getElementById('filtroTextoNoticias').addEventListener('input', comAtraso(carregarNoticias));
    document.getElementById('filtroFonteNoticias').addEventListener('change', carregarNoticias);
    document.getElementById('filtroPeriodoNoticias').addEventListener('change', carregarNoticias);
}

document.addEventListener('DOMContentLoaded', () => {
    configurarAbas();
    configurarFiltros();
    carregarResumo();
    carregarOpcoesVagas();
    carregarOpcoesNoticias();
    carregarEstatisticas();
    carregarNoticias();

    carregarVagas().then(() => {
        // Dá um instante para reparar no número de vagas novas antes de as
        // marcar como "vistas" — assim o contador não desaparece antes de
        // a pessoa sequer o notar.
        setTimeout(marcarVagasComoVistas, 4000);
    });
});

window.addEventListener('resize', comAtraso(desenharGraficosEstatisticas, 150));
