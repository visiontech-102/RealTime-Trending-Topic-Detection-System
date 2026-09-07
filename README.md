# Real-Time Trending Topic Detection System for English and Somali Tweets

Final Year Project (FYP 2026). A full-stack bilingual topic modeling system that ingests Twitter/X data, trains three competing unsupervised models (LDA, NMF, BERTopic) on the same corpus, evaluates them on identical intrinsic metrics, selects a winner by measured performance, tunes it via hyperparameter search, and deploys it for real-time trending topic output.

---

## System Architecture

The full pipeline runs end-to-end in this order (verified against the current code, not just the design intent):

```
Twitter API v2  (currently: 4 active query groups, ALL lang:en — the Somali
                 query set exists in run_data_collection.py but is commented out)
    → raw_tweets (MongoDB)
    → corpus_loader  (shared — loads the same corpus slice for all three models)
    → corpus split by lang_api: df_en / df_so
    ┌──────────────────────────────────────────────────────────────────┐
    │  LDA-EN + LDA-SO      NMF-EN + NMF-SO      BERTopic-EN + BERTopic-SO│
    │  (gensim BoW,         (sklearn TF-IDF,      (SentenceTransformer→UMAP→
    │   trained separately   trained separately    HDBSCAN→c-TF-IDF, trained
    │   per language,        per language,          separately per language,
    │   topics concatenated) topics concatenated)   topics concatenated)
    └──────────────────────────────────────────────────────────────────┘
    → Intrinsic evaluation per model (same reference corpus, same TOP_N_WORDS):
        C_v coherence  /  U_Mass coherence  /  Topic Diversity
        scored two ways: English  /  Somali   ["combined" corpus is built too,
        but only to construct the shared reference Dictionary and to save
        per-model topic-word CSVs — it is NOT a scored, independent slice]
    → coherence_diversity.json  (single source of truth for all downstream steps)
    → Winner selection (Option B): primary = highest English C_v;
        tiebreak = highest Somali C_v; secondary tiebreak = English diversity
    → Enhancement: hyperparameter sweep on winner only  → before_after.json
    → Model comparison report  (all three models, all metrics)  → latest_comparison.json
    → Winner retraining is NOT a separate timed loop — it is triggered inline,
        inside the data-collection loop, immediately after an ingestion cycle
        that brings in enough new tweets (BERTOPIC_NEW_TWEETS_THRESHOLD)
    → detected_trends (MongoDB)  — topics with trend_score = 0.6×volume + 0.4×engagement
    → FastAPI REST endpoints
    → React / Vite dashboard
```

**Known gap between design and running code:**
- `periodic_data_collection_loop()` in `api/app/main.py` builds its query list from a block that is fully commented out, so the `queries` variable it references is undefined. Each 15-minute tick raises a `NameError`, which the loop's own `try/except` swallows and logs as `"Error in background data collection loop"`. **The live server currently does not auto-collect tweets.** Running `python run_data_collection.py` manually still works (it defines its own `queries` list), but only the English query groups in that file are active — the Somali group is present but commented out.
- `periodic_model_comparison_loop()` (the one-time loop meant to auto-run the first evaluation and pick a winner) is defined in `main.py` but is **never started** in `lifespan()`. Only `periodic_data_collection_loop` and `periodic_email_digest_loop` actually run. The first evaluation must currently be triggered manually: `POST /jobs/run-evaluation`.

---

## Architecture Layers

The system is organized into five logical layers, each responsible for a distinct stage of the pipeline. The table below maps every file in the repository to the layer it belongs to.

### 1. Data Collection Layer
Retrieves public tweets from the Twitter (X) API and ingests them into the system for further processing.

