"""
Monitor de Vagas & Notícias — dashboard com login por conta Google.

API + frontend estático servidos pelo mesmo processo FastAPI, tal como no
Controlo de Gastos. Desde a v1.7.0 que qualquer pessoa com o link pode
entrar com a própria conta Google — ver app/auth.py. Por agora (fase 1),
o login identifica quem está a ver o painel, mas as vagas e notícias em
si continuam partilhadas por todos; a separação de dados por utilizador
(cada um com as suas próprias candidaturas) é a fase seguinte.
"""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from authlib.integrations.starlette_client import OAuthError
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.auth import oauth, obter_ou_criar_utilizador, obter_utilizador_opcional
from app.database import get_noticias_collection, get_utilizadores_collection, get_vagas_collection
from app.models import AtualizarEstadoVaga

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Monitor de Vagas & Notícias",
    description=(
        "Painel pessoal que acompanha vagas de emprego reais (API da ITJobs) "
        "e notícias reais do setor de tecnologia interativa (RSS), recolhidas "
        "automaticamente todos os dias. Login com conta Google."
    ),
    version="1.9.0",
)

# A sessão de login fica num cookie assinado com SECRET_KEY — nunca com
# dados sensíveis dentro, só o id do utilizador na coleção `utilizadores`.
# https_only=False localmente (http://localhost), True em produção (o
# Render define sempre a variável de ambiente RENDER="true" sozinho).
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "chave-de-desenvolvimento-local-insegura"),
    same_site="lax",
    https_only=os.environ.get("RENDER") is not None,
)


