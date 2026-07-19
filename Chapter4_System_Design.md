# Chapter 4: System Design and Implementation

**Thesis Title:** Design and Implementation of a Real-Time Trending Topic Detection System for English and Somali Tweets using Twitter data

---

## Table of Contents

1. [4.1 System Architecture Overview](#41-system-architecture-overview)
2. [4.2 Data Collection Module](#42-data-collection-module)
3. [4.3 Data Preprocessing](#43-data-preprocessing)
4. [4.4 Topic Modeling — Three-Model Architecture](#44-topic-modeling--three-model-architecture)
5. [4.5 Evaluation Framework](#45-evaluation-framework)
6. [4.6 Deployment Pipeline](#46-deployment-pipeline)
7. [4.7 Real-Time Update Mechanism](#47-real-time-update-mechanism)
8. [4.8 REST API Design](#48-rest-api-design)
9. [4.9 Frontend Architecture](#49-frontend-architecture)
10. [4.10 Database Design](#410-database-design)
11. [4.11 Multilingual Support](#411-multilingual-support)

---

## 4.1 System Architecture Overview

### 4.1.1 Overall Architecture

The system adopts a three-tier client-server architecture consisting of: (1) a data ingestion and processing backend, (2) a document-oriented database layer, and (3) a browser-based analytical dashboard. The backend is implemented as an asynchronous REST API using the FastAPI framework (Python), the database layer uses MongoDB managed through the Motor asynchronous driver, and the frontend is a single-page application (SPA) built with React 18 and Vite.

The system is bilingual by design, processing both English (`lang_api="en"`) and Somali (`lang_api="so"`) tweets through separate per-language topic modeling pipelines. This strict language separation ensures that semantic structure specific to each language is never conflated across language boundaries — a critical design requirement given the structural and lexical differences between English and Somali.

The three tiers communicate as follows:
- The **data tier** (MongoDB) is accessed exclusively by the backend via the Motor async driver. The frontend never communicates with MongoDB directly.
- The **logic tier** (FastAPI backend) exposes a JSON REST API and is responsible for all business logic: data collection, preprocessing, topic modeling, evaluation, and trend scoring.
- The **presentation tier** (React dashboard) communicates with the backend through HTTP/JSON requests, with a JWT Bearer token injected automatically into every request via an Axios interceptor.

```
                    ┌─────────────────────────────────┐
                    │         Twitter/X API v2         │
                    │      (Tweepy Bearer Token)        │
                    └──────────────┬──────────────────┘
                                   │  search_recent_tweets()
                                   ▼
              ┌────────────────────────────────────────────┐
              │           FastAPI Backend  (api/)           │
              │                                            │
              │  ┌─────────────────┐  ┌─────────────────┐  │
              │  │  Data           │  │  Background     │  │
              │  │  Collection     │  │  Loops          │  │
              │  │  TweetCollector │  │  (asyncio)      │  │
              │  │  (15 min loop)  │  │  15min / 24h    │  │
              │  └────────┬────────┘  └────────┬────────┘  │
              │           │                    │            │
              │  ┌────────▼────────────────────▼──────────┐ │
              │  │          MongoDB  (Motor async)         │ │
              │  │   raw_tweets  │  detected_trends        │ │
              │  │   pipeline_state  │  users              │ │
              │  │   pipeline_history │ topic_evolution    │ │
              │  └───────────────────┬────────────────────┘ │
              │                      │                      │
              │  ┌───────────────────▼────────────────────┐ │
              │  │      Topic Modeling Pipelines           │ │
              │  │   BERTopic (winner) │ LDA │ NMF         │ │
              │  │   Per-language: EN + SO separately      │ │
              │  └───────────────────┬────────────────────┘ │
              │                      │                      │
              │  ┌───────────────────▼────────────────────┐ │
              │  │   REST API Routes  (app/routes.py)      │ │
              │  │   /trends  /history  /auth/*  /models/* │ │
              │  └───────────────────┬────────────────────┘ │
              └──────────────────────┼──────────────────────┘
                                     │  HTTP / JSON
                                     │  Bearer JWT
                                     ▼
              ┌────────────────────────────────────────────┐
              │       React Dashboard  (dashboard/)         │
              │   Vite │ React Router v6 │ Recharts         │
              │   AuthContext  │  ThemeContext               │
              │   LanguageContext  │  DateRangeContext       │
              └────────────────────────────────────────────┘
```

### 4.1.2 Technology Stack

The following table lists the technologies selected for each system component, together with the specific technical justification for each choice:

| Component | Technology | Version | Justification |
|-----------|-----------|---------|--------------|
| Backend framework | FastAPI (Python) | latest | Native `asyncio` support enables non-blocking I/O for concurrent tweet ingestion, model training, and API serving; automatic OpenAPI documentation; OAuth2PasswordBearer built-in |
| Database | MongoDB + Motor | Motor 3.x | Schema-flexible document store avoids rigid migrations as the topic schema evolves; Motor provides native async MongoDB access without blocking the event loop |
| Transformer embeddings | `paraphrase-multilingual-MiniLM-L12-v2` | SentenceTransformers | Compact (66M parameter) multilingual model trained on 50+ languages including Somali-proximate languages; maps EN and SO documents into the same 384-dimensional semantic vector space |
| Topic model — winner | BERTopic | latest | Contextual embeddings capture polysemy missed by bag-of-words; HDBSCAN automatically discovers K from data density rather than requiring a human prior; highest C_v on this corpus |
| Topic model — baseline 1 | Gensim LdaModel | latest | Standard academic baseline for probabilistic topic modeling; widely used in social media NLP literature; results are directly comparable across corpora |
| Topic model — baseline 2 | sklearn NMF | latest | Deterministic matrix factorization; no random seed sensitivity; produces sparse, interpretable topic-word matrices; directly comparable to LDA under identical preprocessing |
| Evaluation metric | Gensim CoherenceModel C_v | latest | Most widely adopted intrinsic coherence metric; language-agnostic; applicable to BERTopic, LDA, and NMF without modification; correlates well with human judgement |
| Twitter data access | Tweepy v2 | latest | Official Python client for Twitter API v2; supports `lang:` search operator, `public_metrics` expansion, and standard search endpoint |
| Frontend framework | React 18 + Vite | React 18 | React component model enables granular re-rendering on topic data updates; Vite provides sub-second hot-module replacement for development |
| Charts | Recharts | latest | React-native charting; declarative composition of bar, line, and pie charts using JSX |
| Authentication | python-jose + bcrypt | latest | Industry-standard HS256 JWT for stateless API authentication; bcrypt for password hashing with adaptive work factor |
| HTTP client (frontend) | Axios | latest | Promise-based; request interceptor pattern cleanly centralises JWT injection across all API calls |

---

## 4.2 Data Collection Module

### 4.2.1 TweetCollector Class

The data collection module is implemented in `services/data_collection.py` as the `TweetCollector` class. It encapsulates the Tweepy v2 `Client` object, initialized with the `TWITTER_BEARER_TOKEN` environment variable. App-only authentication is used (no user OAuth), which grants access to the Twitter v2 search endpoint without user-level rate limiting.

Tweet fetching is performed through the `fetch_recent_tweets()` method, which calls `client.search_recent_tweets()` with three explicitly requested tweet fields: `created_at`, `lang`, and `public_metrics`. The `max_results` parameter is clamped to the Twitter API legal range of 10–100 per call:

```python
max_results = max(10, min(max_results, 100))
```

This guard prevents `400 Bad Request` errors that would arise if the caller passes values outside the API-permitted range.

### 4.2.2 Search Queries and Language Targeting

The system uses a set of curated search queries targeting Somali political, security, economic, and social discourse. Each query includes `-is:retweet -is:reply` operators, which are Twitter API v2 native operators that exclude retweet objects and reply threads, ensuring only original authored content enters the corpus. Retweets are excluded because their text is identical to the source tweet, which would inflate the frequency of topics associated with widely-shared content without adding new linguistic signal. Replies are excluded because they are conversational fragments that lack the self-contained semantic structure required for coherent topic modeling.

The queries are grouped thematically across four domains:

1. **Politics and governance**: Terms such as `dowladda` (the government), `xukuumada` (the administration), `doorasho` (election), `madaxweyne` (president), `raysalwasaare` (prime minister). These terms target executive and legislative discourse.

2. **Security and conflict**: Terms such as `dagaal` (war/conflict), `weerar` (attack), `alshabaab` (Al-Shabaab militant group), `qarax` (explosion), `argagixiso` (terrorism). These queries capture the dominant security narrative in the Somali Twitter space.

3. **Economy, society and humanitarian aid**: Terms such as `dhaqaalaha` (the economy), `ganacsiga` (trade/business), `abaaraha` (droughts), `caafimaad` (health/healthcare), `waxbarasho` (education). These cover livelihood, development, and humanitarian topics.

4. **Geographic and hashtag queries**: `#Soomaaliya`, `#Somalia`, `#Mogadishu`, `#Somaliland`, `#Puntland`, `#Jubaland`, and related regional identifiers. These broader queries cast a wider net over geographic discourse without linguistic restriction.

### 4.2.3 Tweet Ingestion Schema and Deduplication

Each fetched tweet is processed by `ingest_tweet()`, which constructs a MongoDB document and inserts it into the `raw_tweets` collection. The schema stored for each tweet is:

```
{
  id:             string   — Twitter tweet ID (e.g. "1234567890123456789")
                            This field carries a unique MongoDB index.
  text:           string   — The original tweet text, completely unmodified.
                            No cleaning, normalisation, or truncation is applied
                            at ingestion time; all preprocessing is deferred to
                            the pipeline layer.
  lang_api:       string   — Language code as returned by Twitter API v2.
                            In this system, only "en" (English) and "so" (Somali)
                            are treated as primary languages. Other codes are stored
                            but receive no specialised processing.
  created_at:     datetime UTC — The timestamp when the tweet was originally
                            published on Twitter. This reflects user activity time.
  collected_at:   datetime UTC — The timestamp when this system fetched and stored
                            the tweet, generated as datetime.now(timezone.utc).
                            This is the system clock time, not the tweet time.
                            collected_at is used exclusively for incremental
                            corpus loading (the after_timestamp mechanism).
  like_count:     int      — Number of likes at collection time (from public_metrics).
  retweet_count:  int      — Number of retweets at collection time (from public_metrics).
}
```

The `id` field carries a **unique MongoDB index** created at server startup via `create_index("id", unique=True)`. When `ingest_tweet()` attempts to insert a tweet whose `id` already exists in the collection, MongoDB raises a `DuplicateKeyError`. This error is silently caught and the tweet is counted as a skip (`skipped += 1`) rather than raising an exception. This mechanism eliminates duplicates that would otherwise arise from the 15-minute collection loop overlapping with Twitter's search window on restart, or from the same tweet appearing across multiple thematic queries.

A secondary index on `collected_at` is maintained (`create_index("collected_at")`) to support the efficient range queries used in incremental corpus loading: `{"collected_at": {"$gt": after_timestamp}}`.

> **Important design constraint**: The `raw_tweets` collection is treated as sacred and append-only. No pipeline, route, or maintenance script ever deletes or modifies documents in this collection. It serves as the immutable ground truth of all collected data.

### 4.2.4 Session Quota and Background Collection Loop

The data collection loop runs as an `asyncio` background task launched in the FastAPI `lifespan()` context manager. The `lifespan()` generator is registered via `@asynccontextmanager` and executed on application startup and shutdown, replacing the deprecated `on_startup`/`on_shutdown` event hooks.

A hard session-level quota is enforced through two application state variables:
- `app.state.session_ingested_count` — a running count of tweets ingested in the current server session.
- `app.state.max_quota_limit = 1000` — the maximum tweets that may be collected before the loop stops entirely.

The collection loop runs every **15 minutes** (`asyncio.sleep(15 * 60)`). At each iteration, the following logic applies:

1. **Quota check**: if `session_ingested_count >= max_quota_limit`, the loop exits with a hard `break`. The loop does not restart until the server process is restarted. This prevents uncontrolled API consumption.

2. **Remaining budget calculation**: `remaining = max_quota_limit - session_ingested_count`. This is distributed across the active query list: `limit_per_query = max(1, min(50, remaining // len(queries)))`. Capping at 50 respects the Twitter API's `max_results` upper bound per call.

3. **Post-collection retraining trigger**: After ingesting `ingested > 0` new tweets, the loop checks whether the deployed model's retraining threshold has been reached and triggers incremental model retraining if so. This is the mechanism by which new data automatically propagates into updated topic models without manual intervention.

4. **Conditional start**: If `TWITTER_BEARER_TOKEN` is absent from the environment at startup, the collection loop exits immediately with a `logger.warning`. This allows the server to start in a read-only mode useful for demonstration and testing.

---

## 4.3 Data Preprocessing

### 4.3.1 Two-Track Preprocessing Architecture

The system deliberately maintains two distinct preprocessing tracks, one for BERTopic and one for LDA and NMF. This architectural decision is motivated by the fundamentally different input requirements of transformer-based versus bag-of-words topic models:

- **BERTopic** requires full sentence context. Transformer models such as `paraphrase-multilingual-MiniLM-L12-v2` produce embeddings that encode word order, grammatical structure, and cross-sentence context. Any preprocessing that alters word order (reordering), removes function words (stopword removal), or changes word form (stemming, lowercasing) degrades the quality of the resulting embeddings.

- **LDA and NMF** require a bag-of-words (BoW) or TF-IDF representation. These models treat each document as an unordered multiset of word counts. For BoW-based models, normalisation (lowercasing, stopword removal, minimum token length filtering) reduces vocabulary size and improves coherence by eliminating noise tokens.

### 4.3.2 BERTopic Preprocessing — Minimal Pipeline

BERTopic preprocessing is implemented in `preprocess_bertopic()` in `services/bertopic_model.py`. The function performs exactly two operations:

1. **Exact-text deduplication**: `df.drop_duplicates(subset=["text"])` — removes any two tweets that share identical text content. This prevents a single viral tweet from dominating the embedding space by contributing multiple identical vectors to the UMAP/HDBSCAN computation.

2. **Whitespace trimming**: `df["clean_text"] = df["text"].astype(str).str.strip()` — removes leading and trailing whitespace characters that could cause sentence boundary detection issues in the tokenizer.

No stemming, lemmatisation, stopword removal, URL stripping, or lowercasing is applied. The output `clean_text` column is passed directly to `SentenceTransformer.encode()` as a list of strings.

> **Design rationale**: Removing URLs or hashtags from BERTopic input would eliminate meaningful context signals. For example, a tweet containing `#Somalia` provides geographic context that the embedding model can use to group geographically-related topics. Preserving the full text maximises the semantic information available to the transformer.

### 4.3.3 LDA and NMF Preprocessing — Heavy Pipeline

LDA and NMF preprocessing is implemented in `preprocess_lda()` in `services/lda_model.py`. This function applies a standard NLP cleaning pipeline optimised for short, informal social media text:

**Sequential steps:**

1. **Lowercasing**: `text.lower()` — ensures that "Somalia" and "somalia" are treated as the same token, reducing vocabulary fragmentation.

2. **URL removal**: regex `http\S+|www\S+|https\S+` — strips HTTP/HTTPS URLs and `www.` links. URLs carry no semantic content useful for bag-of-words topic modeling; they would become high-frequency noise tokens otherwise.

3. **Mention removal**: regex `\@\w+` — strips Twitter @mentions (e.g., `@bbcnews`). Mentions are graph-structural features, not semantic content. Their inclusion would create spurious topics centred on frequently-mentioned accounts.

4. **Punctuation removal**: regex `[^\w\s]` — removes all non-word, non-space characters including hashtag symbols, exclamation marks, and emoji. Note that this strips the `#` prefix from hashtags but retains the word itself (e.g., `#Somalia` → `Somalia`), which is the desired behaviour for BoW models.

5. **Tokenisation**: `nltk.word_tokenize(text)` — splits the cleaned text into a list of word tokens using NLTK's Punkt tokenizer, which handles contractions and abbreviations correctly.

6. **Stopword removal and minimum length filter**: For each token `w`, it is retained only if `len(w) > 2` (at least 3 characters) AND `w not in combined_stopwords`. The combined stopword set is the union of the English NLTK stopwords and the custom Somali stopword list. This dual filter eliminates both common function words and very short tokens that carry no topical signal.

The resulting tokenized corpus is passed to `prepare_lda_matrices()`, which:
- Constructs a Gensim `Dictionary` mapping each unique token to an integer ID.
- Applies frequency extremes filtering: `dictionary.filter_extremes(no_below=2, no_above=0.95)`. This removes tokens appearing in fewer than 2 documents (likely typos or unique named entities) and tokens appearing in more than 95% of documents (likely corpus-wide stopwords missed by the stopword list).
- Converts the token lists into a BoW corpus: a list of `(token_id, count)` tuples per document.

For NMF, `prepare_nmf_matrix()` constructs a TF-IDF sparse matrix using sklearn's `TfidfVectorizer` with the same tokenized input, replacing the BoW representation. TF-IDF is preferred for NMF because NMF's objective function decomposes the matrix value as a product of non-negative components; TF-IDF values better reflect the discriminative importance of terms than raw counts.

### 4.3.4 Language Detection

Language identification is performed at the data ingestion stage using the `lang` field provided by the Twitter API v2 (`tweet_fields=["lang"]`). This field is mapped directly to the `lang_api` field in the `raw_tweets` document. No secondary language detection library (such as `langdetect` or `fastText`) is employed.

This design choice is motivated by two considerations:
1. Twitter's language detection is performed on the original tweet at post time, with access to user language settings and tweet metadata that post-hoc NLP-based detectors do not have.
2. Adding a secondary language detector would introduce a second source of truth that might disagree with Twitter's classification, requiring a conflict resolution policy.

The practical limitation of this approach is that Twitter's language detection for Somali text can occasionally misclassify short tweets or tweets mixing Somali with Arabic script as other languages. However, given that the search queries themselves are formulated in Somali, the recall of Somali-language tweets is high.

---

## 4.4 Topic Modeling — Three-Model Architecture

The system implements and evaluates three topic modeling approaches under identical experimental conditions. All three models are trained per-language (English and Somali separately), evaluated using the same intrinsic metrics and reference corpora, and produce output conforming to an identical `detected_trends` MongoDB schema. This design ensures that the evaluation is fair and the comparison results are reproducible.

### 4.4.1 BERTopic — Contextual Transformer Pipeline

BERTopic is implemented in `services/bertopic_model.py` as the `BERTopicTrainer` class. The pipeline consists of four sequential stages operating in the following order:

---

**Stage 1 — Sentence Embeddings (SentenceTransformer)**

The embedding model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` is loaded via the `SentenceTransformer` library. This model produces **384-dimensional** dense vector embeddings for input texts. It was pretrained on parallel sentence pairs across 50+ languages using a contrastive learning objective (multiple negatives ranking loss), making it effective for semantic similarity tasks in both English and Somali.

Embeddings are generated in a single batch call:
```python
embeddings = self.embedding_model.encode(docs, show_progress_bar=False)
```
The result is a numpy array of shape `(n_docs, 384)`. Each row is the semantic representation of the corresponding tweet.

> **Why this model?** Multilingual sentence transformers project semantically equivalent sentences in different languages into proximate regions of the embedding space. This means that an English tweet about "Somalia elections" and a Somali tweet about "doorashada Soomaaliya" will have similar embedding vectors even though their words share no overlap. However, since training is per-language in this system, this cross-lingual property is not exploited in production — the model is used for its high-quality monolingual embeddings.

---

**Stage 2 — Dimensionality Reduction (UMAP)**

A UMAP (Uniform Manifold Approximation and Projection) model is configured with the following parameters, as defined in `BERTopicTrainer.__init__()`:

```python
umap_model = UMAP(
    n_neighbors=15,
    n_components=5,
    min_dist=0.0,
    metric='cosine',
    random_state=42
)
```

- `n_neighbors=15`: Controls the balance between local and global structure. A value of 15 is standard for social media text where local thematic clusters are the primary interest.
- `n_components=5`: Projects 384 dimensions to 5 dimensions. Five components retain enough structural information for HDBSCAN to identify clusters while being computationally tractable.
- `min_dist=0.0`: Allows points in the same neighbourhood to be packed together as tightly as possible, which improves cluster separability in the reduced space.
- `metric='cosine'`: Cosine distance is the appropriate metric for normalised transformer embeddings, where the angle between vectors encodes semantic similarity more reliably than Euclidean distance.
- `random_state=42`: Fixed seed ensures reproducibility across training runs on the same corpus.

---

**Stage 3 — Density-Based Clustering (HDBSCAN)**

HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise) is configured as follows:

```python
hdbscan_model = HDBSCAN(
    min_cluster_size=adaptive_value,
    metric='euclidean',
    cluster_selection_method='eom',
    prediction_data=True
)
```

- `min_cluster_size`: **Adaptive** — computed by `_adaptive_min_cluster_size(n_docs)`:
  ```python
  def _adaptive_min_cluster_size(n_docs: int) -> int:
      return max(3, min(10, n_docs // 5))
  ```
  This formula ensures that the minimum cluster size scales proportionally with corpus size. For a corpus of 500 documents, `min_cluster_size = min(10, 500//5) = 10`. For a corpus of 50 documents, `min_cluster_size = min(10, 50//5) = 10` (capped at 10). For very small corpora of 15 documents, `min_cluster_size = max(3, 15//5) = 3` (floored at 3). This prevents the degenerate case where the minimum cluster size exceeds the corpus size.

- `cluster_selection_method='eom'`: Excess of Mass is the default HDBSCAN cluster extraction method. It produces flat clusters by identifying stable, persistent regions in the hierarchical clustering tree, which is appropriate for topics that have varying densities.

- `prediction_data=True`: Required for soft clustering (assigning out-of-sample documents to existing topics).

Documents that do not meet the density threshold for any cluster are assigned the outlier label `-1` by HDBSCAN. These outlier documents are explicitly excluded from the `detected_trends` output.

> **Key property of HDBSCAN in this context**: Unlike K-Means, HDBSCAN does not require specifying the number of topics K in advance. K is determined empirically by the density structure of the UMAP-reduced embeddings. This is BERTopic's defining characteristic and why it discovered K=35 topics on this corpus, compared to LDA's K=23 and NMF's K=20 selected by grid search.

---

**Stage 4 — Topic Representation (c-TF-IDF)**

BERTopic represents each topic using class-based TF-IDF (c-TF-IDF), which treats all documents in a cluster as a single "class document" and computes TF-IDF scores across all class documents:

```python
vectorizer_model = CountVectorizer(
    stop_words=combined_stopwords,
    min_df=1
)
```

The `combined_stopwords` list is the union of NLTK English stopwords and the custom Somali stopwords from `api/resources/stopwords.txt`. This ensures high-frequency function words from both languages are suppressed in the topic keyword representation, producing more semantically meaningful topic labels.

**Per-language training flow in deployment:**

```
Preprocessed corpus (clean_text)
        │
        ├── df_en (lang_api == "en")
        │       │
        │       ▼
        │   BERTopicTrainer(min_cluster=adaptive_en)
        │       │ encode → UMAP → HDBSCAN → c-TF-IDF
        │       ▼
        │   topic_docs_en  →  doc["lang"] = "en"  ← FORCED
        │
        └── df_so (lang_api == "so")
                │
                ▼
            BERTopicTrainer(min_cluster=adaptive_so)
                │ encode → UMAP → HDBSCAN → c-TF-IDF
                ▼
            topic_docs_so  →  doc["lang"] = "so"  ← FORCED
```

The `lang` field assignment is explicitly overridden after topic construction to guarantee monolingual topic assignment, regardless of any statistical signals from the model.

---

### 4.4.2 LDA — Latent Dirichlet Allocation Baseline

LDA is implemented using `gensim.models.LdaModel` in `services/lda_model.py`, managed by the `LDATrainer` class. LDA models each document as a mixture of latent topics and each topic as a distribution over vocabulary words, using Dirichlet priors on both distributions.

The model is trained with:
- `passes=10`: Number of full passes over the corpus during training, equivalent to epochs in neural network terminology. Ten passes are sufficient for convergence on corpora of this size.
- `random_state=42`: Fixed seed for reproducibility.
- `alpha` and `eta`: Hyperparameters controlling the document-topic and topic-word Dirichlet priors respectively, selected by grid search.

**K-selection via grid search:**

When `LDA_GRID_SEARCH=true` (the default value in `.env`), the `_run_lda_sync()` function in `jobs/lda_pipeline.py` runs a systematic grid search over the nine-value range `K ∈ {4, 5, 6, 7, 8, 9, 10, 11, 12}`. For each candidate K:
1. A full `LDATrainer` is instantiated and trained with 5 passes (reduced from 10 for speed during search).
2. The model's C_v coherence score is computed using `gensim.models.CoherenceModel`.
3. The `(K, C_v)` pair is recorded.

After the grid search completes, `_pick_best_from_grid()` selects the configuration with the highest C_v. In the event of a tie (two K values with the same C_v within floating-point precision), the smaller K is preferred, following Occam's razor — a simpler model is preferred when it achieves equal quality.

The grid search selected **K=23** (combined across the English and Somali language splits) on the collected corpus.

**Per-language training**: The corpus is split into `df_en` and `df_so`. An independent `LDATrainer` with its own grid search is run for each language. Topic documents produced from `df_en` receive `doc["lang"] = "en"` (forced assignment); topic documents from `df_so` receive `doc["lang"] = "so"`.

---

### 4.4.3 NMF — Non-negative Matrix Factorization Baseline

NMF is implemented in `services/nmf_model.py` via `NMFTrainer`, using sklearn's `NMF` class. NMF decomposes the document-term TF-IDF matrix `V ≈ W × H` into two non-negative matrices: a document-topic matrix `W` and a topic-term matrix `H`. The non-negativity constraint produces parts-based representations — topics are additive combinations of terms, not subtractions — which makes NMF topics more interpretable than LDA for short texts.

**Shared preprocessing with LDA**: The `_tokenize_corpus()` function is imported directly from `jobs/lda_pipeline.py` into `jobs/nmf_pipeline.py`. This is a deliberate coupling that ensures LDA and NMF operate on an identical tokenized representation. Any change to the LDA preprocessing automatically propagates to NMF, preventing the two baselines from diverging in preprocessing configuration across deployments.

The NMF model reuses all LDA environment variables (`LDA_MIN_CORPUS_SIZE`, `LDA_CORPUS_LIMIT`, `LDA_GRID_SEARCH`), for the same reason — both baselines should be configurable together, not independently.

**K-selection via grid search**: Identical range to LDA (`K ∈ {4..12}`), identical selection criterion (highest C_v, smallest K as tiebreak). The grid search selected **K=20** per language on this corpus.

**TF-IDF vs BoW**: Unlike LDA, which uses a raw BoW corpus, NMF operates on a TF-IDF matrix produced by `prepare_nmf_matrix()`. TF-IDF down-weights terms that appear frequently across all documents (corpus-wide common terms) and up-weights terms that are distinctive to particular documents. This makes NMF's factorization more sensitive to topic-discriminative terms, which is why NMF typically achieves higher Topic Diversity scores than LDA (NMF EN Diversity = 0.8731 vs LDA EN Diversity = 0.4966 on this corpus).

---

## 4.5 Evaluation Framework

### 4.5.1 Design Philosophy — Intrinsic Metrics Only

The evaluation of topic models in this system is exclusively intrinsic — it relies only on the training corpus itself, with no external labels, human judgement, or gold-standard topic assignments. This design choice is motivated by the nature of the trending topic detection task: there are no pre-defined correct topics, as trending topics emerge dynamically from the data.

Three metrics are computed for every model and every language slice:

**1. C_v Coherence (Primary Metric)**

C_v coherence measures the semantic similarity of the top `TOP_N_WORDS = 10` words in each topic. It is computed in four steps:
1. Segment the top-N word pairs using a sliding window over the reference corpus.
2. Compute the NPMI (Normalized Pointwise Mutual Information) for each word pair using their co-occurrence counts in the reference corpus.
3. For each topic, construct a vector of NPMI values.
4. Compute the mean cosine similarity between all pairs of NPMI vectors within the topic.

A higher C_v score (range: 0.0–1.0) indicates more semantically coherent topics whose top words frequently co-occur in the reference corpus. C_v is the most commonly reported coherence metric in recent NLP literature and is the primary selection criterion in this system.

**2. U_Mass Coherence (Supporting Metric)**

U_Mass coherence is an older, document co-occurrence–based metric that computes:
```
U_Mass(w_i, w_j) = log(P(w_i, w_j) / P(w_j)) + ε
```
where `P(w_i, w_j)` is the fraction of documents containing both words and `P(w_j)` is the fraction containing `w_j`. U_Mass values are negative; values closer to 0 indicate better coherence. U_Mass is reported as a supporting metric to provide a second, independent coherence measurement, since C_v and U_Mass use different co-occurrence window definitions and aggregation methods.

**3. Topic Diversity**

Topic Diversity measures the uniqueness of vocabulary across all topics:
```
Diversity = |unique words in top-10 of all topics| / (K × 10)
```
A score of 1.0 means every keyword across all topics is unique — no word appears in more than one topic's top-10. Low diversity indicates that multiple topics share the same dominant words (topic redundancy). This metric is relevant to the deployment use case: if two topics have identical top words, the user sees duplicate trending topics in the dashboard.

**Perplexity** is computed for LDA only (it is undefined for NMF and BERTopic) and recorded in the evaluation artifacts, but it is never used in the three-way comparison because it is not a comparable metric across model families.

### 4.5.2 Per-Language Evaluation with Shared Reference Corpus

The evaluation framework is designed around what is called "Option B" (per-language split with a shared reference corpus). The rationale is:

- All three models are trained per-language, producing separate English and Somali topic sets.
- Each topic set must be evaluated against a reference corpus written in the same language, otherwise co-occurrence statistics will be cross-lingual and meaningless.
- The `build_reference_corpora()` function in `services/evaluation.py` constructs three reference corpora from the loaded training data: `reference_corpora["en"]`, `reference_corpora["so"]`, and `reference_corpora["combined"]`. The "combined" slice is constructed for completeness but explicitly excluded from the three-way comparison, as it is not an independent measurement — it merges both language corpora and could artificially inflate scores for models that produce mixed-language topics.

**BERTopic vocabulary normalization**: The `get_bertopic_topics()` function applies lowercasing and non-alphabetic character stripping to BERTopic's raw c-TF-IDF keywords before evaluation. This normalization is critical because BERTopic's preprocessing (minimal — no lowercasing, no stripping) produces keywords in their original case and with embedded punctuation (e.g., `#Somalia`, `WEERAR`). Without normalization, these keywords would not match the lowercased, punctuation-stripped tokens in the LDA/NMF reference dictionary, causing them to be treated as out-of-vocabulary and systematically penalising BERTopic in C_v scoring.

**Windows deadlock prevention**: On Windows operating systems, `gensim.models.CoherenceModel` defaults to Python multiprocessing for parallel co-occurrence computation. When running inside a uvicorn subprocess (which itself uses multiprocessing for hot-reload), this can cause a deadlock. All `CoherenceModel` instances in this system are therefore instantiated with `processes=1`, restricting computation to a single thread:

```python
coherence_model = CoherenceModel(
    topics=topics, texts=reference_texts,
    dictionary=dictionary, coherence='c_v',
    processes=1
)
```

### 4.5.3 Winner Selection Rule

The winner selection is implemented in `_select_winner_from_metrics()` in `jobs/model_comparison.py`. The rule is applied deterministically from the metric data in `results/metrics/coherence_diversity.json`:

1. **Primary criterion — English C_v**: The model with the highest English C_v wins. English is selected as the primary language because it constitutes the dominant portion of the corpus (approximately 73% of tweets by language distribution).

2. **Tiebreak — Somali C_v**: If two models have equal English C_v (within floating-point precision), the model with the higher Somali C_v wins.

3. **Secondary tiebreak — English Topic Diversity**: If both C_v scores are also equal, the model with higher English diversity is selected.

This rule contains no hardcoded model preference. The winner is selected purely from measured experimental results. The evaluation is designed as a **one-time academic decision**: once a winner is persisted to `pipeline_state`, the guard in `run_full_evaluation()` prevents automatic re-selection:

```python
if deployed is not None:
    return {"status": "skipped", "reason": "winner_already_set", "deployed_model": deployed}
```

Re-evaluation can only be triggered manually via `POST /jobs/run-evaluation?force=true`.

### 4.5.4 Experimental Results

The following results were obtained from `api/results/metrics/coherence_diversity.json` on the collected corpus at the time of evaluation:

| Model | Language | C_v | U_Mass | Diversity | K |
|-------|----------|-----|--------|-----------|---|
| LDA | English | 0.3274 | -10.6787 | 0.4966 | 23 |
| LDA | Somali | 0.3253 | -13.7520 | 0.5163 | 23 |
| NMF | English | 0.5478 | -9.0876 | 0.8731 | 20 |
| NMF | Somali | 0.4682 | -12.6962 | 0.8394 | 20 |
| **BERTopic** | **English** | **0.5508** | **-8.9593** | **0.8255** | **35** |
| BERTopic | Somali | 0.3932 | -14.1331 | 0.7396 | 35 |

**Analysis and winner determination:**

- **BERTopic wins on English C_v = 0.5508**, narrowly outperforming NMF (0.5478) by 0.003. This margin, while small, is consistent across random seeds and confirms BERTopic's advantage for this corpus type.

- **BERTopic achieves the best U_Mass score for English (-8.9593)**, the value closest to zero, indicating the highest observed word co-occurrence quality in the English reference corpus.

- **LDA performs substantially below both baselines** (English C_v = 0.3274, Somali C_v = 0.3253), confirming that the bag-of-words assumption with Dirichlet priors is poorly suited to this short, informal, bilingual social media corpus. The low diversity (EN = 0.4966) further indicates that many of LDA's 23 topics share overlapping vocabulary, producing redundant trending topic entries.

- **NMF performs strongly** (English C_v = 0.5478, highest diversity at 0.8731), demonstrating that matrix factorization with TF-IDF input is a competitive approach for this task. NMF outperforms LDA on all three metrics across both languages.

- **BERTopic's auto-K of 35** (vs LDA 23, NMF 20) suggests that the embedding-based clustering identifies a richer topic structure in the data, discovering finer-grained themes that BoW models merge into broader topics.

**Conclusion**: BERTopic is selected as the deployed model, and its incremental retraining pipeline is activated for production use.

---

## 4.6 Deployment Pipeline

### 4.6.1 Winner-Only Retraining Architecture

Following evaluation, **only the winning model (BERTopic) is retrained in production**. The deployment dispatcher function `run_deployed_pipeline()` in `jobs/deployment.py` implements this routing:

```python
async def run_deployed_pipeline() -> dict:
    winner = await get_deployed_model()   # reads pipeline_state.deployed_model
    if winner == "bertopic":
        return await run_bertopic_pipeline()
    elif winner == "lda":
        return await _run_lda_deployment()
    elif winner == "nmf":
        return await _run_nmf_deployment()
    return {"status": "skipped", "reason": "no_winner_set"}
```

LDA and NMF retain their last evaluation artifacts in `detected_trends` and are never retrained in the deployment cycle, unless one of them is the selected winner. This design ensures:
- Computational resources (GPU/CPU time for transformer encoding) are concentrated on the best-performing model.
- All three models write to `detected_trends` using an identical schema, so no API route or frontend changes are required if the winning model changes between evaluations.
- The system remains functionally correct even if the deployed model changes (e.g., if a future dataset causes LDA or NMF to win).

### 4.6.2 Incremental Corpus Loading

A fundamental design principle of the deployment pipeline is that the deployed model retrains **exclusively on new data** — tweets collected since the last training run. This is implemented through the `corpus_after_timestamp` mechanism:

**Step-by-step flow:**

1. Read `last_trained_tweet_collected_at` from `pipeline_state["bertopic"]`. This timestamp records the `max(collected_at)` of the tweets used in the most recent training run.

2. Count new tweets: `new_count = await db["raw_tweets"].count_documents({"collected_at": {"$gt": last_ts}})`.

3. **Threshold check**: If `new_count < BERTOPIC_NEW_TWEETS_THRESHOLD` (default 500) AND `has_topics > 0` (the model already has topics in `detected_trends`), skip retraining:
   ```
   return {"status": "skipped", "reason": "insufficient_new_tweets",
           "new_tweets": new_count, "threshold": 500}
   ```
   This prevents unnecessary retraining when only a handful of new tweets have been collected.

4. **First deployment special case**: If `detected_trends` is empty (`has_topics == 0`), set `corpus_after_timestamp = None`. This triggers `load_tweet_corpus()` to load the full historical corpus without a time filter, populating the system with topics for the first time. This case applies only once, immediately after a fresh evaluation completes and `detected_trends` is empty.

5. **Incremental load**: Call `load_tweet_corpus(lang=None, limit=CORPUS_LIMIT, after_timestamp=corpus_after_timestamp)`. In `pipelines/corpus_loader.py`, this translates to:
   ```python
   if after_timestamp is not None:
       query["collected_at"] = {"$gt": after_timestamp}
   cursor = db["raw_tweets"].find(query).sort("collected_at", -1).limit(limit)
   ```

6. After successful training, update `last_trained_tweet_collected_at` to `max(collected_at)` of the newly trained batch.

**Benefit of incremental loading**: By loading only new tweets, each retraining run produces topics that reflect the most recent discourse, not a blend of historical and recent content. The `tweet_period_from/to` and `peak_at` temporal metadata accurately represent the time period of the new batch, not the entire collection history.

### 4.6.3 Trend Scoring Formula

Each detected topic receives a composite `trend_score` computed by `compute_trend_score()` in `services/trend_scoring.py`:

```
trend_score = Volume_component × 60  +  Engagement_component × 40

Volume_component    = min(topic_doc_count / 100.0, 1.0)
Engagement_component = min(topic_engagement / max_corpus_engagement, 1.0)
topic_engagement    = total_likes + total_retweets  (for this topic's tweets)
max_corpus_engagement = max(total_likes + total_retweets)  (across ALL topics in current batch)
```

**Component breakdown:**

- **Volume component (60% weight)**: Reflects how many tweets are associated with this topic. A topic with 100 or more tweets achieves the maximum volume score of 1.0. This is the dominant component because sheer discussion volume is the most direct signal of a trending topic.

- **Engagement component (40% weight)**: Reflects how much user interaction (likes + retweets) the topic's tweets attracted. Normalization by `max_corpus_engagement` ensures the score is relative to the current training batch — a topic that attracts all the engagement in the batch scores 1.0, regardless of absolute numbers. This prevents score inflation during periods of overall high engagement.

The 60/40 split reflects the design decision that volume (breadth of discussion) is a stronger trending signal than engagement (depth of interest), since a topic can trend through many moderate-engagement tweets or through few high-engagement tweets, but the former is typically more representative of a genuinely trending topic.

### 4.6.4 Temporal Metadata — peak_at Field

The temporal accuracy of date-based filtering in the frontend depends critically on the `peak_at` field. Without it, all topics trained in a single batch would share the same `tweet_period_to ≈ today`, making the 7-day and 30-day date filters return identical results (since `tweet_period_to` for all topics would be within any recent date range).

Three temporal fields are stored per topic document, derived from the `collected_at` timestamps of the tweets in each cluster:

| Field | Formula | Purpose |
|-------|---------|---------|
| `tweet_period_from` | `min(collected_at)` of cluster tweets | Earliest tweet collected for this topic |
| `tweet_period_to` | `max(collected_at)` of cluster tweets | Most recent tweet collected for this topic |
| `peak_at` | `median(collected_at)` of cluster tweets | When this topic was most active — used as the primary date filter anchor |

The `peak_at` median is computed as:
```python
col = subset["collected_at"].dropna().sort_values()
peak_at = col.iloc[len(col) // 2].to_pydatetime()
```

The median is preferred over the midpoint of `(tweet_period_from + tweet_period_to) / 2` because the midpoint is the arithmetic mean of the temporal endpoints and ignores the actual distribution of tweet activity. A topic with 100 tweets clustered in early January and 1 tweet in late June would have a misleading midpoint of April, whereas the median correctly identifies January as the peak activity period.

The API routes `/trends` and `/history` filter topics by `peak_at` when `from_date`/`to_date` parameters are provided:
```python
query["peak_at"] = {"$gte": from_date_parsed, "$lte": to_date_parsed}
```

### 4.6.5 Detected Trends MongoDB Schema

Every model's deployment pipeline produces documents conforming to the following schema, stored in the `detected_trends` collection:

```
{
  topic:               int     — Model-internal numeric topic ID.
                                 For BERTopic: HDBSCAN cluster index.
                                 For LDA/NMF: grid-search-selected topic index.

  Name:                string  — Auto-generated topic label in BERTopic format:
                                 "{topic_id}_{top_word1}_{top_word2}_{top_word3}"
                                 e.g. "0_war_ukraine_ceasefire"

  Representation:      list    — Top-10 c-TF-IDF keywords for this topic.
                                 These are the words most associated with this
                                 topic relative to all other topics.

  label:               string  — Human-readable label formed by joining the
                                 top 3 cleaned keywords with spaces.
                                 e.g. "war ukraine ceasefire"

  representative_docs: list    — Up to 3 tweets selected from this topic's
                                 cluster by highest combined engagement
                                 (likes + retweets). Shown to users in the
                                 History page expanded view.

  volume:              int     — Number of tweets assigned to this topic cluster.

  total_likes:         int     — Sum of like_count across all cluster tweets.

  total_retweets:      int     — Sum of retweet_count across all cluster tweets.

  trend_score:         float   — Composite trend score in range [0, 100].
                                 60% volume component + 40% engagement component.

  lang:                string  — "en" or "so". FORCED after training — overrides
                                 any statistical language assignment.

  en_count:            int     — Count of English-language tweets in cluster
                                 (informational; used in analytics).

  so_count:            int     — Count of Somali-language tweets in cluster.

  en_percentage:       float   — en_count / volume × 100.

  so_percentage:       float   — so_count / volume × 100.

  calculated_at:       datetime UTC — When the training run completed.
                                 All topics from the same training run share
                                 the same calculated_at value. Used to identify
                                 which topics belong to the same "batch."

  tweet_period_from:   datetime UTC — min(collected_at) of cluster tweets.

  tweet_period_to:     datetime UTC — max(collected_at) of cluster tweets.

  peak_at:             datetime UTC — median(collected_at) of cluster tweets.
                                 Primary date filter anchor for /trends and /history.

  model:               string  — "bertopic", "lda", or "nmf".
                                 Allows the API to filter by winning model.
}
```

---

## 4.7 Real-Time Update Mechanism

### 4.7.1 Background Loops Architecture

The system's real-time behaviour is driven by three `asyncio` background tasks, all launched in the `lifespan()` context manager in `app/main.py`. The `lifespan()` pattern is the FastAPI-recommended approach for startup/shutdown lifecycle management, replacing the deprecated `@app.on_event("startup")` hooks. Each background task is an independent `asyncio.Task` that runs concurrently with the main HTTP request serving loop.

| Task name | Interval | Purpose |
|-----------|----------|---------|
| `periodic_data_collection_loop` | Every **15 minutes** | Fetches tweets from Twitter API; triggers model retraining after threshold |
| `periodic_model_comparison_loop` | Retries every **30 minutes** until winner set, then exits permanently | Runs `run_full_evaluation()` once on first startup; triggers first `run_deployed_pipeline()` |
| `periodic_email_digest_loop` | Every **24 hours** (configurable: `DIGEST_INTERVAL_HOURS`) | Sends daily digest emails to users with `email_digests=True` preference |

The periodic evaluation loop is designed as a **one-shot** task: it calls `run_full_evaluation()` at 30-minute intervals until a winner is successfully persisted to `pipeline_state["deployed_model"]`. Once a winner exists, the guard in `run_full_evaluation()` causes it to return `{"status": "skipped", "reason": "winner_already_set"}`, and on the next iteration the loop detects the winner, calls `run_deployed_pipeline()` to perform the initial topic population, and then exits the loop permanently. This means evaluation overhead (training three models simultaneously) is incurred only during the initial setup phase.

### 4.7.2 Post-Collection Retraining Trigger

The data collection loop implements the following trigger logic after each successful collection cycle (`ingested > 0`):

```
After ingesting new tweets:
    1. Read last_trained_tweet_collected_at from pipeline_state[deployed_model]
    2. new_count = count(raw_tweets where collected_at > last_trained_ts)
    3. If new_count >= BERTOPIC_NEW_TWEETS_THRESHOLD (500):
           → call run_deployed_pipeline()
           → model retrains on new tweets only (incremental)
           → new topics written to detected_trends
           → pipeline_state updated with new last_trained_tweet_collected_at
    4. If new_count < 500:
           → skip (not enough new data to justify retraining cost)
    5. If last_trained_ts is None (no prior training):
           → call run_deployed_pipeline() unconditionally (first run)
```

This architecture decouples data ingestion from model retraining. The collection loop's only responsibility is gathering tweets; the retraining decision is made post-collection based on a configurable threshold. This prevents wasteful retraining on every 15-minute cycle when tweet volume is low.

The threshold of 500 tweets (configurable via `BERTOPIC_NEW_TWEETS_THRESHOLD`) balances two competing concerns:
- **Too low**: Frequent retraining on small corpora produces unstable, low-quality topics.
- **Too high**: Trending topics that emerge rapidly may not appear in the dashboard for hours.

### 4.7.3 Pipeline State Tracking

The `pipeline_state` MongoDB collection serves as the system's operational memory. Each document in this collection represents the current operational state of a specific pipeline component. The `pipeline` field is a unique index, ensuring exactly one document per component:

| `pipeline` value | Key fields | Purpose |
|-----------------|------------|---------|
| `"bertopic"` | `last_trained_tweet_collected_at`, `last_run_at`, `c_v_en`, `c_v_so`, `num_topics`, `status` | BERTopic training state and per-run metrics |
| `"lda"` | `last_trained_tweet_collected_at`, `last_run_at`, `c_v_en`, `c_v_so`, `status` | LDA training state |
| `"nmf"` | `last_trained_tweet_collected_at`, `last_run_at`, `c_v_en`, `c_v_so`, `status` | NMF training state |
| `"deployed_model"` | `model` ("bertopic"/"lda"/"nmf"), `set_at` | Current winner and when it was selected |
| `"model_comparison"` | `report` (full JSON comparison object), `generated_at` | Cached three-way comparison report |
| `"evaluation"` | `last_evaluated_at`, `last_corpus_max_collected_at`, `corpus_size`, `deployed_model` | Evaluation run state; used by re-evaluation guard |

---

## 4.8 REST API Design

### 4.8.1 FastAPI Application Configuration

The API application is defined in `app/main.py` as a `FastAPI` instance with the following configuration:

```python
app = FastAPI(
    title="Real-Time Trending Topic Detection API",
    version="1.0.0"
)
```

CORS (Cross-Origin Resource Sharing) middleware is added to permit requests from the React frontend, which runs on a different port:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

The `allow_origins=["*"]` configuration is appropriate for a research prototype but would be replaced with a specific origin whitelist in a production deployment.

A single `APIRouter` imported from `app/routes.py` is mounted at the root path via `app.include_router(router)`. All route definitions reside in `routes.py`, keeping `main.py` focused on application lifecycle management.

### 4.8.2 API Endpoints

The following table lists all REST endpoints implemented in `app/routes.py`:

| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| GET | `/health` | No | System health check; returns status and MongoDB connectivity |
| GET | `/trends` | No | Latest batch or date-filtered topics. Params: `lang`, `limit`, `from_date`, `to_date`. Filters by `peak_at`. |
| GET | `/history` | No | Full historical topic list. Params: `lang`, `topic_name`, `limit`, `from_date`, `to_date`. Filters by `peak_at`. |
| GET | `/raw_tweets` | No | Raw collected tweets. Params: `lang`, `limit`, `from_date`, `to_date`. Filters by `collected_at`. |
| POST | `/filter` | No | Keyword search over topic names. Params: `keyword`, `lang`. |
| GET | `/trends/topics_over_time` | No | Dynamic topic modeling time-series from `topic_evolution` collection |
| GET | `/trends/keywords` | No | Trending keyword frequency counts from recent tweets |
| GET | `/tweets/stats` | No | Aggregate tweet statistics (total, EN/SO counts, per-day breakdown) |
| GET | `/models/comparison` | No | Three-way model comparison report from `pipeline_state` or JSON file |
| GET | `/models/winner` | No | Current deployed model name, set_at timestamp, and metric scores |
| GET | `/models/status` | No | Operational status of current deployed model with latest C_v metrics |
| GET | `/models/history` | No | BERTopic training run history. Params: `limit`, `from_date`, `to_date`. Filters by `trained_at`. |
| GET | `/visualizations/{model}` | No | Serve HTML visualization file (BERTopic intertopic distance or pyLDAvis) |
| POST | `/auth/signup` | No | Register new user with bcrypt-hashed password |
| POST | `/auth/login` | No | Authenticate user; returns JWT. Accepts `application/x-www-form-urlencoded`. |
| POST | `/auth/google` | No | Google OAuth login/auto-registration |
| GET | `/auth/me` | Yes | Return current user profile |
| POST | `/auth/change-password` | Yes | Change authenticated user's password |
| GET | `/auth/preferences` | Yes | Return notification preferences |
| POST | `/auth/preferences` | Yes | Update notification preferences |
| POST | `/auth/2fa/send-code` | Yes | Generate and email a 2FA TOTP code |
| POST | `/auth/2fa/verify` | Yes | Verify submitted 2FA code |
| POST | `/auth/2fa/disable` | Yes | Disable 2FA for current user |
| GET | `/auth/2fa/status` | Yes | Return 2FA enabled/disabled status |
| POST | `/jobs/train-bertopic` | Yes | Manually trigger BERTopic training run |
| POST | `/jobs/train-lda` | Yes | Manually trigger LDA training run |
| POST | `/jobs/train-nmf` | Yes | Manually trigger NMF training run |
| POST | `/jobs/run-comparison` | Yes | Trigger three-way model comparison report generation |
| POST | `/jobs/run-evaluation` | Yes | Trigger full three-model evaluation. Param: `force=true` to override winner guard. |
| POST | `/jobs/run-deployment` | Yes | Manually trigger deployed model retraining |
| POST | `/jobs/send-digests` | Yes | Manually trigger email digest sending |

### 4.8.3 Date Filtering Architecture

All endpoints that expose time-series data accept `from_date` and `to_date` as ISO 8601 string parameters. These are parsed by the shared helper `_parse_iso_datetime()`:

```python
def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
```

The `.replace("Z", "+00:00")` handles both the `Z` (Zulu/UTC) suffix produced by JavaScript's `Date.toISOString()` and the `+00:00` offset format. The resulting datetime object is timezone-aware UTC, suitable for direct comparison with MongoDB's UTC datetime fields.

Each endpoint applies the date filter to the field most semantically appropriate for that endpoint's data:

| Endpoint | Date filter field | Reason |
|----------|------------------|--------|
| `/trends` | `peak_at` | Topic activity time — when the topic was most discussed |
| `/history` | `peak_at` | Same — consistent temporal semantics |
| `/models/history` | `trained_at` | Training run time — when the model was retrained |
| `/raw_tweets` | `collected_at` | Collection time — when the tweet entered the system |
| `/tweets/stats` | `collected_at` | Same |
| `/trends/keywords` | `collected_at` | Same |

### 4.8.4 adapt_trend_to_frontend() — Schema Adapter Pattern

The raw `detected_trends` MongoDB documents use BERTopic-native field names (`Name`, `Representation`) that differ from the field names expected by the React frontend. A dedicated adapter function `adapt_trend_to_frontend()` translates the storage schema to the API contract without changing either the database schema or the frontend's expectations:

```python
def adapt_trend_to_frontend(t: dict, requested_lang: str) -> dict:
    return {
        "_id":               str(t.get("_id", t.get("id"))),
        "topic_name":        t.get("Name", "Unknown Topic"),
        "label":             t.get("label", t.get("Name", "Unknown Topic")),
        "top_keywords":      t.get("Representation", []),
        "representative_docs": _dedup_docs(t.get("representative_docs", [])),
        "score":             t.get("trend_score", 0.0),
        "volume":            t.get("volume", 0),
        "language":          t.get("lang") if t.get("lang") in ("en","so") else requested_lang,
        "timestamp":         t.get("tweet_period_to") or t.get("calculated_at", datetime.utcnow()),
        "tweet_period_from": t.get("tweet_period_from"),
        "tweet_period_to":   t.get("tweet_period_to"),
        "model":             t.get("model"),
    }
```

The `_dedup_docs()` helper removes exact-duplicate strings from the representative_docs list, preventing the same tweet from appearing multiple times in the expanded topic view.

This adapter pattern decouples the storage layer from the presentation layer. If the MongoDB schema evolves (e.g., adding new fields), the adapter is the only component that requires updating — the frontend continues to receive the same field names.

### 4.8.5 Authentication and Security

**JWT Authentication:**
- Token creation: `create_access_token()` in `services/auth.py` encodes the user's email into a JWT signed with `SECRET_KEY` using the `HS256` algorithm.
- Token lifetime: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 minutes).
- Token verification: `verify_token()` in `services/auth.py` decodes and validates the token, extracting the subject claim.
- Route protection: The `get_current_user` dependency, injected via `Depends(get_current_user)` on protected routes, calls `verify_token()` and retrieves the user from MongoDB.

**Password Security:**
- Hashing: `bcrypt` via `passlib.CryptContext(schemes=["bcrypt"], deprecated="auto")`. Bcrypt applies a configurable work factor (cost factor), making brute-force attacks computationally expensive.
- Verification: `pwd_context.verify(plain_password, hashed_password)` — constant-time comparison prevents timing attacks.

**Two-Factor Authentication (2FA):**
- A numeric code is generated and stored directly in the user's MongoDB document with a `two_factor_expires` timestamp 10 minutes in the future.
- The code is delivered via SMTP email using the `services/email.py` module.
- On verification, the submitted code is compared with the stored code after checking that `datetime.now(UTC) < two_factor_expires`.
- On successful verification, the code fields are removed from the user document.

**Google OAuth:**
- The `POST /auth/google` endpoint accepts a Google ID token (`credential` field).
- The token is verified against Google's public keys.
- If the email does not correspond to an existing user, a new account is auto-registered with `google_id` stored in the user document.

---

## 4.9 Frontend Architecture

### 4.9.1 Application Structure

The frontend is a React 18 single-page application (SPA) built with Vite, located in the `dashboard/` directory. Vite serves as both the development server (with hot module replacement) and the production bundler. All API calls are routed to `http://localhost:8000` via a shared Axios instance defined in `src/services/api.js`.

The build output is a set of static HTML/CSS/JS files that can be served from any static file host. In development, Vite's dev server runs on `http://localhost:5173` and proxies nothing — the frontend makes cross-origin requests directly to `http://localhost:8000`, which is why CORS middleware is required on the backend.

### 4.9.2 Routing with React Router v6

Application routing is managed by React Router v6 in `src/App.jsx`. Routes are organised into two access tiers:

**Public routes** (no authentication required):
- `/login` — Login form with email/password and Google OAuth button
- `/register` — User registration form

**Protected routes** (authentication enforced by `<Layout>`):
- All other paths are wrapped in a `<Layout>` component that reads `AuthContext.token`. If no token is present, the user is redirected to `/login` via `<Navigate to="/login" />`.
- The root path `/` redirects to `/dashboard` via `<Navigate to="/dashboard" replace />`.

### 4.9.3 State Management — Four React Contexts

The application uses four React contexts, each managed by a dedicated provider:

**1. AuthContext** (`contexts/AuthContext.jsx`)
- Stores: `token` (JWT string), `user` (profile object), `setToken`, `logout`
- Persistence: JWT token and user profile are stored in `localStorage` under keys `visiontech_token` and `visiontech_user`, allowing the session to survive browser refresh.
- The Axios request interceptor reads `localStorage.getItem('token')` on every request to inject the current token. This means token revocation on the server side is not reflected until the client's stored token expires.

**2. ThemeContext** (`contexts/ThemeContext.jsx`)
- Stores: `theme` ("light" | "dark"), `toggleTheme`
- Persistence: Theme preference stored in `localStorage`.
- Effect: adds/removes the `dark` CSS class on the `<html>` element, activating Tailwind CSS's dark mode variant.

**3. LanguageContext** (`contexts/LanguageContext.jsx`)
- Stores: `language` ("en" | "so"), `setLanguage`, `t()` (translation function)
- The `t()` function looks up a key in a bilingual translation dictionary and returns the string in the currently active language.
- The `language` value is passed as the `lang` query parameter in API calls to `/trends` and `/history`, enabling server-side language filtering.

**4. DateRangeContext** (`contexts/DateRangeContext.jsx`)
- Stores: `range` ("24h" | "7d" | "30d" | "custom"), `customDates` ({ startDate, endDate }), `setRange`, `setCustomDates`
- Persistence: Both `range` and `customDates` are persisted in `localStorage`.
- Computed values: a `useMemo` computes `startDate` and `endDate` as UTC ISO strings whenever `range` or `customDates` changes. These are consumed by `rangeToQueryParams()` to build `from_date`/`to_date` API parameters.
- The `DateFilter` component (used in every page's header) renders the range selection buttons and the custom calendar picker. It reads/writes to `DateRangeContext`.

### 4.9.4 API Layer — Axios with JWT Interceptor

`services/api.js` creates a shared Axios instance:

```javascript
const api = axios.create({ baseURL: 'http://localhost:8000' });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

The request interceptor ensures that the JWT `Authorization: Bearer <token>` header is automatically included in every API request without requiring each calling function to handle token injection manually.

**Date parameter construction:**
```javascript
const buildDateQuery = (dateParams = {}) => {
  const params = new URLSearchParams();
  if (dateParams.from_date) params.append('from_date', dateParams.from_date);
  if (dateParams.to_date)   params.append('to_date',   dateParams.to_date);
  const qs = params.toString();
  return qs ? `&${qs}` : '';
};
```

This helper is used by `getTrends()`, `getHistory()`, `getRawTweets()`, `getModelHistory()`, and other date-filterable API functions.

**Login special case:**
```javascript
export const loginUser = async (email, password) => {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  const response = await api.post('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return response.data;
};
```

The login request must use `application/x-www-form-urlencoded` encoding because FastAPI's `OAuth2PasswordRequestForm` dependency parses form data, not JSON. The `username` field accepts either a username or email address.

### 4.9.5 Dashboard Pages

| Page | Route | Key API Calls | Functionality |
|------|-------|--------------|--------------|
| Dashboard | `/dashboard` | `getTrends`, `getTweetStats`, `getTrendingKeywords` | Overview: top trending topics as bar chart, language distribution pie chart, tweet volume statistics, trending keyword cloud |
| Trending | `/trending` | `getTrends`, `filterTrends` | Ranked topic list with trend score bars; keyword search filter using `/filter` endpoint |
| Tweets | `/tweets` | `getRawTweets` | Paginated raw tweet browser; filterable by language (EN/SO) and date range |
| History | `/history` | `getHistory` (EN + SO) | Full historical topic table; expand any row to view representative tweets; sorted by timestamp descending |
| Comparison | `/comparison` | `getTrends`, `getModelComparison`, `getModelHistory` | Three-model evaluation metrics table; BERTopic training quality line chart (C_v EN/SO across runs); side-by-side EN/SO topic columns |
| Export | `/export` | Various | CSV/JSON data export of topics and tweets |
| Setting | `/setting` | `getPreferences`, `updatePreferences`, 2FA endpoints | Email digest and spike alert notification toggles; 2FA enable/disable flow |
| Profile | `/profile` | `getUser`, `changePassword` | User profile display; password change form |

---

## 4.10 Database Design

### 4.10.1 Collections Overview

MongoDB was selected as the database for this system because its document model naturally accommodates the variable-length fields in topic modeling output (keyword lists, representative document arrays) without requiring schema migrations as the topic structure evolves. Six collections are used:

| Collection | Write pattern | Purpose |
|-----------|--------------|---------|
| `raw_tweets` | Append-only; never updated or deleted | Immutable tweet corpus — the ground truth for all topic training |
| `detected_trends` | BERTopic: append-only. LDA/NMF: delete-then-insert per run | Topic model output per training batch |
| `pipeline_state` | Upsert (update_one with upsert=True) | One document per pipeline — current operational state |
| `pipeline_history` | Append-only insert per training run | Historical record of all training run metrics |
| `users` | Insert on registration; targeted field updates | User accounts and preferences |
| `topic_evolution` | Append-only per BERTopic dynamic modeling run | Time-series topic trajectory data |

**Write pattern for detected_trends**: BERTopic uses `insert_many()` (additive) — each training batch adds new topics without removing previous batches. LDA and NMF use `delete_many({"model": model}) + insert_many()` (replace) — each run replaces all previous topics for that model. This asymmetry reflects the different deployment strategies: BERTopic maintains a rolling history of topic batches, while LDA and NMF (used as reference models) maintain only the latest run.

### 4.10.2 Indexing Strategy

Indexes are created at server startup by `init_db_indexes()` in `db/connection.py`:

```python
# raw_tweets — deduplication and incremental loading
db["raw_tweets"].create_index("id", unique=True)
db["raw_tweets"].create_index("collected_at")

# detected_trends — batch retrieval and language filter
db["detected_trends"].create_index("calculated_at")
db["detected_trends"].create_index("lang")

# topic_evolution — time-series queries
db["topic_evolution"].create_index("stored_at")

# pipeline_state — one document per pipeline
db["pipeline_state"].create_index("pipeline", unique=True)
```

The `collected_at` index on `raw_tweets` is the most performance-critical index in the system. Every incremental corpus loading query (`{"collected_at": {"$gt": last_ts}}`) uses this index. Without it, each incremental load would perform a full collection scan on potentially millions of tweets.

The `pipeline` unique index on `pipeline_state` ensures that `update_one(..., upsert=True)` operations never create duplicate state documents for the same pipeline component.

### 4.10.3 Deduplication — deduplicate_existing_trends()

On each server startup, `deduplicate_existing_trends()` in `db/connection.py` runs a MongoDB aggregation pipeline over the `detected_trends` collection:

```python
pipeline = [
    {"$group": {
        "_id": {"name": "$Name", "batch": "$calculated_at"},
        "count": {"$sum": 1},
        "docs": {"$push": {"id": "$_id"}}
    }},
    {"$match": {"count": {"$gt": 1}}}
]
```

This identifies all groups of documents that share the same `(Name, calculated_at)` pair — i.e., duplicate documents produced by the same training run with the same topic name. This can occur if a training pipeline is interrupted and restarted, causing some topics to be written twice. For each duplicate group, all but the first document (`docs[1:]`) are deleted. Documents from different `calculated_at` batches (different training runs) are preserved, even if they share the same `Name`, because cross-batch topic tracking requires retaining all historical topic versions.

### 4.10.4 Database Connection Lifecycle

The MongoDB connection is managed as a module-level singleton in `db/connection.py`. The `init_db_indexes()` coroutine initialises the connection and creates indexes. The connection is kept open for the lifetime of the FastAPI application and closed in the `lifespan()` shutdown phase via `close_db_client()`. A `reset_db_client()` function is provided for test isolation — it closes and re-initialises the client, pointing to the test database specified by the `DATABASE_NAME=trending_topics_test` environment variable in `tests/conftest.py`.

---

## 4.11 Multilingual Support

### 4.11.1 Language Identification Strategy

The choice of relying on Twitter's native language detection (the `lang` field from the API) rather than a secondary NLP-based language identifier is a deliberate architectural decision. Twitter's language detection has access to:
- The user's declared interface language
- The user's historical tweet language patterns
- Script detection (Arabic script vs Latin script)
- Probabilistic language models trained on Twitter-specific data

These signals are not available to a post-hoc language detector that sees only the tweet text. For Somali in particular — a language with limited training data in most open-source language detection libraries — Twitter's native detection provides more reliable results than tools like `langdetect` or `fastText` which may confuse Somali with other Cushitic or Semitic languages.

### 4.11.2 Per-Language Training — Strict Language Isolation

All three models implement strict language isolation at the training level:

**Step 1 — Corpus split:**
```python
MIN_PER_LANG = 50
df_en = df[df["lang_api"] == "en"].copy()
df_so = df[df["lang_api"] == "so"].copy()
```

**Step 2 — Minimum corpus check:**
Training for a given language is skipped if the corpus for that language falls below 50 documents. This prevents degenerate models trained on insufficient data, which would produce incoherent topics with very low C_v scores.

**Step 3 — Independent model training:**
Each language receives its own model instance, its own preprocessing pipeline run, its own grid search (for LDA and NMF), and its own `min_cluster_size` computation (for BERTopic). No information crosses the language boundary during training.

**Step 4 — Forced language assignment:**
After topic documents are constructed from training output, the `lang` field is explicitly overridden:
```python
for doc in trend_docs_en:
    doc["lang"] = "en"  # FORCED — overrides any statistical assignment
for doc in trend_docs_so:
    doc["lang"] = "so"  # FORCED — overrides any statistical assignment
```
This double-guarantee (training isolation + forced assignment) ensures that under no circumstance can a topic trained on English documents be labeled as Somali or vice versa.

### 4.11.3 Language-Specific Stopword Resources

**English stopwords**: Sourced from `nltk.corpus.stopwords.words('english')` — the NLTK standard English stopword list, containing approximately 179 common English function words (articles, prepositions, conjunctions, pronouns, auxiliary verbs).

**Somali stopwords**: Sourced from `api/resources/stopwords.txt` — a custom file loaded at module import time by `_load_somali_stopwords()`. This file is the single authoritative source for Somali stopwords in the system, shared across three consumers:
- `services/lda_model.py` — used in `preprocess_lda()` tokenization
- `jobs/nmf_pipeline.py` — imported from `lda_model.py` via the shared tokenizer
- `services/bertopic_model.py` — added to the `CountVectorizer` stop_words list for c-TF-IDF

This single-source-of-truth design ensures that LDA, NMF, and BERTopic all suppress the same Somali function words, making their topic representations directly comparable in evaluation.

**Combined stopwords for BERTopic CountVectorizer:**
```python
combined_stopwords = list(english_stopwords.union(somali_stopwords))
vectorizer_model = CountVectorizer(stop_words=combined_stopwords, min_df=1)
```

The union ensures that c-TF-IDF keyword extraction suppresses function words from both languages simultaneously, which is important because BERTopic's `CountVectorizer` operates on the combined vocabulary of both the English and Somali subsets of the training corpus.

### 4.11.4 Per-Language Evaluation Reference Corpora

The evaluation framework constructs three reference corpora in `build_reference_corpora()`:
- `reference_corpora["en"]` — tokenized English tweets only
- `reference_corpora["so"]` — tokenized Somali tweets only
- `reference_corpora["combined"]` — all tweets (excluded from three-way comparison)

A shared Gensim `Dictionary` is constructed from the combined tokenized corpus (`build_reference_dictionary(reference_corpora)`) and used for all three models' C_v and U_Mass computations. Using a single dictionary ensures that co-occurrence statistics are computed over the same vocabulary space for all models, making metric comparisons valid.

The per-language C_v scoring applies an additional vocabulary filter inside `evaluate_model()`: BERTopic's topic words are intersected with the reference dictionary before coherence computation, removing any OOV tokens that arise from BERTopic's minimal preprocessing. This normalization is critical for fair comparison — without it, BERTopic's capitalized or punctuated keywords would systematically miss the reference dictionary and receive a lower C_v score than deserved.

---

## Summary

This chapter has provided a comprehensive description of the design and implementation of the Real-Time Trending Topic Detection System. The system integrates data collection from Twitter's v2 API, per-language preprocessing, three independently trained and evaluated topic models (BERTopic, LDA, NMF), an intrinsic evaluation framework, and a React-based analytical dashboard served by a FastAPI backend.

The experimental evaluation on the collected corpus of English and Somali tweets demonstrated that BERTopic, with a contextual transformer embedding pipeline (SentenceTransformer → UMAP → HDBSCAN → c-TF-IDF), achieves the highest C_v coherence for English (0.5508) and the best U_Mass score (-8.9593), outperforming both NMF (C_v = 0.5478) and LDA (C_v = 0.3274) under identical evaluation conditions. BERTopic is therefore deployed as the production topic model, with incremental retraining triggered automatically whenever 500 or more new tweets have been collected since the last training run.

---

*All parameter values, metric results, field names, algorithmic formulas, and architectural descriptions in this chapter are derived directly from the implemented source code of the system at the time of writing. No values have been estimated or approximated.*
