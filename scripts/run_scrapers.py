"""
Ponto de entrada usado pelo GitHub Actions (workflow agendado) para correr
os dois robôs de recolha. Corre localmente também, para testares à mão:

    python -m scripts.run_scrapers
    python -m scripts.run_scrapers --so vagas
    python -m scripts.run_scrapers --so noticias
"""
import argparse
import logging
import sys

from app.scrapers.noticias_rss import recolher_noticias
from app.scrapers.vagas_itjobs import recolher_vagas

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre os robôs de recolha de vagas e notícias.")
    parser.add_argument("--so", choices=["vagas", "noticias"], help="Corre só uma das recolhas.")
    args = parser.parse_args()

    erros = []

    if args.so in (None, "vagas"):
        try:
            recolher_vagas()
        except Exception as exc:  # noqa: BLE001 - queremos continuar para as notícias mesmo se isto falhar
            logger.exception("Falha na recolha de vagas")
            erros.append(("vagas", exc))

    if args.so in (None, "noticias"):
        try:
            recolher_noticias()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Falha na recolha de notícias")
            erros.append(("noticias", exc))

    if erros:
        for nome, exc in erros:
            print(f"ERRO em '{nome}': {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
