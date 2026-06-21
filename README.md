# Wedge — Market Opportunity Brief Generator

Hackathon submission for Bright Data GTM Intelligence track.

## Run locally

1. Copy `.env.example` to `.env` and fill in API keys.
2. `python -m venv .venv && .venv\Scripts\pip install -e ".[dev]"`
3. `.venv\Scripts\playwright install chromium` (one-time)
4. `.venv\Scripts\uvicorn wedge.app:app --reload`
5. Open http://localhost:8000 and paste a product idea.

## Run tests

`.venv\Scripts\pytest -v`

All tests use saved Bright Data fixtures — no quota burn.

## Architecture

See `docs/superpowers/specs/2026-05-25-wedge-design.md`.
# Wedge — Generador de Market Opportunity Briefs

> Pegá la idea de un producto y, en ~60 segundos, obtené un **brief de oportunidad de mercado** de una sola página: competidores dominantes, quejas reales de sus clientes, huecos de oportunidad y ángulos de posicionamiento sugeridos.

Proyecto presentado al hackathon de **Bright Data — track GTM Intelligence (Track 1)**.

---

## 1. El concepto

Validar una idea de producto suele costar semanas de research competitivo manual: googlear competidores, leer reviews de G2, bucear en Reddit, tratar de detectar patrones. Wedge comprime ese trabajo en una sola pantalla y ~60 segundos.

El usuario escribe algo como *"AI meeting note-taker para equipos de ventas"* y recibe un **Market Opportunity Brief** con:

1. **Competidores dominantes** del espacio.
2. **Quejas de clientes estructuradas** por competidor (de G2 y Reddit, con cita textual y link a la fuente).
3. **Huecos de oportunidad** sintetizados por un LLM a partir de esas quejas.
4. **Ángulos de posicionamiento** sugeridos para diferenciarse.

El mismo artefacto sirve a dos audiencias:

- **Founders / indie hackers** validando una idea → lo leen de arriba hacia abajo buscando *"¿hay un wedge acá?"*.
- **PMs / PMMs** afinando posicionamiento → lo leen competidor por competidor buscando *"¿cómo me diferencio?"*.

Además del one-shot, hay un toggle **"watch this idea"** que marca la idea para re-correrse periódicamente y enviar un resumen de los cambios (deltas) entre briefs.

### No-objetivos (recortes de alcance del hackathon)

- No es una herramienta de outreach (no redacta emails, no empuja a un CRM).
- No des-anonimiza usuarios de Reddit.
- No scrapea Twitter/X ni LinkedIn.
- Sin features multi-usuario ni de equipo.

El eje de optimización es **caso de uso novedoso + pulido end-to-end con un toque agéntico**, no profundidad técnica sobre Bright Data (la cuota de la API es limitada, y por eso hay un *budget cap* explícito).

---

## 2. Arquitectura

Wedge es **ligeramente agéntico**: un LLM *planner* toma decisiones reales aguas arriba, después corre un pipeline de ejecución determinístico, y al final un LLM *synthesizer* redacta el brief. Solo hay **dos puntos de llamada al LLM** (planificación y síntesis), lo que mantiene el costo y la latencia bajo control.

```
[Idea del usuario]
       │
       ▼
1. Planner (LLM)          → queries SERP, subreddits objetivo, hints de categoría G2
       │
       ▼
2. Discovery              → Bright Data SERP API; rankea candidatos por frecuencia de mención
       │
       ▼
3. Confirmación en G2     → Bright Data (Web Unlocker); deja ≤5 con presencia real en G2
       │
       ▼
4. Minería de quejas      → por competidor: reviews 1-2★ de G2 + threads de Reddit vía SERP
       │
       ▼
5. Síntesis (LLM)         → clusteriza quejas, detecta temas/huecos, redacta posicionamiento
       │
       ▼
6. Render del brief       → HTML server-rendered, persistido en SQLite
```

### Principios de diseño

- **Cada módulo hace un solo trabajo**, se comunica vía dataclasses (`types.py`), no comparte estado global y es testeable de forma aislada con fixtures guardadas de Bright Data.
- **Persistencia por paso.** Cada etapa guarda su output en SQLite antes de que corra la siguiente. Esto permite (a) reintentar solo la síntesis sin re-scrapear, y (b) alimentar la narrativa de progreso vía SSE.
- **Streaming en vez de cola.** El job de ~60s entra dentro de una respuesta HTTP con **Server-Sent Events (SSE)**; no hace falta una cola de tareas ni workers.
- **Degradación elegante.** Un brief parcial es mejor que un 500: si una fuente falla o se agota el presupuesto de llamadas, el pipeline sigue con lo que tiene y marca `partial: true`.

