from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import List, Optional

from database.connection import get_database
from models.schemas import UserCreate, UserResponse, Token, TrendResponse
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
        
    user = await db["users"].find_one({"username": username})
    if user is None:
        raise credentials_exception
    return user


@router.post("/auth/signup", response_model=UserResponse)
async def signup(user: UserCreate, db=Depends(get_database)):
    users_collection = db["users"]
    
    existing_user = await users_collection.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
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
    user = await users_collection.find_one({"username": form_data.username})
    
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

@router.get("/trends", response_model=List[TrendResponse])
async def get_trends(lang: str = "en", limit: int = 10, db=Depends(get_database)):
    """Fetch the latest real-time trends for a specific language."""
    trends_collection = db["trending_topics"]
    cursor = trends_collection.find({"language": lang}).sort("timestamp", -1).limit(limit)
    trends = await cursor.to_list(length=limit)
    
    # Format _id since Pydantic expects hex string or alias
    for t in trends:
        t["_id"] = str(t["_id"])
    return trends

@router.post("/filter", response_model=List[TrendResponse])
async def filter_trends(keyword: str, lang: str = "en", db=Depends(get_database)):
    """Filter trends by specific keywords."""
    trends_collection = db["trending_topics"]
    # Case insensitive regex match in top_keywords
    cursor = trends_collection.find({
        "language": lang,
        "top_keywords": {"$regex": keyword, "$options": "i"}
    }).sort("timestamp", -1).limit(20)
    
    trends = await cursor.to_list(length=20)
    for t in trends:
        t["_id"] = str(t["_id"])
    return trends

@router.get("/history", response_model=List[TrendResponse])
async def get_history(lang: str = "en", current_user=Depends(get_current_user), db=Depends(get_database)):
    """Fetch historical trends to plot growth volume graph."""
    trends_collection = db["trending_topics"]
    # Gets last 50 entries to demonstrate historical growth curve
    cursor = trends_collection.find({"language": lang}).sort("timestamp", -1).limit(50)
    trends = await cursor.to_list(length=50)
    for t in trends:
        t["_id"] = str(t["_id"])
    return trends
