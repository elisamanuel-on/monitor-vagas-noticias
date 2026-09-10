"""
Recolha de vagas reais e atuais via feed RSS do Net-Empregos
(https://www.net-empregos.com/rssfeed.asp) — o maior portal de emprego
generalista de Portugal.

Importante: este feed cobre TODOS os setores (não só tecnologia) e não
suporta pesquisa por palavra-chave. Por isso filtramos localmente pelos
mesmos termos configurados em VAGAS_QUERY (título + descrição) — só ficam
guardadas as vagas que correspondam à área da Elisama. Se o VAGAS_QUERY
estiver muito restrito, é normal esta fonte trazer poucas ou nenhumas vagas
nalgumas execuções (o feed geral pode simplesmente não ter nada dessa área
nesse momento).

Cada vaga é gravada por `link` (chave única, partilhada com as outras
fontes) — nunca mexe no campo `estado`, que é controlado manualmente pela
Elisama no dashboard.
"""
import logging
from datetime import datetime, timezone

import feedparser

from app.database import get_vagas_collection
from app.scrapers.utils import termos_pesquisa, texto_contem_algum_termo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NET_EMPREGOS_RSS = "https://www.net-empregos.com/rssfeed.asp"


def _para_documento(entrada) -> dict | None:
    link = entrada.get("link")
    if not link:
        return None

    publicado_em = None
    if entrada.get("published_parsed"):
        publicado_em = datetime(*entrada["published_parsed"][:6], tzinfo=timezone.utc)

    return {
        "titulo": entrada.get("title", "(sem título)"),
        "empresa": entrada.get("author") or "(empresa não indicada)",
        "localizacoes": [],
        "salario_min": None,
        "salario_max": None,
        "link": link,
        "publicado_em": publicado_em,
        "termo_origem": "net-empregos",
        "fonte": "Net-Empregos",
    }


def recolher_vagas() -> int:
    """
    Lê o feed RSS completo do Net-Empregos, filtra localmente pelos termos
    configurados (VAGAS_QUERY) e grava/atualiza as vagas relevantes no
    MongoDB. Devolve o número de vagas processadas.
    """
    termos = termos_pesquisa()
    logger.info("A ler feed de vagas do Net-Empregos: %s", NET_EMPREGOS_RSS)

    feed = feedparser.parse(NET_EMPREGOS_RSS)
    if feed.bozo and not feed.entries:
        raise RuntimeError(
            f"Não foi possível ler o feed RSS do Net-Empregos ({NET_EMPREGOS_RSS}): "
            f"{feed.bozo_exception}"
        )

    colecao = get_vagas_collection()
    total_processadas = 0

    for entrada in feed.entries:
        titulo = entrada.get("title", "")
        descricao = entrada.get("summary", "")
        if not texto_contem_algum_termo(f"{titulo} {descricao}", termos):
            continue

        documento = _para_documento(entrada)
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

    logger.info(
        "Recolha de vagas (Net-Empregos) concluída: %d vagas processadas.", total_processadas
    )
    return total_processadas


if __name__ == "__main__":
    recolher_vagas()
