# Monitor de Vagas & Notícias

Painel pessoal (sem login) que acompanha, todos os dias e automaticamente:

- **Vagas de emprego reais**, via [API oficial da ITJobs](https://www.itjobs.pt/api) — vagas de tecnologia em Portugal, filtradas pelas palavras-chave configuradas em `VAGAS_QUERY`.
  - (Foram testadas e ficaram de fora do robô automático duas outras fontes, por bloquearem sempre os pedidos vindos do GitHub Actions — mesmo com cabeçalhos de browser real, não é algo que dê para contornar do nosso lado: a [API pública do Landing.jobs](https://landing.jobs), que devolvia sempre 403; e o [Net-Empregos](https://www.net-empregos.com/emprego-informatica-programacao.asp), que redirecionava sempre para a página de login em vez de mostrar a lista de vagas.)
- **Notícias reais** sobre o setor de tecnologia interativa (ecrãs interativos, digital signage, mesas multitoque) — via feed RSS de pesquisa do Google Notícias.

Tudo fica guardado em **MongoDB Atlas** e servido por uma API em **FastAPI**, com um frontend próprio em HTML/CSS/JS puro.

Projeto de portefólio de [Elisama Manuel](https://elisamanuel-on.github.io/portfolio.html).

## Porque existe

Substitui o trabalho manual de percorrer sites de emprego e ficar de olho em notícias do setor — os robôs correm sozinhos uma vez por dia via GitHub Actions, e o dashboard fica só para consulta e para marcar o estado de cada candidatura.

## Arquitetura

```
app/
  main.py              # API FastAPI (rotas /api/vagas, /api/noticias, /api/resumo) + serve o frontend
  database.py          # ligação ao MongoDB (lê MONGODB_URI do ambiente)
  models.py            # schemas Pydantic
  scrapers/
    vagas_itjobs.py        # recolhe vagas reais da API da ITJobs
    noticias_rss.py        # recolhe notícias reais via RSS
scripts/
  run_scrapers.py      # ponto de entrada usado pelo GitHub Actions (e para correr à mão)
static/                # frontend (HTML/CSS/JS puro, sem framework)
tests/                 # testes com respostas simuladas (mocks), não fazem pedidos reais
.github/workflows/
  scraper.yml          # corre os robôs todos os dias às 07:00 UTC
  tests.yml            # corre os testes em cada push/PR
```

Os robôs (`scripts/run_scrapers.py`) e a app web (`app/main.py`) são independentes: o robô só precisa de acesso ao MongoDB para gravar dados; a app web só precisa do MongoDB para os ler. Podes correr um sem o outro.

## Configuração inicial

### 1. MongoDB Atlas (gratuito)

1. Cria conta em [mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register).
2. Cria um cluster gratuito (**M0**).
3. Cria um utilizador de base de dados (**Database Access**).
4. Em **Network Access**, adiciona `0.0.0.0/0` (necessário para o GitHub Actions, que usa IPs variáveis).
5. Em **Connect → Drivers → Python**, copia a connection string. Fica algo como:
   ```
   mongodb+srv://utilizador:password@cluster0.xxxxx.mongodb.net/?appName=Cluster0
   ```

### 2. API key da ITJobs (gratuita)

Em [itjobs.pt/api](https://www.itjobs.pt/api), preenche só o teu email — a chave (de leitura) chega logo.

### 3. Variáveis de ambiente

Copia `.env.example` para `.env` e preenche com os teus valores. **O `.env` nunca é enviado para o git** (está no `.gitignore`).

### 4. Secrets no GitHub (para o robô agendado correr sozinho)

No repositório: **Settings → Secrets and variables → Actions**

- Secrets (valores sensíveis): `MONGODB_URI`, `ITJOBS_API_KEY`
- Variables (não sensíveis, opcionais — têm valores por omissão no código se não definires): `MONGODB_DB`, `VAGAS_QUERY`, `VAGAS_LOCATION_IDS`, `NOTICIAS_QUERY`

### 5. Variável de ambiente no Render (para o dashboard)

Se fores publicar o dashboard no Render (ver `render.yaml`), define `MONGODB_URI` manualmente no dashboard do Render — tal como no Controlo de Gastos, nunca fica no repositório.

## Correr localmente

```bash
pip install -r requirements-dev.txt

# correr os robôs de recolha uma vez
python -m scripts.run_scrapers

# arrancar o dashboard
uvicorn app.main:app --reload
# abre http://localhost:8000
```

## Testes

```bash
pytest -v
```

Os testes usam respostas simuladas da API da ITJobs e do feed RSS (não fazem pedidos reais à internet) e uma base de dados MongoDB simulada em memória (`mongomock`) — correm em qualquer máquina, sem precisar de chaves API nem de ligação real ao MongoDB.

## Deployment

- **Robô de recolha**: corre automaticamente via GitHub Actions (`.github/workflows/scraper.yml`), todos os dias às 07:00 UTC, ou manualmente a partir do separador "Actions" do repositório ("Run workflow").
- **Dashboard**: `render.yaml` configura o deploy no [Render](https://render.com) (plano gratuito), a correr a cada push para `main`.

## Notas de design

- **Sem autenticação** — é uma ferramenta pessoal, não uma app multiutilizador.
- **Nunca apaga o estado de uma vaga já classificada**: quando o robô encontra outra vez uma vaga que já conheces, atualiza os outros dados (salário, etc.) mas nunca mexe no campo `estado` que tu própria vais mudando no dashboard.
- **Dados reais desde o primeiro dia**: nenhuma das fontes usa dados de exemplo — a API da ITJobs e o feed RSS são sempre consultados ao vivo.
