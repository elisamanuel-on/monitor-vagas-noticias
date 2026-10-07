# Monitor de Vagas & Notícias

**Versão atual:** 1.8.0

Painel que acompanha, todos os dias e automaticamente:

- **Vagas de emprego reais**, via [API oficial da ITJobs](https://www.itjobs.pt/api) - vagas de tecnologia em Portugal, filtradas pelas palavras-chave configuradas em `VAGAS_QUERY`.
  - (Foram testadas e ficaram de fora do robô automático duas outras fontes, por bloquearem sempre os pedidos vindos do GitHub Actions, mesmo com cabeçalhos de browser real, não é algo que dê para contornar do nosso lado: a [API pública do Landing.jobs](https://landing.jobs), que devolvia sempre 403; e o [Net-Empregos](https://www.net-empregos.com/emprego-informatica-programacao.asp), que redirecionava sempre para a página de login em vez de mostrar a lista de vagas.)
- **Notícias reais** sobre o setor de tecnologia interativa (ecrãs interativos, digital signage, mesas multitoque) - via feed RSS de pesquisa do Google Notícias.

Tudo fica guardado em **MongoDB Atlas** e servido por uma API em **FastAPI**, com um frontend próprio em HTML/CSS/JS puro.

Projeto de portefólio de [Elisama Manuel](https://elisamanuel-on.github.io/portfolio.html).

## Porque existe

Substitui o trabalho manual de percorrer sites de emprego e ficar de olho em notícias do setor, os robôs correm sozinhos uma vez por dia via GitHub Actions, e o dashboard fica só para consulta e para marcar o estado de cada candidatura.

## Arquitetura

```
app/
  main.py              # API FastAPI (rotas /api/vagas, /api/noticias, /api/resumo) + serve o frontend
  auth.py              # login com conta Google (Authlib) — ver "Login com Google" abaixo
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

Em [itjobs.pt/api](https://www.itjobs.pt/api), preenche só o teu email, a chave (de leitura) chega logo.

### 3. Variáveis de ambiente

Copia `.env.example` para `.env` e preenche com os teus valores. **O `.env` nunca é enviado para o git** (está no `.gitignore`).

### 4. Secrets no GitHub (para o robô agendado correr sozinho)

No repositório: **Settings → Secrets and variables → Actions**

- Secrets (valores sensíveis): `MONGODB_URI`, `ITJOBS_API_KEY`
- Variables (não sensíveis, opcionais, têm valores por omissão no código se não definires): `MONGODB_DB`, `VAGAS_QUERY`, `VAGAS_LOCATION_IDS`, `NOTICIAS_QUERY`

O dashboard (`/dashboard`) exige login — qualquer pessoa com o link pode entrar com a própria conta Google, cada uma vê o painel com a sua sessão própria.

1. Cria um projeto em [console.cloud.google.com](https://console.cloud.google.com).
2. Em **Google Auth Platform → Público-alvo**, tipo de utilizador **Externo**.
3. Em **Clientes → Criar cliente**, tipo **Aplicação Web**, com estes URIs de redirecionamento autorizados:
   - `https://<o-teu-dominio-no-render>/auth/callback`
   - `http://localhost:8000/auth/callback` (para testar localmente)
4. Copia o **Client ID** e o **Client Secret** gerados.
5. Preenche `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env` (local) e como variáveis de ambiente no Render.
6. Gera uma `SECRET_KEY` própria (usada só para assinar o cookie de sessão, nada a ver com o Google): `python -c "import secrets; print(secrets.token_hex(32))"`.

Enquanto o ecrã de consentimento estiver em modo "Teste" no Google Cloud Console, só as contas adicionadas em "Utilizadores de teste" conseguem entrar — publica a app aí quando estiveres pronta para outras pessoas usarem.

### 6. Variáveis de ambiente no Render (para o dashboard)

Se fores publicar o dashboard no Render (ver `render.yaml`), define `MONGODB_URI`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `SECRET_KEY` manualmente no dashboard do Render — tal como no Controlo de Gastos, nunca ficam no repositório.

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

Os testes usam respostas simuladas da API da ITJobs e do feed RSS (não fazem pedidos reais à internet) e uma base de dados MongoDB simulada em memória (`mongomock`), correm em qualquer máquina, sem precisar de chaves API nem de ligação real ao MongoDB.

## Deployment

- **Robô de recolha**: corre automaticamente via GitHub Actions (`.github/workflows/scraper.yml`), todos os dias às 07:00 UTC, ou manualmente a partir do separador "Actions" do repositório ("Run workflow").
- **Dashboard**: `render.yaml` configura o deploy no [Render](https://render.com) (plano gratuito), a correr a cada push para `main`.

## Novidades na v1.8.0

- **Vagas e notícias em páginas de 10**: em vez de uma lista enorme, cada página mostra 10 resultados, com os botões "Anterior" e "Seguinte" e o indicador "Página 1 de N". Ao mudar de página, a vista volta ao início da lista. Quando se aplica um filtro, volta à página 1. (O botão provisório "Ver mais" da versão anterior foi substituído.)

## Novidades na v1.7.1

- **Página de privacidade** (`/privacidade`): explica em português simples que dados pessoais ficam guardados ao entrar com o Google (nome, email, foto), porquê, e como pedir para serem apagados. Link visível no rodapé da vitrine e do painel, e uma nota junto ao botão de entrar na vitrine.
- **Apagar a própria conta**: botão "Apagar a minha conta" no cabeçalho do painel (ao lado de "Sair"), que remove por completo o registo do utilizador da base de dados — direito ao apagamento, cumprido em autosserviço.

## Novidades na v1.7.0

- **Login com conta Google**: o dashboard (`/dashboard`) passou a exigir login — qualquer pessoa com o link pode entrar com a sua própria conta Google, sem passwords geridas por nós (ver `app/auth.py` e a secção "Login com conta Google" acima). O cabeçalho do painel mostra o nome/foto de quem está autenticado e um botão para sair.
- Esta é a fase 1 do suporte multiutilizador: por agora as vagas e notícias continuam partilhadas por todos os utilizadores (é a mesma base de dados de sempre); a próxima fase separa as candidaturas de cada pessoa.
- A vitrine pública (`/`) continua sem exigir login — só o painel de trabalho é que pede.

## Novidades na v1.6.0

- **Limpeza automática de dados antigos**: o robô diário apaga agora notícias e vagas com mais de 90 dias (usando `publicado_em`). Nunca apaga vagas em "candidatei_me" ou "resposta_recebida" - esse é o teu histórico real de candidaturas, e conta para a taxa de resposta nas Estatísticas. Ver `limpar_dados_antigos()` em `app/database.py`.

## Novidades na v1.5.0

- Identidade visual própria ("Azul Editorial") na vitrine pública e no painel de trabalho.
- Aba de **Estatísticas**: evolução de vagas/notícias nos últimos 30 dias, distribuição por termo de pesquisa/localização/fonte e taxa de resposta às candidaturas.
- Indicador de vagas novas desde a última visita, na própria aba "Vagas".
- Versão de secretária (`desktop/`): um `.exe` nativo para Windows, com ecrã de espera enquanto o Render acorda e notificações nativas quando aparecem vagas novas.

## Notas de design

- **Login com conta Google, sem gerir passwords**: o Google trata da autenticação, nós só guardamos o nome, o email e a foto públicos da conta (coleção `utilizadores`). Ver `app/auth.py`.
- **Dados ainda partilhados (fase 1)**: o login identifica quem está a ver o painel, mas as vagas e notícias em si continuam a mesma base de dados para todos os utilizadores — a separação por utilizador é a fase seguinte.
- **Nunca apaga o estado de uma vaga já classificada**: quando o robô encontra outra vez uma vaga que já conheces, atualiza os outros dados (salário, etc.) mas nunca mexe no campo `estado` que tu própria vais mudando no dashboard.
- **Dados reais desde o primeiro dia**: nenhuma das fontes usa dados de exemplo, a API da ITJobs e o feed RSS são sempre consultados ao vivo.
- **Retenção de 90 dias**: notícias e vagas não candidatadas/arquivadas com mais de 90 dias são apagadas automaticamente pelo robô diário, para a base de dados não crescer para sempre. Vagas em "candidatei_me" ou "resposta_recebida" nunca são apagadas.
- **Direito ao apagamento (ver `/privacidade`)**: quem entrou com a conta Google pode apagar a própria conta a qualquer momento, no próprio painel — a conta não fica guardada "para sempre" sem controlo da pessoa.
