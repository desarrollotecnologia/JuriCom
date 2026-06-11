"""Endpoints de autenticación."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.token_service import TokenService
from app.application.interfaces.user_repository import UserRepository
from app.application.use_cases.auth import LoginUser
from app.domain.entities.user import User
from app.domain.exceptions import InvalidCredentialsError
from app.presentation.api.v1.dependencies import (
    get_current_user,
    get_password_hasher,
    get_token_service,
    get_user_repository,
)
from app.presentation.api.v1.schemas import (
    LoginRequest,
    TokenResponse,
    UserPublic,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
    tokens: TokenService = Depends(get_token_service),
) -> TokenResponse:
    try:
        result = LoginUser(users, hasher, tokens).execute(
            username=payload.username,
            password=payload.password,
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=UserPublic(
            id=result.user.id,
            username=result.user.username,
            role=result.user.role,
            is_active=result.user.is_active,
            created_at=result.user.created_at,
            updated_at=result.user.updated_at,
        ),
    )


@router.get("/me", response_model=UserPublic)
def me(current: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic(
        id=current.id,
        username=current.username,
        role=current.role,
        is_active=current.is_active,
        created_at=current.created_at,
        updated_at=current.updated_at,
    )
