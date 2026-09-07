# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Real-Time Trending Topic Detection System — a Final Year Project (FYP 2026) that collects
Twitter/X data and applies unsupervised topic modeling (BERTopic, LDA and NMF) to detect
trending topics in English and Somali. The three models are evaluated against each other and
the winner is deployed to serve users. It exposes a FastAPI backend and a React dashboard.

---

## Commands

### API (run from `api/`)

```bash
# Install dependencies — requirements.txt lives at the REPO ROOT, not in api/
pip install -r ../requirements.txt

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
npm run preview   # Preview production build
```

`npm run lint` is defined in `package.json` but **fails** — the project has no ESLint config
file. Use `npm run build` to catch breakage instead.

Restarting `uvicorn` is required after editing `api/.env`: `--reload` watches Python files,
not the env file.

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

**Entry point**: `app/main.py` — creates the FastAPI `app`, registers CORS middleware, mounts the router from `app/routes.py`, and launches background loops on startup.

**Background loops** — only these two are actually started in `lifespan()`:
| Loop | Interval | Env override |
|---|---|---|
| Data collection (Twitter → MongoDB) | 15 min | — |
| Email digest | 24 h, after a 5-min startup delay | `DIGEST_INTERVAL_HOURS` |

`periodic_model_comparison_loop()` is defined in `main.py` but **never started** — it is dead
code. Model evaluation runs only via `POST /jobs/run-evaluation`.

The data collection loop enforces a hard session quota (`app.state.max_quota_limit = 1000`).
When reached the loop stops entirely until the server restarts. After each collection cycle
it retrains the *deployed* model, but only once `BERTOPIC_NEW_TWEETS_THRESHOLD` new tweets
have arrived since the last training.

**Data pipeline flow** — three models compete, one is deployed:
1. `services/data_collection.py` — `TweetCollector` (Tweepy v2) fetches tweets → `raw_tweets`
2. `jobs/bertopic_pipeline.py`, `jobs/lda_pipeline.py`, `jobs/nmf_pipeline.py` — the three trainers
3. `jobs/evaluation_pipeline.py` — `run_full_evaluation()` scores all three and picks a winner
4. `jobs/deployment.py` — `persist_deployed_model()` writes the winner to
   `pipeline_state{pipeline: "deployed_model"}`; `run_deployed_pipeline()` then runs only that
   model, so `detected_trends` holds a single model's output
5. `jobs/model_comparison.py` — academic side-by-side report (`reports/comparison/`)

Once a winner is set it is never changed automatically. Re-evaluation is a deliberate
academic decision: `POST /jobs/run-evaluation?force=true`.

**Key service files**:
- `services/bertopic_model.py` — `BERTopicTrainer`: SentenceTransformer (multilingual MiniLM-L12-v2) → UMAP → HDBSCAN → c-TF-IDF
- `services/lda_model.py` — `LDATrainer` with gensim; includes English + Somali stopwords used by all models
- `services/nmf_model.py` — NMF baseline (scikit-learn TF-IDF + decomposition)
- `services/evaluation.py` — shared coherence/diversity metrics used to rank the three models
- `services/trend_scoring.py` — `compute_trend_score()`: 60% volume + 40% normalized engagement
- `services/auth.py` — JWT creation/verification via `python-jose`, bcrypt hashing for both passwords and 2FA codes
- `services/notifications.py` — daily digest and spike alert emails
- `services/email.py` — SMTP sender + `secrets`-based 2FA code generator
- `services/monitoring.py` — `collect_system_status()` backing `GET /health`

**Database** (`db/connection.py`): Motor async MongoDB client. Single-instance global. `reset_db_client()` exists for test isolation. `deduplicate_existing_trends()` runs on startup and after every BERTopic write.

