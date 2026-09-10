"""
Testes com respostas simuladas (mocks) das APIs externas — não fazem pedidos
reais à internet, por isso correm em qualquer máquina/CI sem precisar de
chaves API. Usam mongomock para simular o MongoDB sem precisar de ligação real.

Corre com: pytest -v
"""
import os
from unittest.mock import MagicMock, patch

import mongomock
import pytest

os.environ.setdefault("MONGODB_URI", "mongodb://localhost/teste")
os.environ.setdefault("ITJOBS_API_KEY", "chave-de-teste")

from app.scrapers import noticias_rss, vagas_itjobs  # noqa: E402


@pytest.fixture
def colecao_vagas_falsa(monkeypatch):
    cliente = mongomock.MongoClient()
    colecao = cliente["teste"]["vagas"]
    monkeypatch.setattr(vagas_itjobs, "get_vagas_collection", lambda: colecao)
    return colecao


@pytest.fixture
def colecao_noticias_falsa(monkeypatch):
    cliente = mongomock.MongoClient()
    colecao = cliente["teste"]["noticias"]
    monkeypatch.setattr(noticias_rss, "get_noticias_collection", lambda: colecao)
    return colecao


RESPOSTA_ITJOBS_EXEMPLO = {
    "total": 1,
    "page": 1,
    "limit": 50,
    "results": [
        {
            "id": 999001,
            "title": "Programadora Python",
            "company": {"id": 1, "name": "Empresa Exemplo"},
            "salaryMin": 1200,
            "salaryMax": 1800,
            "locations": [{"id": "14", "name": "Braga"}],
            "publishedAt": "2026-09-01 10:00:00",
        }
    ],
}


def test_recolher_vagas_grava_nova_vaga_como_por_candidatar(colecao_vagas_falsa):
    with patch.object(vagas_itjobs, "procurar_vagas", return_value=RESPOSTA_ITJOBS_EXEMPLO):
        total = vagas_itjobs.recolher_vagas()

    assert total >= 1
    guardada = colecao_vagas_falsa.find_one({"itjobs_id": 999001})
    assert guardada is not None
    assert guardada["estado"] == "por_candidatar"
    assert guardada["empresa"] == "Empresa Exemplo"


def test_recolher_vagas_nao_apaga_estado_ja_definido_pela_utilizadora(colecao_vagas_falsa):
    colecao_vagas_falsa.insert_one(
        {
            "itjobs_id": 999001,
            "titulo": "Programadora Python",
            "empresa": "Empresa Exemplo",
            "estado": "candidatei_me",
        }
    )

    with patch.object(vagas_itjobs, "procurar_vagas", return_value=RESPOSTA_ITJOBS_EXEMPLO):
        vagas_itjobs.recolher_vagas()

    guardada = colecao_vagas_falsa.find_one({"itjobs_id": 999001})
    assert guardada["estado"] == "candidatei_me"


def test_recolher_vagas_sem_api_key_da_erro_claro(monkeypatch):
    monkeypatch.delenv("ITJOBS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ITJOBS_API_KEY"):
        vagas_itjobs.recolher_vagas()


class _EntradaFeedFalsa(dict):
    """Simula uma entrada do feedparser (que devolve objetos tipo-dict com atributos)."""

    def __getattr__(self, nome):
        try:
            return self[nome]
        except KeyError as exc:
            raise AttributeError(nome) from exc


def test_recolher_noticias_grava_noticia_nova(colecao_noticias_falsa, monkeypatch):
    entrada = _EntradaFeedFalsa(
        title="Wingsys lança novo ecrã interativo - ECO",
        link="https://exemplo.pt/noticia-1",
        summary="Resumo da notícia de exemplo.",
        published_parsed=(2026, 9, 1, 9, 0, 0, 0, 0, 0),
    )
    feed_falso = MagicMock(bozo=False, entries=[entrada])
    monkeypatch.setattr(noticias_rss.feedparser, "parse", lambda url: feed_falso)

    total = noticias_rss.recolher_noticias()

    assert total == 1
    guardada = colecao_noticias_falsa.find_one({"link": "https://exemplo.pt/noticia-1"})
    assert guardada is not None
    assert guardada["titulo"] == "Wingsys lança novo ecrã interativo"
    assert guardada["fonte"] == "ECO"


def test_recolher_noticias_nao_duplica_a_mesma_noticia(colecao_noticias_falsa, monkeypatch):
    entrada = _EntradaFeedFalsa(
        title="Notícia repetida - Fonte X",
        link="https://exemplo.pt/noticia-repetida",
        summary=None,
        published_parsed=None,
    )
    feed_falso = MagicMock(bozo=False, entries=[entrada, entrada])
    monkeypatch.setattr(noticias_rss.feedparser, "parse", lambda url: feed_falso)

    noticias_rss.recolher_noticias()

    assert colecao_noticias_falsa.count_documents({}) == 1
