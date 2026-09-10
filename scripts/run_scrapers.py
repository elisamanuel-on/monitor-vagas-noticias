"""
Ponto de entrada usado pelo GitHub Actions (workflow agendado) para correr
todos os robôs de recolha. Corre localmente também, para testares à mão:

    python -m scripts.run_scrapers
    python -m scripts.run_scrapers --so vagas
    python -m scripts.run_scrapers --so noticias
"""
import argparse
import logging
import sys

from app.scrapers.noticias_rss import recolher_noticias
from app.scrapers.vagas_itjobs import recolher_vagas as recolher_vagas_itjobs
from app.scrapers.vagas_landing_jobs import recolher_vagas as recolher_vagas_landing_jobs
from app.scrapers.vagas_netempregos import recolher_vagas as recolher_vagas_netempregos

logger = logging.getLogger(__name__)

# Cada fonte de vagas corre de forma independente: se uma falhar (ex: um site
# em baixo), as outras continuam na mesma — o erro só é reportado no fim.
FONTES_VAGAS = [
    ("vagas:itjobs", recolher_vagas_itjobs),
    ("vagas:landing.jobs", recolher_vagas_landing_jobs),
    ("vagas:net-empregos", recolher_vagas_netempregos),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Corre os robôs de recolha de vagas e notícias.")
    parser.add_argument("--so", choices=["vagas", "noticias"], help="Corre só uma das recolhas.")
    args = parser.parse_args()

    erros = []

    if args.so in (None, "vagas"):
        for nome, recolher in FONTES_VAGAS:
            try:
                recolher()
            except Exception as exc:  # noqa: BLE001 - uma fonte falhar não deve travar as outras
                logger.exception("Falha na recolha de '%s'", nome)
                erros.append((nome, exc))

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