| File | Responsibility |
|---|---|
| `api/services/data_collection.py` | `TweetCollector` (Tweepy v2) — queries Twitter API v2, deduplicates, writes to `raw_tweets` |
| `api/run_data_collection.py` | CLI entry point for one-shot tweet ingestion. Currently ships 4 active `lang:en` query groups (politics/diplomacy, war/military, economy/sports, hashtags); a Somali query group exists in the file but is commented out |
| `api/app/main.py` (`periodic_data_collection_loop`) | Schedules the recurring 15-minute collection loop and enforces the 1000-tweet session quota. **Currently broken**: its query list block is commented out, so the loop references an undefined `queries` name and fails silently (caught by its own `try/except`) every tick — no tweets are collected automatically by the running server until this is fixed |

### 2. Storage Layer
Persists both raw tweets and the topics produced by modeling, using a document-oriented database (MongoDB) suited to the semi-structured nature of social-media records.

| File | Responsibility |
|---|---|
| `api/db/connection.py` | Motor async MongoDB client, collection index initialization, `deduplicate_existing_trends()` |
| `api/check_db.py` | Standalone script to inspect database state |
| `api/pipelines/corpus_loader.py` | Reads and filters the `raw_tweets` corpus for the modeling layer |
| MongoDB collections | `raw_tweets`, `detected_trends`, `pipeline_state`, `topic_evolution`, `users` |

### 3. Processing and Modeling Layer
Loads the stored corpus, applies preprocessing, and trains the topic-modeling algorithms to extract and score topics.

| File | Responsibility |
|---|---|
| `api/services/lda_model.py` | `LDATrainer` — gensim BoW, English + Somali stopword preprocessing |
| `api/services/nmf_model.py` | `NMFTrainer` — scikit-learn TF-IDF matrix + NMF factorization |
| `api/services/bertopic_model.py` | `BERTopicTrainer` — SentenceTransformer → UMAP → HDBSCAN → c-TF-IDF |
| `api/services/evaluation.py` | Shared evaluation engine (C_v, U_Mass, Topic Diversity) used by all three models |
| `api/services/trend_scoring.py` | `compute_trend_score()`, `generate_topic_label()` |
| `api/jobs/evaluation_pipeline.py` | Orchestrates training of all 3 models, evaluation, winner selection, chains enhancement + comparison |
| `api/jobs/lda_pipeline.py` | Standalone LDA baseline training pipeline |
| `api/jobs/nmf_pipeline.py` | Standalone NMF baseline training pipeline |
| `api/jobs/bertopic_pipeline.py` | Standalone BERTopic periodic retraining pipeline |
| `api/jobs/model_comparison.py` | Metrics-driven three-way comparison; writes comparison report |
| `api/jobs/enhancement.py` | Hyperparameter sweep for the winning model only |
| `api/jobs/deployment.py` | Deployed-model registry; winner-only training dispatcher |
| `api/run_evaluation.py` | CLI entry point: full three-model evaluation pipeline |
| `api/run_bertopic.py` | CLI entry point: standalone BERTopic run |
| `api/run_deployment.py` | CLI entry point: runs the winner-only deployment retrain |
| `api/resources/stopwords.txt` | Somali stopwords — single source of truth for LDA, NMF, BERTopic preprocessing |
| `api/results/`, `api/reports/` | Runtime output: metrics CSV/JSON, topic CSVs, evaluation reports, comparison JSON |

### 4. Application (Service) Layer
Exposes the system's functionality through HTTP endpoints and coordinates the background tasks that drive real-time behavior; built around FastAPI with asynchronous database access via Motor.

| File | Responsibility |
|---|---|
| `api/app/main.py` | FastAPI app creation, CORS middleware, lifespan startup. Two background loops actually run (data ingestion, email digest); a third (one-time evaluation) is defined but not started — see How to Run |
| `api/app/routes.py` | REST endpoints: auth, trends, history, raw tweets, filters, job triggers, visualizations |
| `api/models/schemas.py` | Pydantic request/response schemas (auth, 2FA, user preferences) |
| `api/services/auth.py` | JWT creation/verification (`python-jose`), bcrypt password hashing |
| `api/services/email.py` | SMTP sender: 2FA codes, spike alerts, digest emails |
| `api/services/notifications.py` | Background notification dispatcher (digests, spike alerts) |
| `api/services/monitoring.py` | Health status and pipeline state checks |
| `api/.env` | Environment configuration (Mongo URI, secrets, tuning parameters) |
| `api/pytest.ini` | Pytest configuration and markers |
| `api/tests/` | Test suite covering routes, auth, evaluation, notifications, trend scoring |
| `requirements.txt` | Python dependency manifest |