### Flujo de estado y eventos

El orquestador (`orchestrator.py`) emite un evento SSE por etapa, y la UI los va narrando en vivo:

| Etapa | Estado en DB | Evento SSE |
|---|---|---|
| Planner | `planning` | `planning_done` |
| Discovery | `discovery` | `candidates_found` |
| Confirmación G2 | `confirming` | `competitors_confirmed` |
| Minería de quejas | `mining` | `complaints_mined` (uno por competidor) |
| Síntesis | `synthesizing` | `brief_ready` |

### Presupuesto de Bright Data

`BrightDataClient` cuenta cada llamada y aborta cuando supera el cap (`WEDGE_BRIGHT_DATA_CALL_CAP`, default **40**). Al excederse, se corre la síntesis con lo recolectado y el brief queda marcado como parcial.

| Etapa | Llamadas (objetivo) |
|---|---|
| Planner | 0 |
| Discovery | 2–3 SERP |
| Confirmación G2 | 5–7 |
| Quejas | 15–20 (≈5 competidores × 3–4) |
| **Total objetivo** | **~25–30** |
| **Cap duro** | **40** |

---

## 3. Componentes (`src/wedge/`)

| Módulo | Rol |
|---|---|
| `app.py` | App FastAPI: endpoints, SSE, templates Jinja2. |
| `orchestrator.py` | Corre el pipeline paso a paso, persiste artefactos y emite eventos. |
| `planner.py` | Llamada LLM #1: convierte la idea en queries SERP, subreddits y hints de G2. Tiene fallback hardcodeado si el JSON sale mal. |
| `discovery.py` | Lanza las queries en paralelo (`asyncio.gather`) y usa el LLM para extraer nombres de productos de los resultados; rankea por frecuencia de mención. |
| `g2_confirm.py` | Para cada candidato arma la URL de G2 y la trae vía Web Unlocker; confirma extrayendo `ratingValue` y `reviewCount` del markup schema.org. Conserva ≤5. |
| `complaints.py` | Por competidor: reviews 1-2★ de G2 + top-3 threads de Reddit (encontrados vía SERP). Todo en paralelo. |
| `synthesis.py` | Pre-clusteriza las quejas con scikit-learn (TF-IDF + clustering aglomerativo) para reducir tokens, y hace la llamada LLM #2 que redacta el brief. |
| `bright_data.py` | Cliente async de Bright Data: SERP API, Web Unlocker (`fetch`) y Scraping Browser (Playwright sobre CDP). Lleva la cuenta de llamadas y aplica el cap. |
| `llm.py` | Cliente LLM sobre la API OpenAI-compatible de NVIDIA. |
| `db.py` | Capa SQLite (stdlib `sqlite3`): tabla `jobs` con un JSON por artefacto. |
| `watcher.py` | Diff entre dos briefs (temas nuevos + cambios de frecuencia) y formateo del email de delta. |
| `config.py` | Carga config desde variables de entorno / `.env`. |
| `types.py` | Dataclasses compartidas (`PlannerOutput`, `Candidate`, `Competitor`, `Complaint`, `ComplaintTheme`, `Brief`). |

### Detalle de la síntesis

En vez de mandar todas las quejas crudas al LLM, primero se **clusterizan localmente**:

1. Un stemmer chico colapsa variantes morfológicas (`crashes`/`crashing` → `crash`).
2. `TfidfVectorizer` vectoriza los excerpts.
3. `AgglomerativeClustering` (distancia coseno, umbral 0.75) agrupa quejas temáticamente relacionadas.

Esto baja los tokens enviados, es **determinístico** y no gasta llamadas extra a ninguna API. Recién el resumen clusterizado va al LLM, que produce el JSON final del brief (tldr, temas con severidad/frecuencia/citas, huecos, posicionamiento).

---

## 4. Stack tecnológico

