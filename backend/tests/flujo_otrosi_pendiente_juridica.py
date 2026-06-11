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


def otrosi_token(contrato_id: int, otrosi_id: int, paso: str) -> str:
    payload = f"otrosi:{contrato_id}:{otrosi_id}:{paso}".encode("utf-8")
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def main() -> None:
    admin_token = login("gerencia2026*", "gerencia2026*")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    ensure_user(admin_token, "compras_otrosi_pendiente", "Compras123*", "compras")
    ensure_user(admin_token, "juridica_otrosi_pendiente", "Juridica123*", "juridica")

    compras_token = login("compras_otrosi_pendiente", "Compras123*")
    compras_headers = {"Authorization": f"Bearer {compras_token}"}
    juridica_token = login("juridica_otrosi_pendiente", "Juridica123*")
    juridica_headers = {"Authorization": f"Bearer {juridica_token}"}

    files = {
        "camara_comercio": ("camara.pdf", io.BytesIO(b"camara"), "application/pdf"),
        "cotizacion": ("cotizacion.pdf", io.BytesIO(b"cotizacion"), "application/pdf"),
        "cedula_rep_legal": ("cedula.pdf", io.BytesIO(b"cedula"), "application/pdf"),
    }
    data = {
        "proveedor_contratista": "Proveedor Otrosi Pendiente SAS",
        "nit_proveedor": "901-OTROSI-PEND",
        "descripcion_servicio": "Contrato activo para flujo de otrosi pendiente",
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
    print(f"[OK] contrato radicado {contrato['codigo']}")

    for paso in ("lider", "gerencia"):
        response = requests.get(
            f"{BASE}/contratos/{contrato_id}/aprobar/{paso}",
            params={"token": approval_token(contrato_id, paso)},
        )
        response.raise_for_status()
        print(f"[OK] contrato aprobado por {paso}")

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
            "descripcion": "Solicitud de prorroga por 2 meses",
            "plazo_adicional_cantidad": "2",
        },
    )
    response.raise_for_status()
    contrato_con_solicitud = response.json()
    otrosi = contrato_con_solicitud["otrosies"][-1]
    otrosi_id = otrosi["id"]
    assert otrosi["estado_aprobacion"] == "pendiente_lider"
    assert contrato_con_solicitud["plazo_cantidad"] == 6
    print(f"[OK] solicitud otrosi creada pendiente_lider id={otrosi_id}")

    for paso in ("lider", "gerencia"):
        response = requests.get(
            f"{BASE}/contratos/{contrato_id}/otrosi/{otrosi_id}/aprobar/{paso}",
            params={"token": otrosi_token(contrato_id, otrosi_id, paso)},
        )
        response.raise_for_status()
        print(f"[OK] otrosi aprobado por {paso}")

    response = requests.get(f"{BASE}/contratos/otrosies/pendientes", headers=juridica_headers)
    response.raise_for_status()
    pendientes = response.json()
    assert any(item["otrosi"]["id"] == otrosi_id for item in pendientes)
    print("[OK] otrosi aparece pendiente para Juridica")

    response = requests.post(
        f"{BASE}/contratos/{contrato_id}/otrosi/{otrosi_id}/finalizar",
        headers=juridica_headers,
        data={
            "tipo": "prorroga",
            "descripcion": "Prorroga final revisada por Juridica",
            "plazo_adicional_cantidad": "2",
        },
        files={"archivo": ("otrosi-firmado.pdf", io.BytesIO(b"firmado"), "application/pdf")},
    )
    response.raise_for_status()
    final = response.json()
    final_otrosi = next(o for o in final["otrosies"] if o["id"] == otrosi_id)
    assert final["plazo_cantidad"] == 8
    assert final_otrosi["archivo_id"] is not None
    print("[OK] Juridica cargo firmado y aplico otrosi sin reenviar aprobaciones")


if __name__ == "__main__":
    main()
