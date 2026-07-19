# Falanqayn Buuxda — Habka Model-ka Guuleystay

---

## 1. Xogta Sida Loo Soo Qaataa

### Goobta: `api/services/data_collection.py` + `api/app/main.py`

**Background loop** (`periodic_data_collection_loop`) wuxuu bilaabaaa server-ka markuu bilaabmo:
- Wuxuu orodaa **marka 15 min** kasta
- Wuxuu adeegsadaa **6 queries** oo `lang:en` leh (Twitter API)
- Xad ugu badan session kasta: **1000 tweet** (ma dhaafaan)
- Kull tweet waxaa lagu kaydiyo `raw_tweets` collection-ka:

```
{
  id:             tweet ID (unique index)
  text:           qoraalka asalka ah
  lang_api:       "en" ama "so" (Twitter API kasoo timid)
  created_at:     goorta tweet-ku la qoray (Twitter-ka)
  collected_at:   goorta system-ku soo qaatay (UTC, hadda)
  like_count:     
  retweet_count:  
}
```

**Xaqiiqo muhiim ah:**
- `collected_at` waa timestamp-ka SYSTEM-ka, ma aha tweet-ka
- Retweets iyo replies waa laga hortag (Twitter query: `-is:retweet -is:reply`)
- Haddii tweet-ku hore jiro (isku `id`), `DuplicateKeyError` → la iska daa, lama korsho

**Hadda xaaladda:** `TWITTER_BEARER_TOKEN` commented out → collection disabled

---

## 2. Xulashada Model-ka Guuleystay

### Goobta: `api/jobs/evaluation_pipeline.py` + `api/jobs/deployment.py`

**Markaad marka hore shaqaynayso (First Run):**
- `periodic_model_comparison_loop()` → LDA, NMF, BERTopic isbarbardhig
- Natiijadiisa: model ugu fiican la doortaa → `pipeline_state.deployed_model = "bertopic"` (tusaale)
- Ka dib: `run_deployed_pipeline()` si toos ah ayaa loo orodsiiyaa

**Ka dib (Recurring):**
- `periodic_winner_training_loop()` → **marka 30 min** kasta
- Wuxuu akhriaa `pipeline_state.deployed_model`
- Hadduu "bertopic" yahay → `run_bertopic_pipeline()` yeedhaa
- Hadduu "lda" yahay → `_run_lda_deployment()` yeedhaa
- Haddaanay jirin winner → skip (noop)

---

## 3. BERTopic Pipeline — Xogta Sida Loogu Soo Qaataa

### Goobta: `api/pipelines/corpus_loader.py` → `load_tweet_corpus(lang=None, limit=100000)`

```python
cursor = db["raw_tweets"].find({}).sort("collected_at", -1).limit(100000)
```




**Natiijada:** Model-ku wuxuu ku tababaraa **xogta oo DHAN** — hore iyo cusub wada.

---

## 4. Preprocessing (Nadiifinta Corpus-ka)

### Goobta: `api/services/bertopic_model.py` → `preprocess_bertopic()`

```python
df_clean = df.drop_duplicates(subset=["text"]).copy()
df_clean["clean_text"] = df_clean["text"].astype(str).str.strip()
df_clean = df_clean[df_clean["clean_text"] != ""]
```

**Waxaa dhacaa:**
- Tweets isku qoraal ah (text dedup) → mid kaliya la ilaaliyaa
- Trimming whitespace
- Mida madhan waa la tirtiraa

**Xaqiiqo:** Marka laga dhigo dedup, corpus-ku wuxuu yareeyaa. Tusaale: 579 raw → 490 nadiif. Tani ayaa keeni karta `BERTOPIC_MIN_CORPUS_SIZE=500` check inuu ka baxo.

---

## 5. Luqadaha Sida Loo Kala Saaraa

### Goobta: `api/jobs/bertopic_pipeline.py` → `run_bertopic_pipeline()` (Updated)

**Habka Cusub (ka dib isbedelkii):**

