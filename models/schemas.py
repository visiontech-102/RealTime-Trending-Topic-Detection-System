from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

# Users
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str = Field(alias="_id")
    username: str
    email: EmailStr
    created_at: datetime
    
    class Config:
        populate_by_name = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Tweets
class TweetData(BaseModel):
    tweet_id: str
    text: str
    language: str
    timestamp: datetime
    engagement_metrics: int

# Trends
class TrendResponse(BaseModel):
    id: str = Field(alias="_id")
    topic_name: str
    top_keywords: List[str]
    representative_docs: List[str]
    score: float
    language: str
    timestamp: datetime
    
    class Config:
        populate_by_name = True