**MongoDB collections**:
- `raw_tweets` — unique on `id` field; fields: `text`, `lang_api`, `created_at`, `collected_at`, `like_count`, `retweet_count`
- `detected_trends` — BERTopic output; key fields: `Name`, `Representation` (keyword list), `representative_docs`, `volume`, `trend_score`, `lang` (array), `calculated_at`, `model`
- `pipeline_state` — unique on `pipeline`. Keys in use: `"deployed_model"` (the winner),
  `"bertopic"` / `"lda"` / `"nmf"` (per-model metrics + `last_trained_tweet_collected_at`),
  `"model_comparison"`, `"notifications"` (`last_digest_at`, `digests_sent`, `last_spike_check`)
- `pipeline_history` — append-only record of past training/evaluation runs
- `topic_evolution` — dynamic topic modeling time series
- `users` — auth fields plus optional `two_factor_enabled`, `two_factor_code_hash`,
  `two_factor_expires`, `two_factor_code_sent_at`, `two_factor_attempts`,
  `email_digests`, `spike_alerts`

**API routes** (`app/routes.py`): single `APIRouter` mounted at root. Auth under `/auth/`,
data routes (`/trends`, `/trends/keywords`, `/trends/topics_over_time`, `/history`,
`/raw_tweets`, `/tweets/stats`, `/filter`), model routes (`/models/winner`, `/models/status`,
`/models/comparison`, `/models/history`), job triggers (`/jobs/train-{bertopic,lda,nmf}`,
`/jobs/run-evaluation`, `/jobs/run-deployment`, `/jobs/run-comparison`, `/jobs/send-digests`),
and `/health`.

The `adapt_trend_to_frontend()` helper translates the MongoDB schema (`Name`,
`Representation`, `trend_score`) into the frontend-expected shape (`topic_name`,
`top_keywords`, `score`).

**Authentication**: JWT via `OAuth2PasswordBearer`. Login accepts email or username.

Login is a **two-step flow when 2FA is enabled**. `POST /auth/login` returns
`{requires_2fa: true, challenge_token}` and *no* access token; the caller then exchanges the
challenge token plus the emailed code at `POST /auth/login/2fa`. `get_current_user()` rejects
any token carrying `purpose: "2fa_challenge"`, so a challenge cannot be used as a session.
Google sign-in routes through the same `_begin_login()` gate and is therefore not a bypass.

2FA specifics: codes come from `secrets`, are stored bcrypt-hashed in `two_factor_code_hash`,
expire after 10 minutes, are single-use, are capped at 5 wrong attempts, and resends are
throttled to 60 s. Disabling 2FA requires re-authentication — the account password, or a
fresh emailed code for Google-provisioned accounts (which have no password the owner knows).

`POST /auth/google` verifies the ID token's signature, issuer, audience and expiry with
`google-auth` against `GOOGLE_CLIENT_ID`. Without that variable the endpoint refuses to sign
anyone in rather than falling back to unverified claims.

Password policy lives in `models/schemas.py` (`validate_password_strength`): minimum 8
characters with at least one letter and one digit, enforced on signup and password change.
It is not applied at login, so pre-existing weaker passwords still work.

**Notifications** (`services/notifications.py`): email digests default to **on** and spike
alerts default to **off**, matching what `GET /auth/preferences` reports. Because a user who
never opened Settings has no preference field at all, the digest recipient query is
`{"email_digests": {"$ne": False}}` rather than an exact `True` match — an exact match would
silently exclude everyone who never touched a toggle. Signup now writes both fields
explicitly, so new accounts are unambiguous.

`send_daily_digests()` checks `pipeline_state{pipeline: "notifications"}.last_digest_at` and
skips when less than `DIGEST_INTERVAL_HOURS` has passed. The background loop fires once soon
after every startup, so without that check each `--reload` restart would resend the digest.
`POST /jobs/send-digests` passes `force=True` to bypass it.

Both senders count only deliveries the SMTP layer confirmed: `digests_sent` / `alerts_sent`
exclude failures, which are reported separately as `digests_failed` / `alerts_failed`.

Known weakness, not yet fixed: `_detect_spikes()` matches topics across batches by `Name`,
but BERTopic names embed the topic index (`0_ai_tech_...`). When a topic's index shifts
between runs it reads as brand new, producing false spikes at `pct_change: 100`.

