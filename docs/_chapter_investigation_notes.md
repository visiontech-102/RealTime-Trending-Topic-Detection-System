# Chapter Investigation Notes
# Real-Time Trending Topic Detection System — FYP 2026
# Generated: 2026-06-30 — Phase 1

---

## PHASE 1 — FULL FOLDER TREE WITH PURPOSE ANNOTATIONS

```
FYP/                                    ← Project root
├── api/                                ← Python FastAPI backend (all server-side logic)
│   ├── app/                            ← FastAPI application entry points
│   │   ├── main.py                     ← App factory, CORS, lifespan background loops
│   │   └── routes.py                   ← All API endpoint definitions
│   ├── db/                             ← Database connectivity layer
│   │   └── connection.py               ← Motor async MongoDB client, singleton + helpers
│   ├── jobs/                           ← Scheduled / trigger-able pipeline jobs
│   │   ├── bertopic_pipeline.py        ← Orchestrates BERTopic training end-to-end
│   │   ├── lda_pipeline.py             ← Orchestrates LDA training end-to-end
│   │   ├── nmf_pipeline.py             ← Orchestrates NMF training end-to-end
│   │   ├── evaluation_pipeline.py      ← Runs evaluation for all three models
│   │   ├── model_comparison.py         ← Compares models, selects winner, writes report
│   │   ├── deployment.py               ← Promotes winning model results to detected_trends
│   │   └── enhancement.py              ← Post-deployment topic enrichment / cleanup
│   ├── models/                         ← Pydantic request/response schemas
│   │   └── schemas.py                  ← Data validation models for API I/O
│   ├── pipelines/                      ← Shared data-loading utilities used by all jobs
│   │   └── corpus_loader.py            ← Fetches + preprocesses tweets from MongoDB
│   ├── services/                       ← Core ML and domain-logic services
│   │   ├── bertopic_model.py           ← BERTopicTrainer: embeddings → UMAP → HDBSCAN → topics
│   │   ├── lda_model.py                ← LDATrainer: BoW → gensim LDA
│   │   ├── nmf_model.py                ← NMFTrainer: TF-IDF → sklearn NMF
│   │   ├── evaluation.py               ← Topic coherence + diversity scoring for all models
│   │   ├── trend_scoring.py            ← compute_trend_score(): volume + engagement formula
│   │   ├── data_collection.py          ← TweetCollector: Tweepy v2 → raw_tweets collection
│   │   ├── auth.py                     ← JWT creation/verification, bcrypt, 2FA helpers
│   │   ├── email.py                    ← SMTP sender + 2FA code generator
│   │   ├── notifications.py            ← Daily digest + spike alert email logic
│   │   └── monitoring.py               ← System-health / pipeline-state monitoring helpers
│   ├── tests/                          ← Pytest test suite (unit + integration)
│   │   ├── conftest.py                 ← Test DB fixture, sets DATABASE_NAME=trending_topics_test
│   │   ├── test_api.py                 ← General API endpoint tests
│   │   ├── test_api_routes.py          ← Route-level tests
│   │   ├── test_evaluation.py          ← Evaluation metric tests
│   │   ├── test_nmf_model.py           ← NMF model unit tests
│   │   ├── test_trend_scoring.py       ← Trend scoring unit tests
│   │   ├── test_integration_db.py      ← MongoDB integration tests (mongo_integration mark)
│   │   ├── test_email_smtp.py          ← SMTP / email tests
│   │   ├── test_notifications.py       ← Notification tests
│   │   ├── test_jose.py                ← JWT / python-jose tests
│   │   ├── bertopic_eval_report.txt    ← Saved evaluation report (test artifact)
│   │   └── bertopic_research_report.txt← Saved research text (test artifact)
│   ├── resources/
│   │   └── stopwords.txt               ← Custom English + Somali stopwords list
│   ├── reports/                        ← Auto-generated pipeline output reports
│   │   ├── bertopic/
│   │   │   ├── latest_clean_corpus.csv ← Last cleaned corpus fed to BERTopic
│   │   │   └── latest_eval_report.txt  ← BERTopic evaluation text report
│   │   └── comparison/
│   │       └── latest_comparison.json  ← Latest model comparison results JSON
│   ├── results/                        ← Research/evaluation artifacts (plots, CSVs)
│   │   ├── metrics/
│   │   │   ├── coherence_diversity.csv ← Per-model metric table
│   │   │   └── coherence_diversity.json← Same data as JSON
│   │   ├── topics/                     ← Per-model per-language topic CSVs
│   │   │   ├── bertopic_combined_topics.csv
│   │   │   ├── bertopic_en_topics.csv
│   │   │   ├── bertopic_so_topics.csv
│   │   │   ├── lda_combined_topics.csv
│   │   │   ├── lda_en_topics.csv
│   │   │   ├── lda_so_topics.csv
│   │   │   ├── nmf_combined_topics.csv
│   │   │   ├── nmf_en_topics.csv
│   │   │   └── nmf_so_topics.csv
│   │   ├── enhancement/
│   │   │   └── before_after.json       ← Before/after topic enhancement comparison
│   │   ├── coherence_comparison.pdf    ← Rendered coherence bar chart
│   │   ├── coherence_comparison.png    ← Rendered coherence bar chart (PNG)
│   │   ├── diversity_comparison.pdf    ← Rendered diversity bar chart
│   │   ├── diversity_comparison.png    ← Rendered diversity bar chart (PNG)
│   │   ├── plot_coherence.py           ← Script that generates coherence chart
│   │   └── plot_diversity.py           ← Script that generates diversity chart
│   ├── run_data_collection.py          ← CLI entry point: one-shot tweet collection
│   ├── run_bertopic.py                 ← CLI entry point: one-shot BERTopic training
│   ├── run_deployment.py               ← CLI entry point: one-shot deployment
│   ├── run_evaluation.py               ← CLI entry point: full three-model evaluation run
│   ├── check_db.py                     ← Diagnostic script: inspect MongoDB state
│   ├── pytest.ini                      ← Pytest configuration
│   └── .env                            ← Local environment variables (not committed)
│
├── dashboard/                          ← React + Vite frontend
│   ├── src/
│   │   ├── App.jsx                     ← Root component: React Router, context providers, route definitions
│   │   ├── main.jsx                    ← Vite entry point: mounts App into the DOM
│   │   ├── index.css                   ← Global Tailwind CSS base styles
│   │   ├── components/
│   │   │   ├── Layout.jsx              ← Authenticated shell: sidebar nav + page outlet
│   │   │   ├── Navigation.jsx          ← Sidebar navigation links and icons
│   │   │   └── DateFilter.jsx          ← Shared date-range picker component
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx         ← JWT token + user state, localStorage persistence
│   │   │   ├── ThemeContext.jsx        ← Light/dark mode toggle
│   │   │   ├── LanguageContext.jsx     ← en/so language toggle sent as API query param
│   │   │   └── DateRangeContext.jsx    ← Global from/to date filter shared across pages
│   │   ├── pages/
│   │   │   ├── Login.jsx               ← Login form (email/username + password + 2FA step)
│   │   │   ├── Register.jsx            ← Registration form
│   │   │   ├── Dashboard.jsx           ← Home: summary stats + trending topic cards
│   │   │   ├── Trending.jsx            ← Trending topics list with keyword chips
│   │   │   ├── Tweets.jsx              ← Raw tweet browser with search/filter
│   │   │   ├── History.jsx             ← Historical topic trend over time
│   │   │   ├── Comparison.jsx          ← Model comparison metrics visualization
│   │   │   ├── Export.jsx              ← Data export (CSV / JSON download)
│   │   │   ├── Profile.jsx             ← User profile + notification preferences
│   │   │   └── Setting.jsx             ← App settings (theme, language, account)
│   │   ├── services/
│   │   │   └── api.js                  ← Axios instance; JWT interceptor; all API call functions
│   │   └── utils/
│   │       └── dateRange.js            ← Date helper: parse, format, build query-param ranges
│   ├── index.html                      ← Vite HTML shell
│   ├── package.json                    ← npm dependencies (React, Recharts, Axios, Tailwind…)
│   ├── vite.config.js                  ← Vite build config
│   ├── tailwind.config.js              ← Tailwind CSS config
│   ├── postcss.config.js               ← PostCSS config
│   └── dist/                           ← Production build output (not manually edited)
│
├── Dockerfile                          ← Container image definition for the API
├── docker-compose.yml                  ← Compose file: API + MongoDB services
├── requirements.txt                    ← Python package dependencies
├── CLAUDE.md                           ← AI coding assistant instructions
├── README.md                           ← Project readme
├── Chapter4_System_Design.docx         ← Prior thesis chapter draft (Word)
├── Chapter4_System_Design.md           ← Same content in Markdown
├── About_System.docx                   ← Earlier system description document
├── About_System_updated.docx           ← Updated system description document
├── baar.md                             ← Working/scratch notes (Somali: "more")
└── db_test_output.txt                  ← Saved database diagnostic output
```

---

### Folder Purpose Summary (one sentence each)

| Folder | Purpose |
|--------|---------|
| `api/` | All Python server-side code: FastAPI app, ML pipelines, database, auth, scheduling |
| `api/app/` | The FastAPI application itself — entry point, routes, CORS, background loop startup |
| `api/db/` | Single-file MongoDB connectivity layer using Motor (async driver) |
| `api/jobs/` | Orchestrator scripts that sequence calls to services; run on a timer or via API trigger |
| `api/models/` | Pydantic schemas for request/response validation |
| `api/pipelines/` | Shared data-preparation code (corpus loading) used by all three model training jobs |
| `api/services/` | Core business logic: ML model trainers, evaluation, scoring, auth, email, notifications |
| `api/tests/` | Automated test suite with unit and MongoDB integration tests |
| `api/resources/` | Static reference files (stopword lists) |
| `api/reports/` | Auto-written pipeline outputs (evaluation reports, comparison JSON) served by the API |
| `api/results/` | Research artifacts: per-model topic CSVs, metric tables, comparison charts |
| `dashboard/` | React + Vite single-page app that is the user-facing web interface |
| `dashboard/src/components/` | Reusable React UI components (layout shell, nav, date filter) |
| `dashboard/src/contexts/` | React Context providers for auth, theme, language, and date-range global state |
| `dashboard/src/pages/` | One file per page/route in the web app |
| `dashboard/src/services/` | Axios HTTP client with auth injection and typed API functions |
| `dashboard/src/utils/` | Pure utility functions (date formatting/parsing) |

---

## PHASE 2 — FILE-BY-FILE INVESTIGATION

---

### FILE 1: api/app/main.py
**Role:** FastAPI application factory. Creates the `app` object, registers middleware, mounts the router, and launches background async loops on startup.

**Key functions/sections:**