def _documento_para_vaga(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _documento_para_noticia(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _cutoff_por_periodo(periodo: Optional[str]) -> Optional[datetime]:
    """Converte um período pré-definido ('24h', '7d', '30d') numa data de corte."""
    duracoes = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    duracao = duracoes.get(periodo) if periodo else None
    if duracao is None:
        return None
    return datetime.now(timezone.utc) - duracao


@app.get("/api/vagas")
def listar_vagas(
    estado: Optional[str] = None,
    texto: Optional[str] = Query(None, description="Pesquisa livre no título ou na empresa"),
    localizacao: Optional[str] = Query(None, description="Filtrar por localização exata"),
    termo_origem: Optional[str] = Query(
        None, description="Filtrar pelo termo de pesquisa que encontrou a vaga"
    ),
    fonte: Optional[str] = Query(
        None, description="Filtrar pela fonte da vaga (ex: ITJobs)"
    ),
    periodo: Optional[str] = Query(
        None, description="Filtrar por data de publicação: '24h', '7d' ou '30d'"
    ),
):
    filtro: dict = {}
    if estado:
        filtro["estado"] = estado
    if texto:
        filtro["$or"] = [
            {"titulo": {"$regex": texto, "$options": "i"}},
            {"empresa": {"$regex": texto, "$options": "i"}},
        ]
    if localizacao:
        # localizacoes é um array — esta sintaxe filtra as vagas cujo array contém o valor
        filtro["localizacoes"] = localizacao
    if termo_origem:
        filtro["termo_origem"] = termo_origem
    if fonte:
        filtro["fonte"] = fonte
    cutoff = _cutoff_por_periodo(periodo)
    if cutoff:
        filtro["publicado_em"] = {"$gte": cutoff}

    colecao = get_vagas_collection()
    vagas = colecao.find(filtro).sort("publicado_em", -1)
    return [_documento_para_vaga(v) for v in vagas]


@app.get("/api/opcoes/vagas")
def opcoes_vagas():
    """Valores distintos usados para preencher os menus de filtro no frontend."""
    colecao = get_vagas_collection()
    localizacoes = sorted({loc for loc in colecao.distinct("localizacoes") if loc})
    termos_origem = sorted({t for t in colecao.distinct("termo_origem") if t})
    fontes = sorted({f for f in colecao.distinct("fonte") if f})
    return {"localizacoes": localizacoes, "termos_origem": termos_origem, "fontes": fontes}


@app.patch("/api/vagas/{vaga_id}")
def atualizar_estado_vaga(vaga_id: str, dados: AtualizarEstadoVaga):
    try:
        oid = ObjectId(vaga_id)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    colecao = get_vagas_collection()
    resultado = colecao.update_one({"_id": oid}, {"$set": {"estado": dados.estado}})
    if resultado.matched_count == 0:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    return _documento_para_vaga(colecao.find_one({"_id": oid}))


@app.get("/api/noticias")
def listar_noticias(
    texto: Optional[str] = Query(None, description="Pesquisa livre no título"),
    fonte: Optional[str] = Query(None, description="Filtrar por fonte/site da notícia"),
    periodo: Optional[str] = Query(
        None, description="Filtrar por data de publicação: '24h', '7d' ou '30d'"
    ),
):
    filtro: dict = {}
    if texto:
        filtro["titulo"] = {"$regex": texto, "$options": "i"}
    if fonte:
        filtro["fonte"] = fonte
    cutoff = _cutoff_por_periodo(periodo)
    if cutoff:
        filtro["publicado_em"] = {"$gte": cutoff}

    colecao = get_noticias_collection()
    noticias = colecao.find(filtro).sort("publicado_em", -1).limit(200)
    return [_documento_para_noticia(n) for n in noticias]


@app.get("/api/opcoes/noticias")
def opcoes_noticias():
    """Valores distintos usados para preencher os menus de filtro no frontend."""
    colecao = get_noticias_collection()
    fontes = sorted({f for f in colecao.distinct("fonte") if f})
    return {"fontes": fontes}


@app.get("/api/resumo")
def resumo():
    """Números rápidos para o topo do dashboard."""
    vagas = get_vagas_collection()
    noticias = get_noticias_collection()

    return {
        "total_vagas": vagas.count_documents({}),
        "vagas_por_candidatar": vagas.count_documents({"estado": "por_candidatar"}),
        "vagas_candidatei_me": vagas.count_documents({"estado": "candidatei_me"}),
        "vagas_resposta_recebida": vagas.count_documents({"estado": "resposta_recebida"}),
        "total_noticias": noticias.count_documents({}),
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }


def _evolucao_por_dia(dias: int = 30) -> list[dict]:
    """Quantas vagas e notícias novas (por data de publicação) em cada um dos
    últimos `dias` dias, para desenhar um gráfico de evolução no tempo."""
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)

    pipeline = [
        {"$match": {"publicado_em": {"$gte": inicio}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$publicado_em"}},
                "total": {"$sum": 1},
            }
        },
    ]
    contagem_vagas = {d["_id"]: d["total"] for d in get_vagas_collection().aggregate(pipeline)}
    contagem_noticias = {d["_id"]: d["total"] for d in get_noticias_collection().aggregate(pipeline)}

    serie = []
    for i in range(dias, -1, -1):
        dia = (agora - timedelta(days=i)).strftime("%Y-%m-%d")
        serie.append({
            "data": dia,
            "vagas": contagem_vagas.get(dia, 0),
            "noticias": contagem_noticias.get(dia, 0),
        })
    return serie


def _distribuicao(colecao, campo: str, limite: int, e_lista: bool = False) -> list[dict]:
    """Top `limite` valores mais frequentes de `campo` numa coleção, para um
    gráfico de barras (termos de pesquisa, localizações ou fontes)."""
    pipeline = []
    if e_lista:
        pipeline.append({"$unwind": f"${campo}"})
    pipeline += [
        {"$match": {campo: {"$nin": [None, ""]}}},
        {"$group": {"_id": f"${campo}", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": limite},
    ]
    return [{"chave": d["_id"], "total": d["total"]} for d in colecao.aggregate(pipeline)]


@app.get("/api/estatisticas")
def estatisticas():
    """Números mais ricos para a aba 'Estatísticas' do painel: evolução no
    tempo, distribuição por termo/localização/fonte (vagas e notícias) e
    taxa de resposta."""
    vagas = get_vagas_collection()
    noticias = get_noticias_collection()

    candidatadas = vagas.count_documents(
        {"estado": {"$in": ["candidatei_me", "resposta_recebida"]}}
    )
    com_resposta = vagas.count_documents({"estado": "resposta_recebida"})
    percentagem = round((com_resposta / candidatadas) * 100, 1) if candidatadas else 0.0

    return {
        "evolucao": _evolucao_por_dia(30),
        "por_termo": _distribuicao(vagas, "termo_origem", limite=12),
        "por_localizacao": _distribuicao(vagas, "localizacoes", limite=10, e_lista=True),
        "por_fonte": _distribuicao(vagas, "fonte", limite=10),
        "por_fonte_noticias": _distribuicao(noticias, "fonte", limite=10),
        "taxa_resposta": {
            "candidatadas": candidatadas,
            "com_resposta": com_resposta,
            "percentagem": percentagem,
        },
    }


@app.get("/api/utilizador-atual")
def utilizador_atual(utilizador: Optional[dict] = Depends(obter_utilizador_opcional)):
    """Quem está autenticado nesta sessão, para o frontend mostrar o nome/
    foto e o botão de sair. 401 se ninguém tiver feito login."""
    if not utilizador:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return {
        "nome": utilizador["nome"],
        "email": utilizador["email"],
        "foto": utilizador.get("foto"),
    }


@app.delete("/api/utilizador-atual")
def apagar_conta(request: Request, utilizador: Optional[dict] = Depends(obter_utilizador_opcional)):
    """Direito ao apagamento: remove por completo o registo do utilizador
    (nome, email, foto, google_id) da coleção `utilizadores` e termina a
    sessão. Não apaga vagas/notícias — essas nunca tiveram dados pessoais."""
    if not utilizador:
        raise HTTPException(status_code=401, detail="Não autenticado")
    get_utilizadores_collection().delete_one({"_id": ObjectId(utilizador["id"])})
    request.session.clear()
    return {"apagado": True}


@app.get("/auth/login")
async def auth_login(request: Request, destino: str = "/dashboard"):
    """Início do login: guarda para onde voltar depois (ex: /dashboard?modo=app,
    para o executável de secretária) e envia para o ecrã de consentimento do Google."""
    request.session["destino_pos_login"] = destino
    redirect_uri = str(request.url_for("auth_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request):
    """Para onde o Google reenvia depois da pessoa autorizar (ou recusar)."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        # Login recusado ou falhado — volta à vitrine em vez de mostrar um erro técnico.
        return RedirectResponse(url="/")

    dados_google = token.get("userinfo")
    if not dados_google:
        return RedirectResponse(url="/")

    utilizador = obter_ou_criar_utilizador(dados_google)
    request.session["utilizador_id"] = utilizador["id"]
    destino = request.session.pop("destino_pos_login", "/dashboard")
    return RedirectResponse(url=destino)


@app.get("/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")


# Frontend estático (tem de vir depois das rotas /api/... para não as tapar)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


_SEM_CACHE = {"Cache-Control": "no-cache"}


@app.get("/")
def raiz():
    """Vitrine pública: apresentação do projeto com dados reais em destaque."""
    return FileResponse(str(BASE_DIR / "static" / "vitrine.html"), headers=_SEM_CACHE)


@app.get("/dashboard")
def painel(request: Request, utilizador: Optional[dict] = Depends(obter_utilizador_opcional)):
    """Painel de trabalho completo — exige login com conta Google."""
    if not utilizador:
        modo = request.query_params.get("modo")
        destino = "/dashboard" + (f"?modo={modo}" if modo else "")
        return RedirectResponse(url=f"/auth/login?destino={quote(destino)}")
    return FileResponse(str(BASE_DIR / "static" / "index.html"), headers=_SEM_CACHE)


@app.get("/privacidade")
def privacidade():
    """Página pública: que dados pessoais guardamos ao entrar com o Google e como pedir para os apagar."""
    return FileResponse(str(BASE_DIR / "static" / "privacidade.html"), headers=_SEM_CACHE)
