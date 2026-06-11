from __future__ import annotations

import hashlib
import hmac
import io

import requests

from app.infrastructure.config import settings


BASE = "http://127.0.0.1:8000/api/v1"


def token(contrato_id: int, paso: str) -> str:
    payload = f"{contrato_id}:{paso}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{BASE}/auth/login", json={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def ensure_user(admin_token: str, username: str, password: str, role: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = requests.get(f"{BASE}/users", headers=headers).json()
    if any(u["username"] == username for u in users):
        print(f"[OK] usuario {username} ya existe")
        return
    response = requests.post(
        f"{BASE}/users",
        headers=headers,
        json={"username": username, "password": password, "role": role},
    )
    response.raise_for_status()
    print(f"[OK] usuario {username} creado")


def main() -> None:
    admin_token = login("gerencia2026*", "gerencia2026*")
    print("[OK] admin login")
    ensure_user(admin_token, "compras_prueba", "Compras123*", "compras")
    ensure_user(admin_token, "juridica_prueba", "Juridica123*", "juridica")

    compras_token = login("compras_prueba", "Compras123*")
    files = {
        "camara_comercio": ("camara.pdf", io.BytesIO(b"camara"), "application/pdf"),
        "cotizacion": ("cotizacion.pdf", io.BytesIO(b"cot"), "application/pdf"),
        "cedula_rep_legal": ("cedula.pdf", io.BytesIO(b"cedula"), "application/pdf"),
    }
    data = {
        "proveedor_contratista": "Proveedor Flujo Pendiente SAS",
        "nit_proveedor": "901555777-1",
        "descripcion_servicio": "Prueba flujo aprobacion lider gerencia",
        "obligaciones_colbeef": "Pagar segun condiciones",
        "obligaciones_proveedor": "Ejecutar servicio",
        "valor": "2500000",
        "moneda": "COP",
        "plazo_cantidad": "15",
        "plazo_unidad": "dias",
        "renovacion_automatica": "false",
        "condiciones_recibido_satisfactorio": "Validacion del lider",
        "requiere_poliza": "false",
        "correo_lider_proceso": "tommyelite25@gmail.com",
        "correo_gerencia": "desarrollo.tecnologia@colbeef.com",
    }
    response = requests.post(
        f"{BASE}/contratos",
        headers={"Authorization": f"Bearer {compras_token}"},
        data=data,
        files=files,
    )
    response.raise_for_status()
    contrato = response.json()
    contrato_id = contrato["id"]
    print(
        f"[OK] radicado {contrato['codigo']} estado_aprobacion="
        f"{contrato['estado_aprobacion']}"
    )

    response = requests.get(
        f"{BASE}/contratos/{contrato_id}/aprobar/lider",
        params={"token": token(contrato_id, "lider")},
    )
    response.raise_for_status()
    print("[OK] aprobado por lider")

    response = requests.get(
        f"{BASE}/contratos/{contrato_id}/aprobar/gerencia",
        params={"token": token(contrato_id, "gerencia")},
    )
    response.raise_for_status()
    print("[OK] aprobado por gerencia")

    juridica_token = login("juridica_prueba", "Juridica123*")
    pendientes = requests.get(
        f"{BASE}/contratos?estado=en_proceso",
        headers={"Authorization": f"Bearer {juridica_token}"},
    )
    pendientes.raise_for_status()
    match = next((c for c in pendientes.json() if c["id"] == contrato_id), None)
    if not match:
        raise AssertionError("El contrato no aparece en pendientes juridica.")
    print(f"[OK] aparece en Pendientes Juridica: {match['codigo']}")


if __name__ == "__main__":
    main()