```python
df_en = df_clean[df_clean["lang_api"] == "en"].copy()   # ~73%
df_so = df_clean[df_clean["lang_api"] == "so"].copy()   # ~27%

# Train EN separately
trainer_en, topics_en, docs_en = _run_training_sync(df_en, min_cluster_en)
for doc in td_en: doc["lang"] = "en"   # FORCED — no mixing

# Train SO separately
trainer_so, topics_so, docs_so = _run_training_sync(df_so, min_cluster_so)
for doc in td_so: doc["lang"] = "so"   # FORCED — no mixing
```

**Waxaan halkan ka ogaaday:**
- ✅ EN iyo SO **gaar gaar** ayaa lagu tababaraa — laba trainer oo gooni ah
- ✅ Mawduuc kasta `lang` = "en" **ama** "so" (hal keliya, kuma qasna)
- ✅ `min_cluster_size` mid walba gooni ayaa loo xisaabaa (corpus-kiisa wayn ku xidhan)
- ✅ Minimum per language: 50 doc (hadduu ka yar yahay → la iska daa, kale waa la tababaraa)
- ✅ C_v EN = cosine similarity avg of EN trainer's topics
- ✅ C_v SO = cosine similarity avg of SO trainer's topics
- ❌ Labadooduba **xog oo dhan** ayay ku tababaraan — ma ahan xog cusub oo kaliya

---

## 6. Embedding iyo Clustering

### Goobta: `api/services/bertopic_model.py` → `BERTopicTrainer.train()`

```
docs → SentenceTransformer (paraphrase-multilingual-MiniLM-L12-v2)
     → UMAP (n_components=5, n_neighbors=15)
     → HDBSCAN (min_cluster_size=adaptive, metric='euclidean')
     → c-TF-IDF representation
```

**Xaqiiqo:**
- Embedding model-ku **multilingual** yahay — EN iyo SO labadoodaba si fiican ayuu u gartaa
- HDBSCAN wuxuu qaar xoog `-1` (outlier) ahaan ku calaamadiyaa — topics-ka ku darma
- `min_cluster_size = max(3, min(10, n_docs // 5))`:
  - 500 doc → 10
  - 100 doc → 10
  - 50 doc → 10
  - 20 doc → 4

---

## 7. Topic Documents — Sida Loo Abuuro

### Goobta: `api/jobs/bertopic_pipeline.py` → `_build_trend_documents()`

Mawduuc kasta waxaa laga soo saara:

```
{
  topic:              ID-ga (BERTopic internal)
  Name:               "0_war_ukraine" (auto-generated)
  Representation:     ["war", "ukraine", "ceasefire", ...]
  label:              "war ukraine" (human readable)
  representative_docs: [tweet1, tweet2, tweet3] (ugu engagement badan)
  volume:             tirada tweets-ka mawduucaas ku jira
  total_likes:        
  total_retweets:     
  trend_score:        60% volume + 40% engagement
  lang:               "en" OR "so" (FORCED — no array)
  en_count:           (xogta ayaa ku jirta - informational)
  so_count:           
  en_percentage:      
  so_percentage:      
  calculated_at:      goorta training-ku dhacay (UTC now)
  tweet_period_from:  min(collected_at) ee tweets-ka mawduucaas ku jira
  tweet_period_to:    max(collected_at) ee tweets-ka mawduucaas ku jira
  model:              "bertopic"
}
```

**Xaqiiqo muhiim — tweet_period_from/to:**

Mawduuc "war" oo ku jira tweets-ka laga soo qaatay January + June labadoodaba:
```
tweet_period_from = January 15
tweet_period_to   = June 26 (maanta)
```
Filter "last 24h" → mawduucan wuu soo baxaa — sababtoo ah `tweet_period_to = maanta`.
Laakiin mawduucan xogtiisu waxay ka timid 6 bilood!

---

## 8. Topic Storage — Sida DB Loogu Keydiyo

### Goobta: `api/jobs/bertopic_pipeline.py` → `_persist_trends()`

**Hadda xaaladda (ka dib isbedelka):**

