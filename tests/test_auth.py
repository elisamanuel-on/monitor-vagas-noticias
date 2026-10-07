"""
Testes do login com conta Google — não fazem pedidos reais ao Google nem à
internet. Usam mongomock para simular o MongoDB e um objeto simples no
lugar do `Request` do FastAPI, para simular sessões com e sem login.

Corre com: pytest -v
"""
import os

import mongomock
import pytest

os.environ.setdefault("MONGODB_URI", "mongodb://localhost/teste")
os.environ.setdefault("SECRET_KEY", "chave-de-teste")

from app import auth  # noqa: E402


@pytest.fixture
def colecao_utilizadores_falsa(monkeypatch):
    cliente = mongomock.MongoClient()
    colecao = cliente["teste"]["utilizadores"]
    monkeypatch.setattr(auth, "get_utilizadores_collection", lambda: colecao)
    return colecao


class PedidoFalso:
    """Substitui o Request do FastAPI só para o que obter_utilizador_opcional usa: request.session."""

    def __init__(self, session=None):
        self.session = session or {}


DADOS_GOOGLE_EXEMPLO = {
    "sub": "1234567890",
    "name": "Elisama Manuel",
    "email": "elisama@example.com",
    "picture": "https://exemplo.com/foto.jpg",
}


def test_primeiro_login_cria_utilizador(colecao_utilizadores_falsa):
    utilizador = auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)

    assert utilizador["google_id"] == "1234567890"
    assert utilizador["nome"] == "Elisama Manuel"
    assert utilizador["email"] == "elisama@example.com"
    assert utilizador["foto"] == "https://exemplo.com/foto.jpg"
    assert "id" in utilizador
    assert colecao_utilizadores_falsa.count_documents({}) == 1


def test_segundo_login_atualiza_sem_duplicar(colecao_utilizadores_falsa):
    auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)

    dados_atualizados = dict(
        DADOS_GOOGLE_EXEMPLO, name="Elisama M.", picture="https://exemplo.com/nova-foto.jpg"
    )
    utilizador = auth.obter_ou_criar_utilizador(dados_atualizados)

    assert colecao_utilizadores_falsa.count_documents({}) == 1  # não duplicou o registo
    assert utilizador["nome"] == "Elisama M."
    assert utilizador["foto"] == "https://exemplo.com/nova-foto.jpg"


def test_criado_em_nao_muda_entre_logins(colecao_utilizadores_falsa):
    primeiro = auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)
    segundo = auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)

    assert primeiro["criado_em"] == segundo["criado_em"]
    assert segundo["ultimo_login_em"] >= primeiro["ultimo_login_em"]


def test_utilizadores_diferentes_ficam_separados(colecao_utilizadores_falsa):
    outro = dict(DADOS_GOOGLE_EXEMPLO, sub="999", email="colega@example.com", name="Colega")

    auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)
    auth.obter_ou_criar_utilizador(outro)

    assert colecao_utilizadores_falsa.count_documents({}) == 2


def test_obter_utilizador_opcional_sem_sessao(colecao_utilizadores_falsa):
    assert auth.obter_utilizador_opcional(PedidoFalso()) is None


def test_obter_utilizador_opcional_com_sessao_valida(colecao_utilizadores_falsa):
    utilizador = auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)

    encontrado = auth.obter_utilizador_opcional(
        PedidoFalso({"utilizador_id": utilizador["id"]})
    )
    assert encontrado is not None
    assert encontrado["email"] == "elisama@example.com"


def test_obter_utilizador_opcional_com_id_invalido(colecao_utilizadores_falsa):
    assert auth.obter_utilizador_opcional(PedidoFalso({"utilizador_id": "não-é-um-object-id"})) is None


def test_obter_utilizador_opcional_com_id_inexistente(colecao_utilizadores_falsa):
    from bson import ObjectId

    assert auth.obter_utilizador_opcional(
        PedidoFalso({"utilizador_id": str(ObjectId())})
    ) is None


