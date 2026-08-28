"""El correo debe poder llevar adjuntos (informe final / acta de liquidación).

Verifica que SmtpEmailNotifier._build_mime incruste el adjunto con su nombre y
tipo, conservando el cuerpo HTML.
"""

from app.application.interfaces.email_notifier import EmailAttachment, EmailMessage
from app.infrastructure.email.smtp_notifier import SmtpEmailNotifier


def _notifier() -> SmtpEmailNotifier:
    return SmtpEmailNotifier(
        host="smtp.test",
        port=465,
        use_ssl=True,
        username="u",
        password="p",
        from_email="from@test.com",
        from_name="JuriColbeef",
    )


def test_build_mime_incluye_adjunto():
    msg = EmailMessage(
        asunto="Falta acta",
        destinatarios=["juridica@test.com"],
        cuerpo_html="<p>hola</p>",
        cuerpo_texto="hola",
        adjuntos=[
            EmailAttachment(
                nombre="informe.pdf",
                contenido=b"%PDF-1.4 contenido de prueba",
                mime_type="application/pdf",
            )
        ],
    )
    mime = _notifier()._build_mime(msg)

    adjuntos = [
        part
        for part in mime.walk()
        if part.get_content_disposition() == "attachment"
    ]
    assert len(adjuntos) == 1
    adj = adjuntos[0]
    assert adj.get_filename() == "informe.pdf"
    assert adj.get_content_type() == "application/pdf"
    assert adj.get_payload(decode=True) == b"%PDF-1.4 contenido de prueba"

    # El cuerpo HTML sigue presente.
    htmls = [p for p in mime.walk() if p.get_content_type() == "text/html"]
    assert htmls and "hola" in htmls[0].get_content()


def test_build_mime_sin_adjuntos_no_falla():
    msg = EmailMessage(
        asunto="x",
        destinatarios=["a@test.com"],
        cuerpo_html="<p>x</p>",
        cuerpo_texto="x",
    )
    mime = _notifier()._build_mime(msg)
    adjuntos = [
        p for p in mime.walk() if p.get_content_disposition() == "attachment"
    ]
    assert adjuntos == []


if __name__ == "__main__":
    test_build_mime_incluye_adjunto()
    test_build_mime_sin_adjuntos_no_falla()
    print("OK")