```python
# delete_many LA JIRTO (la saaray)
unique_trend_docs = trend_docs
if unique_trend_docs:
    await coll.insert_many(unique_trend_docs)   # ADD — old topics stay
```

**Natiijada:**
- Training run kasta wuxuu ku **daraa** topics cusub — ma tirtiray kuwa hore
- Batches-kii hore weli jiraan DB
- Kull batch wuxuu leeyahay `calculated_at` gooni ah

**`pipeline_history` — run kasta record:**
```
{
  pipeline:       "bertopic"
  trained_at:     calculated_at
  corpus_size:    tirada docs la tababaray
  num_topics:     K_en + K_so
  c_v_en:         cohesion EN
  c_v_so:         cohesion SO
  diversity_en:   
  diversity_so:   
  ...
}
```

---

## 9. Deduplication — Qabashada Nuqulada

### Goobta: `api/db/connection.py` → `deduplicate_existing_trends()` (Updated)

**Hadda:**
```python
"_id": {"name": "$Name", "batch": "$calculated_at"}
```

**Macnaheeda:**
- Keliya mawduucyo **isku batch + isku magac** ah ayaa la tirtiraa (accident)
- Batches kala duwan ee isku magac ah **WAAN ILAALIYAA**
- Wuxuu orodaa server startup-ka

---

## 10. Frontend — Sida Topics Loogu Siiyo

### Goobta: `api/app/routes.py` → `GET /trends`

**Xaaladda 1 — Date filter la'aanta (default):**
```python
latest_trend = await trends_collection.find_one(
    {"model": "bertopic"}, sort=[("calculated_at", -1)]
)
query["calculated_at"] = latest_trend["calculated_at"]
```
→ Kaliya **ugu dambe batch** ee la tababaray ayaa la soo celiyaa

**Xaaladda 2 — Date filter leh:**
```python
query["tweet_period_to"] = {"$gte": from_date, "$lte": to_date}
```
→ Topics la soo celiyaa marka `tweet_period_to` (goorta ugu dambe ee tweet-ka) rangega ku dhex jiro

**Language filter:**
```python
if lang in ("en", "so"):
    query["lang"] = lang
```
→ Waxaa ka yimid per-language training-ka: mawduuc kasta waa "en" ama "so" keliya

**Dedup-ka frontend:**
```python
word_key = re.sub(r'^-?\d+_', '', t.get("Name", ""))
# "0_war_ukraine" → "war_ukraine"
# "5_war_ukraine" → "war_ukraine"  ← SAME! Only first shown
```
→ Haddii batches kala duwan ay soo saaraan isku magac topic, hal keliya ayaa la muujiyaa

---

## 11. Wadarta — Jawaabaha Su'aalaha

### Q1: Xogta oo dhan miyaa lagu tababaraa, mise xog cusub oo keliya?

**Jawaabta: XOG OO DHAN.**

`load_tweet_corpus(lang=None, limit=100000)` wuxuu rariaa ALL tweets from `raw_tweets` — waqti filter ma jiro. Model-ku wuxuu marka kasta arkaa xogta oo dhan: January + February + ... + June wada.

`BERTOPIC_NEW_TWEETS_THRESHOLD` wuxuu keliya **shaqada** go'aansadaa (run ama skip), laakiin hadduu run-garayana, xogta oo dhan ayuu isticmaalaa — ma ahan xog cusub oo keliya.

### Q2: Mawduucyada cusub ee maanta kaliya — ma suurtagal?

**Hadda ma suurtagal.** Mawduuc "war" wuxuu ku jiraa tweets January + June labadoodaba. `tweet_period_to` = maanta sababtoo ah war-tweets ayaa maanta la soo qaatay. "Last 24h" filter → mawduucan wuu soo baxaa — laakiin mawduucan ma ahan "mawduuc cusub", waa mawduuc taariikhda leh.

**Sidaad u ogtahay mawduuca goorta la soo saaray:**
- `calculated_at` = goorta training-ku dhacay (run-ga time)
- `tweet_period_from` = goorta ugu horreeya ee tweet-ka mawduucaas
- `tweet_period_to` = goorta ugu dambeeyay ee tweet-ka mawduucaas

