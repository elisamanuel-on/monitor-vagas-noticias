"""
Ligação ao MongoDB Atlas.

A connection string vem sempre da variável de ambiente `MONGODB_URI` — nunca
fica escrita no código nem no repositório. Localmente define-a num ficheiro
`.env` (ver `.env.example`); no GitHub Actions e no Render define-a como
"secret" / variável de ambiente na própria plataforma.
"""
import os

import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import OperationFailure

load_dotenv()

_client: MongoClient | None = None


def get_client() -> MongoClient:
    global _client
    if _client is None:
        uri = os.environ.get("MONGODB_URI")
        if not uri:
            raise RuntimeError(
                "MONGODB_URI não está definida. Cria um ficheiro .env a partir "
                "de .env.example (localmente) ou define o secret MONGODB_URI "
                "no GitHub Actions / variável de ambiente no Render."
            )
        # tlsCAFile=certifi.where(): usa um conjunto de certificados-raiz
        # atualizado em vez do do sistema operativo. Sem isto, ligar ao Atlas
        # a partir de alguns runners Linux (como o do GitHub Actions) falha o
        # handshake TLS com "TLSV1_ALERT_INTERNAL_ERROR" — problema conhecido,
        # nada a ver com a connection string em si.
        _client = MongoClient(uri, tlsCAFile=certifi.where())
    return _client


def get_db() -> Database:
    # "or" em vez do 2º argumento do .get(): no GitHub Actions, uma "Variable"
    # (vars.X) que não exista chega aqui como env var DEFINIDA mas vazia (""),
    # não como env var ausente — por isso .get("MONGODB_DB", "omissão") não
    # chegaria a usar a omissão. O "or" apanha também esse caso.
    nome = os.environ.get("MONGODB_DB") or "monitor_vagas_noticias"
    return get_client()[nome]


def get_vagas_collection() -> Collection:
    colecao = get_db()["vagas"]
    # até agora a chave única era o itjobs_id (só fazia sentido quando a
    # única fonte de vagas era a API da ITJobs); agora que há várias fontes
    # (ITJobs, Landing.jobs, Net-Empregos), a chave única passa a ser o
    # `link` de cada vaga — é sempre único, seja qual for a fonte de onde
    # veio, tal como já acontece na coleção de notícias.
    try:
        colecao.drop_index("itjobs_id_1")
    except OperationFailure:
        pass  # já não existia (instalação nova, ou já tinha sido removido antes)
    colecao.create_index("link", unique=True)
    return colecao


def get_noticias_collection() -> Collection:
    colecao = get_db()["noticias"]
    colecao.create_index("link", unique=True)
    return colecao
