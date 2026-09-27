"""
Monitor de Vagas & Notícias — versão de secretária.

Não é uma cópia local da app: é uma janela nativa (sem barra de endereço,
sem separadores, sem menus de browser) que mostra o painel de trabalho
já em produção no Render. Por isso:

  - precisa de internet para funcionar, tal como o browser precisava;
  - nunca guarda nem embrulha nenhuma password ou chave de API — não há
    nada sensível dentro deste executável, é só uma janela apontada
    para o site de sempre;
  - mostra sempre os dados mais recentes, porque é sempre o mesmo site,
    nunca uma cópia desatualizada.

Para reconstruir o .exe depois de alterar este ficheiro, ver README.md
nesta pasta.
"""
import webview

URL_PAINEL = "https://monitor-vagas-noticias.onrender.com/dashboard"
TITULO_JANELA = "Monitor de Vagas & Notícias"


def principal():
    webview.create_window(
        title=TITULO_JANELA,
        url=URL_PAINEL,
        width=1280,
        height=860,
        min_size=(960, 640),
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    principal()
