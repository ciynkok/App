from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class Provider(str, Enum):
    google = "google"
    github = "github"


# Request schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refreshToken: str


# Response schemas
class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str


class AuthResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserResponse

'''
class OAuthCallbackResponse(BaseModel):
    message: str = "Authentication successful"
    accessToken: Optional[str] = None
    refreshToken: Optional[str] = None
'''

# Validation schemas
class TokenValidateResponse(BaseModel):
    """Ответ валидации токена для межсервисного общения"""
    valid: bool
    user_id: str
    email: str
    exp: Optional[datetime] = None
    iat: Optional[datetime] = None
