"""
Recolha de notícias reais e atuais sobre o setor de tecnologia interativa,
via feed RSS de pesquisa do Google News — não precisa de API key nenhuma.

Formato do feed: https://news.google.com/rss/search?q=<termos>&hl=pt-PT&gl=PT&ceid=PT:pt

Cada notícia é gravada por `link` (chave única), para nunca duplicar a mesma
notícia em execuções sucessivas do robô.
"""
import logging
import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser

from app.database import get_noticias_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=pt-PT&gl=PT&ceid=PT:pt"


def _query_configurada() -> str:
    return os.environ.get(
        "NOTICIAS_QUERY",
        'tecnologia interativa OR "digital signage" OR "ecrãs interativos"',
    )


def montar_url_feed(query: str) -> str:
    return GOOGLE_NEWS_RSS.format(query=quote_plus(query))


def _para_documento(entrada) -> dict | None:
    link = entrada.get("link")
    if not link:
        return None

    publicado_em = None
    if entrada.get("published_parsed"):
        publicado_em = datetime(*entrada["published_parsed"][:6], tzinfo=timezone.utc)

    # o Google News RSS costuma devolver o título como "Título - Fonte"
    titulo = entrada.get("title", "(sem título)")
    fonte = "Google Notícias"
    if hasattr(entrada, "source") and getattr(entrada.source, "title", None):
        fonte = entrada.source.title
    elif " - " in titulo:
        titulo, fonte = titulo.rsplit(" - ", 1)

    return {
        "titulo": titulo.strip(),
        "fonte": fonte.strip(),
        "resumo": entrada.get("summary"),
        "link": link,
        "publicado_em": publicado_em,
    }


def recolher_noticias() -> int:
    """
    Vai buscar o feed RSS real e atual configurado e grava as notícias novas
    no MongoDB. Devolve o número de notícias processadas.
    """
    query = _query_configurada()
    url = montar_url_feed(query)
    logger.info("A ler feed de notícias: %s", url)

    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raise RuntimeError(f"Não foi possível ler o feed RSS ({url}): {feed.bozo_exception}")

    colecao = get_noticias_collection()
    total_processadas = 0

    for entrada in feed.entries:
        documento = _para_documento(entrada)
        if documento is None:
            continue

        agora = datetime.now(timezone.utc)
        colecao.update_one(
            {"link": documento["link"]},
            {
                "$set": documento,
                "$setOnInsert": {"criado_em": agora},
            },
            upsert=True,
        )
        total_processadas += 1

    logger.info("Recolha de notícias concluída: %d notícias processadas.", total_processadas)
    return total_processadas


if __name__ == "__main__":
    recolher_noticias()
