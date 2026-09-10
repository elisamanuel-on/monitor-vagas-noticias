"""
Recolha de vagas reais e atuais via API oficial da ITJobs (https://www.itjobs.pt/api).

A API key é gratuita e de leitura — pede-se em itjobs.pt/api só com um email,
não precisa de conta com password. Fica guardada como variável de ambiente
`ITJOBS_API_KEY`, nunca no código.

Cada vaga é gravada por `itjobs_id` (chave única): numa vaga já conhecida,
atualizamos os dados (título, empresa, salário, etc.) mas NUNCA mexemos no
campo `estado`, porque esse é o único campo que a Elisama controla manualmente
no dashboard (por_candidatar / candidatei_me / resposta_recebida / arquivada).
"""
import logging
import os
from datetime import datetime, timezone

import requests

from app.database import get_vagas_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ITJOBS_SEARCH_URL = "https://api.itjobs.pt/job/search.json"


def _termos_pesquisa() -> list[str]:
    bruto = os.environ.get("VAGAS_QUERY", "python,fastapi,programador web")
    return [termo.strip() for termo in bruto.split(",") if termo.strip()]


def _location_ids() -> list[str]:
    bruto = os.environ.get("VAGAS_LOCATION_IDS", "")
    return [loc.strip() for loc in bruto.split(",") if loc.strip()]


def procurar_vagas(termo: str, api_key: str, pagina: int = 1, limite: int = 50) -> dict:
    """Chama a API da ITJobs para um único termo de pesquisa. Real, não simulado."""
    parametros = {
        "api_key": api_key,
        "q": termo,
        "page": pagina,
        "limit": limite,
    }
    locations = _location_ids()
    if locations:
        parametros["location"] = ",".join(locations)

    resposta = requests.get(ITJOBS_SEARCH_URL, params=parametros, timeout=20)
    resposta.raise_for_status()
    return resposta.json()


def _para_documento(vaga_api: dict, termo_origem: str) -> dict:
    publicado_em = None
    if vaga_api.get("publishedAt"):
        try:
            publicado_em = datetime.strptime(vaga_api["publishedAt"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            publicado_em = None

    return {
        "itjobs_id": vaga_api["id"],
        "titulo": vaga_api.get("title", "(sem título)"),
        "empresa": (vaga_api.get("company") or {}).get("name", "(empresa não indicada)"),
        "localizacoes": [loc.get("name") for loc in vaga_api.get("locations", []) if loc.get("name")],
        "salario_min": vaga_api.get("salaryMin"),
        "salario_max": vaga_api.get("salaryMax"),
        "link": f"https://www.itjobs.pt/oferta/{vaga_api['id']}",
        "publicado_em": publicado_em,
        "termo_origem": termo_origem,
    }


def recolher_vagas() -> int:
    """
    Corre a recolha completa (todos os termos configurados) e grava/atualiza
    as vagas encontradas no MongoDB. Devolve o número de vagas processadas.
    """
    api_key = os.environ.get("ITJOBS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ITJOBS_API_KEY não está definida. Pede uma chave gratuita em "
            "https://www.itjobs.pt/api e define-a como variável de ambiente."
        )

    colecao = get_vagas_collection()
    total_processadas = 0

    for termo in _termos_pesquisa():
        logger.info("A procurar vagas para o termo: %s", termo)
        pagina = 1
        while True:
            dados = procurar_vagas(termo, api_key, pagina=pagina)
            resultados = dados.get("results", [])
            if not resultados:
                break

            for vaga_api in resultados:
                documento = _para_documento(vaga_api, termo)
                agora = datetime.now(timezone.utc)
                colecao.update_one(
                    {"itjobs_id": documento["itjobs_id"]},
                    {
                        "$set": documento,
                        "$setOnInsert": {"estado": "por_candidatar", "criado_em": agora},
                    },
                    upsert=True,
                )
                total_processadas += 1

            # a API da ITJobs pagina os resultados; paramos quando já vimos tudo
            if pagina * dados.get("limit", 50) >= dados.get("total", 0):
                break
            pagina += 1

    logger.info("Recolha de vagas concluída: %d vagas processadas.", total_processadas)
    return total_processadas


if __name__ == "__main__":
    recolher_vagas()
