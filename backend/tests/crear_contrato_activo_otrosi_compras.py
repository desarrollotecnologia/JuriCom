from __future__ import annotations

import hashlib
import hmac
import io

import requests

from app.infrastructure.config import settings


BASE = "http://127.0.0.1:8000/api/v1"


def login(username: str, password: str) -> str:
    response = requests.post(
        f"{BASE}/auth/login", json={"username": username, "password": password}
    )
    response.raise_for_status()
    return response.json()["access_token"]


def ensure_user(admin_token: str, username: str, password: str, role: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    users = requests.get(f"{BASE}/users", headers=headers)
    users.raise_for_status()
    if any(u["username"] == username for u in users.json()):
        return
    response = requests.post(
        f"{BASE}/users",
        headers=headers,
        json={"username": username, "password": password, "role": role},
    )
    response.raise_for_status()


def approval_token(contrato_id: int, paso: str) -> str:
    payload = f"{contrato_id}:{paso}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def main() -> None:
    admin_token = login("gerencia2026*", "gerencia2026*")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    ensure_user(admin_token, "compras_prueba", "Compras123*", "compras")
    ensure_user(admin_token, "juridica_prueba", "Juridica123*", "juridica")

    compras_token = login("compras_prueba", "Compras123*")
    compras_headers = {"Authorization": f"Bearer {compras_token}"}

    files = {
        "camara_comercio": ("camara.pdf", io.BytesIO(b"camara"), "application/pdf"),
        "cotizacion": ("cotizacion.pdf", io.BytesIO(b"cotizacion"), "application/pdf"),
        "cedula_rep_legal": ("cedula.pdf", io.BytesIO(b"cedula"), "application/pdf"),
    }
    data = {
        "proveedor_contratista": "Proveedor Activo Otrosi Compras SAS",
        "nit_proveedor": "901-OTROSI-COMPRA",
        "descripcion_servicio": "Contrato activo para probar otrosi desde Compras",
        "obligaciones_colbeef": "Pagar el servicio conforme a entregables",
        "obligaciones_proveedor": "Prestar el servicio y entregar soportes",
        "valor": "3000000",
        "moneda": "COP",
        "plazo_cantidad": "6",
        "plazo_unidad": "meses",
        "renovacion_automatica": "false",
        "condiciones_recibido_satisfactorio": "Acta de recibido del lider",
        "requiere_poliza": "false",
        "correo_lider_proceso": "tommyelite25@gmail.com",
        "correo_gerencia": "desarrollo.tecnologia@colbeef.com",
    }
    response = requests.post(
        f"{BASE}/contratos", headers=compras_headers, data=data, files=files
    )
    response.raise_for_status()
    contrato = response.json()
    contrato_id = contrato["id"]
    print(f"[OK] radicado {contrato['codigo']}")

    for paso in ("lider", "gerencia"):
        response = requests.get(
            f"{BASE}/contratos/{contrato_id}/aprobar/{paso}",
            params={"token": approval_token(contrato_id, paso)},
        )
        response.raise_for_status()
        print(f"[OK] aprobado {paso}")

    response = requests.put(
        f"{BASE}/contratos/{contrato_id}/estado",
        headers=admin_headers,
        json={"estado": "activo"},
    )
    response.raise_for_status()
    print("[OK] contrato activo")

    response = requests.post(
        f"{BASE}/contratos/{contrato_id}/otrosi",
        headers=compras_headers,
        data={
            "tipo": "prorroga",
            "descripcion": "Otrosi de prueba desde Compras: prorroga por 2 meses",
            "plazo_adicional_cantidad": "2",
        },
    )
    response.raise_for_status()
    final = response.json()
    print(
        "[OK] otrosi aplicado por Compras | "
        f"codigo={final['codigo']} estado={final['estado']} "
        f"plazo={final['plazo_cantidad']} {final['plazo_unidad']} "
        f"otrosies={len(final['otrosies'])}"
    )


if __name__ == "__main__":
    main()
