"""Utilitários partilhados pelos vários robôs de recolha de vagas."""
import os


def termos_pesquisa() -> list[str]:
    """
    Termos de pesquisa configurados — a mesma variável de ambiente serve
    para todas as fontes de vagas, para não teres de repetir a configuração
    em cada uma.

    "or", não o 2º argumento do .get(): uma Variable do GitHub Actions por
    definir chega como env var vazia (""), não ausente — ver a nota em
    database.py sobre este mesmo comportamento.
    """
    bruto = os.environ.get("VAGAS_QUERY") or "python,fastapi,programador web"
    return [termo.strip() for termo in bruto.split(",") if termo.strip()]


def texto_contem_algum_termo(texto: str, termos: list[str]) -> bool:
    """
    Pesquisa simples (sem distinguir maiúsculas/minúsculas) usada pelas
    fontes que não suportam pesquisa por palavra-chave do lado do servidor
    (Landing.jobs e Net-Empregos) — filtramos localmente depois de recolher
    os resultados.
    """
    texto_lower = (texto or "").lower()
    return any(termo.lower() in texto_lower for termo in termos)
