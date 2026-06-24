"""Schemas Pydantic para gestión de usuarios."""

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.value_objects.roles import Role


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=4, max_length=200)
    role: Role
    email: str = Field(default="", max_length=255)


class UserUpdateRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    email: Optional[str] = Field(None, max_length=255)


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=200)
