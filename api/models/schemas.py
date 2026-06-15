from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any
from datetime import datetime

# Users
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class TwoFactorVerifyRequest(BaseModel):
    code: str

class TwoFactorStatusResponse(BaseModel):
    two_factor_enabled: bool

class UserPreferences(BaseModel):
    email_digests: bool
    spike_alerts: bool

class UserResponse(BaseModel):
    id: Any = Field(alias="_id")
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
    id: str
    text: str
    lang_api: str
    created_at: datetime
    retweet_count: int = 0
    like_count: int = 0
    collected_at: datetime
    
    # Optional fields added during processing pipeline
    lang: Optional[str] = None
    clean_text: Optional[str] = None
    topic: Optional[int] = None

# Trends 
class TrendResponse(BaseModel):
    id: Any = Field(default=None, alias="_id")
    topic: int
    volume: int
    total_likes: int
    total_retweets: int
    trend_score: float
    Name: str
    Representation: List[str]
    calculated_at: datetime
    
    class Config:
        populate_by_name = True
