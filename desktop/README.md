# Monitor de Vagas & Notícias — versão de secretária

Um `.exe` a sério: abre numa janela própria, sem barra de endereço nem
separadores de browser. Não corre nada localmente e não guarda nenhuma
password ou chave de API dentro do ficheiro — é só uma janela nativa
apontada para o site que já está em produção no Render
(`monitor-vagas-noticias.onrender.com/dashboard`). Por isso precisa de
internet para funcionar, tal como precisavas de internet para abrir o
site num browser.

## Construir o .exe (fazer só uma vez, ou sempre que mudares `app_desktop.py`)

Estes comandos correm no teu terminal normal do Windows (o mesmo onde
corres o `git`), **não** no terminal isolado desta conversa — construir
um `.exe` do Windows só é possível a partir de um Windows a sério.

```
cd "C:\Users\elisa\Documents\monitor-vagas-noticias\desktop"
pip install -r requirements-desktop.txt
pyinstaller --onefile --windowed --icon=monitor.ico --name "Monitor" app_desktop.py
```

O ficheiro final fica em `desktop\dist\Monitor.exe`. Podes copiá-lo para
o ambiente de trabalho, fixá-lo na barra de tarefas, o que quiseres —
é um ficheiro independente, não precisa dos outros ficheiros da pasta
`desktop` para funcionar.

## Um aviso do Windows na primeira vez que abrires

Como o `.exe` não tem uma assinatura digital paga (isso custa dinheiro
e exige uma empresa registada), o Windows Defender SmartScreen
provavelmente vai avisar "Windows protegeu o teu PC" na primeira vez
que o abrires, no teu computador ou em qualquer outro onde o copies.
Não é o antivírus a dizer que há um vírus, é só o SmartScreen a
desconfiar de qualquer `.exe` novo sem assinatura. Para abrir: clica em
"Mais informações" e depois em "Executar mesmo assim". Isto só acontece
a primeira vez que o Windows vê aquele ficheiro específico.

## Se a janela não abrir

O pywebview usa o WebView2 do Windows (o motor do Edge) para desenhar a
página. Os Windows 10/11 atualizados já o trazem instalado; se a janela
não abrir de todo, o Windows normalmente mostra um instalador do
"WebView2 Runtime" sozinho, ou podes ir a
https://developer.microsoft.com/microsoft-edge/webview2/ e instalá-lo
manualmente.