### 5. Presentation Layer
Renders trends, historical results, and model comparisons for the end user through a React single-page web application (Vite, Tailwind CSS, Recharts).

| File | Responsibility |
|---|---|
| `dashboard/src/App.jsx` | React Router v6 route table (public vs. authenticated routes) |
| `dashboard/src/main.jsx` | React app bootstrap/mount point |
| `dashboard/src/services/api.js` | Axios instance, base URL, JWT request interceptor |
| `dashboard/src/contexts/AuthContext.jsx` | JWT token + user session state |
| `dashboard/src/contexts/ThemeContext.jsx` | Light/dark mode state |
| `dashboard/src/contexts/LanguageContext.jsx` | English/Somali toggle |
| `dashboard/src/contexts/DateRangeContext.jsx` | Global date-range filter state |
| `dashboard/src/components/Layout.jsx` | Authenticated page shell/wrapper |
| `dashboard/src/components/Navigation.jsx` | Sidebar/nav bar |
| `dashboard/src/components/DateFilter.jsx` | Shared date-range picker control |
| `dashboard/src/pages/Dashboard.jsx` | Overview page: summary stats, top trends |
| `dashboard/src/pages/Trending.jsx` | Live trending topics view |
| `dashboard/src/pages/Tweets.jsx` | Raw tweet browsing/search |
| `dashboard/src/pages/History.jsx` | Historical trend view over time |
| `dashboard/src/pages/Comparison.jsx` | LDA vs. NMF vs. BERTopic comparison view |
| `dashboard/src/pages/Export.jsx` | Data export page |
| `dashboard/src/pages/Setting.jsx` | User settings / notification preferences |
| `dashboard/src/pages/Profile.jsx` | User profile management |
| `dashboard/src/pages/Login.jsx` / `Register.jsx` | Public authentication pages |
| `dashboard/src/utils/dateRange.js` | Date-range helper utilities |
| `dashboard/src/index.css` | Tailwind base styles |
| `dashboard/index.html`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js` | Build/tooling configuration |
| `dashboard/package.json` | Node dependency manifest |

### Project-Level / Cross-Cutting Files
Not part of a single layer — support development, deployment, and documentation across the whole system.

| File | Responsibility |
|---|---|
| `README.md` | Project documentation (this file) |
| `CLAUDE.md` | Guidance for AI-assisted development on this repo |
| `Dockerfile`, `docker-compose.yml` | Containerized deployment of the API (and dependent services) |
| `.gitignore` | Version-control exclusions |

---

## Project Structure

```
api/                                  # Python FastAPI backend
├── app/
│   ├── main.py                       # FastAPI lifespan; 2 loops actually run (ingestion*, digest), 1 defined but unstarted (*ingestion loop currently no-ops — see How to Run)
│   └── routes.py                     # REST endpoints: auth, trends, jobs, visualizations
├── db/
│   └── connection.py                 # Motor async MongoDB client, index init, dedup
├── models/
│   └── schemas.py                    # Pydantic schemas for auth, 2FA, user preferences
├── pipelines/
│   └── corpus_loader.py              # Loads and filters raw_tweets from MongoDB
├── jobs/
│   ├── evaluation_pipeline.py        # Trains all 3 models, evaluates, selects winner,
│   │                                 #   chains enhancement and comparison
│   ├── bertopic_pipeline.py          # Standalone BERTopic periodic retrain pipeline
│   ├── lda_pipeline.py               # Standalone LDA baseline pipeline
│   ├── nmf_pipeline.py               # Standalone NMF baseline pipeline
│   ├── model_comparison.py           # Metrics-driven 3-way comparison; writes report
│   ├── enhancement.py                # Hyperparameter sweep for winning model only
│   └── deployment.py                 # Deployed-model registry; winner-only dispatcher
├── services/
│   ├── bertopic_model.py             # BERTopicTrainer: SentenceTransformer→UMAP→HDBSCAN→c-TF-IDF
│   ├── lda_model.py                  # LDATrainer: tokenization, stopwords, gensim, pyLDAvis
│   ├── nmf_model.py                  # NMFTrainer: TF-IDF matrix, scikit-learn NMF, coherence
│   ├── evaluation.py                 # Shared evaluation engine for all three models
│   ├── trend_scoring.py              # compute_trend_score(), generate_topic_label()
│   ├── auth.py                       # JWT creation/verification, bcrypt password hashing
│   ├── data_collection.py            # TweetCollector (Tweepy v2), dedup logic
│   ├── email.py                      # SMTP: 2FA codes, spike alerts, digest emails
│   ├── notifications.py              # Background notification dispatcher
│   └── monitoring.py                 # Health status and pipeline state checks
├── resources/
│   └── stopwords.txt                 # Somali stopwords — single source of truth (one word per line)
├── results/                          # Written by pipelines at runtime; not committed
│   ├── metrics/
│   │   ├── coherence_diversity.csv   # Per-model per-language scores from run_full_evaluation()
│   │   └── coherence_diversity.json
│   ├── topics/                       # Top-word CSVs: <model>_<lang>_topics.csv
│   └── enhancement/
│       └── before_after.json         # Hyperparameter sweep result for the winning model
├── reports/
│   └── comparison/
│       └── latest_comparison.json    # Three-way comparison report with winner rationale
├── tests/                            # pytest test suite
├── run_evaluation.py                 # CLI entry point: trains all 3 models, full evaluation
├── run_data_collection.py            # CLI entry point: one-shot tweet ingestion
└── requirements.txt                  # Python dependencies

