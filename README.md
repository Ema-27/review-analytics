# TourInsight

Applicazione cloud per la raccolta, gestione e analisi di recensioni di strutture e servizi turistici (hotel, ristoranti, attrazioni). Calcola sentiment e aspetti apprezzati/criticati di ogni recensione, mostra dashboard e grafici interattivi e genera — con un LLM eseguito interamente in locale — report di sintesi, analisi competitive tra strutture e suggerimenti di miglioramento.

L'intero sistema si avvia con un solo comando `docker compose up`. Tutta l'AI gira in locale: **nessuna chiave API a pagamento richiesta**.

## Indice

- [Funzionalità](#funzionalità)
- [Architettura](#architettura)
- [Stack tecnologico](#stack-tecnologico)
- [Provider AI pluggable](#provider-ai-pluggable)
- [Avvio rapido (Docker)](#avvio-rapido-docker)
- [Acquisire recensioni reali da Tripadvisor](#acquisire-recensioni-reali-da-tripadvisor)
- [Avvio in sviluppo (senza Docker)](#avvio-in-sviluppo-senza-docker)
- [Struttura del repository](#struttura-del-repository)
- [API principali](#api-principali)
- [Variabili d'ambiente](#variabili-dambiente)
- [Test automatici](#test-automatici)
- [Note di progettazione e limiti noti](#note-di-progettazione-e-limiti-noti)
- [Licenza](#licenza)

## Funzionalità

- **Acquisizione recensioni** da Tripadvisor via [Apify](https://apify.com) (con fallback automatico a un dataset di esempio), oppure inserimento manuale via API.
- **Analisi NLP** per ogni recensione: sentiment a 5 livelli e estrazione degli aspetti citati (colazione, personale, pulizia, prezzo, ...) con il relativo giudizio.
- **Dashboard e analytics**: elenco strutture con valutazione media e sentiment, trend delle valutazioni nel tempo, distribuzione del sentiment, aspetti più apprezzati e più criticati.
- **AI generativa** (LLM locale): report descrittivo di sintesi per struttura, analisi competitiva tra 2–6 strutture simili, suggerimenti di interventi migliorativi con priorità operative. Ogni testo è ancorato ai numeri reali calcolati dal sistema.
- **Dataset di esempio** incluso (12 strutture in 4 città europee, centinaia di recensioni multilingua) per provare tutte le funzionalità senza dipendere da servizi esterni.

## Architettura

```
                        ┌──────────────────────┐
                        │   Browser (utente)    │
                        └──────────┬───────────┘
                                   │ HTTP
                        ┌──────────▼───────────┐
                        │  frontend (nginx)     │  React + Vite, grafici
                        │  container :8080→80   │  interattivi (Recharts)
                        └──────────┬───────────┘
                                   │ /api  (reverse proxy nginx)
                        ┌──────────▼───────────┐
                        │  backend (FastAPI)    │  REST API, orchestrazione
                        │  container :8000      │  ingestion + AI/NLP
                        └──┬────────┬────────┬──┘
                           │        │        │
                 ┌─────────▼──┐  ┌──▼──────┐ │ sentiment/aspetti
                 │ PostgreSQL  │  │ Ollama   │ │ (Hugging Face,
                 │ container   │  │ container│ │  in-process nel
                 │ :5432       │  │ :11434   │ │  backend)
                 │             │  │ LLM      │ │
                 └─────────────┘  │ instruct │ │
                            ▲     │ (gemma2)  │ │
                            │     └──────────┘ │
                            │ fallback se non configurato
                 ┌──────────┴───────────┐
                 │   Apify API           │  scraping recensioni
                 │   (servizio esterno,  │  Tripadvisor (opzionale)
                 │   opzionale)          │
                 └────────────────────────┘
```

Servizi Docker orchestrati con **docker-compose**:

| Servizio | Ruolo |
|---|---|
| `db` | PostgreSQL 16 — persistenza di strutture, recensioni, analisi, job di ingestion |
| `ollama` | LLM instruct locale (`gemma2:2b`, quantizzato) per la generazione testuale |
| `ollama-init` | job one-shot: pre-scarica il modello all'avvio, poi termina |
| `backend` | API REST FastAPI, pipeline di ingestion e NLP |
| `frontend` | SPA React servita da nginx, che fa anche da reverse proxy `/api` verso il backend |

I container comunicano sulla rete interna creata da Compose; il sistema è riproducibile su qualsiasi macchina con Docker.

## Stack tecnologico

| Livello | Scelta | Note |
|---|---|---|
| Backend | **Python 3.11 + FastAPI** | API REST tipizzate (Pydantic), documentazione OpenAPI/Swagger automatica su `/docs`, supporto asincrono nativo. |
| ORM / Database | **SQLAlchemy 2.0 + PostgreSQL** | tipi SQLAlchemy portabili (JSON generico anziché JSONB): i test girano su SQLite in-memory senza modifiche al codice applicativo. |
| Frontend | **React 18 + Vite + Recharts** | SPA con componenti separati per grafici, pagine e chiamate API; grafici interattivi con tooltip e layout responsive. |
| Sentiment / aspetti | **Hugging Face `transformers` (locale)** | `nlptown/bert-base-multilingual-uncased-sentiment`: classificatore piccolo e veloce, eseguito in-process nel container backend. |
| Generazione testo | **LLM instruct locale via Ollama** (`gemma2:2b`, 4-bit) | container `ollama` dedicato; gratuito e offline dopo il primo download (~1 GB nel volume `ollama_data`). Modello sostituibile con la sola variabile `OLLAMA_MODEL` in `backend/.env`. |
| Acquisizione dati | **Apify REST API** (con fallback locale) | scraping di recensioni Tripadvisor; se Apify non è configurato o fallisce, si usa il dataset di esempio incluso. |
| Containerizzazione | **Docker + docker-compose** | avvio dell'intero sistema con un solo comando. |

## Provider AI pluggable

Le funzionalità di AI/NLP (`backend/app/ai_providers/`) sono dietro un'interfaccia astratta (`AIProvider`, pattern *Strategy*). Il resto del sistema dipende solo dall'interfaccia: cambiare motore richiede solo di scrivere una nuova classe e impostare `AI_PROVIDER`.

- **`OllamaProvider`** — *default*. Sentiment e aspetti tramite i modelli Hugging Face in-process; generazione di sintesi/confronto/suggerimenti tramite l'LLM instruct servito dal container `ollama`. Tutto locale e gratuito.
- **`HuggingFaceLocalProvider`** — variante interamente in-process: la generazione usa `google/flan-t5-base`. Più leggera (nessun container extra) ma con qualità testuale in italiano scarsa; utile per ambienti con RAM molto limitata.
- **`MockAIProvider`** — deterministico e istantaneo, senza scaricare modelli; usato nei test automatici e per demo offline rapidissime.

Ogni generazione testuale è **ancorata a fatti reali** calcolati da `stats_service.py` (numero recensioni, valutazione media, aspetti più citati, ...) iniettati nel prompt. In più `is_low_quality_generation` (`narrative_templates.py`) scarta gli output inutilizzabili (eco del prompt, testo ripetitivo, troppo corto): in quei casi il sistema restituisce comunque un report leggibile e coerente costruito dai template sui dati reali, senza mai propagare un errore all'utente.

Aggiungere un provider basato su API cloud (es. Claude, OpenAI) significa implementare la stessa interfaccia in una nuova classe e cambiare `AI_PROVIDER` in `.env`: nessun'altra parte del sistema va toccata.

## Avvio rapido (Docker)

Prerequisiti: Docker e Docker Compose.

```bash
# 1. Configurazione (i default funzionano già così come sono)
cp backend/.env.example backend/.env

# 2. Build e avvio dello stack
docker compose up --build

# 3. (in un altro terminale, a container avviati) popola i dati di esempio
curl -X POST http://localhost:8000/api/v1/ingestion/seed-demo-data
```

Poi apri:

- **Frontend**: http://localhost:8080
- **API + documentazione interattiva (Swagger UI)**: http://localhost:8000/docs

Al **primo** `docker compose up`:

- il servizio `ollama-init` scarica il modello LLM `gemma2:2b` (~1 GB) nel volume `ollama_data`; avviene **una sola volta** (i riavvii successivi lo riusano). Finché non è completo, le funzioni di generazione ricadono automaticamente sui report basati su template, senza errori. Progresso: `docker compose logs -f ollama-init`.
- al primo utilizzo del sentiment il backend scarica il modello Hugging Face di classificazione (~1 GB), poi messo in cache nel volume `model_cache`.

La prima generazione dopo l'avvio dello stack carica il modello in RAM (~15 s una tantum, se non è stato pre-scaldato); ogni generazione poi impiega ~25–45 s su CPU. Il modello resta caldo per 30 min (`OLLAMA_KEEP_ALIVE`). Un modello alternativo si imposta con `OLLAMA_MODEL` in `backend/.env`.

**Requisiti di RAM**: il default (`gemma2:2b`) richiede ~3–4 GB di RAM complessivi per lo stack.

Comandi utili:

```bash
docker compose ps               # stato dei servizi
docker compose logs -f backend  # log del backend
docker compose down             # ferma, mantenendo dati e modelli
docker compose up -d            # riavvio veloce (nessun ri-download)
docker compose down -v          # azzera anche DB e modelli scaricati
```

## Acquisire recensioni reali da Tripadvisor

Di default il sistema usa il dataset di esempio incluso. Per acquisire recensioni reali:

1. Crea un account gratuito su https://console.apify.com e genera un **API token** (*Settings → Integrations*).
2. **Approva l'Actor una tantum**: apri lo Store Apify, cerca *"Tripadvisor Reviews Scraper"* (`maxcopell/tripadvisor-reviews`) e avvia una run qualsiasi dalla console — al primo utilizzo chiede di approvare i permessi dell'Actor. Senza questa approvazione l'API risponde `full-permission-actor-not-approved` e il sistema ricade sul dataset di esempio.
3. In `backend/.env`:
   ```
   APIFY_API_TOKEN=apify_api_xxxxxxxxxxxxxxxxxxxx
   APIFY_TRIPADVISOR_ACTOR_ID=maxcopell/tripadvisor-reviews
   APIFY_RUN_TIMEOUT_SECS=300
   ```
4. Ricrea il container backend perché rilegga `.env`: `docker compose up -d backend` (⚠️ `docker compose restart` **non** ricarica le variabili d'ambiente).
5. Dalla pagina **Acquisizione dati** del Front-End, oppure via API:
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/ingestion/run \
     -H 'Content-Type: application/json' -d '{
       "property_name": "Hotel Danieli",
       "property_type": "hotel",
       "city": "Venezia",
       "country": "Italia",
       "tripadvisor_url": "https://www.tripadvisor.it/Hotel_Review-g187870-d199449-Reviews-Hotel_Danieli-Venice_Veneto.html",
       "max_reviews": 100
     }'
   ```
   `property_type` ∈ `hotel | restaurant | attraction`. L'URL deve essere la scheda della struttura (`.../Hotel_Review-g…-d…-Reviews-…`); i link in formato `HotelHighlight` (tipici dei risultati di ricerca) vengono normalizzati automaticamente.
6. Controlla il job restituito: `"source": "tripadvisor"` con `error_message` nullo significa che le recensioni reali sono state acquisite; `"source": "sample_dataset"` significa che Apify ha fallito (token mancante, Actor non approvato, credito esaurito, timeout) e il sistema è ricaduto sul dataset di esempio, con il motivo in `error_message`.

L'ingestion è **idempotente** (deduplica per `external_review_id`): rilanciarla aggiunge solo le recensioni nuove.

Se per una struttura non presente nel dataset di esempio non è configurato Apify (o l'URL è errato / l'Actor non approvato), la ingestion si conclude con `records_ingested: 0` e un `error_message` esplicativo, **senza** creare una struttura vuota né copiare i dati di un'altra struttura.

Recensioni da altre fonti si possono inserire una a una con `POST /api/v1/reviews` (vengono analizzate immediatamente).

## Avvio in sviluppo (senza Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# richiede un PostgreSQL raggiungibile (o cambiare DATABASE_URL in .env);
# senza un container Ollama, impostare AI_PROVIDER=huggingface_local o mock
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, con proxy verso il backend su :8000
```

## Struttura del repository

```
.
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py              # entry point FastAPI
│   │   ├── config.py            # configurazione da variabili d'ambiente
│   │   ├── database.py          # engine/sessione SQLAlchemy
│   │   ├── models/              # modelli ORM (Property, Review, ...)
│   │   ├── schemas/             # schemi Pydantic (request/response API)
│   │   ├── routers/             # endpoint REST (properties, reviews, analytics, ai, ingestion)
│   │   ├── services/            # logica applicativa (ingestion, stats, nlp factory, apify client)
│   │   ├── ai_providers/        # provider AI pluggable (interfaccia astratta + implementazioni)
│   │   └── data/sample_reviews.json  # dataset di esempio multilingua
│   ├── scripts/generate_sample_dataset.py
│   ├── tests/                   # test automatici (pytest)
│   ├── Dockerfile
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── api/client.js        # client Axios verso le API REST
    │   ├── components/          # componenti riutilizzabili (grafici, card, navbar)
    │   ├── pages/               # pagine (Dashboard, Dettaglio struttura, Confronto, Acquisizione)
    │   └── theme/               # design tokens colore (palette dati accessibile)
    ├── Dockerfile
    └── nginx.conf
```

## API principali

Documentazione interattiva completa su `/docs` (Swagger UI) quando il backend è in esecuzione. Prefisso: `/api/v1`.

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/properties` | Elenco strutture con statistiche aggregate (filtrabile per tipo/città) |
| GET | `/properties/{id}` | Dettaglio di una struttura |
| GET | `/reviews?property_id=...` | Recensioni di una struttura |
| POST | `/reviews` | Inserimento manuale di una recensione (analizzata subito) |
| GET | `/analytics/properties/{id}` | Trend valutazioni, distribuzione sentiment, aspetti principali |
| POST | `/ai/summary` | Report descrittivo di sintesi per una struttura |
| POST | `/ai/comparison` | Analisi competitiva tra 2–6 strutture |
| POST | `/ai/suggestions` | Suggerimenti di miglioramento basati sulle criticità |
| POST | `/ingestion/run` | Acquisizione mirata (Apify con fallback automatico) |
| POST | `/ingestion/seed-demo-data` | Popola il database con l'intero dataset di esempio |

## Variabili d'ambiente

Elenco completo con descrizione in `backend/.env.example`. Le principali:

- `DATABASE_URL` — connection string PostgreSQL
- `APIFY_API_TOKEN` — token Apify (opzionale, fallback automatico se assente)
- `APIFY_RUN_TIMEOUT_SECS` — timeout di attesa della run Apify (default 120)
- `AI_PROVIDER` — `ollama` (default), `huggingface_local` oppure `mock`
- `OLLAMA_MODEL` — modello LLM per la generazione (default `gemma2:2b`; letto sia dal backend sia dal job `ollama-init` che lo pre-scarica)
- `OLLAMA_BASE_URL` — URL del servizio Ollama (impostato da docker-compose a `http://ollama:11434`)
- `HF_SENTIMENT_MODEL`, `HF_GENERATION_MODEL` — modelli Hugging Face usati
- `CORS_ALLOW_ORIGINS` — origini ammesse per il CORS (default `*`)

## Test automatici

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

I test (27) usano SQLite in-memory e il `MockAIProvider` per essere veloci, deterministici e non dipendere dal download di modelli o da un database esterno, pur validando l'intera catena applicativa (ingestion → persistenza → analisi statistica → generazione report → API REST). Fra gli altri: `test_generation_quality_guard.py` verifica il filtro che scarta gli output generativi inutilizzabili facendo scattare il fallback a template; `test_apify_normalization.py` copre il mapping e la normalizzazione degli URL dell'Actor Tripadvisor.

## Note di progettazione e limiti noti

- **Estrazione aspetti**: basata su un lessico multilingua (IT/EN/FR/ES) + classificazione del sentiment della frase, non su un modello ABSA dedicato. Scelta per restare leggeri ed eseguibili interamente in locale, con risultati interpretabili; il lessico è facilmente estendibile (`aspect_lexicon.py`).
- **Qualità e latenza della generazione testuale**: il provider di default usa un LLM instruct quantizzato (`gemma2:2b`) eseguibile su CPU, con qualità in italiano adeguata per report descrittivi brevi ma inferiore a un LLM cloud di ultima generazione; su CPU ogni generazione richiede ~25–45 s. Ogni funzione di generazione ha comunque un fallback a template basato sui dati reali, così il sistema resta sempre utilizzabile anche se il container `ollama` non è pronto o l'output non è valido. Per qualità/latenza da produzione, l'architettura a provider rende immediato il passaggio a un provider cloud.
- **Elaborazione NLP in linea**: l'analisi sentiment/aspetti avviene durante la richiesta di ingestion (in batch: una sola inferenza per l'intero lotto di recensioni). Per volumi molto maggiori la si delegherebbe a una coda asincrona (es. Celery + Redis); alla scala attuale la scelta mantiene il sistema più semplice da comprendere ed eseguire.
- **Dataset di esempio**: sintetico, costruito con template realistici multilingua che menzionano aspetti concreti (colazione, personale, pulizia, ...), così da mostrare in modo credibile tutte le funzionalità anche senza connettività verso servizi esterni.

## Licenza

Distribuito con licenza [MIT](LICENSE).
