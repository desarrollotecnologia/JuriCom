"""Envía a cada usuario activo de JURICOM el manual (Word) de su(s) rol(es).

Uso:
    python docs/manual-usuario/enviar_manuales.py                   # sólo muestra a quién le llega qué
    python docs/manual-usuario/enviar_manuales.py --prueba X@y.com  # envía UN correo de muestra a X
    python docs/manual-usuario/enviar_manuales.py --enviar          # envía a todos (real)
    python docs/manual-usuario/enviar_manuales.py --enviar --solo a@y.com b@y.com  # reintenta sólo esos
"""

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "backend"))

from app.application.interfaces.email_notifier import EmailAttachment, EmailMessage  # noqa: E402
from app.infrastructure.config.settings import settings  # noqa: E402
from app.infrastructure.database.session import SessionLocal  # noqa: E402
from app.infrastructure.email.smtp_notifier import SmtpEmailNotifier  # noqa: E402
from app.infrastructure.repositories.sqlalchemy_user_repository import (  # noqa: E402
    SqlAlchemyUserRepository,
)

POR_ROL = HERE / "por-rol"
# Rol del sistema -> (nombre visible, archivo del manual)
MANUAL_POR_ROL = {
    "admin": ("Administrador", "Manual JURICOM - Administrador.docx"),
    "solicitante": ("Supervisor", "Manual JURICOM - Supervisor.docx"),
    "compras": ("Compras", "Manual JURICOM - Compras.docx"),
    "proyectos": ("Proyectos", "Manual JURICOM - Proyectos.docx"),
    "lider_aprobador": ("Líder Aprobador", "Manual JURICOM - Lider Aprobador.docx"),
    "contabilidad": ("Contabilidad", "Manual JURICOM - Contabilidad.docx"),
    "tesoreria": ("Tesorería", "Manual JURICOM - Tesoreria.docx"),
    "juridica": ("Jurídica", "Manual JURICOM - Juridica.docx"),
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def manuales_de(user) -> list[tuple[str, str]]:
    vistos, out = set(), []
    for rol in user.roles():
        clave = getattr(rol, "value", rol)
        if clave in MANUAL_POR_ROL and clave not in vistos:
            vistos.add(clave)
            out.append(MANUAL_POR_ROL[clave])
    return out


def construir_mensaje(email: str, nombre: str, manuales: list[tuple[str, str]]) -> EmailMessage:
    roles_txt = ", ".join(n for n, _ in manuales)
    url = (settings.APP_PUBLIC_URL or "").rstrip("/")
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    html = f"""
    <div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1f2937;max-width:600px">
      <h2 style="color:#163966;margin-bottom:4px">Manual de usuario JURICOM</h2>
      <p>{saludo}</p>
      <p>Te compartimos el manual de usuario de JURICOM según tu rol en el sistema:
         <strong>{roles_txt}</strong>.</p>
      <p>En el documento adjunto encontrarás, paso a paso, cómo ingresar, navegar,
         la trazabilidad del proceso y las acciones que puedes realizar.</p>
      {f'<p><a href="{url}/app/login.html" style="background:#163966;color:#fff;padding:10px 18px;border-radius:6px;text-decoration:none">Ingresar a JURICOM</a></p>' if url else ''}
      <p style="color:#6b7280;font-size:12px">Si tienes dudas, responde a este correo.</p>
    </div>"""
    texto = (
        f"{saludo}\n\nTe compartimos el manual de usuario de JURICOM según tu rol: {roles_txt}.\n"
        + (f"Ingresa en: {url}/app/login.html\n" if url else "")
    )
    adjuntos = [
        EmailAttachment(nombre=archivo, contenido=(POR_ROL / archivo).read_bytes(), mime_type=DOCX_MIME)
        for _, archivo in manuales
    ]
    return EmailMessage(
        asunto="[JURICOM] Tu manual de usuario",
        destinatarios=[email],
        cuerpo_html=html,
        cuerpo_texto=texto,
        adjuntos=adjuntos,
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--enviar", action="store_true", help="Envía a todos los usuarios (real).")
    p.add_argument("--prueba", metavar="EMAIL", help="Envía un único correo de muestra a EMAIL.")
    p.add_argument("--solo", nargs="+", metavar="EMAIL", help="Limita a estos usuarios (p. ej. reintentar fallidos).")
    args = p.parse_args()

    for _, archivo in MANUAL_POR_ROL.values():
        if not (POR_ROL / archivo).exists():
            sys.exit(f"Falta el manual: {POR_ROL / archivo}")

    db = SessionLocal()
    try:
        usuarios = [u for u in SqlAlchemyUserRepository(db).list_all() if u.is_active and (u.email or "").strip()]
    finally:
        db.close()
    if args.solo:
        solo = {e.strip().lower() for e in args.solo}
        usuarios = [u for u in usuarios if u.email.strip().lower() in solo]

    plan = [(u, manuales_de(u)) for u in usuarios]
    for u, mans in plan:
        roles = ", ".join(getattr(r, "value", r) for r in u.roles())
        print(f"{u.email:45s} [{roles}] -> {', '.join(n for n, _ in mans) or 'SIN MANUAL'}")
    print(f"\nTotal: {len(plan)} usuarios, {sum(1 for _, m in plan if m)} con manual.")

    if not (args.enviar or args.prueba):
        print("\nModo vista previa: no se envió nada.")
        return

    notifier = SmtpEmailNotifier()
    if not notifier.disponible:
        sys.exit("SMTP no configurado.")

    if args.prueba:
        u, mans = next(((u, m) for u, m in plan if len(m) > 1), next((x for x in plan if x[1])))
        msg = construir_mensaje(args.prueba, u.nombre or "", mans)
        msg.asunto += f" (muestra de {u.email})"
        notifier.send(msg)
        print(f"\nMuestra enviada a {args.prueba} (manuales de {u.email}).")
        return

    ok, fallos = 0, []
    for u, mans in plan:
        if not mans:
            continue
        try:
            notifier.send(construir_mensaje(u.email.strip(), u.nombre or "", mans))
            ok += 1
            print(f"OK   {u.email}")
        except Exception as e:  # sigue con el resto; se reporta al final
            fallos.append((u.email, str(e)))
            print(f"FALLO {u.email}: {e}")
        time.sleep(1)  # ponytail: pausa fija para no saturar el SMTP; si hay muchos usuarios, usar lotes.
    print(f"\nEnviados: {ok}. Fallidos: {len(fallos)}.")
    for email, err in fallos:
        print(f"  - {email}: {err}")


if __name__ == "__main__":
    main()