dashboard/                            # React + Vite frontend
├── src/
│   ├── App.jsx                       # React Router v6 (public: /login, /register; protected: rest)
│   ├── services/api.js               # Axios (base: http://localhost:8000; JWT interceptor)
│   ├── context/                      # AuthContext, ThemeContext, LanguageContext, DateRangeContext
│   ├── pages/                        # Dashboard, Trending, Tweets, History, Comparison, Export,
│   │                                 #   Settings, Profile
│   └── components/                   # Shared UI: Layout, nav, sidebar
└── package.json
```

---

## Setup & Installation

**Prerequisites**

- Python 3.9+ [check version — confirmed 3.9+ badge in prior README; minimum may be higher due to bertopic/sentence-transformers]
- Node.js 18+
- MongoDB (local `localhost:27017` or Atlas URI)

**Backend**

```bash
# From repo root
pip install -r requirements.txt
```

Create `api/.env` (see Environment Variables for the full list):

```env
MONGODB_URL=mongodb://localhost:27017/
DATABASE_NAME=trending_topics_db
TWITTER_BEARER_TOKEN=your_twitter_v2_bearer_token
SECRET_KEY=your_jwt_signing_key_change_in_production
```

**Somali stopwords file**

The system reads Somali stopwords from:

```
api/resources/stopwords.txt   (one word per line, UTF-8)
```

This is the single source of truth used by LDA, NMF, and BERTopic preprocessing. If the file is missing, a `logger.error` fires at startup and all Somali preprocessing runs with no stopword filtering. Check the server log immediately on first startup.

**Frontend**

```bash
cd dashboard
npm install
npm run dev   # development server at http://localhost:5173
```

---

## Environment Variables

All read via `python-dotenv` from `api/.env`. Defaults are the values used when the variable is absent.

| Variable | Default | Controls |
|---|---|---|
| `MONGODB_URL` | `mongodb://localhost:27017/` | MongoDB connection URI |
| `DATABASE_NAME` | `trending_topics_db` | Database name (test suite overrides to `trending_topics_test`) |
| `TWITTER_BEARER_TOKEN` | *(none)* | Twitter API v2 auth; ingestion loop disabled if absent |
| `SECRET_KEY` | `your_super_secret_key_here` | JWT signing key — must be changed in production |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access token lifetime (minutes) |
| `LDA_MIN_CORPUS_SIZE` | `1000` | Minimum total tweets before LDA or NMF trains |
| `LDA_CORPUS_LIMIT` | `2000` | Maximum tweets loaded per LDA / NMF training run |
| `LDA_GRID_SEARCH` | `true` | Enable K-grid search for LDA and NMF (dense grid K ∈ {4..12}, highest C_v wins, tiebreak K ascending) |
| `LDA_NEW_TWEETS_THRESHOLD` | `1000` | Read by `nmf_pipeline.py` but not currently consulted by the winner-deployment path (see `DEPLOYED_MODEL_RETRAIN_THRESHOLD`) |
| `BERTOPIC_MIN_CORPUS_SIZE` | `1000` | Minimum total tweets before BERTopic trains |
| `BERTOPIC_CORPUS_LIMIT` | `2000` | Maximum tweets loaded per BERTopic training run |
| `BERTOPIC_NEW_TWEETS_THRESHOLD` | `500` | Minimum new tweets required before the deployed model retrains — read in two places: the inline post-ingestion check in `main.py`, and inside `bertopic_pipeline.py` itself |
| `WINNER_TRAIN_INTERVAL_MINUTES` | `30` | **Not read anywhere in the code.** No standalone winner-retrain loop exists — retraining is triggered inline after ingestion (see How to Run) |
| `DEPLOYED_MODEL_RETRAIN_THRESHOLD` | `500` | Minimum new tweets required before `_run_lda_deployment` / `_run_nmf_deployment` actually retrain (checked inside `deployment.py`, in addition to the `BERTOPIC_NEW_TWEETS_THRESHOLD` pre-check in `main.py`) |
| `COMPARISON_INTERVAL_HOURS` | `168` | **Not read anywhere in the code.** No recurring comparison-refresh loop exists; the comparison report only regenerates when `run_full_evaluation()` runs or via `POST /jobs/run-comparison` |
| `DIGEST_INTERVAL_HOURS` | `24` | Background loop interval for email digests — this one is actually wired up and running |
| `SMTP_ENABLED` | `false` | Enable SMTP features (2FA codes, digests, spike alerts) |
| `SMTP_HOST` | *(empty)* | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP server port |
| `SMTP_USER` | *(empty)* | SMTP authentication username |
| `SMTP_PASSWORD` | *(empty)* | SMTP authentication password |
| `SMTP_FROM` | *(SMTP_USER)* | Sender address for outgoing emails |
| `SMTP_USE_TLS` | `true` | Use TLS for SMTP connection |
| `SPIKE_THRESHOLD_PCT` | `25` | Topic volume change (%) that triggers a spike alert email |
| `BERTOPIC_OUTLIER_WARN_RATIO` | `0.35` | HDBSCAN outlier ratio that triggers a monitoring warning |

