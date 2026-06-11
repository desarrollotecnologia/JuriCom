"""Endpoints de gestión de usuarios (sólo admin).

El admin puede:
- Crear usuarios con cualquier rol.
- Listar todos los usuarios.
- Editar username, rol y estado activo de cualquier usuario.
- Reasignar contraseña de cualquier usuario.
- Eliminar usuarios.

Nota: ver contraseñas en texto plano no es posible (bcrypt es irreversible).
Para "cambiar" la contraseña a otro usuario se reasigna una nueva.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.application.interfaces.contrato_repository import ContratoRepository
from app.application.interfaces.password_hasher import PasswordHasher
from app.application.interfaces.user_repository import UserRepository
from app.application.use_cases.users import (
    ChangePassword,
    CreateUser,
    DeleteUser,
    ListUsers,
    RevealPasswordPolicy,
    UpdateUser,
)
from app.domain.entities.user import User
from app.domain.exceptions import (
    UnauthorizedError,
    UserAlreadyExistsError,
    UserInUseError,
    UserNotFoundError,
)
from app.presentation.api.v1.dependencies import (
    get_contrato_repository,
    get_current_user,
    get_password_hasher,
    get_user_repository,
    require_admin,
)
from app.presentation.api.v1.schemas import (
    ChangePasswordRequest,
    UserCreateRequest,
    UserPublic,
    UserUpdateRequest,
)


router = APIRouter(prefix="/users", tags=["users"])


def _to_public(u: User) -> UserPublic:
    return UserPublic(
        id=u.id,
        username=u.username,
        role=u.role,
        is_active=u.is_active,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


@router.get("", response_model=list[UserPublic])
def list_users(
    admin: User = Depends(require_admin),
    users: UserRepository = Depends(get_user_repository),
) -> list[UserPublic]:
    items = ListUsers(users).execute(actor=admin)
    return [_to_public(u) for u in items]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    admin: User = Depends(require_admin),
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> UserPublic:
    try:
        created = CreateUser(users, hasher).execute(
            actor=admin,
            username=payload.username,
            password=payload.password,
            role=payload.role,
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except (ValueError, UnauthorizedError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_public(created)


@router.put("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    admin: User = Depends(require_admin),
    users: UserRepository = Depends(get_user_repository),
) -> UserPublic:
    try:
        updated = UpdateUser(users).execute(
            actor=admin,
            target_user_id=user_id,
            new_username=payload.username,
            new_role=payload.role,
            new_is_active=payload.is_active,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    return _to_public(updated)


@router.put("/{user_id}/password", response_model=UserPublic)
def change_password(
    user_id: int,
    payload: ChangePasswordRequest,
    current: User = Depends(get_current_user),
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> UserPublic:
    try:
        updated = ChangePassword(users, hasher).execute(
            actor=current,
            target_user_id=user_id,
            new_password=payload.new_password,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return _to_public(updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    users: UserRepository = Depends(get_user_repository),
    contratos: ContratoRepository = Depends(get_contrato_repository),
) -> None:
    try:
        DeleteUser(users, contratos).execute(actor=admin, target_user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except UserInUseError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.get("/password-policy")
def password_policy(_: User = Depends(require_admin)) -> dict:
    """Devuelve la política sobre por qué no se muestran contraseñas en claro."""
    return {"message": RevealPasswordPolicy.MESSAGE}
