"""
Recolha de vagas reais e atuais via API pública do Landing.jobs
(https://landing.jobs/api/v1/jobs) — mercado de vagas de tecnologia na
Europa, sem precisar de chave/registo.

Esta API não suporta pesquisa por palavra-chave do lado do servidor, por
isso paginamos a lista completa e filtramos localmente pelos mesmos termos
configurados em VAGAS_QUERY (comparando com o título e as tags da vaga).

Cada vaga é gravada por `link` (chave única, partilhada com as outras
fontes) — numa vaga já conhecida, atualizamos os dados mas NUNCA mexemos no
campo `estado`, que é o único campo que a Elisama controla manualmente no
dashboard.
"""
import logging
from datetime import datetime, timezone

import requests

from app.database import get_vagas_collection
from app.scrapers.utils import termos_pesquisa, texto_contem_algum_termo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LANDING_JOBS_URL = "https://landing.jobs/api/v1/jobs"
LIMITE_POR_PAGINA = 50
PAGINAS_MAXIMAS = 5  # até 250 vagas por execução — suficiente, e razoável para uma API pública sem chave

# Alguns servidores bloqueiam pedidos com o user-agent por omissão da
# biblioteca requests — ver a mesma nota em vagas_itjobs.py.
CABECALHOS_PEDIDO = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def procurar_pagina(offset: int, limit: int = LIMITE_POR_PAGINA) -> list[dict]:
    """Chama a API do Landing.jobs para uma página de resultados. Real, não simulado."""
    parametros = {"offset": offset, "limit": limit}
    resposta = requests.get(
        LANDING_JOBS_URL, params=parametros, headers=CABECALHOS_PEDIDO, timeout=20
    )
    resposta.raise_for_status()
    return resposta.json()


def _empresa_a_partir_do_link(link: str) -> str:
    """A API não devolve o nome da empresa num campo próprio — só no URL da
    vaga (formato .../at/<empresa>/...). Extraímos e formatamos esse pedaço."""
    partes = link.split("/at/")
    if len(partes) < 2:
        return "(empresa não indicada)"
    slug = partes[1].split("/")[0]
    return slug.replace("-", " ").title() or "(empresa não indicada)"


def _para_documento(vaga_api: dict) -> dict | None:
    link = vaga_api.get("url")
    if not link:
        return None

    publicado_em = None
    if vaga_api.get("published_at"):
        try:
            publicado_em = datetime.fromisoformat(vaga_api["published_at"].replace("Z", "+00:00"))
        except ValueError:
            publicado_em = None

    localizacoes = [loc.get("city") for loc in vaga_api.get("locations", []) if loc.get("city")]
    if vaga_api.get("remote") and not localizacoes:
        localizacoes = ["Remoto"]

    return {
        "landing_jobs_id": vaga_api.get("id"),
        "titulo": vaga_api.get("title", "(sem título)"),
        "empresa": _empresa_a_partir_do_link(link),
        "localizacoes": localizacoes,
        "salario_min": vaga_api.get("gross_salary_low"),
        "salario_max": vaga_api.get("gross_salary_high"),
        "link": link,
        "publicado_em": publicado_em,
        "termo_origem": "landing.jobs",
        "fonte": "Landing.jobs",
    }


def recolher_vagas() -> int:
    """
    Percorre as páginas da API pública, filtra localmente pelos termos
    configurados (VAGAS_QUERY) e grava/atualiza as vagas relevantes no
    MongoDB. Devolve o número de vagas processadas.
    """
    termos = termos_pesquisa()
    colecao = get_vagas_collection()
    total_processadas = 0

    for pagina in range(PAGINAS_MAXIMAS):
        offset = pagina * LIMITE_POR_PAGINA
        resultados = procurar_pagina(offset)
        if not resultados:
            break

        for vaga_api in resultados:
            titulo = vaga_api.get("title", "")
            tags = " ".join(vaga_api.get("tags") or [])
            if not texto_contem_algum_termo(f"{titulo} {tags}", termos):
                continue

            documento = _para_documento(vaga_api)
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

        if len(resultados) < LIMITE_POR_PAGINA:
            break  # já não há mais páginas

    logger.info(
        "Recolha de vagas (Landing.jobs) concluída: %d vagas processadas.", total_processadas
    )
    return total_processadas


if __name__ == "__main__":
    recolher_vagas()