---

## How to Run

All commands run from `api/` unless noted.

### 1. Start the API server

```bash
uvicorn app.main:app --reload
```

Server at `http://localhost:8000`. Swagger docs at `http://localhost:8000/docs`.

**Only two background loops are actually started** in `lifespan()` (requires MongoDB; ingestion additionally requires `TWITTER_BEARER_TOKEN`):

| Loop | Interval | Env override | Status |
|---|---|---|---|
| Data ingestion (Twitter → `raw_tweets`) | 15 min | — | Started, but currently no-ops every tick — see known gap above (`queries` undefined) |
| Email digest | 24 h | `DIGEST_INTERVAL_HOURS` | Running as documented |

Two loops that exist in the code are **not** wired up and do not run:

| Loop (defined but not started) | Would-be interval | Notes |
|---|---|---|
| `periodic_model_comparison_loop` (one-time initial evaluation) | retries every `BERTOPIC_TRAIN_INTERVAL_MINUTES` (30 min default) until it succeeds, then exits forever | Never called from `lifespan()`. Trigger the first evaluation manually: `POST /jobs/run-evaluation` |
| A recurring "winner retrain" / "model comparison refresh" timer | — | Does not exist as a standalone loop. Winner retraining is triggered **inline** at the end of `periodic_data_collection_loop`, only right after an ingestion cycle that brought in ≥ `BERTOPIC_NEW_TWEETS_THRESHOLD` new tweets since the winner's last training |