#### `periodic_data_collection_loop(app)`
- **Input:** The FastAPI `app` instance (to read/write `app.state`).
- **Logic:**
  - Checks `app.state.session_ingested_count` against `app.state.max_quota_limit` (hardcoded = **1000**). If limit is reached, the loop does a strict `break` — stops permanently for this server session.
  - Computes `remaining` quota and `limit_per_query = max(1, min(50, remaining // len(queries)))`.
  - Calls `run_data_collection_pipeline(collector, queries, limit_per_query)` which returns the count of newly ingested tweets.
  - After each successful ingestion, checks whether the **deployed model** needs retraining: reads `pipeline_state` for `last_trained_tweet_collected_at`, counts new tweets since then, and if `>= BERTOPIC_NEW_TWEETS_THRESHOLD` (env default `"500"`) calls `run_deployed_pipeline()`.
  - Sleeps `15 * 60` seconds between iterations.
- **Output:** Side effects on `raw_tweets` collection and possible model retraining.
- **Why:** Continuously feeds the database so models always have fresh data to train on.

**NOTE:** The `queries` list is commented out in the current file (lines 27–35). The variable `queries` is referenced but not defined in scope — the loop will crash at runtime unless queries are defined. This is a known unfinished state.

#### `periodic_model_comparison_loop()`
- **Input:** None.
- **Logic:**
  - Waits 300 seconds (5-min startup delay).
  - Checks if a winner is already deployed (`get_deployed_model()`). If yes, exits immediately — "evaluation is a one-time academic decision."
  - If no winner: calls `run_full_evaluation()`. On success, calls `run_deployed_pipeline()` and exits permanently.
  - On insufficient data, retries every `retry_minutes` (env var `BERTOPIC_TRAIN_INTERVAL_MINUTES`, default `"30"`).
- **Output:** Winner model written to `pipeline_state`, topics written to `detected_trends`.
- **Why:** Automates the initial model selection without requiring manual intervention.

#### `periodic_email_digest_loop()`
- **Input:** None.
- **Logic:** Every `DIGEST_INTERVAL_HOURS` (default `"24"`) hours, calls `send_daily_digests()`.
- **Output:** Email sent (or logged to console if SMTP not configured).

#### `lifespan(app)`
- **Input:** The FastAPI `app`.
- **Logic:** On startup: calls `init_db_indexes()`, `deduplicate_existing_trends()`, pings MongoDB. If DB is connected, starts `periodic_data_collection_loop` and `periodic_email_digest_loop` as asyncio Tasks. On shutdown: cancels all tasks, closes DB client.
- **Why:** FastAPI's `asynccontextmanager` lifespan is the standard async startup/shutdown hook.

#### App-level constants (set at module level, not inside a function)
```python
app.state.session_ingested_count = 0
app.state.max_quota_limit = 1000
```
- CORS: `allow_origins=["*"]` — fully open for development.

---

### FILE 2: api/app/routes.py
**Role:** All API endpoint definitions. Single `APIRouter` mounted at root. Provides auth, data access, job triggers, and model status endpoints.

#### `get_current_user(token, db)` — dependency
- Decodes JWT via `jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])`.
- Looks up user by username OR email in `users` collection.

#### Auth endpoints
| Route | Method | What it does |
|---|---|---|
| `/auth/signup` | POST | Validates no duplicate username/email, hashes password with bcrypt, inserts user |
| `/auth/login` | POST | OAuth2PasswordRequestForm; accepts email or username; returns JWT |
| `/auth/google` | POST | Reads Google credential JWT (unverified claims!); auto-registers if new; returns JWT |
| `/auth/change-password` | POST | Verifies current password; hashes new; updates user doc |
| `/auth/2fa/status` | GET | Returns `two_factor_enabled` field |
| `/auth/2fa/send-code` | POST | Generates 6-digit code, stores with 10-min expiry, emails it |
| `/auth/2fa/verify` | POST | Checks code and expiry; sets `two_factor_enabled=True`; unsets code fields |
| `/auth/2fa/disable` | POST | Sets `two_factor_enabled=False` |
| `/auth/preferences` | GET/POST | Read/write `email_digests` and `spike_alerts` user fields |

#### Job trigger endpoints (all authenticated)
| Route | What it triggers |
|---|---|
| `POST /jobs/train-bertopic` | `run_bertopic_pipeline()` |
| `POST /jobs/train-lda` | `run_lda_pipeline()` |
| `POST /jobs/train-nmf` | `run_nmf_pipeline()` |
| `POST /jobs/run-deployment` | `run_deployed_pipeline()` |
| `POST /jobs/run-comparison` | `run_model_comparison()` |
| `POST /jobs/run-evaluation` | `run_full_evaluation(force=...)` |
| `POST /jobs/send-digests` | `send_daily_digests()` |

#### Model information endpoints
| Route | Returns |
|---|---|
| `GET /models/comparison` | Latest comparison report from `pipeline_state` or fallback to JSON file |
| `GET /models/winner` | Deployed model name and selection metadata |
| `GET /models/status` | Rich status: deployed model, metrics, eval metrics, history delta |
| `GET /models/history` | Training run history from `pipeline_history` collection |
| `GET /health` | DB ping + `collect_system_status()` |

#### Data endpoints
| Route | Returns |
|---|---|
| `GET /trends` | Latest batch of detected trends, adapted for frontend via `adapt_trend_to_frontend()` |
| `GET /history` | Historical trends filtered by date/lang/topic name |
| `POST /filter` | Trends matching a keyword regex in `Representation` array |
| `GET /raw_tweets` | Raw tweets from `raw_tweets` collection |
| `GET /trends/topics_over_time` | Aggregated category volumes per day (top 5 categories) |
| `GET /trends/keywords` | Top 30 word frequencies from raw tweets |
| `GET /tweets/stats` | Count of total/English/Somali tweets |

#### `adapt_trend_to_frontend(t, requested_lang)`
- Translates the MongoDB BERTopic schema (`Name`, `Representation`, `trend_score`) into the frontend-expected shape (`topic_name`, `top_keywords`, `score`).
- Uses `_dedup_docs()` to deduplicate representative documents by URL-stripped text (returns ≤ 3).
- Language assignment: uses `t.get("lang")` if it's `"en"` or `"so"`, otherwise falls back to `requested_lang`.

#### `get_clean_topic_name()` (inside `/trends/topics_over_time`)
- A local function that maps topic keywords/names to 10 semantic categories: Security, Politics, AI, Economy, Business, Sports, Health, Education, Technology, Climate, Other.
- Used only in the topics-over-time endpoint to aggregate volume by category.

---

### FILE 3: api/db/connection.py
**Role:** Provides the single shared Motor async MongoDB client used by all other modules.

**Key constants:**
- `MONGODB_URL` = env `MONGODB_URL`, default `"mongodb://localhost:27017/"`
- `DATABASE_NAME` = env `DATABASE_NAME`, default `"trending_topics_db"`

**Key functions:**

#### `_ensure_client()` — private
- If `_client` is None, creates `AsyncIOMotorClient(MONGODB_URL)` and sets `_db = _client[DATABASE_NAME]`.
- Returns `(_client, _db)`. Called by all other functions to guarantee singleton.

#### `get_database()` — async, main entry point
- Calls `_ensure_client()`.
- On first call, pings MongoDB to verify connection and sets `_verified = True`.
- Returns the database object. Used as a FastAPI dependency in routes.

#### `init_db_indexes()` — async
- Creates: `raw_tweets.id` (unique), `raw_tweets.collected_at`, `detected_trends.calculated_at`, `detected_trends.lang`, `topic_evolution.stored_at`, `pipeline_state.pipeline` (unique).

#### `deduplicate_existing_trends()` — async
- Runs an aggregation pipeline grouping by `(Name, calculated_at)` to find duplicates within the same batch.
- Deletes all but the first document in each duplicate group.
- Called on startup and after every BERTopic write.

#### `reset_db_client(url, name)` — sync
- Closes and nulls the client. Used exclusively by the test suite to swap in the test database.

---

### FILE 4: api/pipelines/corpus_loader.py
**Role:** Shared data-loading layer used by all three model training jobs. Reads `raw_tweets` from MongoDB and returns a clean pandas DataFrame.

**Constants:**
- `SUPPORTED_LANGS = ("en", "so")`

#### `load_tweet_corpus(lang, limit, min_text_length, after_timestamp)` — async
- **Input:** Optional `lang` filter (`"en"` or `"so"` or None for combined), `limit` (default `5000`), `min_text_length` (default `3`), optional `after_timestamp` for incremental loads.
- **Logic:**
  - Builds MongoDB query: adds `lang_api` filter if `lang` is set; adds `collected_at > after_timestamp` if provided.
  - Fetches most-recent-first (`sort("collected_at", -1)`), up to `limit` documents.
  - Converts to DataFrame; drops rows with null/empty `text`; ensures `like_count` and `retweet_count` are numeric (fills NaN with 0); fills missing `lang_api` with `"und"`.
- **Output:** pandas DataFrame with columns: `text`, `lang_api`, `like_count`, `retweet_count`, `created_at`, `collected_at`.
- **Why:** Centralizing corpus loading in one place means LDA, NMF, and BERTopic always load data identically — preventing subtle differences that could bias the evaluation.

#### `get_corpus_count(lang, after_timestamp)` — async
- Returns MongoDB count of qualifying documents without loading them. Used for pre-flight checks in all pipeline jobs.

---

### FILE 5: api/services/data_collection.py
**Role:** Wraps Tweepy v2 API to fetch tweets and persist them to the `raw_tweets` MongoDB collection.

#### `TweetCollector.__init__(bearer_token)`
- Initialises `tweepy.Client(bearer_token=bearer_token)`. If no token, logs a warning and sets `self.client = None`.

#### `TweetCollector.ingest_tweet(tweet_id, text, lang, created_at, metrics)` — async
- **Input:** Individual tweet fields.
- **Logic:** Normalises `created_at` to timezone-aware UTC datetime. Builds document:
  ```python
  {"id": tweet_id, "text": text, "lang_api": lang, "created_at": dt,
   "collected_at": datetime.now(timezone.utc), "retweet_count": ..., "like_count": ...}
  ```
  Inserts into `raw_tweets`. On `DuplicateKeyError` (unique index on `id`), silently returns `False`.
- **Output:** `True` if inserted, `False` if duplicate.

#### `TweetCollector.fetch_recent_tweets(query, max_results)` — async
- Clamps `max_results` to `[10, 100]`.
- Calls `self.client.search_recent_tweets(query, tweet_fields=["created_at", "lang", "public_metrics"], max_results=max_results)` via `asyncio.get_event_loop().run_in_executor()` (runs blocking Tweepy call in thread pool).
- Returns list of tweet objects or `[]` on error.

#### `run_data_collection_pipeline(collector, query_list, limit_per_query)` — async
- Iterates through each query string in `query_list`, calls `fetch_recent_tweets`, then calls `ingest_tweet` for each result.
- Returns total count of newly ingested (non-duplicate) tweets.

---

### FILE 6: api/services/trend_scoring.py
**Role:** Pure-function scoring utilities with no I/O or database calls.

#### `_NOISE_BLOCKLIST` = `frozenset({'https', 'http', 'www', 'co', 'rt', 'amp', 't'})`

#### `clean_keywords(words)` → list
- Removes entries in `_NOISE_BLOCKLIST` and "hash-like" tokens (alphanumeric, length >= 5, mixed letters+digits).
- Used in BERTopic pipeline and deployment to strip URL fragments from topic keyword lists.