| Capa | Elección | Por qué |
|---|---|---|
| Backend | **Python 3.11+ · FastAPI · Uvicorn** | Mejor ecosistema para Bright Data + LLMs. |
| LLM | **NVIDIA build — Llama 3.3 70B Instruct** (`meta/llama-3.3-70b-instruct`) vía API OpenAI-compatible (SDK `openai`) | Mismo modelo para planner y síntesis; el cliente mantiene el split por roles para poder cambiarlos por separado. |
| Recolección de datos | **Bright Data** — SERP API, Web Unlocker y Scraping Browser (vía Playwright/CDP) | Acceso a SERP de Google y a sitios anti-bot (G2, Reddit). |
| Clustering | **scikit-learn** (TF-IDF + Agglomerative) + **NumPy** | Pre-clustering determinístico y sin costo de API. |
| Frontend | **HTML server-rendered (Jinja2) + JS mínimo para SSE** | Sin build step; cero fricción de tooling. |
| Persistencia | **SQLite** (`sqlite3` de la stdlib) | Zero-ops; habilita el diffing semanal del "watch". |
| Cola / async | **Ninguna** — request síncrono con streaming SSE; concurrencia interna con `asyncio.gather` | Un job de ~60s entra en una respuesta HTTP streameada. |
| Tests | **pytest · pytest-asyncio · respx** | Tests offline contra fixtures guardadas de Bright Data. |

> **Nota histórica:** el documento de diseño original (`docs/superpowers/specs/`) planteaba usar Claude (Haiku para el planner, Sonnet para la síntesis). La implementación migró a la build de NVIDIA con Llama 3.3 70B; las claves `"haiku"`/`"sonnet"` en `llm.py` quedaron como nombres de rol y hoy apuntan ambas al mismo modelo.

---

## 5. Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Formulario para pegar la idea. |
| `POST` | `/generate` | Crea el job, dispara el pipeline en background y devuelve la vista de progreso. |
| `GET` | `/stream/{job_id}` | Stream SSE con los eventos de cada etapa. |
| `GET` | `/brief/{job_id}` | Brief renderizado en HTML. |
| `POST` | `/watch/{job_id}` | Marca la idea para re-correrse (toggle "watch"). |

---

## 6. Cómo correrlo localmente

**Requisitos:** Python 3.11+, una API key de la build de NVIDIA y credenciales de Bright Data (zonas de SERP, Web Unlocker y endpoint del Scraping Browser).

1. Copiá `.env.example` a `.env` y completá las claves:

   ```dotenv
   NVIDIA_API_KEY=nvapi-...
   BRIGHT_DATA_API_TOKEN=...
   BRIGHT_DATA_SERP_ZONE=serp_api1
   BRIGHT_DATA_UNLOCKER_ZONE=unlocker1
   BRIGHT_DATA_BROWSER_WS=wss://brd-customer-...@brd.superproxy.io:9222
   WEDGE_DB_PATH=./wedge.db
   WEDGE_BRIGHT_DATA_CALL_CAP=40
   ```

2. Creá el entorno e instalá:

   ```bash
   python -m venv .venv
   .venv\Scripts\pip install -e ".[dev]"
   ```

3. Instalá Chromium para Playwright (una sola vez):

   ```bash
   .venv\Scripts\playwright install chromium
   ```

4. Levantá el server:

   ```bash
   .venv\Scripts\uvicorn wedge.app:app --reload
   ```

5. Abrí http://localhost:8000 y pegá una idea de producto.

---

## 7. Tests

```bash
.venv\Scripts\pytest -v
```

Todos los tests usan **fixtures guardadas de Bright Data** (`tests/fixtures/`), así que corren offline y **no consumen cuota**. Hay tests unitarios por módulo más un end-to-end (`test_app_e2e.py`) que ejercita el pipeline completo con todas las llamadas de Bright Data mockeadas.

---

## 8. Modelo de datos

Una sola tabla `jobs` en SQLite, con un campo JSON por artefacto del pipeline:

```
jobs(
  id, idea, status, created_at,
  planner_output_json, candidates_json, competitors_json,
  complaints_json, brief_json,
  watched, bright_data_calls
)
```

Guardar el output de cada etapa por separado es lo que permite reintentar solo la síntesis y, a futuro, diffear briefs semana a semana (`watcher.py`).

---

## 9. Estructura del repo

```
src/wedge/
  app.py            # FastAPI + SSE + templates
  orchestrator.py   # pipeline paso a paso
  planner.py        # LLM #1: idea → plan de research
  discovery.py      # SERP → candidatos
  g2_confirm.py     # confirmación en G2
  complaints.py     # minería de quejas (G2 + Reddit)
  synthesis.py      # clustering + LLM #2 → brief
  bright_data.py    # cliente Bright Data (SERP/Unlocker/Browser)
  llm.py            # cliente LLM (NVIDIA/Llama)
  db.py             # capa SQLite
  watcher.py        # diff de briefs + email de delta
  config.py · types.py
  templates/ · static/
tests/              # unit + e2e con fixtures
docs/superpowers/   # spec y plan de diseño original
```
