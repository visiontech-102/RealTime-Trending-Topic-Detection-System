# Real-Time Trending Topic Detection System for English and Somali Tweets

Final Year Project (FYP 2026). A full-stack bilingual topic modeling system that ingests Twitter/X data, trains three competing unsupervised models (LDA, NMF, BERTopic) on the same corpus, evaluates them on identical intrinsic metrics, selects a winner by measured performance, tunes it via hyperparameter search, and deploys it for real-time trending topic output.

---

## System Architecture

The full pipeline runs end-to-end in this order:

```
Twitter API v2
    → raw_tweets (MongoDB)
    → corpus_loader  (shared — all three models use the same loaded slice)
    ┌──────────────────────────────────────────────────────────┐
    │  LDA training        NMF training        BERTopic training│
    │  (gensim BoW)        (sklearn TF-IDF)    (SentenceTransformer→UMAP→HDBSCAN→c-TF-IDF)
    └──────────────────────────────────────────────────────────┘
    → Intrinsic evaluation per model (same reference corpus, same TOP_N_WORDS):
        C_v coherence  /  U_Mass coherence  /  Topic Diversity
        split three ways: English  /  Somali  /  Combined
    → coherence_diversity.json  (single source of truth for all downstream steps)
    → Metrics-driven winner selection  (highest mean C_v; diversity tiebreak)
    → Enhancement: hyperparameter sweep on winner only  → before_after.json
    → Model comparison report  (all three models, all metrics)  → latest_comparison.json
    → periodic_winner_training_loop: retrains winner on new tweets every N minutes
    → detected_trends (MongoDB)  — topics with trend_score = 0.6×volume + 0.4×engagement
    → FastAPI REST endpoints
    → React / Vite dashboard
```

---

## Project Structure

```
api/                                  # Python FastAPI backend
├── app/
│   ├── main.py                       # FastAPI lifespan; four background loops
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
| `LDA_GRID_SEARCH` | `true` | Enable K-grid search for LDA and NMF (K ∈ {5, 8, 10, 12}) |
| `LDA_NEW_TWEETS_THRESHOLD` | `1000` | Minimum new tweets required before LDA / NMF retrains |
| `BERTOPIC_MIN_CORPUS_SIZE` | `1000` | Minimum total tweets before BERTopic trains |
| `BERTOPIC_CORPUS_LIMIT` | `2000` | Maximum tweets loaded per BERTopic training run |
| `BERTOPIC_NEW_TWEETS_THRESHOLD` | `1000` | Minimum new tweets required before BERTopic retrains |
| `WINNER_TRAIN_INTERVAL_MINUTES` | `30` | Background loop interval for retraining the deployed model |
| `DEPLOYED_MODEL_RETRAIN_THRESHOLD` | `500` | Minimum new tweets required before the deployed model retrains |
| `COMPARISON_INTERVAL_HOURS` | `168` | Background loop interval for refreshing the comparison report (7 days) |
| `DIGEST_INTERVAL_HOURS` | `24` | Background loop interval for email digests |
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

Four background loops start automatically on server boot (requires MongoDB and `TWITTER_BEARER_TOKEN`):

| Loop | Interval | Env override |
|---|---|---|
| Data ingestion (Twitter → `raw_tweets`) | 15 min | — |
| Winner model retrain | 30 min | `WINNER_TRAIN_INTERVAL_MINUTES` |
| Model comparison refresh | 168 h | `COMPARISON_INTERVAL_HOURS` |
| Email digest | 24 h | `DIGEST_INTERVAL_HOURS` |

The ingestion loop enforces a hard session quota of 1000 tweets and stops entirely when reached (restarts on server restart).

### 2. Collect tweets (one-shot)

```bash
python run_data_collection.py
```

Fetches up to 50 tweets per query across four bilingual query groups (Somali politics, security, economy/society, hashtags) and writes to `raw_tweets`. Requires `TWITTER_BEARER_TOKEN`.

### 3. Run the full evaluation

```bash
python run_evaluation.py
```

This is the main academic pipeline. Runs in this order:

1. Loads shared corpus (up to `LDA_CORPUS_LIMIT` tweets)
2. Trains LDA, NMF, BERTopic on the **same** corpus with the **same** seed (42)
3. Scores each model: C_v coherence, U_Mass coherence, Topic Diversity — per English / Somali / combined
4. Writes `results/metrics/coherence_diversity.csv` and `coherence_diversity.json`
5. Saves per-model per-language top-word CSVs under `results/topics/`
6. Selects winner by highest mean C_v (diversity tiebreak); persists to `pipeline_state`
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

Each metric is computed three times per model against the **same reference corpus and the same tokenization** (`preprocess_lda`): once for English-only documents, once for Somali-only, and once for the combined bilingual corpus. This makes per-language performance directly visible and comparable across all three models.

**Winner selection rule:** highest mean C_v across all three language slices (None values from sparse slices are skipped, not counted as zero). Topic Diversity breaks ties.

**Enhancement:** after winner selection, a hyperparameter grid is swept for the winning model only (LDA: 8 candidates; NMF: 4 candidates; BERTopic: up to 3 min-cluster-size values). The enhanced configuration is adopted only when the best candidate's mean C_v **strictly exceeds** the baseline; otherwise the original is kept.

---

## Key Design Decisions

**Same corpus, same seed.** All three models are trained on the identical corpus slice (`load_tweet_corpus()`, same `CORPUS_LIMIT`, random seed 42 enforced in LDA, NMF, and BERTopic). This is the primary fairness invariant for the academic comparison.

**BERTopic uses lighter preprocessing.** LDA and NMF require tokenized bag-of-words input; BERTopic uses `preprocess_bertopic()` which preserves word order for transformer embeddings. Coherence scoring uses the same reference corpus and same tokenization for all three models, so this asymmetry in training preprocessing does not affect the evaluation yardstick.

**Perplexity excluded from three-way comparison.** NMF is non-probabilistic; including perplexity would make a three-way comparison impossible. Only C_v coherence, U_Mass coherence, and Topic Diversity are used.

**Somali stopwords from a single file.** `api/resources/stopwords.txt` is loaded at import time by `lda_model.py` and shared with `bertopic_model.py`. Updating stopwords requires editing this file only — no code changes.

**Winner-only deployment.** After `run_full_evaluation()` selects a winner, only that model's production pipeline retrains on the `WINNER_TRAIN_INTERVAL_MINUTES` tick. The two losing models remain frozen with their last artifacts intact.

**LDA and NMF use identical corpus thresholds.** `nmf_pipeline.py` intentionally reads `LDA_MIN_CORPUS_SIZE`, `LDA_CORPUS_LIMIT`, and `LDA_GRID_SEARCH` — the same env vars as LDA — so the two baselines cannot diverge in configuration.

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
