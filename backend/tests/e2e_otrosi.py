"""E2E smoke test del flujo de otrosí.

- Login admin → crea (o reutiliza) usuarios compras y juridica
- Compras radica un contrato (con todos los archivos requeridos)
- Juridica adjunta póliza + borrador
- Juridica activa el contrato
- Juridica aplica varios otrosíes:
    * PRORROGA (suma plazo)
    * ADICION (suma valor)
    * MODIFICACION (cambia descripción)
    * OTRO (sólo deja constancia)
- Verifica que cada cambio se haya aplicado al contrato
- Verifica que un compras NO pueda aplicar otrosí (403)
- Verifica que NO se puedan aplicar otrosíes con el contrato no-activo (409)
"""

from __future__ import annotations

import io
import sys
import time
from decimal import Decimal

import requests

BASE = "http://127.0.0.1:8000/api/v1"

ADMIN_USER = "gerencia2026*"
ADMIN_PASS = "gerencia2026*"

COMPRAS_USER = "compras_otrosi"
COMPRAS_PASS = "Compras123*"
JURIDICA_USER = "juridica_otrosi"
JURIDICA_PASS = "Juridica123*"


def section(t):
    print()
    print("=" * 72)
    print(f" {t}")
    print("=" * 72)


def ok(msg):
    print(f" [OK]   {msg}")


def fail(msg):
    print(f" [FAIL] {msg}")
    sys.exit(1)


def info(msg):
    print(f" [..]   {msg}")


def login(user, pwd) -> str:
    r = requests.post(f"{BASE}/auth/login", json={"username": user, "password": pwd})
    if r.status_code != 200:
        fail(f"login {user}: {r.status_code} {r.text}")
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def ensure_user(admin_token, username, password, role):
    r = requests.get(f"{BASE}/users", headers=auth(admin_token))
    if r.status_code != 200:
        fail(f"listar users: {r.status_code} {r.text}")
    found = next((u for u in r.json() if u["username"] == username), None)
    if found:
        ok(f"usuario {username} ya existe (id={found['id']})")
        return found["id"]
    r = requests.post(
        f"{BASE}/users",
        headers=auth(admin_token),
        json={"username": username, "password": password, "role": role},
    )
    if r.status_code not in (200, 201):
        fail(f"crear user {username}: {r.status_code} {r.text}")
    uid = r.json()["id"]
    ok(f"usuario {username} creado (id={uid})")
    return uid


def radicar_contrato(compras_token):
    files = {
        "camara_comercio": ("camara.pdf", io.BytesIO(b"dummy-camara"), "application/pdf"),
        "cotizacion": ("cotizacion.pdf", io.BytesIO(b"dummy-cot"), "application/pdf"),
        "cedula_rep_legal": ("cedula.pdf", io.BytesIO(b"dummy-ced"), "application/pdf"),
        "correo_aprobacion_gerencia": ("ger.png", io.BytesIO(b"dummy-ger"), "image/png"),
        "correo_aprobacion_lider": ("lid.png", io.BytesIO(b"dummy-lid"), "image/png"),
    }
    data = {
        "proveedor_contratista": "Proveedor Otrosí SAS",
        "nit_proveedor": "900111222-3",
        "descripcion_servicio": "Servicio inicial de mantenimiento",
        "obligaciones_colbeef": "Pagar a tiempo",
        "obligaciones_proveedor": "Cumplir cronograma",
        "valor": "1000000.00",
        "moneda": "COP",
        "plazo_cantidad": "6",
        "plazo_unidad": "meses",
        "renovacion_automatica": "false",
        "condiciones_recibido_satisfactorio": "Acta de recibo firmada",
        "requiere_poliza": "true",
    }
    r = requests.post(
        f"{BASE}/contratos", headers=auth(compras_token), data=data, files=files
    )
    if r.status_code != 201:
        fail(f"radicar: {r.status_code} {r.text}")
    c = r.json()
    ok(f"contrato radicado: id={c['id']} codigo={c['codigo']} estado={c['estado']}")
    return c


def adjuntar(token, contrato_id, kind, fname, content, mime="application/pdf"):
    r = requests.post(
        f"{BASE}/contratos/{contrato_id}/{kind}",
        headers=auth(token),
        files={"archivo": (fname, io.BytesIO(content), mime)},
    )
    if r.status_code not in (200, 201):
        fail(f"subir {kind}: {r.status_code} {r.text}")
    ok(f"{kind} subido")


