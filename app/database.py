"""
Ligação ao MongoDB Atlas.

A connection string vem sempre da variável de ambiente `MONGODB_URI` — nunca
fica escrita no código nem no repositório. Localmente define-a num ficheiro
`.env` (ver `.env.example`); no GitHub Actions e no Render define-a como
"secret" / variável de ambiente na própria plataforma.
"""
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

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
        _client = MongoClient(uri)
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
    colecao.create_index("itjobs_id", unique=True)
    return colecao


def get_noticias_collection() -> Collection:
    colecao = get_db()["noticias"]
    colecao.create_index("link", unique=True)
    return colecao
