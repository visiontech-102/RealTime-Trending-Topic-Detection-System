# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-Time Trending Topic Detection System — a Final Year Project (FYP 2026) that collects Twitter/X data and applies NLP topic modeling (BERTopic + LDA) to detect trending topics in English and Somali. It exposes a FastAPI backend and a React dashboard.

---

## Commands

### API (run from `api/`)

```bash
# Start the FastAPI server
uvicorn app.main:app --reload

# Run all tests
pytest tests/ -v

# Run a single test file or test function
pytest tests/test_api_routes.py -v
pytest tests/test_api.py::test_function_name -v

# Run integration tests only (requires live MongoDB)
pytest tests/ -m integration -v
```

### Dashboard (run from `dashboard/`)

```bash
npm run dev       # Vite dev server (connects to API at http://localhost:8000)
npm run build     # Production build
npm run lint      # ESLint
npm run preview   # Preview production build
```

---

## Architecture

### Two separate apps, one repo

```
api/         # Python FastAPI backend
dashboard/   # React + Vite frontend
```

The frontend makes all API calls to `http://localhost:8000` (hardcoded in `dashboard/src/services/api.js`).

---

### Backend (`api/`)

**Entry point**: `app/main.py` — creates the FastAPI `app`, registers CORS middleware, mounts the router from `app/routes.py`, and launches four async background loops on startup.

**Background loops** (all started in `lifespan()`):
| Loop | Interval | Env override |
|---|---|---|
| Data collection (Twitter → MongoDB) | 15 min | — |
| BERTopic training | 30 min | `BERTOPIC_TRAIN_INTERVAL_MINUTES` |
| Model comparison (LDA vs BERTopic) | 168 h | `COMPARISON_INTERVAL_HOURS` |
| Email digest | 24 h | `DIGEST_INTERVAL_HOURS` |

The data collection loop enforces a hard session quota (`app.state.max_quota_limit = 1000`). When reached the loop stops entirely until the server restarts.

**Data pipeline flow**:
1. `services/data_collection.py` — `TweetCollector` (Tweepy v2) fetches tweets → `raw_tweets` collection
2. `jobs/bertopic_pipeline.py` — loads corpus from `raw_tweets`, runs `BERTopicTrainer`, writes topics to `detected_trends`
3. `jobs/lda_pipeline.py` — LDA baseline (academic comparison only, not shown to users)
4. `jobs/model_comparison.py` — compares both models and writes to `pipeline_state` + `reports/comparison/`

**Key service files**:
- `services/bertopic_model.py` — `BERTopicTrainer`: SentenceTransformer (multilingual MiniLM-L12-v2) → UMAP → HDBSCAN → c-TF-IDF
- `services/lda_model.py` — `LDATrainer` with gensim; includes English + Somali stopwords used by both models
- `services/trend_scoring.py` — `compute_trend_score()`: 60% volume + 40% normalized engagement
- `services/auth.py` — JWT creation/verification via `python-jose`, bcrypt password hashing
- `services/notifications.py` — daily digest and spike alert emails
- `services/email.py` — SMTP sender + 2FA code generator

**Database** (`db/connection.py`): Motor async MongoDB client. Single-instance global. `reset_db_client()` exists for test isolation. `deduplicate_existing_trends()` runs on startup and after every BERTopic write.

**MongoDB collections**:
- `raw_tweets` — unique on `id` field; fields: `text`, `lang_api`, `created_at`, `collected_at`, `like_count`, `retweet_count`
- `detected_trends` — BERTopic output; key fields: `Name`, `Representation` (keyword list), `representative_docs`, `volume`, `trend_score`, `lang` (array), `calculated_at`, `model`
- `pipeline_state` — unique on `pipeline` (`"bertopic"`, `"lda"`, `"model_comparison"`); stores metrics and `last_trained_tweet_collected_at`
- `topic_evolution` — dynamic topic modeling time series
- `users` — auth fields including optional `two_factor_code`, `two_factor_expires`, `email_digests`, `spike_alerts`

**API routes** (`app/routes.py`): single `APIRouter` mounted at root. Auth routes under `/auth/`, data routes (`/trends`, `/history`, `/raw_tweets`, `/filter`), job triggers (`/jobs/train-*`, `/jobs/run-comparison`), visualization HTML serving (`/visualizations/{model}`).

The `adapt_trend_to_frontend()` helper translates the BERTopic MongoDB schema (`Name`, `Representation`, `trend_score`) into the frontend-expected shape (`topic_name`, `top_keywords`, `score`).

**Authentication**: JWT via `OAuth2PasswordBearer`. Login accepts email or username. Google OAuth auto-registers users. 2FA is TOTP-via-email (code stored in user doc with 10-min expiry).

---

### Frontend (`dashboard/`)

**Routing** (`src/App.jsx`): React Router v6. Public routes: `/login`, `/register`. All other routes are wrapped in `<Layout>` (requires auth).

**Pages**: Dashboard, Trending, Tweets, History, Comparison, Export, Setting, Profile.

**State management**: Four React contexts:
- `AuthContext` — JWT token + user info, stored in `localStorage`
- `ThemeContext` — light/dark mode
- `LanguageContext` — `"en"` / `"so"` toggle (passed as query param to API)
- `DateRangeContext` — global from/to date filter applied across pages

**API layer** (`src/services/api.js`): Axios instance with base URL `http://localhost:8000`. JWT injected automatically via request interceptor. Login sends `application/x-www-form-urlencoded` (FastAPI `OAuth2PasswordRequestForm` requirement).

**Charts**: Recharts. Word cloud on the Keywords page uses a custom implementation.

---

## Environment Variables

Create a `.env` file in `api/` (loaded by `python-dotenv`):

```env
TWITTER_BEARER_TOKEN=...           # Required for data ingestion
MONGODB_URL=mongodb://localhost:27017/
DATABASE_NAME=trending_topics_db

# Optional tuning
BERTOPIC_TRAIN_INTERVAL_MINUTES=30
BERTOPIC_MIN_CORPUS_SIZE=1000      # Pipeline won't train below this
BERTOPIC_CORPUS_LIMIT=2000
BERTOPIC_NEW_TWEETS_THRESHOLD=1000 # Min new tweets since last train
LDA_MIN_CORPUS_SIZE=1000
LDA_CORPUS_LIMIT=2000
LDA_GRID_SEARCH=true               # Runs hyperparameter grid search
COMPARISON_INTERVAL_HOURS=168
DIGEST_INTERVAL_HOURS=24

# Email (for 2FA and digests)
SMTP_HOST=...
SMTP_PORT=...
SMTP_USER=...
SMTP_PASSWORD=...
```

---

## Testing

Tests live in `api/tests/`. `conftest.py` sets `DATABASE_NAME=trending_topics_test` and provides the `test_db` async fixture that wipes all collections before and after each test.

Integration tests require a running MongoDB and are marked with the `mongo_integration` pytest mark (auto-skipped when MongoDB is unavailable). Run only unit tests by omitting `-m integration`.

---

## Generated Artifacts

BERTopic and LDA pipelines write files to:
- `api/artifacts/visualizations/` — interactive HTML charts (pyLDAvis, BERTopic intertopic distance)
- `api/reports/bertopic/` — evaluation text report, latest clean corpus CSV
- `api/reports/lda/` — evaluation JSON
- `api/reports/comparison/` — model comparison JSON (also cached in `pipeline_state` collection)

These are served via `/visualizations/{model}` and `/models/comparison` endpoints.
