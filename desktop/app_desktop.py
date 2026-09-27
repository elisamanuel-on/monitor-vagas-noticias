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

Para reconstruir o .exe depois de alterar este ficheiro, ver README.md
nesta pasta.
"""
import time
import urllib.request

import webview

URL_PAINEL = "https://monitor-vagas-noticias.onrender.com/dashboard?modo=app"
TITULO_JANELA = "Monitor de Vagas & Notícias"
TEMPO_LIMITE_SEGUNDOS = 75

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
</style>
</head>
<body>
  <div class="caixa">
    <div class="anel"></div>
    <h1>A ligar ao Monitor de Vagas & Notícias…</h1>
    <p>Pode demorar um pouco na primeira vez do dia.</p>
  </div>
</body>
</html>
"""

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


def principal():
    janela = webview.create_window(
        title=TITULO_JANELA,
        html=PAGINA_ESPERA,
        width=1280,
        height=860,
        min_size=(960, 640),
        text_select=True,
    )
    webview.start(_esperar_e_abrir_painel, janela)


if __name__ == "__main__":
    principal()