# --- Testes de integração das rotas (TestClient), com o Mongo simulado ---

os.environ.setdefault("GOOGLE_CLIENT_ID", "id-de-teste")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "segredo-de-teste")


@pytest.fixture
def cliente_com_mongo_falso(monkeypatch):
    """TestClient da app inteira, com o MongoClient usado por app/database.py
    substituído por mongomock — para testar as rotas (proteção do /dashboard,
    apagar conta, etc.) sem precisar de um MongoDB real nem de rede. Como
    get_client() guarda o cliente numa variável global (_client), o mesmo
    cliente simulado é reutilizado por todas as coleções durante o teste."""
    import app.database as database_module

    monkeypatch.setattr(database_module, "MongoClient", mongomock.MongoClient)
    monkeypatch.setattr(database_module, "_client", None)

    from fastapi.testclient import TestClient
    from app import main as main_module

    with TestClient(main_module.app) as cliente:
        yield cliente, main_module

    main_module.app.dependency_overrides.clear()


def test_dashboard_sem_login_redireciona(cliente_com_mongo_falso):
    cliente, _ = cliente_com_mongo_falso
    resposta = cliente.get("/dashboard", follow_redirects=False)
    assert resposta.status_code == 307
    assert resposta.headers["location"].startswith("/auth/login")


def test_dashboard_modo_app_sem_login_vai_para_o_ecra_de_entrada_da_app(cliente_com_mongo_falso):
    cliente, _ = cliente_com_mongo_falso
    resposta = cliente.get("/dashboard?modo=app", follow_redirects=False)
    assert resposta.headers["location"] == "/?modo=app"


def test_versao_da_api_e_a_do_ficheiro_unico(cliente_com_mongo_falso):
    from app.versao import VERSAO
    cliente, _ = cliente_com_mongo_falso
    assert cliente.get("/api/versao").json() == {"versao": VERSAO}


def test_dashboard_com_login_devolve_a_pagina(cliente_com_mongo_falso):
    cliente, main_module = cliente_com_mongo_falso
    main_module.app.dependency_overrides[auth.obter_utilizador_opcional] = lambda: {
        "id": "abc", "nome": "Elisama", "email": "e@example.com", "foto": None
    }
    assert cliente.get("/dashboard").status_code == 200


def test_vitrine_e_privacidade_sao_publicas(cliente_com_mongo_falso):
    cliente, _ = cliente_com_mongo_falso
    assert cliente.get("/").status_code == 200
    assert cliente.get("/privacidade").status_code == 200


def test_apagar_conta_sem_login_devolve_401(cliente_com_mongo_falso):
    cliente, _ = cliente_com_mongo_falso
    assert cliente.delete("/api/utilizador-atual").status_code == 401


def test_apagar_conta_remove_o_registo(cliente_com_mongo_falso):
    cliente, main_module = cliente_com_mongo_falso
    # Cria o utilizador através do mesmo Mongo simulado que a app usa (a
    # fixture já garante que é o mesmo cliente, por causa do cache em _client).
    utilizador = auth.obter_ou_criar_utilizador(DADOS_GOOGLE_EXEMPLO)

    main_module.app.dependency_overrides[auth.obter_utilizador_opcional] = lambda: utilizador
    resposta = cliente.delete("/api/utilizador-atual")

    assert resposta.status_code == 200
    assert resposta.json() == {"apagado": True}

    from app.database import get_utilizadores_collection
    assert get_utilizadores_collection().count_documents({}) == 0


def test_url_inicio_no_executavel_volta_ao_ecra_de_entrada():
    assert auth.url_inicio("/dashboard?modo=app") == "/?modo=app"


def test_url_inicio_no_site_volta_a_vitrine():
    assert auth.url_inicio("/dashboard") == "/"
    assert auth.url_inicio(None) == "/"