`WINNER_TRAIN_INTERVAL_MINUTES` and `COMPARISON_INTERVAL_HOURS` (see Environment Variables) are **not read anywhere in the codebase** — setting them currently has no effect.

The ingestion loop (once its `queries` bug is fixed) enforces a hard session quota of 1000 tweets and stops entirely when reached (restarts on server restart).

### 2. Collect tweets (one-shot)

```bash
python run_data_collection.py
```

Fetches up to 50 tweets per query. Currently 4 **English-only** (`lang:en`) query groups are active (politics/diplomacy, war/military, economy/sports, hashtags); a Somali query group is present in the file but commented out. Writes to `raw_tweets`. Requires `TWITTER_BEARER_TOKEN`.

### 3. Run the full evaluation

```bash
python run_evaluation.py
```

This is the main academic pipeline. Runs in this order:

1. Loads shared corpus (up to `LDA_CORPUS_LIMIT` tweets), then splits it into `df_en` / `df_so` by `lang_api`
2. Trains LDA, NMF, and BERTopic **independently per language** (LDA-EN + LDA-SO, NMF-EN + NMF-SO, BERTopic-EN + BERTopic-SO) on the same loaded corpus, then concatenates each model's per-language topics
3. Scores each model: C_v coherence, U_Mass coherence, Topic Diversity — **English and Somali only** (Option B). A "combined" tokenized corpus is also built, but only to construct the shared reference `Dictionary` and to save combined topic-word CSVs — it is not an independently scored slice
4. Writes `results/metrics/coherence_diversity.csv` and `coherence_diversity.json` (rows for `en` and `so` only)
5. Saves per-model per-language top-word CSVs under `results/topics/` (en / so / combined — combined here is CSV output only, not a metric)
6. Selects winner: primary = highest English C_v, tiebreak = highest Somali C_v, secondary tiebreak = highest English Topic Diversity; persists to `pipeline_state`
7. Runs enhancement: hyperparameter sweep on winning model only; writes `results/enhancement/before_after.json`
8. Runs model comparison: writes `reports/comparison/latest_comparison.json` and updates `pipeline_state`

Requires at least `LDA_MIN_CORPUS_SIZE` tweets in MongoDB.

### 4. View evaluation results

| File | Contents |
|---|---|
| `results/metrics/coherence_diversity.csv` | Per-model per-language C_v, U_Mass, diversity, K |
| `results/metrics/coherence_diversity.json` | Same data as JSON |
| `results/topics/<model>_<lang>_topics.csv` | Top-word lists per model per language |
| `results/enhancement/before_after.json` | Baseline vs. best-candidate comparison for winning model |
| `reports/comparison/latest_comparison.json` | Three-way comparison with winner selection rationale |

---

## Evaluation Methodology

Intrinsic metrics only — this task has no ground-truth topic labels, so accuracy, precision, recall, and F1 are not applicable.

| Metric | Role | Details |
|---|---|---|
| C_v coherence | Primary | Word co-occurrence probability in a sliding window; higher is better |
| U_Mass coherence | Supporting | Document co-occurrence frequency; negative; less negative is better |
| Topic Diversity | Tiebreak | Proportion of unique words across all topics' top-N words; 1.0 = no reuse |