#### `compute_trend_score(doc_count, total_likes, total_retweets, corpus_max_engagement)` → float
- **Formula:** `volume_component + engagement_component`
  - `volume_component = min(doc_count / 100.0, 1.0) * 60.0` — capped at 60 points
  - `engagement_component = min((likes + retweets) / max(corpus_max_engagement, 1), 1.0) * 40.0` — capped at 40 points
- Score range: 0.0 – 100.0. Volume is 60%, engagement 40%.
- Returns `round(..., 4)`.

#### `dominant_language(langs)` → dict
- Counts `{"en": N, "so": M, "others": K}` from a list of language codes.

#### `assign_topic_lang(langs)` → str
- **70% majority rule:** if English ≥ 70% of (en + so), returns `"en"`; if Somali ≥ 70%, returns `"so"`.
- If neither reaches 70%: simple majority; tie → `"en"`.
- If no recognised languages: defaults to `"en"`.

#### `generate_topic_label(keywords, n=3)` → str
- Cleans keywords, takes first `n`, title-cases, joins with `" & "`.

---

### FILE 7: api/services/bertopic_model.py
**Role:** `BERTopicTrainer` class — the four-stage BERTopic pipeline (embeddings → UMAP → HDBSCAN → c-TF-IDF).

#### `preprocess_bertopic(df, text_col)` → DataFrame
- **Minimal preprocessing:** only removes exact duplicate tweets and strips whitespace. Intentionally does NOT apply stemming, lemmatisation, or stopword removal — this preserves sentence structure so the SentenceTransformer can use context.

#### `BERTopicTrainer.__init__(embedding_model_name, min_cluster_size, n_neighbors)`
- **Embedding model:** `"sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"` — multilingual (supports Somali and English).
- **UMAP:** `n_neighbors=15`, `n_components=5`, `min_dist=0.0`, `metric="cosine"`, `random_state=42`.
- **HDBSCAN:** `min_cluster_size=min_cluster_size`, `metric="euclidean"`, `cluster_selection_method="eom"`, `prediction_data=True`.
- **CountVectorizer:** uses combined English + Somali stopwords (imported from `lda_model.py`).
- **BERTopic:** `nr_topics=None` (no forced reduction), `calculate_probabilities=True`.

#### `BERTopicTrainer.train(docs)` → `(topics, probabilities)`
- Generates embeddings via `self.embedding_model.encode(docs)` — a single unified semantic vector space pass.
- Calls `self.topic_model.fit_transform(docs, embeddings)` which internally runs UMAP → HDBSCAN → c-TF-IDF.
- Sets `self.is_fitted = True` and stores `self._training_docs`.

#### `BERTopicTrainer.evaluate_cohesion(docs, topics)` → float
- For each topic (excluding -1 outlier): computes mean pairwise cosine similarity between document embeddings within the cluster.
- Returns mean over all topics.

#### `BERTopicTrainer.run_dynamic_topic_modeling(docs, timestamps)` → DataFrame
- Calls `self.topic_model.topics_over_time(docs, formatted_timestamps, topics=self.topic_model.topics_)` to track how topic prominence changes over time.

#### `BERTopicTrainer.apply_hierarchical_reduction(num_topics)`
- Calls `self.topic_model.reduce_topics(docs, nr_topics=num_topics)` to merge low-volume topics.

#### `BERTopicTrainer.calculate_topic_diversity(top_n_words=10)` → float
- Unique words / total words across all topics' top-N keywords. Returns 0.0–1.0.

#### `BERTopicTrainer.generate_evaluation_report(docs, topics, report_path)`
- Writes text report to `reports/bertopic/latest_eval_report.txt` with cohesion, diversity, and topic statistics.

---

### FILE 8: api/services/lda_model.py
**Role:** LDA model training, preprocessing, and evaluation using gensim. Also the single source of truth for English and Somali stopwords used by all three models.

#### Stopwords
- `english_stopwords` = `set(nltk.corpus.stopwords.words('english'))` — NLTK built-in
- `somali_stopwords` = loaded from `api/resources/stopwords.txt` via `_load_somali_stopwords()` — resolves path relative to the file

#### `preprocess_lda(text, lang)` → list of tokens
- **Heavy preprocessing pipeline:**
  1. Lowercase
  2. Remove URLs (`http`, `www`, `https`)
  3. Remove mentions (`@word`)
  4. Remove punctuation (`re.sub(r'[^\w\s]', '', text)`)
  5. NLTK word tokenisation
  6. Stopword removal (English stopwords for `lang=="en"`, Somali stopwords for `lang=="so"`, combined for other)
  7. Drop tokens with length ≤ 2
- Returns list of clean tokens.

#### `prepare_lda_matrices(tokenized_docs, use_tfidf)` → `(dictionary, corpus_bow/tfidf)`
- Creates a `gensim.corpora.Dictionary` from tokenized docs.
- Filters extremes: `no_below=2`, `no_above=0.95`.
- Builds BoW corpus; optionally applies TF-IDF weighting.

#### `LDATrainer.__init__(dictionary, corpus)`

#### `LDATrainer.train(num_topics, alpha, eta, passes)` → gensim `LdaModel`
- `alpha` default `"symmetric"`, `eta` (beta) default `"symmetric"`, `passes=10`, `random_state=42`.

#### `LDATrainer.evaluate(tokenized_docs)` → `(coherence_score, perplexity)`
- C_v coherence via `CoherenceModel(... coherence='c_v', processes=1)`.
- **`processes=1` note:** gensim's default multiprocessing pool deadlocks on Windows when invoked without a `__main__` guard (e.g., under pytest or uvicorn). Fixed by forcing single process.
- Perplexity via `model.log_perplexity(self.corpus)`.

#### `run_lda_grid_search(tokenized_docs, corpus, dictionary, topic_range, alphas, betas)` → DataFrame
- Grid over all combinations; for each: trains LDA and calls `evaluate()`.
- Returns DataFrame with columns: `K`, `alpha`, `beta`, `coherence`, `perplexity`.

#### `split_corpus_temporally(tweets, interval_hours=24)` → dict
- Groups tweets by `created_at` rounded down to `interval_hours` boundaries.

---

### FILE 9: api/services/nmf_model.py
**Role:** NMF topic model training and evaluation using scikit-learn, sharing vocabulary/preprocessing with LDA.

#### `prepare_nmf_matrix(tokenized_docs, dictionary)` → `(tfidf_matrix, vectorizer)`
- Builds TF-IDF matrix using `sklearn.TfidfVectorizer` restricted to the SAME vocabulary as the gensim Dictionary passed in (via `vocabulary=dictionary.token2id`).
- The `analyzer=lambda tokens: tokens` tells the vectorizer the input is already tokenized.
- **Key design point:** LDA and NMF use identical vocabularies — only the weighting scheme (BoW vs TF-IDF) and decomposition technique differ.

#### `NMFTrainer.__init__(tfidf_matrix, vectorizer)`

#### `NMFTrainer.train(num_topics)` → sklearn `NMF` model
- Uses `NMF(n_components=num_topics, init="nndsvda", max_iter=400, random_state=42)`.

#### `NMFTrainer.get_topics(num_words=10)` → list of word lists
- For each component: `component.argsort()[::-1][:num_words]` → top word indices.

#### `NMFTrainer.evaluate(tokenized_docs, dictionary, num_words=10)` → `(cv_score, umass_score)`
- C_v coherence (primary) and U_Mass coherence (supporting) via gensim `CoherenceModel`.
- `processes=1` for the same Windows deadlock reason.
- **No perplexity** — NMF is non-probabilistic by design.

#### `calculate_topic_diversity(topics)` → float
- Module-level function (not a method): `len(set(all_words)) / len(all_words)`. Generalised to plain list-of-word-lists so it's usable for LDA, NMF, and BERTopic.

#### `run_nmf_grid_search(tokenized_docs, dictionary, topic_range, num_words)` → DataFrame
- Grid over K values, same selection criterion as LDA (highest C_v, tiebreak smaller K).

---

### FILE 10: api/services/evaluation.py
**Role:** Shared intrinsic evaluation engine. Computes C_v coherence, U_Mass coherence, and Topic Diversity for all three models against the SAME reference corpus.

#### Key constant: `TOP_N_WORDS = 10` — same for every model and language slice.
#### `LANGUAGES = ("en", "so")` — "combined" slice is excluded by design.

#### `build_reference_corpora(df, text_col, lang_col)` → dict
- Tokenizes the FULL corpus using `preprocess_lda()` (heavy preprocessing) for every document regardless of which model is being evaluated.
- Returns `{"en": [...], "so": [...], "combined": [...]}`.
- **Why:** All three models are evaluated against the same tokenized reference. This is the common yardstick — BERTopic trained with minimal preprocessing is still scored on the same standard.

#### `build_reference_dictionary(reference_corpora)` → `gensim.Dictionary`
- Unfiltered dictionary from the combined corpus. Permissive so every model's topic words have the best chance of resolving to an ID.

#### `compute_coherence(topics, tokenized_docs, dictionary)` → `(c_v, u_mass)`
- Filters topics to those with ≥ 2 words.
- C_v via `CoherenceModel(... coherence="c_v", processes=1)`.
- U_Mass via `CoherenceModel(... coherence="u_mass", processes=1)`.

#### `evaluate_model(model_name, topics, num_topics, reference_corpora, dictionary)` → list of rows
- Evaluates one model's topics over `LANGUAGES = ("en", "so")`.
- Per-language: strips topic words that don't appear in that language slice's reference docs (prevents NaN from PMI denominator = 0 when Somali words appear in English evaluation).
- Returns list of dicts: `{model, language, c_v, u_mass, diversity, K}`.

#### `_safe_round(value, ndigits)` → float or None
- None-safe AND NaN-safe rounding. C_v can degenerate to NaN on very sparse corpora.

#### `get_lda_topics(model, num_words)`, `get_nmf_topics(trainer, num_words)`, `get_bertopic_topics(topic_model, num_words)`
- Extract top-word lists from each model type.
- **BERTopic normalization in `get_bertopic_topics`:** Applies `_normalize(word)` which lowercases and keeps only alphabetic chars. Without this, BERTopic's lightly-preprocessed keywords (mixed-case, punctuation) would fail to match the `preprocess_lda()`-built reference dictionary, systematically disadvantaging BERTopic in C_v scoring.

#### `save_metrics_table(rows, metrics_dir)` → dict of paths
- Writes `results/metrics/coherence_diversity.csv` and `results/metrics/coherence_diversity.json`.

#### `save_topic_words(model_name, topics, reference_corpora, topics_dir)` → dict of paths
- Saves per-model per-language topic CSV files to `results/topics/`.

---

### FILE 11: api/services/auth.py
**Role:** JWT and password utilities.

**Constants (from env):**
- `SECRET_KEY` = env `SECRET_KEY`, default `"your_super_secret_key_here"`
- `ALGORITHM` = env `ALGORITHM`, default `"HS256"`
- `ACCESS_TOKEN_EXPIRE_MINUTES` = env `ACCESS_TOKEN_EXPIRE_MINUTES`, default `"30"` (30 minutes)

