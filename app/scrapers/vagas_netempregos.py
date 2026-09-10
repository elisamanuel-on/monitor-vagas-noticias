"""
Recolha de vagas reais e atuais da categoria "Informática (Programação)" do
Net-Empregos (https://www.net-empregos.com/emprego-informatica-programacao.asp)
— o maior portal de emprego generalista de Portugal.

Porquê a página da categoria em vez do feed RSS geral (usado numa versão
anterior deste ficheiro): o feed RSS geral (/rssfeed.asp) mistura ofertas de
TODOS os setores — de ~20 ofertas por leitura só 1 ou 2 eram de tecnologia,
por isso quase nunca havia nada relevante para guardar. Esta página da
categoria já vem só com ofertas de "Informática (Programação)" (perto de
1000 no total).

Ao contrário da ITJobs, aqui NÃO filtramos localmente pelos termos de
VAGAS_QUERY: essa opção foi testada e eliminava praticamente tudo, porque
compara só com o título da vaga, e a maioria dos títulos reais (ex:
"Fullstack Developer", "DevOps Engineer") não contém literalmente palavras
como "python" ou "fastapi" — mesmo sendo vagas de programação relevantes.
Como a categoria em si já é o filtro (é só "Informática (Programação)"),
guardamos todas as vagas encontradas em cada execução.

O robots.txt do site permite isto (`User-agent: * / Allow: /`) — não há
nenhuma proibição a páginas de categoria como esta.

Cada vaga é gravada por `link` (chave única, partilhada com as outras
fontes) — nunca mexe no campo `estado`, controlado manualmente pela
Elisama no dashboard.
"""
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from app.database import get_vagas_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://www.net-empregos.com"
CATEGORIA_URL = f"{BASE_URL}/emprego-informatica-programacao.asp"
PAGINAS_MAXIMAS = 10  # até ~180 vagas por execução — suficiente, e um pedido respeitoso ao site
PAUSA_ENTRE_PAGINAS_S = 1  # não encadear pedidos em catadupa

CABECALHOS_PEDIDO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-PT,pt;q=0.9",
}


def procurar_pagina(pagina: int) -> str:
    """Vai buscar o HTML de uma página da categoria. Real, não simulado."""
    parametros = {"page": pagina} if pagina > 1 else {}
    resposta = requests.get(
        CATEGORIA_URL, params=parametros, headers=CABECALHOS_PEDIDO, timeout=20
    )
    # Diagnóstico temporário: o site pode devolver 200 OK mas com uma página
    # de bloqueio/desafio (ex: Cloudflare) em vez do HTML real — isto não dá
    # erro (raise_for_status não dispara), mas também não tem vagas nenhumas.
    # Estas linhas de log ajudam a confirmar se é isso que está a acontecer
    # a partir do GitHub Actions.
    titulo_pagina = None
    inicio_texto = BeautifulSoup(resposta.text, "html.parser").title
    if inicio_texto:
        titulo_pagina = inicio_texto.get_text(strip=True)
    logger.info(
        "Net-Empregos página %d: status=%d, tamanho=%d bytes, <title>=%r",
        pagina,
        resposta.status_code,
        len(resposta.text),
        titulo_pagina,
    )
    resposta.raise_for_status()
    return resposta.text


def _texto_do_icone(item: Tag, classe_icone: str) -> Optional[str]:
    icone = item.select_one(f".job-ad-item i.{classe_icone}")
    if icone is None:
        return None
    li = icone.find_parent("li")
    texto = li.get_text(strip=True) if li else None
    return texto or None


def _data_publicacao(texto: Optional[str]) -> Optional[datetime]:
    if not texto:
        return None
    try:
        return datetime.strptime(texto, "%d-%m-%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _para_documento(item: Tag) -> Optional[dict]:
    link_tag = item.select_one("h2 a.oferta-link")
    if link_tag is None or not link_tag.get("href"):
        return None

    href = link_tag["href"]
    link = href if href.startswith("http") else f"{BASE_URL}{href}"
    titulo = link_tag.get_text(strip=True) or "(sem título)"

    localizacao = _texto_do_icone(item, "flaticon-pin")
    empresa = _texto_do_icone(item, "flaticon-work") or "(empresa não indicada)"
    data_texto = _texto_do_icone(item, "flaticon-calendar")

    return {
        "titulo": titulo,
        "empresa": empresa,
        "localizacoes": [localizacao] if localizacao else [],
        "salario_min": None,
        "salario_max": None,
        "link": link,
        "publicado_em": _data_publicacao(data_texto),
        "termo_origem": "net-empregos",
        "fonte": "Net-Empregos",
    }


def recolher_vagas() -> int:
    """
    Percorre as páginas da categoria "Informática (Programação)" e
    grava/atualiza todas as vagas encontradas no MongoDB (sem filtro local
    de termos — ver nota no topo do ficheiro). Devolve o número de vagas
    processadas.
    """
    colecao = get_vagas_collection()
    total_processadas = 0

    for pagina in range(1, PAGINAS_MAXIMAS + 1):
        html = procurar_pagina(pagina)
        soup = BeautifulSoup(html, "html.parser")
        itens = soup.select(".job-item")
        if not itens:
            break

        for item in itens:
            documento = _para_documento(item)
            if documento is None:
                continue

            agora = datetime.now(timezone.utc)
            colecao.update_one(
                {"link": documento["link"]},
                {
                    "$set": documento,
                    "$setOnInsert": {"estado": "por_candidatar", "criado_em": agora},
                },
                upsert=True,
            )
            total_processadas += 1

        if pagina < PAGINAS_MAXIMAS:
            time.sleep(PAUSA_ENTRE_PAGINAS_S)

    logger.info(
        "Recolha de vagas (Net-Empregos) concluída: %d vagas processadas.", total_processadas
    )
    return total_processadas


if __name__ == "__main__":
    recolher_vagas()
