import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pathlib import Path
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import os
import re as _re_routes
from pydantic import BaseModel

from db.connection import get_database
from models.schemas import UserCreate, UserResponse, Token, ChangePasswordRequest, TwoFactorVerifyRequest, TwoFactorStatusResponse, UserPreferences
from services.email import send_2fa_code, generate_2fa_code
from services.auth import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from jose import JWTError, jwt
from services.auth import SECRET_KEY, ALGORITHM

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Dependency to get current user
async def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_database)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await db["users"].find_one({"$or": [{"username": username}, {"email": username}]})
    if user is None:
        raise credentials_exception
    return user

@router.post("/auth/signup", response_model=UserResponse)
async def signup(user: UserCreate, db=Depends(get_database)):
    users_collection = db["users"]
    
    existing_user = await users_collection.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
        
    hashed_password = get_password_hash(user.password)
    user_dict = {
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(user_dict)
    user_dict["_id"] = str(result.inserted_id)
    return user_dict

@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_database)):
    users_collection = db["users"]
    user = await users_collection.find_one({"$or": [{"username": form_data.username}, {"email": form_data.username}]})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

class GoogleLoginRequest(BaseModel):
    credential: str

@router.post("/auth/google", response_model=Token)
async def google_login(request: GoogleLoginRequest, db=Depends(get_database)):
    try:
        payload = jwt.get_unverified_claims(request.credential)
        email = payload.get("email")
        
        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token: No email found.")
            
        users_collection = db["users"]
        user = await users_collection.find_one({"email": email})
        
        if not user:
            # Auto-register the user if they don't exist
            username = email.split("@")[0]
            # Ensure unique username
            while await users_collection.find_one({"username": username}):
                username += "_g"
                
            user_dict = {
                "username": username,
                "email": email,
                "hashed_password": get_password_hash("GOOGLE_OAUTH_DUMMY_PASSWORD"),
                "created_at": datetime.utcnow()
            }
            await users_collection.insert_one(user_dict)
            user = user_dict
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to verify Google account: {str(e)}")

@router.post("/auth/change-password")
async def change_password(request: ChangePasswordRequest, current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    users_collection = db["users"]
    
    if not verify_password(request.current_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    new_hashed_password = get_password_hash(request.new_password)
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"hashed_password": new_hashed_password}}
    )
    
    return {"message": "Password updated successfully"}

@router.get("/auth/2fa/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(current_user: dict = Depends(get_current_user)):
    return {"two_factor_enabled": current_user.get("two_factor_enabled", False)}

@router.post("/auth/2fa/send-code")
async def request_2fa_code(current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    users_collection = db["users"]
    
    code = generate_2fa_code()
    expires = datetime.utcnow() + timedelta(minutes=10)
    
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"two_factor_code": code, "two_factor_expires": expires}}
    )
    
    await send_2fa_code(current_user["email"], code)
    
    return {"message": "Verification code sent to your email"}

@router.post("/auth/2fa/verify")
async def verify_2fa_code(request: TwoFactorVerifyRequest, current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    users_collection = db["users"]
    
    stored_code = current_user.get("two_factor_code")
    expires = current_user.get("two_factor_expires")
    
    if not stored_code or not expires:
        raise HTTPException(status_code=400, detail="No 2FA code requested")
        
    if datetime.utcnow() > expires:
        raise HTTPException(status_code=400, detail="Verification code expired")
        
    if request.code != stored_code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
        
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {"two_factor_enabled": True},
            "$unset": {"two_factor_code": "", "two_factor_expires": ""}
        }
    )
    
    return {"message": "Two-Factor Authentication enabled successfully"}

@router.post("/auth/2fa/disable")
async def disable_2fa(current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    users_collection = db["users"]
    
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"two_factor_enabled": False}}
    )
    
    return {"message": "Two-Factor Authentication disabled"}

