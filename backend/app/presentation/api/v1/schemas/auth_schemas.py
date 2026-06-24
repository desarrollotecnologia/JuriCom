"""Schemas Pydantic para autenticación."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.value_objects.roles import Role


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class UserPublic(BaseModel):
    id: int
    username: str
    role: Role
    email: str = ""
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserPublic
