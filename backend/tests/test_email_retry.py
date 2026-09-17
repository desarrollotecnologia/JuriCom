"""Reintentos del notificador SMTP.

- Un fallo transitorio (conexión caída, timeout) debe reintentarse hasta lograr
  el envío. Sin esto, un bache de red pierde la notificación silenciosamente.
- Un fallo permanente (auth inválida, destinatario rechazado) NO debe
  reintentarse: la causa no cambia y bloquearía el request.
"""

import smtplib

from app.application.interfaces.email_notifier import EmailMessage
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
        max_attempts=3,
        retry_backoff=(0.0,),  # sin dormir en tests
    )


def _msg() -> EmailMessage:
    return EmailMessage(
        asunto="x",
        destinatarios=["a@test.com"],
        cuerpo_html="<p>x</p>",
        cuerpo_texto="x",
    )


def test_reintenta_fallo_transitorio_hasta_exito():
    n = _notifier()

    class Fake:
        calls = 0

        def __call__(self, mime, dests):
            Fake.calls += 1
            if Fake.calls <= 2:
                raise smtplib.SMTPServerDisconnected("conexión caída")
            # 3.ª pasada: éxito

    fake = Fake()
    n._estrategias = lambda: iter([fake])
    n.send(_msg())  # no debe levantar
    assert Fake.calls == 3, Fake.calls


def test_no_reintenta_error_permanente():
    n = _notifier()

    class Fake:
        calls = 0

        def __call__(self, mime, dests):
            Fake.calls += 1
            raise smtplib.SMTPAuthenticationError(535, b"credenciales invalidas")

    fake = Fake()
    n._estrategias = lambda: iter([fake])
    try:
        n.send(_msg())
        raise AssertionError("debió levantar RuntimeError")
    except RuntimeError:
        pass
    assert Fake.calls == 1, Fake.calls


if __name__ == "__main__":
    test_reintenta_fallo_transitorio_hasta_exito()
    test_no_reintenta_error_permanente()
    print("OK")
