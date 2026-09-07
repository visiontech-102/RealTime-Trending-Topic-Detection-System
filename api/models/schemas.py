import re

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List, Optional, Any
from datetime import datetime

# --- Password policy ---
# Enforced server-side: the browser's minLength attribute is trivially bypassed
# by calling the API directly, so it cannot be the only check.
MIN_PASSWORD_LENGTH = 8


def validate_password_strength(value: str) -> str:
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number")
    return value


# Users
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

class TwoFactorVerifyRequest(BaseModel):
    code: str

class TwoFactorDisableRequest(BaseModel):
    """
    Re-authentication before switching 2FA off. Either proof is accepted:
    the account password, or a fresh emailed code (for Google-provisioned
    accounts, which have no password their owner knows).
    """
    password: Optional[str] = None
    code: Optional[str] = None

class TwoFactorLoginRequest(BaseModel):
    """Second step of login: exchange a challenge token + emailed code for a real token."""
    challenge_token: str
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

class LoginResponse(BaseModel):
    """
    Login result. When the account has 2FA enabled no access token is issued —
    only a short-lived challenge token that is useless against any other endpoint.
    """
    access_token: Optional[str] = None
    token_type: str = "bearer"
    requires_2fa: bool = False
    challenge_token: Optional[str] = None
    # Populated only when TWO_FA_DEV_ECHO=true (offline demos). Never set in production.
    dev_code: Optional[str] = None

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
