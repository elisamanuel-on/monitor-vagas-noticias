"""
Login com conta Google (OAuth 2.0), via Authlib.

Não vemos nem guardamos a password de ninguém — o Google trata da
autenticação e devolve-nos só o nome, o email e a foto da conta que entrou.
Isso fica associado a um registo próprio na coleção `utilizadores`,
identificado pelo `google_id` (o "sub" que o Google devolve, único e
estável para cada conta, mesmo que o nome ou a foto mudem).

Fase 1 do suporte multiutilizador: isto dá-nos login e sabe "quem está a
ver o painel", mas as vagas e notícias em si continuam partilhadas por
todos — a separação de dados por utilizador (cada um com as suas próprias
candidaturas) é a fase seguinte.
"""
import os
from datetime import datetime, timezone
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from bson import ObjectId
from bson.errors import InvalidId
from starlette.requests import Request

from app.database import get_utilizadores_collection

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def _documento_para_utilizador(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def obter_ou_criar_utilizador(dados_google: dict) -> dict:
    """Cria o registo do utilizador na primeira vez que entra com uma conta
    Google; nas vezes seguintes só atualiza o nome/foto (podem mudar)."""
    google_id = dados_google["sub"]
    colecao = get_utilizadores_collection()
    agora = datetime.now(timezone.utc)

    colecao.update_one(
        {"google_id": google_id},
        {
            "$set": {
                "nome": dados_google.get("name", ""),
                "email": dados_google.get("email", ""),
                "foto": dados_google.get("picture"),
                "ultimo_login_em": agora,
            },
            "$setOnInsert": {"criado_em": agora},
        },
        upsert=True,
    )
    return _documento_para_utilizador(colecao.find_one({"google_id": google_id}))


def obter_utilizador_opcional(request: Request) -> Optional[dict]:
    """Dependency do FastAPI: devolve o utilizador autenticado na sessão
    atual, ou None se ninguém tiver feito login. Não bloqueia o pedido —
    quem precisa de exigir login usa isto e decide o que fazer com None."""
    utilizador_id = request.session.get("utilizador_id")
    if not utilizador_id:
        return None
    try:
        oid = ObjectId(utilizador_id)
    except InvalidId:
        return None
    doc = get_utilizadores_collection().find_one({"_id": oid})
    if not doc:
        return None
    return _documento_para_utilizador(doc)
