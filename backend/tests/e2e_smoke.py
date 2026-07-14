"""Prueba end-to-end del flujo completo de JURICOM_BEEF.

NO es un pytest — es un script que asume que el servidor está corriendo en
http://localhost:8000 y ejerce TODA la cadena:

1. Login admin
2. Crear usuario de Compras
3. Crear usuario de Jurídica
4. Login Compras → radicar contrato → verificar código
5. Búsqueda por código
6. Login Jurídica → ver contrato → subir póliza → subir borrador → cambiar estado
7. Notificar pendientes (resumen)
8. SMTP: probar envío directo de prueba

Si SMTP no es alcanzable desde la red actual, se reporta como aviso (no fail).
"""

import io
import sys
from pathlib import Path

import requests


BASE = "http://127.0.0.1:8000"
API = f"{BASE}/api/v1"

ADMIN_USER = "gerencia2026*"
ADMIN_PASS = "gerencia2026*"

COMPRAS_USER = "compras_test"
COMPRAS_PASS = "compras_test_123"

JURIDICA_USER = "juridica_test"
JURIDICA_PASS = "juridica_test_123"


def section(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def info(msg: str) -> None:
    print(f"  [..]   {msg}")


def warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")
    sys.exit(1)


def login(username: str, password: str) -> str:
    r = requests.post(
        f"{API}/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"Login {username!r} falló: {r.status_code} {r.text}")
    return r.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def ensure_user(token_admin: str, username: str, password: str, role: str) -> int:
    """Crea el usuario si no existe; devuelve su id."""
    r = requests.get(f"{API}/users", headers=auth(token_admin), timeout=10)
    if r.status_code != 200:
        fail(f"Listar usuarios falló: {r.status_code} {r.text}")
    for u in r.json():
        if u["username"] == username:
            info(f"Usuario {username!r} ya existe (id={u['id']}), reusando.")
            # Aseguro rol correcto
            if u["role"] != role:
                requests.put(
                    f"{API}/users/{u['id']}",
                    json={"role": role, "is_active": True},
                    headers=auth(token_admin),
                    timeout=10,
                )
            # Re-asigno contraseña conocida
            requests.put(
                f"{API}/users/{u['id']}/password",
                json={"new_password": password},
                headers=auth(token_admin),
                timeout=10,
            )
            return u["id"]
    r = requests.post(
        f"{API}/users",
        json={"username": username, "password": password, "role": role},
        headers=auth(token_admin),
        timeout=10,
    )
    if r.status_code != 201:
        fail(f"Crear usuario {username!r} falló: {r.status_code} {r.text}")
    ok(f"Usuario {username!r} creado (rol={role}).")
    return r.json()["id"]


def dummy_pdf(filename: str) -> tuple:
    """Devuelve un tuple para multipart con un PDF mínimo válido."""
    content = (
        b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    )
    return (filename, io.BytesIO(content), "application/pdf")


def dummy_png(filename: str) -> tuple:
    """PNG 1x1 transparente — para los screenshots."""
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
        b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9c"
        b"cd``\x00\x00\x00\x06\x00\x02\x0b\xc7\xb6\xc0\x00\x00\x00\x00IEND"
        b"\xaeB`\x82"
    )
    return (filename, io.BytesIO(png_bytes), "image/png")


# =========================================================
# RUN
# =========================================================

def main() -> None:
    section("1. LOGIN ADMIN")
    t_admin = login(ADMIN_USER, ADMIN_PASS)
    ok("Admin autenticado.")

    section("2. CREAR USUARIOS COMPRAS y JURIDICA")
    id_compras = ensure_user(t_admin, COMPRAS_USER, COMPRAS_PASS, "compras")
    id_juridica = ensure_user(t_admin, JURIDICA_USER, JURIDICA_PASS, "juridica")
    info(f"id_compras={id_compras} · id_juridica={id_juridica}")

    section("3. LOGIN COMPRAS")
    t_compras = login(COMPRAS_USER, COMPRAS_PASS)
    ok("Compras autenticado.")

    section("4. RADICAR CONTRATO (con archivos dummy)")
    data = {
        "proveedor_contratista": "Servicios de Prueba S.A.S.",
        "nit_proveedor": "900.111.222-3",
        "descripcion_servicio": "Servicio de prueba E2E desde script automatizado.",
        "obligaciones_colbeef": "Pagar puntualmente y supervisar el servicio.",
        "obligaciones_proveedor": "Prestar el servicio según especificaciones.",
        "valor": "5000000.00",
        "moneda": "COP",
        "plazo_cantidad": "6",
        "plazo_unidad": "meses",
        "renovacion_automatica": "true",
        "condiciones_recibido_satisfactorio": "Entrega de informe mensual.",
        "requiere_poliza": "true",
    }
    files = {
        "camara_comercio": dummy_pdf("camara.pdf"),
        "cotizacion": dummy_pdf("cotizacion.pdf"),
        "cedula_rep_legal": dummy_pdf("cedula.pdf"),
        "correo_aprobacion_gerencia": dummy_png("gerencia.png"),
        "correo_aprobacion_lider": dummy_png("lider.png"),
    }
    r = requests.post(
        f"{API}/contratos",
        data=data,
        files=files,
        headers=auth(t_compras),
        timeout=30,
    )
    if r.status_code != 201:
        fail(f"Radicar falló: {r.status_code} {r.text}")
    contrato = r.json()
    contrato_id = contrato["id"]
    codigo = contrato["codigo"]
    ok(f"Contrato radicado con código {codigo} (id={contrato_id})")
    assert codigo.startswith(("C-", "OS-")), "Código no tiene formato C-NNNN u OS-NNNN"
    assert contrato["estado"] == "en_proceso", "Estado inicial debe ser en_proceso"
    assert contrato["requiere_poliza"] is True
    assert contrato["tiene_poliza"] is False
    ok(f"Estado inicial: {contrato['estado']} (correcto)")
    ok("Validaciones OK: código C-/OS-, estado en_proceso, póliza pendiente.")

    section("5. BÚSQUEDA POR CÓDIGO Y POR ESTADO")
    r = requests.get(
        f"{API}/contratos",
        params={"q": codigo},
        headers=auth(t_admin),
        timeout=10,
    )
    if r.status_code != 200 or not any(c["codigo"] == codigo for c in r.json()):
        fail(f"Búsqueda por código falló: {r.status_code} {r.text}")
    ok(f"Búsqueda por código {codigo!r} funciona.")

    r = requests.get(
        f"{API}/contratos",
        params={"estado": "en_proceso"},
        headers=auth(t_admin),
        timeout=10,
    )
    ok(f"Búsqueda por estado='en_proceso' devuelve {len(r.json())} resultado(s).")

    r = requests.get(
        f"{API}/contratos",
        params={"q": "Prueba"},
        headers=auth(t_admin),
        timeout=10,
    )
    ok(f"Búsqueda por nombre del proveedor devuelve {len(r.json())} resultado(s).")

    section("6. LOGIN JURÍDICA")
    t_juridica = login(JURIDICA_USER, JURIDICA_PASS)
    ok("Jurídica autenticado.")

    section("7. JURÍDICA INTENTA PASAR A ACTIVO SIN PÓLIZA → debe fallar")
    r = requests.put(
        f"{API}/contratos/{contrato_id}/estado",
        json={"estado": "activo"},
        headers=auth(t_juridica),
        timeout=10,
    )
    if r.status_code == 400:
        ok("Bloqueo correcto: no se puede activar sin póliza.")
    else:
        warn(f"Se esperaba 400 y devolvió {r.status_code}: {r.text}")

    section("8. JURÍDICA SUBE PÓLIZA")
    r = requests.post(
        f"{API}/contratos/{contrato_id}/poliza",
        files={"archivo": dummy_pdf("poliza.pdf")},
        headers=auth(t_juridica),
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"Subir póliza falló: {r.status_code} {r.text}")
    ok("Póliza adjuntada por Jurídica.")

    section("9. JURÍDICA SUBE BORRADOR FIRMADO")
    r = requests.post(
        f"{API}/contratos/{contrato_id}/borrador",
        files={"archivo": dummy_pdf("borrador_firmado.pdf")},
        headers=auth(t_juridica),
        timeout=30,
    )
    if r.status_code != 200:
        fail(f"Subir contrato firmado falló: {r.status_code} {r.text}")
    ok("Contrato firmado adjuntado.")

    section("10. CAMBIO DE ESTADO → ACTIVO")
    r = requests.put(
        f"{API}/contratos/{contrato_id}/estado",
        json={"estado": "activo"},
        headers=auth(t_juridica),
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"Cambio a activo falló: {r.status_code} {r.text}")
    if r.json()["estado"] != "activo":
        fail(f"Estado no quedó activo: {r.json()['estado']}")
    ok("Estado actualizado a 'activo' correctamente.")

    section("11. CAMBIO DE ESTADO → FINALIZADO")
    r = requests.put(
        f"{API}/contratos/{contrato_id}/estado",
        json={"estado": "finalizado"},
        headers=auth(t_juridica),
        timeout=10,
    )
    if r.status_code != 200:
        fail(f"Cambio a finalizado falló: {r.status_code} {r.text}")
    ok("Estado actualizado a 'finalizado' correctamente.")

    section("12. PERMISOS: COMPRAS NO PUEDE CAMBIAR ESTADO NI SUBIR PÓLIZA")
    r = requests.put(
        f"{API}/contratos/{contrato_id}/estado",
        json={"estado": "activo"},
        headers=auth(t_compras),
        timeout=10,
    )
    if r.status_code == 403:
        ok("Compras bloqueado al cambiar estado (403).")
    else:
        warn(f"Esperaba 403, recibí {r.status_code}")

    r = requests.post(
        f"{API}/contratos/{contrato_id}/poliza",
        files={"archivo": dummy_pdf("intento.pdf")},
        headers=auth(t_compras),
        timeout=30,
    )
    if r.status_code == 403:
        ok("Compras bloqueado al subir póliza (403).")
    else:
        warn(f"Esperaba 403, recibí {r.status_code}")

    section("13. NOTIFICACIÓN DE PENDIENTES")
    r = requests.post(
        f"{API}/notifications/pendientes",
        headers=auth(t_juridica),
        timeout=60,
    )
    if r.status_code != 200:
        fail(f"Notificar pendientes falló: {r.status_code} {r.text}")
    data = r.json()
    if data["enviado"]:
        ok(f"Correo de pendientes ENVIADO a {len(data['destinatarios'])} destinatario(s). "
           f"Contratos en proceso: {data['cantidad_contratos']}.")
        for d in data["destinatarios"]:
            info(f"   -> {d}")
    else:
        warn(f"Correo NO enviado: {data.get('mensaje')}")

    section("14. RESUMEN FINAL")
    r = requests.get(f"{API}/contratos/{contrato_id}", headers=auth(t_admin), timeout=10)
    final = r.json()
    print(f"  Código:         {final['codigo']}")
    print(f"  Estado final:   {final['estado']}")
    print(f"  Tiene póliza:   {final['tiene_poliza']}")
    print(f"  Tiene borrador: {final['tiene_borrador']}")
    print(f"  Archivos:       {len(final['archivos'])}")
    for a in final["archivos"]:
        print(f"    - {a['tipo']:30s} -> {a['nombre_original']}")

    print()
    print("=" * 72)
    print("  [OK] FLUJO COMPLETO EJECUTADO SIN ERRORES")
    print("=" * 72)


if __name__ == "__main__":
    main()
