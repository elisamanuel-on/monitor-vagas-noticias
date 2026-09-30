"""
Monitor de Vagas & Notícias — versão de secretária.

Não é uma cópia local da app: é uma janela nativa (sem barra de endereço,
sem separadores, sem menus de browser) que mostra o painel de trabalho
já em produção no Render. Por isso:

  - precisa de internet para funcionar, tal como precisavas de internet
    para abrir o site num browser;
  - nunca guarda nem embrulha nenhuma password ou chave de API — não há
    nada sensível dentro deste executável, é só uma janela apontada
    para o site de sempre;
  - mostra sempre os dados mais recentes, porque é sempre o mesmo site,
    nunca uma cópia desatualizada.

O Render "adormece" a app quando ninguém a usa há um tempo, por isso a
primeira vez que abrires o executável pode demorar até um minuto a
acordar. Em vez de mostrar uma janela em branco (ou um erro de "página
não encontrada") nesse tempo, esta janela abre já com um ecrã de espera
com o logótipo, e só troca para o painel quando o site responder.

Enquanto a janela está aberta, uma verificação em segundo plano (a cada
15 minutos) compara o número total de vagas com o que viu da última vez
e, se houver vagas novas, mostra uma notificação nativa do Windows —
mesmo que estejas a trabalhar noutra janela. Essa contagem fica guardada
num pequeno ficheiro local (na pasta de dados da aplicação), para a
comparação continuar a fazer sentido mesmo depois de fechares e voltares
a abrir o Monitor.

Para reconstruir o .exe depois de alterar este ficheiro, ver README.md
nesta pasta.
"""
import json
import os
import threading
import time
import urllib.request
from pathlib import Path

import webview

URL_PAINEL = "https://monitor-vagas-noticias.onrender.com/dashboard?modo=app"
URL_RESUMO = "https://monitor-vagas-noticias.onrender.com/api/resumo"
VERSAO = "1.7.0"
TITULO_JANELA = "Monitor de Vagas & Notícias"
TITULO_JANELA_COM_VERSAO = f"{TITULO_JANELA} — v{VERSAO}"
TEMPO_LIMITE_SEGUNDOS = 75
INTERVALO_VERIFICACAO_SEGUNDOS = 15 * 60

PAGINA_ESPERA = """
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<style>
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  body {
    margin: 0; height: 100vh; display: flex; align-items: center;
    justify-content: center; background: linear-gradient(160deg, #13294b, #2f6db0);
    font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #fff;
  }
  .caixa { text-align: center; }
  .anel {
    width: 46px; height: 46px; margin: 0 auto 22px;
    border: 3px solid rgba(255,255,255,.25); border-top-color: #fff;
    border-radius: 999px; animation: girar 0.9s linear infinite;
  }
  @keyframes girar { to { transform: rotate(360deg); } }
  h1 { font-size: 17px; font-weight: 700; margin: 0 0 6px; }
  p { font-size: 13px; color: rgba(255,255,255,.75); margin: 0; }
  .versao { margin-top: 14px; font-size: 11px; color: rgba(255,255,255,.45); }
</style>
</head>
<body>
  <div class="caixa">
    <div class="anel"></div>
    <h1>A ligar ao Monitor de Vagas & Notícias…</h1>
    <p>Pode demorar um pouco na primeira vez do dia.</p>
    <p class="versao">v{VERSAO}</p>
  </div>
</body>
</html>
""".replace("{VERSAO}", VERSAO)

PAGINA_FALHA = """
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<style>
  body {
    margin: 0; height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #f4f6fa; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color: #16213a;
  }
  .caixa { text-align: center; max-width: 360px; }
  h1 { font-size: 16px; margin: 0 0 8px; }
  p { font-size: 13px; color: #51607a; margin: 0; }
</style>
</head>
<body>
  <div class="caixa">
    <h1>Não foi possível ligar agora</h1>
    <p>Confirma a tua ligação à internet e volta a abrir o Monitor.</p>
  </div>
</body>
</html>
"""


def _esperar_e_abrir_painel(janela):
    fim = time.monotonic() + TEMPO_LIMITE_SEGUNDOS
    while time.monotonic() < fim:
        try:
            urllib.request.urlopen(URL_PAINEL, timeout=5)
            janela.load_url(URL_PAINEL)
            return
        except Exception:
            time.sleep(2)
    janela.load_html(PAGINA_FALHA)


def _pasta_dados_locais() -> Path:
    """Pasta de dados da aplicação (AppData no Windows), para guardar o
    pequeno ficheiro de estado local — nunca dados sensíveis, só um número."""
    base = os.environ.get("APPDATA") or str(Path.home())
    pasta = Path(base) / "MonitorVagasNoticias"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


FICHEIRO_ESTADO_LOCAL = _pasta_dados_locais() / "estado_local.json"


def _ler_total_vagas_conhecido():
    try:
        dados = json.loads(FICHEIRO_ESTADO_LOCAL.read_text(encoding="utf-8"))
        return dados.get("total_vagas")
    except Exception:
        return None


def _gravar_total_vagas_conhecido(total: int) -> None:
    try:
        FICHEIRO_ESTADO_LOCAL.write_text(json.dumps({"total_vagas": total}), encoding="utf-8")
    except Exception:
        pass


def _notificar_vagas_novas(novas: int, janela) -> None:
    texto = "1 vaga nova encontrada." if novas == 1 else f"{novas} vagas novas encontradas."

    def ao_clicar(_args=None):
        try:
            janela.restore()
        except Exception:
            pass

    try:
        from win11toast import notify
        notify(TITULO_JANELA, texto, on_click=ao_clicar)
    except Exception:
        # Notificações nativas são um extra, não algo essencial — se o
        # Windows ou o pacote win11toast falharem por qualquer razão, o
        # resto da aplicação continua a funcionar normalmente.
        pass


def _verificar_vagas_novas_periodicamente(janela) -> None:
    # Dá tempo à janela principal de acabar de abrir antes da primeira
    # verificação, para não competir com o arranque com o Render a acordar.
    time.sleep(30)
    while True:
        try:
            with urllib.request.urlopen(URL_RESUMO, timeout=10) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
            total_atual = dados.get("total_vagas")
            if isinstance(total_atual, int):
                total_anterior = _ler_total_vagas_conhecido()
                if total_anterior is not None and total_atual > total_anterior:
                    _notificar_vagas_novas(total_atual - total_anterior, janela)
                _gravar_total_vagas_conhecido(total_atual)
        except Exception:
            pass
        time.sleep(INTERVALO_VERIFICACAO_SEGUNDOS)


def principal():
    janela = webview.create_window(
        title=TITULO_JANELA_COM_VERSAO,
        html=PAGINA_ESPERA,
        width=1280,
        height=860,
        min_size=(960, 640),
        text_select=True,
    )
    threading.Thread(
        target=_verificar_vagas_novas_periodicamente, args=(janela,), daemon=True
    ).start()
    webview.start(_esperar_e_abrir_painel, janela)


if __name__ == "__main__":
    principal()