Each metric is computed **twice** per model against the **same reference corpus and the same tokenization** (`preprocess_lda`): once for English-only documents and once for Somali-only documents (Option B). A combined bilingual corpus is also tokenized internally, but solely to build the shared reference `Dictionary` that both language slices score against, and to save a `combined` topic-word CSV for inspection — it is never scored as its own row, by design: merging both languages would double-count signal already captured separately and would inflate the bag-of-words models (LDA/NMF) via cross-lingual TF-IDF terms.

**Winner selection rule:** primary = highest English C_v (English is the dominant language in the corpus); tiebreak = highest Somali C_v; secondary tiebreak = highest English Topic Diversity. This is implemented in `jobs/model_comparison.py::_select_winner_from_metrics()`, not as a mean across language slices.

**Enhancement:** after winner selection, a hyperparameter grid is swept for the winning model only (LDA: 8 candidates; NMF: 4 candidates; BERTopic: up to 3 min-cluster-size values). The enhanced configuration is adopted only when the best candidate's mean C_v **strictly exceeds** the baseline; otherwise the original is kept.

---

## Key Design Decisions

**Same loaded corpus, trained per-language, same seed.** All three models load the identical corpus slice (`load_tweet_corpus()`, same `CORPUS_LIMIT`), then each one trains **two separate models** — one on the English slice, one on the Somali slice — with random seed 42 enforced in LDA, NMF, and BERTopic. The two per-language topic sets are concatenated before evaluation. This keeps topics monolingual and keeps C_v scoring matched to a same-language reference corpus.

**BERTopic uses lighter preprocessing.** LDA and NMF require tokenized bag-of-words input; BERTopic uses `preprocess_bertopic()` which preserves word order for transformer embeddings. Coherence scoring uses the same reference corpus and same tokenization for all three models, so this asymmetry in training preprocessing does not affect the evaluation yardstick.

**Perplexity excluded from the comparison.** NMF is non-probabilistic; including perplexity would make a three-model comparison impossible. Only C_v coherence, U_Mass coherence, and Topic Diversity are used.

**Somali stopwords from a single file.** `api/resources/stopwords.txt` is loaded at import time by `lda_model.py` and shared with `bertopic_model.py`. Updating stopwords requires editing this file only — no code changes.

**"Combined" is not a scored language slice (Option B).** Only English and Somali rows are written to `coherence_diversity.json` and used for winner selection. A combined bilingual corpus is still built, but purely to (a) construct the shared reference `Dictionary` both language slices score against, and (b) save a `combined` topic-word CSV — never as an independently measured C_v/diversity row.

**Winner-only deployment, triggered inline (not a timed loop).** After a winner is selected, only that model's production pipeline retrains — the two losing models stay frozen with their last artifacts. In the running server this retrain is fired from inside `periodic_data_collection_loop`, right after an ingestion cycle that brought in enough new tweets — there is no separate scheduled "winner retrain" timer, and `WINNER_TRAIN_INTERVAL_MINUTES` is not read anywhere.

**LDA and NMF use identical corpus thresholds.** `nmf_pipeline.py` intentionally reads `LDA_MIN_CORPUS_SIZE`, `LDA_CORPUS_LIMIT`, and `LDA_GRID_SEARCH` — the same env vars as LDA — so the two baselines cannot diverge in configuration.

**Initial winner selection currently requires a manual trigger.** `periodic_model_comparison_loop()` (meant to auto-run the first evaluation) is defined in `main.py` but is not started in `lifespan()`. Until that's wired up, run the first evaluation yourself: `POST /jobs/run-evaluation` (or `python run_evaluation.py`).

---

## Testing

```bash
# From api/
pytest tests/ -v

# Integration tests only (require live MongoDB)
pytest tests/ -m mongo_integration -v
```

`conftest.py` sets `DATABASE_NAME=trending_topics_test` and wipes all collections before and after each test. Integration tests are auto-skipped when MongoDB is unavailable. No real data or production database is touched.

---

## License

MIT License. Developed by Vision Tech, FYP 2026.