- `pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")`
- `verify_password(plain, hashed)` → bool
- `get_password_hash(password)` → str (bcrypt hash)
- `create_access_token(data, expires_delta)` → JWT string (HS256, sets `exp` claim)

---

### FILE 12: api/services/email.py
**Role:** SMTP email sending for 2FA codes, spike alerts, and daily digests.

**Env vars:**
- `SMTP_ENABLED` = `"false"` by default — in dev mode, emails are printed to console
- `SMTP_HOST`, `SMTP_PORT` (default `587`), `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` (default `"true"`)

#### `_send_smtp_sync(to_email, subject, body)` — blocking
- Builds `MIMEMultipart` message, connects via STARTTLS or SSL, sends, quits.
- Called via `asyncio.to_thread()` to avoid blocking the event loop.

#### `_send_email(email, subject, body)` — async
- If SMTP configured: calls `_send_smtp_sync` via thread pool.
- Otherwise: logs and prints email content to console (dev mode).

#### `send_2fa_code(email, code)`, `generate_2fa_code()`, `send_spike_alert(email, spikes)`, `send_email_digest(email, trends)`
- `generate_2fa_code()` returns `str(random.randint(100000, 999999))` — 6-digit code.
- Spike alerts format: "topic: old_score → new_score (+pct%)".
- Digest: top 10 trends by `trend_score`, formatted as numbered list.

---

### FILE 13: api/services/notifications.py
**Role:** Spike detection and digest sending driven by user preferences in the `users` collection.

**Constant:** `SPIKE_THRESHOLD_PCT` = env `SPIKE_THRESHOLD_PCT`, default `"25"` (25% increase triggers alert)

#### `_get_latest_two_batches(db)` → `(current, previous)`
- Aggregates `detected_trends` to find the two most recent `calculated_at` timestamps.
- Returns the full trend lists for those two batches.

#### `_detect_spikes(current, previous)` → list
- For each current trend: if the previous score exists and the percentage increase ≥ `SPIKE_THRESHOLD_PCT`, adds to spikes list.
- If score ≥ 50 and no previous batch entry exists (brand new topic), also alerts.

#### `check_and_send_spike_alerts()` — async
- Finds all users with `spike_alerts=True`.
- Sends `send_spike_alert(email, spikes[:5])` to each.
- Updates `pipeline_state` with `pipeline="notifications"`.

#### `send_daily_digests()` — async
- Finds the most recent `calculated_at` batch and fetches top 10 trends sorted by `trend_score`.
- Sends `send_email_digest()` to all users with `email_digests=True`.

---

### FILE 14: api/services/monitoring.py
**Role:** Generates a system-health snapshot for the `/health` endpoint.

**Constants:** `BERTOPIC_MIN` = `BERTOPIC_MIN_CORPUS_SIZE` (default `1000`), `LDA_MIN` = `LDA_MIN_CORPUS_SIZE` (default `1000`), `OUTLIER_WARN_THRESHOLD` = `BERTOPIC_OUTLIER_WARN_RATIO` (default `0.35`)

#### `collect_system_status()` → dict
- Reads `raw_tweets` count, latest tweet timestamp, and pipeline states from MongoDB.
- Generates alerts: low corpus (info), high outlier ratio (warning), no topics produced (warning), LDA not yet run (info).
- Returns a structured dict with `checked_at`, `raw_tweet_count`, `last_ingestion_at`, pipeline states, thresholds, and `alerts`.

---

### FILE 15: api/jobs/bertopic_pipeline.py
**Role:** End-to-end BERTopic production job. Loads tweets, trains separate EN and SO models, builds `detected_trends` documents, and persists to MongoDB.

**Constants:**
- `MIN_CORPUS_SIZE` = env `BERTOPIC_MIN_CORPUS_SIZE`, default `1000`
- `CORPUS_LIMIT` = env `BERTOPIC_CORPUS_LIMIT`, default `2000`
- `MIN_PER_LANG_CORPUS = 50` (hardcoded minimum per language)

#### `_adaptive_min_cluster_size(n_docs)` → int
- `max(3, min(10, n_docs // 5))` — scales HDBSCAN's `min_cluster_size` to the corpus size.

#### `_run_training_sync(df_clean, min_cluster_size)` — blocking, runs in thread pool
- Creates `BERTopicTrainer`, calls `train(docs)`, returns `(trainer, topics, docs)`.

#### `_build_trend_documents(df_clean, trainer, topics, calculated_at)` → list
- For each non-outlier topic in `topic_info`:
  - Computes `volume`, `total_likes`, `total_retweets`, `langs`.
  - Gets `representation` (top 10 keywords from c-TF-IDF).
  - For each of the top 3 keywords, finds the best tweet (by engagement) from this topic's document subset that contains that keyword as a representative doc — de-duped by URL-stripped text.
  - Assigns `lang` via `assign_topic_lang(langs)` (70% majority rule).
  - Computes `trend_score` via `compute_trend_score()`.
  - Builds the full MongoDB document with all required fields including `tweet_period_from/to` and `peak_at` (median collected_at).
  - Sets `model="bertopic"`.
- Sorts result by `trend_score` descending.

#### `_persist_trends(trend_docs, calculated_at, metrics, last_trained_tweet_collected_at)` → int
- Inserts all trend docs into `detected_trends`.
- Upserts `pipeline_state` with `pipeline="bertopic"`, setting `metrics` (and `prev_metrics` from prior state).
- Inserts a row into `pipeline_history` for audit trail.

#### `run_bertopic_pipeline()` — async, main entry point
- Checks if there are enough new tweets since last training (uses `BERTOPIC_NEW_TWEETS_THRESHOLD`, env default `"500"`). Skips if not enough new data (unless `detected_trends` is empty).
- Loads corpus via `load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)`.
- Applies `preprocess_bertopic()`.
- Saves clean corpus CSV to `reports/bertopic/latest_clean_corpus.csv`.
- Splits into English (df_en) and Somali (df_so) DataFrames.
- Trains separate EN and SO BERTopic models (each in a thread pool to avoid blocking the event loop).
- After training: computes standardized C_v metrics via `evaluate_model()` (same as evaluation_pipeline).
- Persists trends and metrics.
- After persistence: calls `check_and_send_spike_alerts()`.

---

### FILE 16: api/jobs/lda_pipeline.py
**Role:** LDA baseline job — NOT deployed to production. Trains LDA, evaluates, saves report. Used only for academic comparison.

**Constants:**
- `MIN_CORPUS_SIZE` = env `LDA_MIN_CORPUS_SIZE`, default `1000`
- `CORPUS_LIMIT` = env `LDA_CORPUS_LIMIT`, default `2000`
- `RUN_GRID_SEARCH` = env `LDA_GRID_SEARCH` == `"true"`, default `true`
- `NEW_TWEETS_THRESHOLD` = env `LDA_NEW_TWEETS_THRESHOLD`, default `1000`

#### `_tokenize_corpus(df)` → list of token lists
- For each row: calls `preprocess_lda(text, lang)` with the row's `lang_api` (falls back to `"en"` for unsupported langs).