---

### Frontend (`dashboard/`)

**Routing** (`src/App.jsx`): React Router v6. Public routes: `/login`, `/register`. All other routes are wrapped in `<Layout>` (requires auth).

**Pages**: Dashboard, Trending, Tweets, History, Comparison, Export, Setting, Profile.

**State management**: Four React contexts:
- `AuthContext` — JWT token + user info, stored in `localStorage`
- `ThemeContext` — light/dark mode
- `LanguageContext` — `"en"` / `"so"` toggle (passed as query param to API)
- `DateRangeContext` — global from/to date filter applied across pages

**API layer** (`src/services/api.js`): Axios instance with base URL `http://localhost:8000`.
JWT injected automatically via a request interceptor. Login sends
`application/x-www-form-urlencoded` (FastAPI `OAuth2PasswordRequestForm` requirement).

A response interceptor handles two cross-cutting concerns, so pages do not repeat them:
- FastAPI's 422 `detail` array is flattened to a string (pages render `detail` directly, and
  an array would crash React)
- a 401 on any non-login endpoint clears the stored token and redirects to
  `/login?expired=1`, which `Login.jsx` renders as "Your session expired"

`Login.jsx` is two-phase: when `login()` resolves with `requires2FA`, it swaps the form for a
6-digit code screen and calls `completeLogin2FA()`. No token is stored until that succeeds.

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
DIGEST_INTERVAL_HOURS=24
SPIKE_THRESHOLD_PCT=25             # trend_score rise that counts as a spike

# Auth
SECRET_KEY=...                     # JWT signing key; falls back to a public default if unset
ACCESS_TOKEN_EXPIRE_MINUTES=120    # Default is 30, which expires mid-demo
GOOGLE_CLIENT_ID=...               # Required, or /auth/google refuses all sign-ins

# Email (for 2FA and digests)
SMTP_ENABLED=false                 # false = codes print to the server console
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...                  # Gmail needs a 16-char App Password, not the account password
TWO_FA_DEV_ECHO=false              # true returns the 2FA code in the API response (offline demos only)
```

`SMTP_ENABLED=false` is not a failure mode: `services/email.py` falls back to printing the
message to stdout, so 2FA works offline. `dashboard/.env` holds `VITE_GOOGLE_CLIENT_ID`
separately for the browser-side Google button.

---

## Testing

Tests live in `api/tests/`. `conftest.py` sets `DATABASE_NAME=trending_topics_test` and provides the `test_db` async fixture that wipes all collections before and after each test.

Integration tests require a running MongoDB and are marked with the `integration` pytest mark
(registered in `pytest.ini`). Run only unit tests by omitting `-m integration`.

`tests/test_2fa_login.py` covers the security surface end-to-end through the real ASGI app:
2FA-gated login, challenge-token rejection, single-use codes, the brute-force cap, expiry,
disable re-authentication, password policy, and forged Google credentials.

**Known-failing tests, unrelated to auth** (they fail on a clean checkout too):
`test_evaluation.py::test_evaluate_model_produces_one_row_per_language`,
`test_evaluation.py::test_save_topic_words_writes_per_language_csv`,
`test_nmf_model.py::test_run_nmf_sync_end_to_end_on_dummy_data`,
`test_integration_db.py::test_model_comparison_with_pipeline_states`.
They assert on topic-modeling output shapes that the current pipeline no longer produces.

---

## Generated Artifacts

The pipelines write files to:
- `api/reports/bertopic/` — evaluation text report, latest clean corpus CSV
- `api/reports/comparison/` — model comparison JSON (also cached in `pipeline_state`)

`reports/lda/` and `reports/nmf/` are created on demand by their pipelines and are absent
until those models run.

Reports reach the frontend through `GET /models/comparison`. There is **no**
`/visualizations/{model}` endpoint and no `api/artifacts/` directory — earlier versions of
this file described both.
