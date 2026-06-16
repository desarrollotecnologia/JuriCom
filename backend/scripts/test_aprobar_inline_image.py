"""Reproduce aprobar with inline base64 image."""
import base64
import json
import struct
import urllib.error
import urllib.request
import zlib


def tiny_png_b64(size: int = 400) -> str:
    w = h = size
    raw = b"".join([b"\x00" + bytes([255, 0, 0] * w) for _ in range(h)])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return base64.b64encode(sig + ihdr + idat + iend).decode()


def api(method: str, path: str, token: str | None = None, data=None, form=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"http://127.0.0.1:8000/api/v1{path}", data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    _, raw = api("POST", "/auth/login", data={"username": "TIC", "password": "SIRT123"})
    token = json.loads(raw)["access_token"]
    print("login ok")

    _, raw = api("GET", "/solicitudes-gestion/pendientes-aprobacion", token=token)
    items = json.loads(raw)
    print("pendientes", len(items))
    if not items:
        print("no pending items")
        return
    sid = items[0]["id"]
    print("testing solicitud", sid, "estado", items[0]["estado"])

    import os

    for size_kb in [50, 70, 100, 200, 500]:
        fake = base64.b64encode(os.urandom(size_kb * 1024)).decode()
        html = f'<p>test</p><img src="data:image/png;base64,{fake}" class="richtext-inline-image" />'
        print(f"\n--- size_kb={size_kb} html_len={len(html)} ---")
        status, body = api(
            "POST",
            f"/solicitudes-gestion/{sid}/aprobar",
            token=token,
            form={
                "observacion": html,
                "observacion_texto": "Observacion con imagen grande",
            },
        )
        print("aprobar status", status)
        print(body[:400].decode(errors="replace"))
        if status != 200:
            break
        # reload pending for next iteration if approval succeeded
        _, raw = api("GET", "/solicitudes-gestion/pendientes-aprobacion", token=token)
        items = json.loads(raw)
        if not items:
            print("no more pending after approval")
            break
        sid = items[0]["id"]
        print("next sid", sid, items[0]["estado"])


if __name__ == "__main__":
    main()