#### `_pick_best_from_grid(results_df)` → dict
- Sorts by coherence descending, then K ascending (Occam's razor tie-break).

#### `_run_lda_sync(tokenized_docs, use_grid)` — blocking
- If `use_grid` and ≥ 50 docs: runs grid search over `topic_range = list(range(4, 13))` (K from 4 to 12), `alphas=["symmetric"]`, `betas=["symmetric"]`. Picks best by C_v.
- If no grid: `k = max(3, min(10, len(tokenized_docs) // 15))`.
- Trains final `LDATrainer` with chosen K, evaluates (C_v + perplexity).

#### `run_lda_pipeline()` — async, main entry point
- Guard: skips if fewer than `NEW_TWEETS_THRESHOLD` new tweets since last training.
- Guard: skips if corpus < `MIN_CORPUS_SIZE`.
- Loads corpus, tokenizes, trains, evaluates.
- Saves `reports/lda/latest_eval.json` with full results.
- Upserts `pipeline_state` with `pipeline="lda"`.

---

### FILE 17: api/jobs/nmf_pipeline.py
**Role:** NMF baseline job — mirrors `lda_pipeline.py` in structure. NOT deployed; academic comparison only.

**Key design decisions:**
- Reuses `LDA_MIN_CORPUS_SIZE`, `LDA_CORPUS_LIMIT`, `LDA_GRID_SEARCH`, `LDA_NEW_TWEETS_THRESHOLD` env vars deliberately — "so the two baselines cannot drift apart in configuration."
- Imports `_tokenize_corpus` from `jobs.lda_pipeline` — not duplicated, so LDA and NMF can never tokenize differently.
- `TOPIC_RANGE = list(range(4, 13))` — same dense K range as LDA.

#### `_run_nmf_sync(tokenized_docs, use_grid)` — blocking
- Builds shared dictionary via `prepare_lda_matrices()`.
- If grid search: runs `run_nmf_grid_search()` over K∈{4..12}, picks best C_v (no perplexity for NMF).
- Trains `NMFTrainer`, evaluates (C_v + U_Mass), calculates diversity.
- Saves `reports/nmf/latest_eval.json`.

#### `run_nmf_pipeline()` — async, main entry point
- Same guard pattern as `run_lda_pipeline()`.

---

### FILE 18: api/jobs/evaluation_pipeline.py
**Role:** Runs all three models on the SAME loaded corpus for a fair comparison, selects the winner, writes metrics, and calls `run_model_comparison()`.

**Constants:**
- `EVAL_NEW_TWEETS_THRESHOLD` = env `EVAL_NEW_TWEETS_THRESHOLD`, default = `MIN_CORPUS_SIZE` = `1000`

#### `run_full_evaluation(run_grid_search, force)` — async, main entry point

**Guard 1 (unless `force=True`):** If a winner is already deployed, skips entirely — "evaluation is a one-time academic decision."

**Guard 2 (unless `force=True`):** If not enough new tweets since last evaluation attempt, skips.

**Training sequence (per-language, all on the SAME loaded corpus):**
1. Splits corpus into `df_en` and `df_so` (min 50 docs per language to train).
2. **LDA-EN** and **LDA-SO**: tokenized separately, grid search K∈{4..12}, trains and evaluates.
3. **NMF-EN** and **NMF-SO**: uses the SAME tokenized docs as LDA.
4. **BERTopic-EN** and **BERTopic-SO**: minimal preprocessing, HDBSCAN auto-K (unconstrained — its "defining characteristic").

**Evaluation:** Calls `evaluate_model()` for each model with the shared `reference_corpora` and `dictionary`. Saves metrics to `results/metrics/coherence_diversity.json` and topic words to `results/topics/*.csv`.

**Winner selection:** Calls `_select_winner_from_metrics(rows)` — primary criterion: English C_v; tiebreak: Somali C_v; secondary tiebreak: English diversity.

**After winner selection:**
- Calls `persist_deployed_model(winner)`.
- Stamps all three `pipeline_state` entries with `last_evaluated_at` and `last_trained_tweet_collected_at`.
- Calls `run_model_comparison()` to sync the comparison report.

---

### FILE 19: api/jobs/model_comparison.py
**Role:** Assembles the three-way comparison report and persists it; also executes winner selection from the saved metrics file.

#### `_load_evaluation_metrics()` → list
- Reads `results/metrics/coherence_diversity.json`. Returns `[]` if file doesn't exist.

#### `_select_winner_from_metrics(rows)` → `(winner: str | None, scores: dict)`
- **Option B winner selection:**
  - Primary: English C_v (highest wins).
  - Tiebreak: Somali C_v.
  - Secondary tiebreak: English Topic Diversity.
  - `"combined"` rows are ignored.
- Returns `(None, {})` if rows is empty — a winner is NEVER chosen without measured data.

#### `run_model_comparison()` — async
- Checks all three `pipeline_state` entries exist (lda, nmf, bertopic). If any missing, returns `"incomplete_pipeline_runs"`.
- Loads metrics, selects winner, builds comparison report dict with:
  - `selected_deployment_model`, `winner_selection_basis`, `winner_selection_rule`
  - `lda_metrics`, `nmf_metrics`, `bertopic_metrics` (per language: c_v, u_mass, diversity, K)
  - `academic_note` explaining the evaluation approach
- Saves to `reports/comparison/latest_comparison.json`.
- Upserts `pipeline_state` with `pipeline="model_comparison"`.
- Calls `persist_deployed_model(winner)`.

---

### FILE 20: api/jobs/deployment.py
**Role:** Deployment registry (persist/read winner name) and dispatcher (retrain only the winner).

**Constant:** `DEPLOYED_RETRAIN_THRESHOLD` = env `DEPLOYED_MODEL_RETRAIN_THRESHOLD`, default `500`.

#### `persist_deployed_model(model_name)` — async
- Upserts `pipeline_state` with `pipeline="deployed_model"`, `model=model_name`, `set_at=now`.

#### `get_deployed_model()` — async
- Returns `state.get("model")` or `None`.

#### `run_deployed_pipeline()` — async, dispatcher
- Reads deployed model name. Routes to `_run_lda_deployment()`, `_run_nmf_deployment()`, or `run_bertopic_pipeline()`.

#### `_build_trend_docs_lda(df, valid_idx, lda_result, calculated_at)` → list
- Assigns each tokenized document to its dominant LDA topic via `model.get_document_topics(bow)` argmax.
- Builds detected_trends documents in the SAME schema as BERTopic (same field names: `Name`, `Representation`, `trend_score`, `lang`, etc.) with `model="lda"`.

#### `_build_trend_docs_nmf(df, valid_idx, nmf_result, calculated_at)` → list
- Assigns documents to dominant NMF topic via `H.argmax(axis=1)` where H is the doc-topic activation matrix from `trainer.model.transform(tfidf_matrix)`.
- Same schema as BERTopic, with `model="nmf"`.

#### `_persist_trend_docs(trend_docs, calculated_at, model_name)` — async
- **Replaces** (delete_many + insert_many) the previous run's topics for this model — one clean set, no accumulation.

#### `_run_lda_deployment()` and `_run_nmf_deployment()` — async
- Incremental: loads only tweets newer than `last_trained_tweet_collected_at`.
- Splits into EN/SO, trains per-language, builds trend docs, persists, computes standardized metrics, writes to `pipeline_history`.

---

### FILE 21: api/jobs/enhancement.py
**Role:** Post-evaluation hyperparameter tuning stage. Sweeps a small grid for the WINNING MODEL ONLY, compares C_v against baseline, and saves a before/after JSON. Adopted only if best candidate strictly beats baseline.

**Hyperparameter grids:**
- LDA: 2 × 2 × 2 = 8 candidates: `LDA_ALPHA_RANGE = ["symmetric", "auto"]`, `LDA_ETA_RANGE = ["symmetric", "auto"]`, `LDA_PASSES_RANGE = [10, 20]`
- NMF: 2 × 2 = 4 candidates: `NMF_INIT_RANGE = ["nndsvda", "nndsvd"]`, `NMF_MAXITER_RANGE = [400, 600]`
- BERTopic: ≤ 3 candidates: `BERTOPIC_MCS_OFFSETS = [0, 2, 4]` added to adaptive base `min_cluster_size`

#### `run_enhancement(winner)` — async
1. Reads baseline from `results/metrics/coherence_diversity.json`.
2. Loads corpus with same `CORPUS_LIMIT` and same `load_tweet_corpus()` as evaluation.
3. Builds same `reference_corpora` + `ref_dictionary`.
4. Runs the appropriate sweep (`_sweep_lda`, `_sweep_nmf`, or `_sweep_bertopic`) in thread pool.
5. Ranks candidates by `(mean_c_v desc, mean_diversity desc)`.
6. `adopted = True` only if `best_cv > baseline_cv` (strictly greater).
7. Saves report to `results/enhancement/before_after.json`.

---

### FILE 22: api/run_evaluation.py (CLI entry point)
- Calls `asyncio.run(run_full_evaluation())`.
- Used as the one-time offline evaluation command: `python run_evaluation.py` from `api/`.
- This is what the user runs after data collection to train all three models and select the winner.

---

### FILE 23: dashboard/src/App.jsx
**Role:** Root React component. Sets up React Router v6 routing and wraps everything in context providers (configured in `main.jsx`).

- Public routes: `/login`, `/register`.
- Protected routes wrapped in `<Layout>` (auth guard inside Layout): `/dashboard`, `/trending`, `/tweets`, `/history`, `/comparison`, `/export`, `/setting`, `/profile`.
- Root `/` redirects to `/dashboard`.

---

### FILE 24: dashboard/src/services/api.js
**Role:** All HTTP communication between frontend and backend. Single Axios instance with base URL `http://localhost:8000`.

**Request interceptor:** Reads `token` from `localStorage`; if present, adds `Authorization: Bearer <token>` header to every request.

**Login special case:** `loginUser()` sends `application/x-www-form-urlencoded` (required by FastAPI's `OAuth2PasswordRequestForm`), mapping the `email` parameter to the `username` field.

**Key exported functions:**
- `loginUser`, `signupUser`, `loginWithGoogle`, `changeUserPassword`
- `get2FAStatus`, `request2FACode`, `verify2FACode`, `disable2FA`
- `getPreferences`, `updatePreferences`
- `getTrends(lang, dateParams)` — `GET /trends?lang=...&limit=50&from_date=...&to_date=...`
- `getHistory(lang, dateParams, limit)` — `GET /history?...`
- `filterTrends(keyword, lang)` — `POST /filter?keyword=...&lang=...`
- `getRawTweets(lang, dateParams, limit)` — `GET /raw_tweets?...`
- `getHealth()` — `GET /health`
- `getModelComparison()` — `GET /models/comparison`
- `runModelComparison()` — `POST /jobs/run-comparison`
- `trainLda()`, `trainBertopic()`, `trainNmf()` — trigger training jobs
- `getTopicTrends(dateParams)` — `GET /trends/topics_over_time?...`
- `getTrendingKeywords(dateParams)` — `GET /trends/keywords?...`
- `getTweetStats(dateParams)` — `GET /tweets/stats?...`
- `getModelStatus()` — `GET /models/status`
- `getModelHistory(limit, dateParams)` — `GET /models/history?...`

`buildDateQuery(dateParams)` — helper that appends `from_date` and `to_date` as URL params.

---

### FILE 25: dashboard/src/utils/dateRange.js
**Role:** Converts the global `DateRangeContext` state into API-compatible `{from_date, to_date}` ISO strings.

#### `rangeToQueryParams(range, customDates)` → `{from_date?, to_date?}`
- `"24h"` or `"24 HOURS"` → last 24 hours
- `"7d"` or `"7 DAYS"` → last 7 days
- `"30d"` or `"30 DAYS"` → last 30 days
- `"custom"` with valid `customDates` → uses `startDate T00:00:00` to `endDate T23:59:59`
- `"all"` or `"ALL"` → `{}` (no date filter, returns all data)
- Default fallback → last 24 hours

---

### FILE 26: dashboard/src/components/Layout.jsx
**Role:** Authentication guard and page shell. Checks `isAuthenticated` from `AuthContext`. Redirects to `/login` if not authenticated. Renders `<Navigation />` at top and `<Outlet />` (the current page) below.

---

### FILE 27: dashboard/src/components/Navigation.jsx
**Role:** Top navigation bar. Contains brand logo, nav links with active-state highlighting, language toggle (EN↔SO), dark/light mode toggle, and profile link.

- Nav links: Dashboard, Trending, Tweets, History, Comparison, Export, Settings.
- Language toggle: switches between `"en"` and `"so"` via `LanguageContext.toggleLanguage()`.
- Theme toggle: via `ThemeContext.toggleTheme()`.

---

### FILE 28: dashboard/src/components/DateFilter.jsx
**Role:** Shared date filter widget used by every page. Provides preset buttons (24 HOURS, 7 DAYS, 30 DAYS) and a custom calendar picker. Updates `DateRangeContext`.

- Custom picker is a bespoke calendar grid component (`CustomNativePicker`) — no third-party calendar library.
- `handleApplyCustom()` calls `setCustomDates({startDate, endDate})` and `setRange('custom')` when both dates are selected.

---

### FILE 29: dashboard/src/pages/Dashboard.jsx
**Role:** Home page. Shows summary statistics (tweet counts, trending topic count) and three charts.

**Data fetched:**
- `getTweetStats(dateParams)` → total, English, Somali tweet counts
- `getTrends('en', dateParams)` + `getTrends('so', dateParams)` → combined, sorted by score
- `getTrendingKeywords(dateParams)` → top 30 word frequencies

**Charts rendered:**
- Language Distribution: Recharts `PieChart` (donut) with English/Somali breakdown
- Trending Now: Custom word cloud using font-size proportional to word frequency
- Top Topics: Recharts horizontal `BarChart` showing top 8 topics by score

---

### FILE 30: dashboard/src/pages/Trending.jsx
**Role:** Full trending topics table with search and language filter.

- Fetches both EN and SO trends; combines and sorts by score.
- Search: 500ms debounced; if keyword present, calls `filterTrends(keyword, lang)` instead of `getTrends`.
- Language filter buttons: ALL / ENGLISH / SOMALI.
- Expandable rows: clicking a row shows `representative_docs` (up to 3 real tweets from that topic).

---

### FILE 31: dashboard/src/pages/Comparison.jsx
**Role:** Model comparison metrics visualization. Shows BERTopic training quality over time and the three-way model evaluation table.

**Data fetched:**
- `getTrends('en')` and `getTrends('so')` — to show side-by-side English and Somali topic lists
- `getModelComparison()` — `GET /models/comparison` — three-way metrics table
- `getModelHistory(20, dateParams)` — `GET /models/history` — BERTopic quality metrics over runs

**Displays:**
- BERTopic Quality Metrics line chart: C_v EN and C_v SO across training runs
- Three-way comparison table: LDA, NMF, BERTopic — columns: Model, Language, C_v, U_Mass, Diversity, K — winner highlighted with a star
- English and Somali topic lists side by side

---

### FILE 32: dashboard/src/pages/History.jsx
**Role:** Historical trend browser. Shows a table of all past detected trends with date, language, and score.

- Fetches `getHistory('en', dateParams)` + `getHistory('so', dateParams)`, combines, sorts by timestamp desc.
- Summary cards: total fetched, average score, top trending topic name.
- Expandable rows showing `representative_docs`.

---

### FILE 33: dashboard/src/pages/Tweets.jsx
**Role:** Raw tweet browser. Shows live-refreshing table of collected tweets.

- Fetches `getRawTweets(lang, dateParams, 50)` per language. Auto-refreshes every 15 seconds via `setInterval`.
- Displays: tweet text, language badge, timestamp.

---

### FILE 34: dashboard/src/pages/Export.jsx
**Role:** Data export with preview table, paginated (page size 20).

- Fetches `getHistory()` for both languages combined.
- **CSV export:** Builds CSV in-browser with headers: Rank, Topic Label, Keywords, Language, Score, Volume, Period. Creates a download link via `data:text/csv` URI.
- **PDF export:** Generates a full HTML page with print styles and `window.print()` auto-triggered in a new tab.

---

### FILE 35: dashboard/src/pages/Profile.jsx
**Role:** User profile and quick preferences card.

- Shows username/email from `AuthContext.user`.
- Quick toggles for language preference and theme.
- Sign out button calls `logout()` then navigates to `/login`.

---

### FILE 36: dashboard/src/pages/Setting.jsx
**Role:** Full settings page with modals for password change, 2FA, notifications, and about.

- Loads 2FA status and notification preferences on mount via `get2FAStatus()` and `getPreferences()`.
- **Password modal:** form → `changePassword(currentPassword, newPassword)` → `POST /auth/change-password`.
- **2FA modal:** "Enable" → sends code via `request2FACode()` → shows input → verifies via `verify2FACode()`. "Disable" → confirm dialog → `disable2FA()`.
- **Notifications modal:** toggle Email Digests and Spike Alerts; each toggle immediately calls `updatePreferences()`.
- **About modal:** Shows system name, developers (Vision Tech Team), institution (Jamhuriya University of Science and Technology).

---

### FILE 37: dashboard/src/contexts/AuthContext.jsx
**Role:** Provides JWT token and user state globally. Persists token in `localStorage`.

- On mount: reads `token` from localStorage, decodes JWT client-side (`decodeJWT` — pure base64 decode, no signature verification), extracts `sub` claim as username.
- `login()`: calls `loginUser()`, stores token and decoded user in state + localStorage.
- `googleLogin()`: calls `loginWithGoogle()`, same pattern.
- `logout()`: clears token and user from state + localStorage.
- Context value exports: `user`, `token`, `isAuthenticated` (`!!token`), `isLoading`, `login`, `signup`, `googleLogin`, `logout`, `changePassword`, plus all 2FA and preference API functions (proxied from `api.js`).

---

**Total: 37 files documented.**

---

## PHASE 3 — END-TO-END DATA FLOW + CONFIG FACTS

---

### SECTION A — END-TO-END DATA FLOW WALKTHROUGH

This is the complete lifecycle of data: from a tweet being posted on Twitter to a user seeing it displayed as a trend on the dashboard.

---

#### STEP 1 — Twitter Ingestion (runs every 15 minutes)

**File:** `api/app/main.py` → `periodic_data_collection_loop(app)`

Every 15 minutes (`asyncio.sleep(15 * 60)`) the ingestion loop wakes up.

1. It checks `app.state.session_ingested_count` against `app.state.max_quota_limit` (hardcoded 1000). If the limit is reached, the loop does a hard `break` and **stops permanently** for this server session.
2. It calculates `remaining = max_quota_limit - session_ingested_count` and then `limit_per_query = max(1, min(50, remaining // len(queries)))`. This dynamically reduces how many tweets are requested per query as the quota runs low.
3. It calls `run_data_collection_pipeline(collector, queries, limit_per_query)` from `api/services/data_collection.py`.
   - Inside `fetch_recent_tweets()`: Tweepy's `client.search_recent_tweets()` is called via `asyncio.get_event_loop().run_in_executor()` — the blocking HTTP call runs in a thread pool so it does not block the FastAPI event loop.
   - For each returned tweet: `ingest_tweet()` builds the MongoDB document `{id, text, lang_api, created_at, collected_at, retweet_count, like_count}` and inserts it into the `raw_tweets` collection. If the tweet `id` already exists (MongoDB unique index), the `DuplicateKeyError` is silently caught — no crash, no double-count.
4. After ingestion, the loop counts tweets newer than `pipeline_state.last_trained_tweet_collected_at`. If `new_count >= BERTOPIC_NEW_TWEETS_THRESHOLD` (env default 500), it calls `run_deployed_pipeline()` from `api/jobs/deployment.py` to retrain the winner on fresh data.

**Output of Step 1:** New tweet documents in `raw_tweets`. Possible model retraining side-effect.

---

#### STEP 2 — One-Time Academic Evaluation (runs once at startup, then exits)

**File:** `api/app/main.py` → `periodic_model_comparison_loop()`

This loop starts after a 300-second delay (5 minutes after startup). Its job is to do the one-time three-model competition and pick the winner.

1. It calls `get_deployed_model()` from `api/jobs/deployment.py`. If a winner already exists in `pipeline_state`, the loop returns immediately and **never runs again**.
2. If no winner: it calls `run_full_evaluation()` from `api/jobs/evaluation_pipeline.py`.

**Inside `run_full_evaluation()` (`api/jobs/evaluation_pipeline.py`):**

a. **Corpus load:** `load_tweet_corpus(lang=None, limit=CORPUS_LIMIT)` from `api/pipelines/corpus_loader.py` queries `raw_tweets`, sorts newest-first, returns a pandas DataFrame with columns `{text, lang_api, like_count, retweet_count, created_at, collected_at}`.

b. **Language split:** DataFrame is split into `df_en` (rows where `lang_api=="en"`) and `df_so` (rows where `lang_api=="so"`). Minimum 50 documents per language is required to train.

c. **Tokenization (shared):** `_tokenize_corpus(df_en)` and `_tokenize_corpus(df_so)` from `api/jobs/lda_pipeline.py` apply `preprocess_lda(text, lang)` from `api/services/lda_model.py`:
   - Lowercase → remove URLs/mentions → remove punctuation → NLTK tokenize → remove stopwords (English or Somali) → drop tokens with length ≤ 2.

d. **LDA training — English and Somali separately:**
   - `prepare_lda_matrices(tokenized_docs)` in `api/services/lda_model.py` builds a gensim `Dictionary` (filters: no_below=2, no_above=0.95) and a Bag-of-Words corpus.
   - If `LDA_GRID_SEARCH=true`: sweeps K ∈ {4, 5, 6, 7, 8, 9, 10, 11, 12}, alpha=symmetric, beta=symmetric. Best K = highest C_v, ties broken by smaller K (Occam's razor).
   - Trains `LdaModel(random_state=42, passes=10)`.

e. **NMF training — English and Somali separately:**
   - Imports `_tokenize_corpus` from `lda_pipeline` (identical tokenization — not duplicated).
   - `prepare_nmf_matrix(tokenized_docs, dictionary)` in `api/services/nmf_model.py` builds a TF-IDF matrix using `sklearn.TfidfVectorizer` restricted to the EXACT SAME gensim Dictionary vocabulary as LDA. This is the fairness guarantee: LDA and NMF differ only in weighting (BoW vs TF-IDF) and decomposition, not vocabulary.
   - If `LDA_GRID_SEARCH=true`: sweeps same K range {4..12}.
   - Trains `NMF(init="nndsvda", max_iter=400, random_state=42)`.

f. **BERTopic training — English and Somali separately:**
   - `preprocess_bertopic(df)` in `api/services/bertopic_model.py` does ONLY dedup + strip. No stopword removal, no tokenization — SentenceTransformer needs full sentences.
   - Creates `BERTopicTrainer` with:
     - `SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")` encodes all docs into dense 384-dim vectors.
     - `UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)` reduces to 5 dimensions.
     - `HDBSCAN(min_cluster_size=adaptive, metric="euclidean", cluster_selection_method="eom")` clusters.
     - `CountVectorizer(stop_words=combined_stopwords)` + c-TF-IDF extracts representative keywords per cluster.
   - BERTopic's K is NOT set manually — it is determined entirely by HDBSCAN cluster density. Tweets that don't fit any cluster become "outlier" topic -1 (excluded from results).

g. **Shared evaluation (same yardstick for all three):**
   - `build_reference_corpora(df)` and `build_reference_dictionary(reference_corpora)` in `api/services/evaluation.py` build one common tokenized reference and one common gensim Dictionary.
   - `evaluate_model(model_name, topics, num_topics, reference_corpora, dictionary)` scores each model in TWO language slices (en, so). For each language slice:
     - `_filter_topics_to_vocab(topics, slice_dictionary)` drops words not in that language's reference vocab (prevents NaN from cross-lingual PMI in C_v scoring).
     - For BERTopic: `get_bertopic_topics()` normalizes keywords to lowercase alpha-only (matching preprocess_lda form) before coherence scoring, so BERTopic is not systematically disadvantaged.
     - `compute_coherence(topics, tokenized_docs, dictionary)` computes C_v (primary) and U_Mass (supporting). All `CoherenceModel` calls use `processes=1` to prevent Windows multiprocessing deadlock.
     - `calculate_topic_diversity(topics)` computes unique_words / total_words across all topics' top-10 keywords.
   - Returns list of rows: `{model, language, c_v, u_mass, diversity, K}` — one row per model-language combination, "combined" excluded.

h. **Metrics saved:** `save_metrics_table(rows, metrics_dir)` in `evaluation.py` writes `results/metrics/coherence_diversity.json` and `.csv`.

i. **Winner selection (`_select_winner_from_metrics(rows)` in `api/jobs/model_comparison.py`):**
   - Primary: highest English C_v wins.
   - First tiebreak: highest Somali C_v.
   - Second tiebreak: highest English Topic Diversity.
   - Never picks a winner if rows are empty.

j. **Winner persisted:** `persist_deployed_model(winner)` in `api/jobs/deployment.py` upserts `{pipeline: "deployed_model", model: winner_name, set_at: now}` into `pipeline_state`.

k. **Comparison report synced:** `run_model_comparison()` in `api/jobs/model_comparison.py` reads the metrics file, rebuilds the report dict, saves to `reports/comparison/latest_comparison.json`, and updates `pipeline_state` with `pipeline="model_comparison"`.

3. After the winner is picked, `periodic_model_comparison_loop()` calls `run_deployed_pipeline()` to do the first production training run with the winner, then **returns permanently**.

**Output of Step 2:** Winner name stored in `pipeline_state`. Comparison report JSON on disk. First batch of production topics in `detected_trends`.

---

#### STEP 3 — Production Model Retraining (triggered incrementally)

**File:** `api/jobs/deployment.py` → `run_deployed_pipeline()`

This is called from two places:
- After initial winner selection (Step 2 above)
- After each ingestion cycle, if enough new tweets have arrived (Step 1)

`run_deployed_pipeline()` reads the deployed model name and routes:
- `model == "bertopic"` → calls `run_bertopic_pipeline()` in `api/jobs/bertopic_pipeline.py`
- `model == "lda"` → calls `_run_lda_deployment()` in `deployment.py`
- `model == "nmf"` → calls `_run_nmf_deployment()` in `deployment.py`

**BERTopic production path (`api/jobs/bertopic_pipeline.py` → `run_bertopic_pipeline()`):**

1. Checks if there are at least `BERTOPIC_NEW_TWEETS_THRESHOLD` (default 500) new tweets since `last_trained_tweet_collected_at`. Skips if not (unless `detected_trends` is empty — forces training on first run).
2. `load_tweet_corpus(lang=None, limit=CORPUS_LIMIT=2000)` via corpus_loader.
3. `preprocess_bertopic(df)` — dedup + strip only.
4. Saves clean corpus CSV to `reports/bertopic/latest_clean_corpus.csv`.
5. Splits df into df_en and df_so (min 50 per language).
6. `_adaptive_min_cluster_size(n_docs)` = `max(3, min(10, n_docs // 5))` — scales HDBSCAN cluster sensitivity.
7. `_run_training_sync(df_clean, min_cluster_size)` runs BERTopicTrainer.train() in a thread pool (blocking call, keeps event loop free).
8. `_build_trend_documents(df_clean, trainer, topics, calculated_at)`:
   - For each non-outlier topic in `topic_model.get_topic_info()`:
     - Identifies which tweet docs belong to this topic.
     - For each of the top-3 keywords: searches this topic's tweets for ones containing that keyword, sorts by engagement (likes + retweets), takes the best as a representative document. URL-strips and deduplicates to max 3 representative docs.
     - `langs` = list of `lang_api` values from all docs in this topic.
     - `assign_topic_lang(langs)` → 70% majority rule → "en" or "so".
     - `compute_trend_score(doc_count, total_likes, total_retweets, corpus_max_engagement)` → 0–100 score.
     - Generates `peak_at` (median of `collected_at` timestamps), `tweet_period_from`, `tweet_period_to`.
   - Sorts all topics by `trend_score` descending.
9. `_persist_trends(trend_docs, ...)`:
   - `detected_trends.insert_many(trend_docs)`.
   - Upserts `pipeline_state` for `pipeline="bertopic"` (storing metrics, previous metrics, timestamp).
   - Inserts row into `pipeline_history`.
10. `deduplicate_existing_trends()` removes any duplicate (Name, calculated_at) combos.
11. `check_and_send_spike_alerts()` from `api/services/notifications.py`:
    - Gets last two batches from `detected_trends`.
    - For each trend: if `trend_score` increased ≥ 25% vs previous batch, or if it's a brand-new topic with score ≥ 50 → marks as spike.
    - Sends `send_spike_alert()` to all users with `spike_alerts=True`.

**LDA/NMF deployment paths (`api/jobs/deployment.py`):**
- Same incremental threshold check.
- Same corpus load.
- Same tokenization as evaluation (via `_tokenize_corpus`).
- After training: builds `detected_trends` documents in the SAME schema as BERTopic (same field names), so the frontend API does not need to know which model won.
- `_persist_trend_docs(trend_docs, calculated_at, model_name)` does a **full replacement**: `delete_many({"model": model_name})` then `insert_many(trend_docs)`.

**Output of Step 3:** Fresh set of `detected_trends` documents for the winning model, with all trend metadata. `pipeline_state` updated. Spike alert emails triggered.

---

#### STEP 4 — Frontend Request → API Response

**Files:** `dashboard/src/services/api.js` → `api/app/routes.py`

When a user opens the Dashboard page:

1. React mounts `Dashboard.jsx`. On mount, `useEffect` fires four parallel fetches:
   - `getTweetStats(dateParams)` → `GET /tweets/stats?from_date=...&to_date=...`
   - `getTrends('en', dateParams)` → `GET /trends?lang=en&limit=50&from_date=...&to_date=...`
   - `getTrends('so', dateParams)` → `GET /trends?lang=so&limit=50&...`
   - `getTrendingKeywords(dateParams)` → `GET /trends/keywords?...`

2. Each Axios request passes through the request interceptor in `api.js` which attaches `Authorization: Bearer <token>` from `localStorage`.

3. The route handler for `GET /trends` in `routes.py`:
   a. Resolves the date range from `from_date` / `to_date` query params via `_parse_iso_datetime()`.
   b. Calls `get_deployed_model()` to get the winner model name.
   c. Queries `detected_trends` with filter `{model: winner, lang: {$in: [requested_lang, "both"]}}` plus optional date filter on `calculated_at`.
   d. Groups results by the "latest batch" (`calculated_at` max).
   e. **Deduplicates** by stripping the numeric prefix from `Name` (e.g., `"0_war_ukraine"` → `"war_ukraine"`), keeping highest-score duplicate.
   f. For each trend: calls `adapt_trend_to_frontend(t, requested_lang)` which:
      - Maps `Name` → `topic_name` (cleaned label via `get_clean_topic_name()`)
      - Maps `Representation` → `top_keywords` (list of strings)
      - Maps `trend_score` → `score`
      - `_dedup_docs()` → de-duplicates `representative_docs` by URL-stripped text comparison → max 3 docs
   g. Returns JSON array sorted by `score` descending.

4. React receives the JSON, merges EN and SO trends, renders:
   - Horizontal bar chart of top 8 topics (Recharts `BarChart`)
   - Word cloud scaled by keyword frequency
   - Language distribution donut (Recharts `PieChart`)
   - Four stat cards (total tweets, English, Somali, trending topics count)

5. **Date filter interactions:** The global `DateRangeContext` (preset 24h/7d/30d or custom) converts via `rangeToQueryParams()` in `dateRange.js` to ISO string `from_date`/`to_date` params, which are passed to every API call.

6. **Language toggle:** `LanguageContext` switches the `lang` parameter sent to `getTrends()`. The frontend always requests one language at a time; both EN and SO are fetched in parallel and displayed side by side (e.g., on Comparison page).

7. **Tweets page auto-refresh:** `Tweets.jsx` sets up `setInterval(..., 15000)` on mount to re-call `getRawTweets()` every 15 seconds.

**Output of Step 4:** Rendered React dashboard with live topic data.

---

#### STEP 5 — Email Notification Loop (every 24 hours)

**File:** `api/app/main.py` → `periodic_email_digest_loop()` → `api/services/notifications.py` → `send_daily_digests()`

After the initial 300-second startup delay, every `DIGEST_INTERVAL_HOURS` (default 24) hours:
1. `send_daily_digests()` queries `detected_trends` for the latest batch (most recent `calculated_at`).
2. Takes top 10 trends by `trend_score`.
3. For each user with `email_digests=True`: calls `send_email_digest(email, trends)` → `_send_email()` in `api/services/email.py`.
4. If `SMTP_ENABLED=false` (default): prints email content to console instead of sending.
5. If SMTP configured: runs `_send_smtp_sync()` in a thread via `asyncio.to_thread()`.

Separately, spike alerts fire inside each BERTopic training run (Step 3), not on a timer.

---

### SECTION B — COMPLETE ENVIRONMENT VARIABLE REFERENCE

Format: `VAR_NAME` | file where read | env default | what it controls

---

#### Database & Connection

| Variable | File | Default | Controls |
|---|---|---|---|
| `MONGODB_URL` | `api/db/connection.py` | `"mongodb://localhost:27017/"` | Full MongoDB connection string including host, port, auth |
| `DATABASE_NAME` | `api/db/connection.py` | `"trending_topics_db"` | Which MongoDB database to use (test suite overrides to `trending_topics_test`) |

---

#### Authentication

| Variable | File | Default | Controls |
|---|---|---|---|
| `SECRET_KEY` | `api/services/auth.py` | `"your_super_secret_key_here"` | JWT signing secret — MUST be changed in production; anyone who knows this can forge tokens |
| `ALGORITHM` | `api/services/auth.py` | `"HS256"` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `api/services/auth.py` | `"30"` | How long JWT tokens remain valid (in minutes) |

---

#### Twitter Data Collection

| Variable | File | Default | Controls |
|---|---|---|---|
| `TWITTER_BEARER_TOKEN` | `api/services/data_collection.py` | None (required) | Tweepy v2 Bearer Token for `search_recent_tweets`. Without this, ingestion loop cannot call the API |

---

#### BERTopic Pipeline

| Variable | File | Default | Controls |
|---|---|---|---|
| `BERTOPIC_MIN_CORPUS_SIZE` | `api/jobs/bertopic_pipeline.py`, `api/services/monitoring.py` | `"1000"` | Minimum number of tweets required before BERTopic will train |
| `BERTOPIC_CORPUS_LIMIT` | `api/jobs/bertopic_pipeline.py` | `"2000"` | Maximum tweets loaded per BERTopic training run |
| `BERTOPIC_NEW_TWEETS_THRESHOLD` | `api/jobs/bertopic_pipeline.py`, `api/app/main.py` | `"500"` | Minimum number of new tweets (since last training) required to trigger BERTopic retraining |
| `BERTOPIC_TRAIN_INTERVAL_MINUTES` | `api/app/main.py` | `"30"` | Retry interval (minutes) for the evaluation loop when corpus is still insufficient |
| `BERTOPIC_OUTLIER_WARN_RATIO` | `api/services/monitoring.py` | `"0.35"` | If the fraction of tweets assigned to outlier topic -1 exceeds this, `/health` raises a warning |

---

#### LDA Pipeline

| Variable | File | Default | Controls |
|---|---|---|---|
| `LDA_MIN_CORPUS_SIZE` | `api/jobs/lda_pipeline.py`, `api/services/monitoring.py` | `"1000"` | Minimum tweets for LDA training |
| `LDA_CORPUS_LIMIT` | `api/jobs/lda_pipeline.py` | `"2000"` | Maximum tweets loaded per LDA run |
| `LDA_GRID_SEARCH` | `api/jobs/lda_pipeline.py`, `api/jobs/nmf_pipeline.py` | `"true"` | Whether to sweep K ∈ {4..12} to find best number of topics. If false, K is estimated heuristically as `max(3, min(10, n_docs // 15))` |
| `LDA_NEW_TWEETS_THRESHOLD` | `api/jobs/lda_pipeline.py`, `api/jobs/nmf_pipeline.py` | `"1000"` | Minimum new tweets to trigger LDA/NMF retraining (NMF deliberately reuses this same variable) |

---

#### Evaluation Pipeline

| Variable | File | Default | Controls |
|---|---|---|---|
| `EVAL_NEW_TWEETS_THRESHOLD` | `api/jobs/evaluation_pipeline.py` | Same as `BERTOPIC_MIN_CORPUS_SIZE` = `"1000"` | Minimum new tweets since last evaluation attempt before the three-model evaluation will run again |

---

#### Deployment

| Variable | File | Default | Controls |
|---|---|---|---|
| `DEPLOYED_MODEL_RETRAIN_THRESHOLD` | `api/jobs/deployment.py` | `"500"` | Minimum new tweets to trigger retraining of the currently deployed winning model |

---

#### Email / SMTP

| Variable | File | Default | Controls |
|---|---|---|---|
| `SMTP_ENABLED` | `api/services/email.py` | `"false"` | If `"false"` (default), emails are printed to console — safe for development with no SMTP server |
| `SMTP_HOST` | `api/services/email.py` | None | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | `api/services/email.py` | `587` | SMTP port (587 for STARTTLS, 465 for SSL) |
| `SMTP_USER` | `api/services/email.py` | None | SMTP authentication username |
| `SMTP_PASSWORD` | `api/services/email.py` | None | SMTP authentication password |
| `SMTP_FROM` | `api/services/email.py` | None | Sender address shown in sent emails |
| `SMTP_USE_TLS` | `api/services/email.py` | `"true"` | Whether to use STARTTLS. If `"false"`, connects plain or uses direct SSL depending on port |

---

#### Notifications

| Variable | File | Default | Controls |
|---|---|---|---|
| `SPIKE_THRESHOLD_PCT` | `api/services/notifications.py` | `"25"` | A topic whose trend_score rises ≥ 25% between two consecutive batches triggers a spike alert email to subscribed users |
| `DIGEST_INTERVAL_HOURS` | `api/app/main.py` | `"24"` | How often (hours) the email digest loop sends daily digests |

---

### SECTION C — COMPLETE API ENDPOINT REFERENCE

All endpoints are served by `api/app/routes.py` mounted at the root of the FastAPI app.
"Auth required" = JWT Bearer token must be present in `Authorization` header.

---

#### Authentication Endpoints

| Method | Path | Auth Required | Request Body / Params | Returns |
|---|---|---|---|---|
| `POST` | `/auth/signup` | No | JSON `{username, email, password}` | `{message, username}` |
| `POST` | `/auth/login` | No | Form `username, password` (OAuth2PasswordRequestForm) | `{access_token, token_type: "bearer"}` |
| `POST` | `/auth/google` | No | JSON `{credential}` (Google JWT string) | `{access_token, token_type: "bearer"}` |
| `POST` | `/auth/change-password` | Yes | JSON `{current_password, new_password}` | `{message}` |
| `GET` | `/auth/2fa/status` | Yes | — | `{two_factor_enabled: bool}` |
| `POST` | `/auth/2fa/send-code` | Yes | — | `{message}` (sends 6-digit code to user's email) |
| `POST` | `/auth/2fa/verify` | Yes | JSON `{code}` | `{message}` (enables 2FA if code matches and not expired) |
| `POST` | `/auth/2fa/disable` | Yes | — | `{message}` |
| `GET` | `/auth/preferences` | Yes | — | `{email_digests: bool, spike_alerts: bool}` |
| `POST` | `/auth/preferences` | Yes | JSON `{email_digests?, spike_alerts?}` | `{message}` |

---

#### Data Endpoints

| Method | Path | Auth Required | Query Params | Reads | Returns |
|---|---|---|---|---|---|
| `GET` | `/trends` | No | `lang`, `limit` (default 50), `from_date`, `to_date` | `detected_trends`, `pipeline_state` | List of adapted trend objects (topic_name, top_keywords, score, representative_docs, lang, volume, trend_score, calculated_at) |
| `GET` | `/history` | No | `lang`, `topic_name`, `limit`, `from_date`, `to_date` | `detected_trends` | Historical trend list, filtered by date range on `peak_at` and optional topic_name regex |
| `POST` | `/filter` | No | `keyword`, `lang` | `detected_trends` | Trends where any keyword in `Representation` matches the regex |
| `GET` | `/raw_tweets` | No | `lang`, `limit` (default 50), `from_date`, `to_date` | `raw_tweets` | Raw tweet documents |
| `GET` | `/tweets/stats` | No | `from_date`, `to_date` | `raw_tweets` | `{total, english, somali}` counts |
| `GET` | `/trends/topics_over_time` | No | `from_date`, `to_date` | `detected_trends` | Daily category volume time series, top 5 categories (Security/Politics/AI/Economy/Sports/Health/Education/Technology/Climate/Other) |
| `GET` | `/trends/keywords` | No | `from_date`, `to_date` | `raw_tweets` (up to 1000 tweets) | Top 30 word frequency pairs `[{word, count}]` |

---

#### System Health & Model Endpoints

| Method | Path | Auth Required | Params | Reads | Returns |
|---|---|---|---|---|---|
| `GET` | `/health` | No | — | `raw_tweets`, `pipeline_state`, `detected_trends` | System status snapshot + alert list from `collect_system_status()` |
| `GET` | `/models/comparison` | No | — | `pipeline_state`, `reports/comparison/latest_comparison.json` | Three-way comparison report (LDA/NMF/BERTopic × en/so × metrics) |
| `GET` | `/models/winner` | No | — | `pipeline_state` | `{model, set_at, winner_selection_basis}` |
| `GET` | `/models/status` | No | — | `pipeline_state`, `pipeline_history`, `detected_trends` | Rich status object: deployed model, latest metrics, delta since evaluation, training history summary |
| `GET` | `/models/history` | No | `limit`, `from_date`, `to_date` | `pipeline_history` | List of historical training run records (trained_at, c_v_en, c_v_so, num_topics, model) |
| `GET` | `/visualizations/{model}` | No | Path: `model` (`"bertopic"` or `"lda"`) | `api/artifacts/visualizations/` | HTML file (BERTopic intertopic distance map or pyLDAvis) served as `text/html` |

---

#### Job Trigger Endpoints (all require authentication)

| Method | Path | What it triggers | Side effects |
|---|---|---|---|
| `POST` | `/jobs/train-bertopic` | `run_bertopic_pipeline()` | Trains BERTopic, writes to `detected_trends`, updates `pipeline_state` |
| `POST` | `/jobs/train-lda` | `run_lda_pipeline()` | Trains LDA (baseline only), writes to `reports/lda/`, updates `pipeline_state` |
| `POST` | `/jobs/train-nmf` | `run_nmf_pipeline()` | Trains NMF (baseline only), writes to `reports/nmf/`, updates `pipeline_state` |
| `POST` | `/jobs/run-deployment` | `run_deployed_pipeline()` | Retrains the currently deployed winner, replaces `detected_trends` for that model |
| `POST` | `/jobs/run-comparison` | `run_model_comparison()` | Reads saved metrics, rebuilds comparison report, updates `pipeline_state` |
| `POST` | `/jobs/run-evaluation` | `run_full_evaluation(force=...)` | Trains all 3 models, evaluates, picks winner, persists deployed model — full 3-way evaluation |
| `POST` | `/jobs/send-digests` | `send_daily_digests()` | Sends daily email digests to subscribed users |

---

### SECTION D — ALL BACKGROUND LOOPS

**Location:** `api/app/main.py` → `lifespan(app)` async context manager.

All loops are launched as `asyncio.create_task()` inside `lifespan()` and cancelled on server shutdown. They are NOT separate processes — they run as coroutines on the single FastAPI event loop.

---

#### Loop 1 — Data Collection Loop

- **Function:** `periodic_data_collection_loop(app)`
- **Starts:** Immediately on startup (after MongoDB connection verified)
- **Interval:** Every 15 minutes (`asyncio.sleep(15 * 60)`)
- **Termination condition:** Permanently stops when `session_ingested_count >= max_quota_limit (1000)`. This is a hard session limit — requires server restart to resume.
- **What it does each cycle:**
  1. Checks quota
  2. Calls `run_data_collection_pipeline()` → Tweepy → `raw_tweets`
  3. After ingestion, checks whether to trigger deployed model retraining (based on `BERTOPIC_NEW_TWEETS_THRESHOLD`)

---

#### Loop 2 — Model Evaluation Loop

- **Function:** `periodic_model_comparison_loop()`
- **Starts:** 300 seconds after server startup (to allow DB and data ingestion to settle)
- **Interval:** Retries every `BERTOPIC_TRAIN_INTERVAL_MINUTES` (default 30 minutes) ONLY if data is insufficient
- **Termination condition:** Exits permanently after the first successful evaluation AND winner selection. If a winner already exists on startup, exits immediately without evaluating.
- **What it does:**
  1. Checks if winner already deployed → exits if yes
  2. Calls `run_full_evaluation()` → trains all 3 models → selects winner → calls `run_deployed_pipeline()` → exits
  3. If data insufficient: waits 30 minutes and tries again (will keep retrying until enough data exists)

---

#### Loop 3 — Email Digest Loop

- **Function:** `periodic_email_digest_loop()`
- **Starts:** 300 seconds after server startup
- **Interval:** Every `DIGEST_INTERVAL_HOURS` (default 24) hours
- **Termination condition:** Never terminates (runs for the lifetime of the server session)
- **What it does each cycle:**
  1. Calls `send_daily_digests()` → fetches top 10 trends from latest batch
  2. Sends digest email (or logs to console if SMTP disabled) to all users with `email_digests=True`

---

#### Non-loop: Spike Alerts

- **Not a loop** — triggered at the end of every BERTopic training run (inside `run_bertopic_pipeline()` and LDA/NMF deployment paths)
- **Function:** `check_and_send_spike_alerts()` in `api/services/notifications.py`
- **Trigger:** Any time a model training completes and topics are written to `detected_trends`
- **What it does:** Compares current batch trend scores to previous batch. If any trend rose ≥ 25% or is brand-new with score ≥ 50, sends spike alert to all users with `spike_alerts=True`.

---

### SECTION E — MONGODB COLLECTIONS REFERENCE

| Collection | Key fields | Unique index | Purpose |
|---|---|---|---|
| `raw_tweets` | `id`, `text`, `lang_api`, `created_at`, `collected_at`, `like_count`, `retweet_count` | `id` | Raw ingested tweets from Tweepy |
| `detected_trends` | `Name`, `Representation`, `trend_score`, `lang`, `calculated_at`, `model`, `representative_docs`, `volume`, `peak_at`, `tweet_period_from`, `tweet_period_to` | None | Topic modeling output — one document per detected topic per training run |
| `pipeline_state` | `pipeline`, `model`, `metrics`, `prev_metrics`, `last_trained_tweet_collected_at`, `last_evaluated_at` | `pipeline` | One document per named pipeline ("bertopic", "lda", "nmf", "model_comparison", "deployed_model", "notifications") |
| `pipeline_history` | `pipeline`, `trained_at`, `c_v_en`, `c_v_so`, `num_topics_en`, `num_topics_so` | None | Audit trail of every training run — used by `/models/history` and the Comparison page quality chart |
| `topic_evolution` | `topic_id`, `name`, `timestamps`, `frequencies`, `stored_at` | None | Dynamic Topic Modeling time series from BERTopic's `topics_over_time()` |
| `users` | `username`, `email`, `hashed_password`, `two_factor_enabled`, `two_factor_code`, `two_factor_expires`, `email_digests`, `spike_alerts` | `username`, `email` | User accounts; 2FA codes stored inline with 10-minute expiry |