def cambiar_estado(token, contrato_id, nuevo):
    r = requests.put(
        f"{BASE}/contratos/{contrato_id}/estado",
        headers=auth(token),
        json={"estado": nuevo},
    )
    if r.status_code != 200:
        fail(f"cambiar estado: {r.status_code} {r.text}")
    ok(f"estado cambiado a '{r.json()['estado']}'")
    return r.json()


def aplicar_otrosi(token, contrato_id, data, file=None, expect=200):
    files = None
    if file is not None:
        files = {"archivo": file}
    r = requests.post(
        f"{BASE}/contratos/{contrato_id}/otrosi",
        headers=auth(token),
        data=data,
        files=files,
    )
    if r.status_code != expect:
        fail(
            f"otrosi (esperaba {expect}) → {r.status_code} {r.text} (data={data})"
        )
    if expect == 200:
        return r.json()
    return None


def main():
    section("0. Login admin & usuarios")
    admin_token = login(ADMIN_USER, ADMIN_PASS)
    ok("admin login OK")
    ensure_user(admin_token, COMPRAS_USER, COMPRAS_PASS, "compras")
    ensure_user(admin_token, JURIDICA_USER, JURIDICA_PASS, "juridica")
    compras_token = login(COMPRAS_USER, COMPRAS_PASS)
    juridica_token = login(JURIDICA_USER, JURIDICA_PASS)
    ok("compras + juridica login OK")

    section("1. Compras radica un contrato")
    c = radicar_contrato(compras_token)
    contrato_id = c["id"]

    section("2. Intentar otrosí con contrato en_proceso (debe fallar 409)")
    aplicar_otrosi(
        juridica_token, contrato_id,
        {"tipo": "prorroga", "descripcion": "no debería pasar",
         "plazo_adicional_cantidad": "10"},
        expect=409,
    )
    ok("rechazado correctamente (contrato no activo)")

    section("3. Jurídica: subir póliza + borrador y activar")
    adjuntar(juridica_token, contrato_id, "poliza", "poliza.pdf", b"x" * 200)
    adjuntar(juridica_token, contrato_id, "borrador", "borrador.pdf", b"y" * 200)
    cambiar_estado(juridica_token, contrato_id, "activo")

    section("4. Compras intenta aplicar otrosí (debe fallar 403)")
    aplicar_otrosi(
        compras_token, contrato_id,
        {"tipo": "otro", "descripcion": "no autorizado"},
        expect=403,
    )
    ok("compras correctamente bloqueado")

    section("5. Aplicar PRORROGA (+3 meses)")
    r = aplicar_otrosi(
        juridica_token, contrato_id,
        {"tipo": "prorroga", "descripcion": "Prórroga por retraso en obra civil",
         "plazo_adicional_cantidad": "3"},
    )
    if r["plazo_cantidad"] != 9:
        fail(f"esperaba plazo=9, obtuvo {r['plazo_cantidad']}")
    ok(f"plazo del contrato pasó de 6 a {r['plazo_cantidad']} meses")
    if len(r["otrosies"]) != 1:
        fail(f"esperaba 1 otrosí, hay {len(r['otrosies'])}")
    ok(f"otrosí #{r['otrosies'][0]['numero']} registrado en historial")

    section("6. Aplicar ADICION (+500.000)")
    r = aplicar_otrosi(
        juridica_token, contrato_id,
        {"tipo": "adicion", "descripcion": "Adición por nuevos requerimientos",
         "valor_adicional": "500000"},
    )
    if Decimal(r["valor"]) != Decimal("1500000.00"):
        fail(f"esperaba valor=1500000, obtuvo {r['valor']}")
    ok(f"valor del contrato pasó de 1.000.000 a {r['valor']}")
    if len(r["otrosies"]) != 2:
        fail(f"esperaba 2 otrosíes, hay {len(r['otrosies'])}")
    ok("2do otrosí registrado")

    section("7. Aplicar MODIFICACION (cambia descripción)")
    nueva = "Servicio AMPLIADO: mantenimiento + instalación de equipos nuevos"
    r = aplicar_otrosi(
        juridica_token, contrato_id,
        {"tipo": "modificacion",
         "descripcion": "Modificación: incluye instalación",
         "nueva_descripcion_servicio": nueva},
    )
    if r["descripcion_servicio"] != nueva:
        fail("la descripción no se actualizó")
    ok("descripción del servicio actualizada correctamente")

    section("8. Aplicar OTRO con PDF adjunto")
    pdf = ("otrosi-firmado.pdf", io.BytesIO(b"%PDF-1.4 dummy" + b"x" * 100), "application/pdf")
    r = aplicar_otrosi(
        juridica_token, contrato_id,
        {"tipo": "otro", "descripcion": "Cambio de domicilio fiscal del proveedor"},
        file=pdf,
    )
    if len(r["otrosies"]) != 4:
        fail(f"esperaba 4 otrosíes, hay {len(r['otrosies'])}")
    ult = r["otrosies"][-1]
    if not ult["archivo_id"]:
        fail("el otrosí 'otro' no quedó con archivo adjunto")
    ok(f"4to otrosí registrado con archivo_id={ult['archivo_id']}")

    # Verifica que el PDF se haya guardado como tipo 'otrosi' en archivos
    archivos_otrosi = [a for a in r["archivos"] if a["tipo"] == "otrosi"]
    if not archivos_otrosi:
        fail("no se encontró archivo con tipo='otrosi'")
    ok(f"PDF del otrosí guardado como tipo='otrosi': {archivos_otrosi[0]['nombre_original']}")

    section("9. Validaciones")
    # prórroga sin cantidad
    aplicar_otrosi(juridica_token, contrato_id,
                   {"tipo": "prorroga", "descripcion": "x"}, expect=400)
    ok("prórroga sin cantidad → 400")
    # adición con valor 0
    aplicar_otrosi(juridica_token, contrato_id,
                   {"tipo": "adicion", "descripcion": "x", "valor_adicional": "0"},
                   expect=400)
    ok("adición con valor=0 → 400")
    # modificación sin nuevo texto
    aplicar_otrosi(juridica_token, contrato_id,
                   {"tipo": "modificacion", "descripcion": "x"}, expect=400)
    ok("modificación sin nueva descripción → 400")
    # descripción vacía → FastAPI lo trata como missing (422); nuestro use case
    # también rechaza " " (sólo espacios) con 400.
    aplicar_otrosi(juridica_token, contrato_id,
                   {"tipo": "otro", "descripcion": "   "}, expect=400)
    ok("descripción en blanco → 400")

    section("10. Listar contrato y verificar cantidad_otrosies")
    r = requests.get(f"{BASE}/contratos", headers=auth(juridica_token))
    if r.status_code != 200:
        fail(r.text)
    item = next((x for x in r.json() if x["id"] == contrato_id), None)
    if not item:
        fail("no encontré el contrato en el listado")
    if item.get("cantidad_otrosies") != 4:
        fail(f"esperaba cantidad_otrosies=4, obtuvo {item.get('cantidad_otrosies')}")
    ok(f"listado expone cantidad_otrosies={item['cantidad_otrosies']}")

    section("RESUMEN")
    print()
    print("  Estado final del contrato:")
    print(f"    codigo                  = {r.json()[0]['codigo'] if False else c['codigo']}")
    final = requests.get(f"{BASE}/contratos/{contrato_id}",
                         headers=auth(juridica_token)).json()
    print(f"    codigo                  = {final['codigo']}")
    print(f"    estado                  = {final['estado']}")
    print(f"    plazo                   = {final['plazo_cantidad']} {final['plazo_unidad']}")
    print(f"    valor                   = {final['valor']} {final['moneda']}")
    print(f"    descripcion_servicio    = {final['descripcion_servicio'][:60]}...")
    print(f"    cantidad otrosíes       = {len(final['otrosies'])}")
    for o in final["otrosies"]:
        extra = ""
        if o["tipo"] == "prorroga":
            extra = f"+{o['plazo_adicional_cantidad']} {o['plazo_adicional_unidad']}"
        elif o["tipo"] == "adicion":
            extra = f"+{o['valor_adicional']}"
        elif o["tipo"] == "modificacion":
            extra = "nueva descripción"
        else:
            extra = "—"
        archivo = f" [PDF #{o['archivo_id']}]" if o["archivo_id"] else ""
        print(f"      #{o['numero']} {o['tipo']:<13} {extra}{archivo}")
    print()
    print("  [SUCCESS] Todo el flujo de otrosí funciona correctamente.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        fail(f"Error de red: {e}")
