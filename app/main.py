"""
Monitor de Vagas & Notícias — dashboard pessoal, sem autenticação.

API + frontend estático servidos pelo mesmo processo FastAPI, tal como no
Controlo de Gastos — mas aqui sem login, porque é uma ferramenta só para a
Elisama consultar, não uma app multiutilizador.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_noticias_collection, get_vagas_collection
from app.models import AtualizarEstadoVaga

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Monitor de Vagas & Notícias",
    description=(
        "Painel pessoal que acompanha vagas de emprego reais (API da ITJobs) "
        "e notícias reais do setor de tecnologia interativa (RSS), recolhidas "
        "automaticamente todos os dias."
    ),
    version="1.0.0",
)


def _documento_para_vaga(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _documento_para_noticia(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/api/vagas")
def listar_vagas(
    estado: Optional[str] = None,
    texto: Optional[str] = Query(None, description="Pesquisa livre no título ou na empresa"),
):
    filtro: dict = {}
    if estado:
        filtro["estado"] = estado
    if texto:
        filtro["$or"] = [
            {"titulo": {"$regex": texto, "$options": "i"}},
            {"empresa": {"$regex": texto, "$options": "i"}},
        ]

    colecao = get_vagas_collection()
    vagas = colecao.find(filtro).sort("publicado_em", -1)
    return [_documento_para_vaga(v) for v in vagas]


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
def listar_noticias(texto: Optional[str] = Query(None, description="Pesquisa livre no título")):
    filtro: dict = {}
    if texto:
        filtro["titulo"] = {"$regex": texto, "$options": "i"}

    colecao = get_noticias_collection()
    noticias = colecao.find(filtro).sort("publicado_em", -1).limit(200)
    return [_documento_para_noticia(n) for n in noticias]


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


# Frontend estático (tem de vir depois das rotas /api/... para não as tapar)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
def raiz():
    return FileResponse(str(BASE_DIR / "static" / "index.html"))
