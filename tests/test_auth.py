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
