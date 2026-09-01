"""Verifica el soporte multi-rol: entidad User y parse/serialize del repo."""

from app.domain.entities.user import User
from app.domain.value_objects.roles import Role
from app.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository as Repo,
)


def test_usuario_con_rol_extra_tiene_ambos():
    u = User(
        username="julian",
        password_hash="x",
        role=Role.SOLICITANTE,
        extra_roles=[Role.JURIDICA],
    )
    assert u.is_solicitante() is True
    assert u.is_juridica() is True
    assert u.is_compras() is False
    assert u.roles() == [Role.SOLICITANTE, Role.JURIDICA]
    # Un solicitante+jurídica sigue pudiendo crear solicitudes.
    assert u.puede_crear_solicitudes_gestion() is True


def test_roles_no_duplica_principal_en_extras():
    u = User(
        username="dup",
        password_hash="x",
        role=Role.JURIDICA,
        extra_roles=[Role.JURIDICA, Role.ADMIN],
    )
    assert u.roles() == [Role.JURIDICA, Role.ADMIN]


def test_parse_extra_roles_ignora_principal_e_invalidos():
    extras = Repo._parse_extra_roles("juridica,compras", Role.SOLICITANTE)
    assert extras == [Role.JURIDICA, Role.COMPRAS]

    # Ignora el principal repetido, espacios y valores basura.
    extras = Repo._parse_extra_roles(" solicitante , basura , juridica ", Role.SOLICITANTE)
    assert extras == [Role.JURIDICA]


def test_serialize_extra_roles_round_trip():
    u = User(
        username="nidia",
        password_hash="x",
        role=Role.LIDER_APROBADOR,
        extra_roles=[Role.JURIDICA],
    )
    serial = Repo._serialize_extra_roles(u)
    assert serial == "juridica"
    extras = Repo._parse_extra_roles(serial, u.role)
    assert extras == [Role.JURIDICA]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"OK {name}")
    print("Todos los checks multi-rol pasaron.")