### Q3: EN iyo SO sida loo kala saaraa?

**Laba trainer gooni ah.** `df_en` (lang_api=="en") → trainer_en, `df_so` (lang_api=="so") → trainer_so. Ka dib, doc kasta `lang` forced ahaan "en" ama "so". Shan ayaa mawduuc walba leh hal luqad oo keliya, iskuma qasna.

### Q4: 20 topics hore iyadoo waqtigoodii la ilaalinayo — sidee?

Ka dib training-ka hore (3 model comparison):
- **`calculated_at`** = goorta training dhacday (e.g. June 24 10:00)
- **`tweet_period_from`** = Jan 1 (oldest tweet in that topic cluster)
- **`tweet_period_to`** = June 24 (newest tweet in that topic cluster)

Topics-kaas weli jiraan DB (delete_many la saaray). Default view = latest batch.

### Q5: Xog cusub oo kaliya topics-keeda sida loo soo saaro — suurtogal?

**Hadda code-ka: MAYA.** Laakiin xal jiraa: `tweet_period_from` ku saleysan filter. Haddaad u rabtaa "mawduucyada tweet-kooda ugu yaraan 90% maanta la soo qaatay", waxaad u baahan tahay:

```
query["tweet_period_from"] = {"$gte": 24h_ago}  
# show only topics whose FIRST tweet is from today
```

Tani waxay soo celin doontaa topics aan lahayn tweet hore (dhif).

---

## 12. Dhibaatooyinka La Ogaaday

| # | Dhibaato | Heerka | Goobta |
|---|----------|--------|--------|
| 1 | Model wuxuu xogta oo dhan ku tababaraa — mawduucyo "cusub" oo keliya ma soo saaraan | Weyn | `corpus_loader.py` line 36-40 |
| 2 | `tweet_period_to` filter: mawduuc duug ah leh tweet maanta ah wuu soo baxaa "last 24h" | Dhexdhexaad | `routes.py` line 452 |
| 3 | `BERTOPIC_MIN_CORPUS_SIZE=500` aad u dhow corpus-ka (579 raw, ~490 nadiif) | Dhexdhexaad | `.env` |
| 4 | `TWITTER_BEARER_TOKEN` commented out → xog cusub ma soo galayso | Weyn | `.env` |
| 5 | `periodic_model_comparison_loop()` **ma la bilaabayo** startup-ka — manual evaluation keliya | Faahfaahin | `main.py` line 160-162 |
| 6 | Frontend word_key dedup: batches kala duwan ee isku magac topics → hal keliya muuqda | Yar | `routes.py` line 465-473 |
| 7 | `_persist_topic_evolution()` kaliya EN trainer waxay u shaqaysaa (SO skip) | Yar | `bertopic_pipeline.py` line 295 |

---

## 13. Wadarta Guud — Diagram

```
raw_tweets (2000+ tweets, ALL history)
        │
        ▼
load_tweet_corpus(lang=None, limit=100000)
        │  → ALL tweets loaded (no time filter)
        ▼
preprocess_bertopic()
        │  → text dedup, strip
        ▼
     df_clean
    ┌────────┴────────┐
    │                 │
  df_en             df_so
  (73%)             (27%)
    │                 │
    ▼                 ▼
BERTopicTrainer   BERTopicTrainer
    │                 │
  topics_en        topics_so
  lang="en"        lang="so"
    │                 │
    └────────┬────────┘
             │
         trend_docs_all
             │
             ▼
    detected_trends (insert, no delete)
             │
    ┌────────┴────────────────────┐
    │ calculated_at = now         │
    │ tweet_period_from = oldest  │
    │ tweet_period_to = newest    │
    └─────────────────────────────┘
             │
             ▼
       Frontend /trends
    ┌──────────────────────────┐
    │ Default: latest batch    │ ← calculated_at filter
    │ Date range: tweet_period │ ← tweet_period_to filter
    └──────────────────────────┘
```