@router.get("/auth/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: dict = Depends(get_current_user)):
    return {
        "email_digests": current_user.get("email_digests", True),
        "spike_alerts": current_user.get("spike_alerts", False)
    }

@router.post("/auth/preferences")
async def update_user_preferences(prefs: UserPreferences, current_user: dict = Depends(get_current_user), db=Depends(get_database)):
    users_collection = db["users"]
    
    await users_collection.update_one(
        {"_id": current_user["_id"]},
        {"$set": {
            "email_digests": prefs.email_digests,
            "spike_alerts": prefs.spike_alerts
        }}
    )
    
    return {"message": "Preferences updated successfully"}


# --- SYSTEM HEALTH & MANUAL TRAINING ---

@router.get("/health")
async def health_check(db=Depends(get_database)):
    """Pipeline and database status for monitoring."""
    from services.monitoring import collect_system_status

    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        db_ok = False

    monitoring = await collect_system_status()
    trend_count = await db["detected_trends"].count_documents({})

    return {
        "status": "ok" if db_ok and not any(a["level"] == "error" for a in monitoring["alerts"]) else "degraded",
        "database_connected": db_ok,
        "detected_trend_count": trend_count,
        "min_corpus_for_training": int(os.getenv("BERTOPIC_MIN_CORPUS_SIZE", "1000")),
        **monitoring,
    }


@router.post("/jobs/train-bertopic")
async def trigger_bertopic_training(current_user: dict = Depends(get_current_user)):
    """Manually trigger BERTopic training (authenticated)."""
    from jobs.bertopic_pipeline import run_bertopic_pipeline
    result = await run_bertopic_pipeline()
    return result


@router.post("/jobs/train-lda")
async def trigger_lda_training(current_user: dict = Depends(get_current_user)):
    """Manually trigger LDA baseline training (authenticated)."""
    from jobs.lda_pipeline import run_lda_pipeline
    return await run_lda_pipeline()


@router.post("/jobs/train-nmf")
async def trigger_nmf_training(current_user: dict = Depends(get_current_user)):
    """Manually trigger NMF baseline training (authenticated)."""
    from jobs.nmf_pipeline import run_nmf_pipeline
    return await run_nmf_pipeline()


@router.post("/jobs/run-deployment")
async def trigger_deployment(current_user: dict = Depends(get_current_user)):
    """Run deployed model — trains only if ≥ BERTOPIC_NEW_TWEETS_THRESHOLD new tweets exist."""
    from jobs.deployment import run_deployed_pipeline
    return await run_deployed_pipeline()


@router.post("/jobs/run-comparison")
async def trigger_model_comparison(current_user: dict = Depends(get_current_user)):
    """Run three-way metrics-driven comparison of LDA, NMF, and BERTopic."""
    from jobs.model_comparison import run_model_comparison
    return await run_model_comparison()

@router.post("/jobs/send-digests")
async def trigger_email_digests(current_user: dict = Depends(get_current_user)):
    """Manually send daily digests to opted-in users."""
    from services.notifications import send_daily_digests
    return await send_daily_digests()


@router.get("/models/comparison")
async def get_model_comparison(db=Depends(get_database)):
    """Return the latest three-way model comparison report (LDA, NMF, BERTopic)."""
    state = await db["pipeline_state"].find_one({"pipeline": "model_comparison"})
    if state and state.get("report"):
        return state["report"]
    report_path = Path(__file__).resolve().parent.parent / "reports" / "comparison" / "latest_comparison.json"
    if report_path.exists():
        import json
        return json.loads(report_path.read_text(encoding="utf-8"))
    raise HTTPException(
        status_code=404,
        detail="No comparison report yet. Run POST /jobs/train-lda, /jobs/train-nmf, /jobs/train-bertopic, then /jobs/run-comparison.",
    )


@router.get("/models/winner")
async def get_winner_model(db=Depends(get_database)):
    """Return the currently deployed (winning) model and its selection metadata."""
    from jobs.deployment import get_deployed_model
    deployed = await get_deployed_model()
    if deployed is None:
        raise HTTPException(
            status_code=404,
            detail="No model deployed yet. Evaluation runs automatically after enough tweets are collected.",
        )
    state = await db["pipeline_state"].find_one({"pipeline": "deployed_model"})
    set_at = state.get("set_at") if state else None

    comparison_state = await db["pipeline_state"].find_one({"pipeline": "model_comparison"})
    metric_scores = None
    if comparison_state and comparison_state.get("report"):
        metric_scores = comparison_state["report"].get("model_metric_scores")

    return {
        "deployed_model": deployed,
        "set_at": set_at,
        "metric_scores": metric_scores,
    }


@router.get("/models/status")
async def get_model_status(db=Depends(get_database)):
    """Current deployed model with operational metrics, prev delta, and evaluation comparison."""
    bertopic_state, deployed_state, comparison_state = await asyncio.gather(
        db["pipeline_state"].find_one({"pipeline": "bertopic"},          {"_id": 0}),
        db["pipeline_state"].find_one({"pipeline": "deployed_model"},    {"_id": 0}),
        db["pipeline_state"].find_one({"pipeline": "model_comparison"},  {"_id": 0}),
    )
    if not bertopic_state and not deployed_state:
        return {"status": "no_data"}

    report = (comparison_state or {}).get("report") or {}
    return {
        "deployed_model":   deployed_state.get("model") if deployed_state else "bertopic",
        "set_at":           deployed_state.get("set_at") if deployed_state else None,
        "last_run_at":      (bertopic_state or {}).get("last_run_at"),
        "topics_written":   (bertopic_state or {}).get("topics_written", 0),
        "last_trained_tweet_collected_at": (bertopic_state or {}).get("last_trained_tweet_collected_at"),
        # Operational BERTopic-internal metrics (corpus size, num_topics, outlier_ratio)
        "metrics":          (bertopic_state or {}).get("metrics"),
        "prev_metrics":     (bertopic_state or {}).get("prev_metrics"),
        # Evaluation metrics — c_v / diversity per model per language (used for winner selection)
        "eval_metrics": {
            "bertopic": report.get("bertopic_metrics"),
            "lda":      report.get("lda_metrics"),
            "nmf":      report.get("nmf_metrics"),
        },
        "model_scores":  report.get("model_metric_scores"),
        "winner_rule":   report.get("winner_selection_rule"),
        "evaluated_at":  report.get("generated_at"),
    }


@router.get("/models/history")
async def get_model_history(
    limit: int = 20,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """Training run history from pipeline_history collection."""
    query: dict = {"pipeline": "bertopic"}
    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["trained_at"] = time_filter
    cursor = db["pipeline_history"].find(query, {"_id": 0}).sort("trained_at", -1).limit(limit)
    records = await cursor.to_list(length=limit)
    return records


@router.post("/jobs/run-evaluation")
async def trigger_full_evaluation(
    force: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """
    Manually trigger three-way evaluation, select winner, and deploy (authenticated).
    Pass ?force=true to bypass the new-data guard and re-evaluate on existing corpus.
    """
    from jobs.evaluation_pipeline import run_full_evaluation
    return await run_full_evaluation(force=force)



# --- ADAPTER ROUTES FOR FRONTEND COMPATIBILITY ---

def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


_URL_RE = _re_routes.compile(r'https?://\S+')

def _dedup_docs(docs: list) -> list:
    """Return up to 3 docs, deduplicating by URL-stripped text."""
    seen: set = set()
    result: list = []
    for d in docs:
        if not d:
            continue
        norm = _URL_RE.sub('', d).strip()
        if norm not in seen:
            seen.add(norm)
            result.append(d)
            if len(result) == 3:
                break
    return result


def adapt_trend_to_frontend(t: dict, requested_lang: str):
    """Wraps the strict FYP.ipynb output into the format expected by the legacy Frontend UI."""
    return {
        "_id": str(t.get("_id", t.get("id"))),
        "topic_name": t.get("Name", "Unknown Topic"),
        "label": t.get("label", t.get("Name", "Unknown Topic")),
        "top_keywords": t.get("Representation", []),
        "representative_docs": _dedup_docs(t.get("representative_docs", [])),
        "score": t.get("trend_score", 0.0),
        "volume": t.get("volume", 0),
        "language": t.get("lang") if t.get("lang") in ("en", "so") else requested_lang,
        "timestamp": t.get("tweet_period_to") or t.get("calculated_at", datetime.utcnow()),
        "tweet_period_from": t.get("tweet_period_from"),
        "tweet_period_to": t.get("tweet_period_to"),
        "model": t.get("model"),
    }

@router.get("/trends")
async def get_trends(
    lang: str = "en",
    limit: int = 10,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """Fetch trends: latest batch by default, or filtered by date range."""
    from jobs.deployment import get_deployed_model
    deployed = await get_deployed_model()
    if deployed is None:
        return []

    trends_collection = db["detected_trends"]

    # Check whether the winning model has topics written yet.
    # If deployment hasn't completed after a fresh evaluation (brief race window),
    # fall back to the most-recently-written topics from any model so the frontend
    # never returns an empty list while data exists in the collection.
    winner_has_data = await trends_collection.find_one({"model": deployed})
    effective_model = deployed if winner_has_data else None
    if effective_model is None:
        any_trend = await trends_collection.find_one({}, sort=[("calculated_at", -1)])
        if not any_trend:
            return []
        effective_model = any_trend.get("model", deployed)

    query = {"model": effective_model}
    if lang in ("en", "so"):
        query["lang"] = lang

    import re as _re

    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["peak_at"] = time_filter
        cursor = trends_collection.find(query).sort("trend_score", -1).limit(limit * 5)
        trends = await cursor.to_list(length=limit * 5)
    else:
        # No date filter: fetch all batches sorted newest-batch-first then by score.
        # Dedup below keeps the most-recent version of each topic Name across batches.
        fetch_limit = max(limit * 20, 500)
        cursor = trends_collection.find(query).sort(
            [("calculated_at", -1), ("trend_score", -1)]
        ).limit(fetch_limit)
        trends = await cursor.to_list(length=fetch_limit)

    # Dedup: strip numeric prefix so "0_war_ukraine" and "3_war_ukraine" collapse to
    # "war_ukraine". First occurrence wins — newest batch (sorted above) comes first.
    seen: set = set()
    deduped: list = []
    for t in trends:
        word_key = _re.sub(r'^-?\d+_', '', t.get("Name", ""))
        if word_key not in seen:
            seen.add(word_key)
            deduped.append(t)

    return [adapt_trend_to_frontend(t, lang) for t in deduped[:limit]]

@router.get("/history")
async def get_history(
    lang: str = "en",
    topic_name: Optional[str] = None,
    limit: int = 50,
    from_date: Optional[str] = Query(None, description="ISO date lower bound"),
    to_date: Optional[str] = Query(None, description="ISO date upper bound"),
    db=Depends(get_database),
):
    """Fetch historical trends to plot growth volume graph."""
    trends_collection = db["detected_trends"]

    query = {}
    if topic_name:
        query["Name"] = {"$regex": topic_name, "$options": "i"}
    if lang in ("en", "so"):
        query["lang"] = lang

    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["peak_at"] = time_filter

    cursor = trends_collection.find(query).sort("peak_at", -1).limit(limit)
    trends = await cursor.to_list(length=limit)
    return [adapt_trend_to_frontend(t, lang) for t in trends]

@router.post("/filter")
async def filter_trends(keyword: str, lang: str = "en", db=Depends(get_database)):
    """Filter trends by specific keywords."""
    trends_collection = db["detected_trends"]
    
    # The new structure stores keywords in the 'Representation' array
    cursor = trends_collection.find({
        "Representation": {"$regex": keyword, "$options": "i"}
    }).sort("calculated_at", -1).limit(20)
    
    trends = await cursor.to_list(length=20)
    return [adapt_trend_to_frontend(t, lang) for t in trends]

@router.get("/raw_tweets")
async def get_raw_tweets(
    lang: str = "en",
    limit: int = 50,
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database)
):
    """Fetch raw tweets (adapter for frontend)."""
    raw_collection = db["raw_tweets"]
    
    query = {"lang_api": lang}
    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["collected_at"] = time_filter

    cursor = raw_collection.find(query).sort("collected_at", -1).limit(limit)
    tweets = await cursor.to_list(length=limit)
    
    # Adapt to Frontend
    results = []
    for t in tweets:
        results.append({
            "_id": str(t["_id"]),
            "tweet_id": t.get("id", ""),
            "text": t.get("text", ""),
            "language": t.get("lang_api", lang),
            "timestamp": t.get("collected_at", datetime.utcnow()),
            "engagement_metrics": t.get("like_count", 0) + t.get("retweet_count", 0)
        })
    return results


@router.get("/trends/topics_over_time")
async def get_trends_topics_over_time(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """Aggregate real topic frequencies over time from detected_trends, limited to top 5 topics."""
    col = db["detected_trends"]
    
    query = {}
    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["calculated_at"] = time_filter
        
    cursor = col.find(query).sort("calculated_at", 1)
    docs = await cursor.to_list(length=2000)
    
    def get_clean_topic_name(name: str, representation: list) -> str:
        words = [w.lower() for w in representation] + name.lower().split('_')
        
        if any(w in words for w in ["war", "security", "military", "police", "dagaal", "amniga", "conflict", "israel", "iran"]):
            return "Security"
        if any(w in words for w in ["politics", "political", "election", "trump", "government", "democracy", "parliament", "siyaasad", "madaxweyne"]):
            return "Politics"
        if "ai" in words or "artificial" in words:
            return "AI"
        if any(w in words for w in ["economy", "economic", "finance", "stock", "stocks", "profits", "dhaqaalaha"]):
            return "Economy"
        if any(w in words for w in ["business", "company", "market", "trade"]):
            return "Business"
        if any(w in words for w in ["cup", "football", "futbol", "sports", "sport", "game"]):
            return "Sports"
        if any(w in words for w in ["health", "medical", "hospital", "doctor", "virus", "vaccine"]):
            return "Health"
        if any(w in words for w in ["education", "school", "university", "student", "academic"]):
            return "Education"
        if any(w in words for w in ["technology", "tech", "software", "digital", "internet"]):
            return "Technology"
        if any(w in words for w in ["climate", "weather", "environment", "earth"]):
            return "Climate"
        return "Other"
        
    daily_data = {}
    
    for doc in docs:
        ts = doc.get("calculated_at")
        if not ts:
            continue
            
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                try:
                    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    
        date_str = ts.strftime("%b %d")
        
        name = doc.get("Name", "")
        rep = doc.get("Representation", [])
        volume = doc.get("volume", 0)
        
        category = get_clean_topic_name(name, rep)
        
        if date_str not in daily_data:
            daily_data[date_str] = {
                "date": date_str
            }
            
        if category not in daily_data[date_str]:
            daily_data[date_str][category] = 0
            
        daily_data[date_str][category] += volume

    # 1. Calculate total volume for each category to identify top 5
    total_volumes = {}
    for day in daily_data.values():
        for cat, vol in day.items():
            if cat != "date":
                total_volumes[cat] = total_volumes.get(cat, 0) + vol
                
    # Get top 5 categories by total volume
    top_categories = sorted(total_volumes.keys(), key=lambda c: total_volumes[c], reverse=True)[:5]
    
    # 2. Sort the dates and assemble results with uniform keys (only top 5 categories)
    sorted_days = sorted(daily_data.keys(), key=lambda d: datetime.strptime(d + f" {datetime.now().year}", "%b %d %Y"))
    
    results = []
    for d in sorted_days:
        day_cleaned = {"date": d}
        for cat in top_categories:
            day_cleaned[cat] = daily_data[d].get(cat, 0)
        results.append(day_cleaned)
        
    return results


@router.get("/trends/keywords")
async def get_trends_keywords(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database),
):
    """Aggregate real top keywords and their frequencies from raw_tweets."""
    col = db["raw_tweets"]
    
    query = {}
    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["collected_at"] = time_filter
        
    cursor = col.find(query).sort("collected_at", -1)
    tweets = await cursor.to_list(length=1000)
    
    # Extract keywords
    import re
    from collections import Counter
    
    ENGLISH_STOPWORDS = {
        "the", "and", "to", "of", "a", "in", "is", "that", "it", "for", "on", "with", "as", "at", "by", "an", "be", "this", "are", "from", "was", "but", "not", "he", "she", "they", "we", "i", "you", "your", "my", "me", "our", "us", "about", "all", "any", "can", "do", "go", "has", "have", "had", "his", "her", "him", "into", "its", "just", "like", "more", "no", "or", "out", "so", "some", "up", "will", "what", "which", "who", "get", "rt", "http", "https", "co", "amp", "via", "after", "full", "use", "because", "over", "years", "then", "only", "those", "may", "now", "new", "most", "only", "other", "them", "then", "also", "into", "than", "were", "been", "would", "could", "should", "some", "very", "make", "made", "here", "there", "when", "how", "why", "where", "who", "what", "which", "one", "two", "three", "four", "five", "first", "second", "third", "day", "days", "time", "year", "years", "week", "weeks"
    }

    SOMALI_STOPWORDS = {
        "waa", "ee", "oo", "eey", "eeu", "ku", "ka", "la", "in", "uu", "ay", "ayuu", "ayey", "soo", "u", "kuwa", "kula", "kaga", "kuba", "si", "wuxuu", "waxay", "iska", "amma", "ama", "leh", "ah", "e", "loo", "eey", "iwu", "ahaa", "ahaantii", "ayadoo", "iyadoo", "kuwaas"
    }

    STOPWORDS = ENGLISH_STOPWORDS.union(SOMALI_STOPWORDS)
    
    words_list = []
    for t in tweets:
        text = t.get("text", "")
        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", "", text)
        # Remove mentions
        text = re.sub(r"@\w+", "", text)
        # Find words
        words = re.findall(r"\b\w{3,15}\b", text.lower())
        for w in words:
            if w.isdigit() or w in STOPWORDS:
                continue
            words_list.append(w)
            
    counts = Counter(words_list)
    top_words = counts.most_common(30)
    
    results = [{"text": word, "value": freq} for word, freq in top_words]
    return results


@router.get("/tweets/stats")
async def get_tweet_stats(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db=Depends(get_database)
):
    """Retrieve raw tweet metrics directly from MongoDB raw_tweets collection with optional date filters."""
    raw_collection = db["raw_tweets"]
    
    query = {}
    if from_date or to_date:
        time_filter = {}
        if from_date:
            time_filter["$gte"] = _parse_iso_datetime(from_date)
        if to_date:
            time_filter["$lte"] = _parse_iso_datetime(to_date)
        query["collected_at"] = time_filter
        
    total = await raw_collection.count_documents(query)
    
    en_query = {"lang_api": "en"}
    if query:
        en_query.update(query)
    english = await raw_collection.count_documents(en_query)
    
    so_query = {"lang_api": "so"}
    if query:
        so_query.update(query)
    somali = await raw_collection.count_documents(so_query)
    
    return {
        "totalTweets": total,
        "totalEnglishTweets": english,
        "totalSomaliTweets": somali
    }


