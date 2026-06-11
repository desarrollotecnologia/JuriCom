"""Política de "ver" contraseñas.

Nota técnica importante:
Las contraseñas se almacenan con bcrypt (hash unidireccional). Esto significa
que NADIE puede recuperar la contraseña original en texto plano — ni siquiera
el administrador, ni el desarrollador, ni un atacante con acceso a la BD.

Por eso, el "ver contraseña" del administrador se implementa así:
- El admin NO ve la contraseña original.
- El admin SÍ puede **reasignar** la contraseña de cualquier usuario
  (use case `ChangePassword`), y luego comunicarla al usuario por canal seguro.

Esta es la práctica estándar de la industria (Google, Microsoft, etc.) y
protege a la empresa frente a fugas de datos.
"""


class RevealPasswordPolicy:
    """Documenta la política. No expone contraseñas en texto plano."""

    MESSAGE = (
        "Por seguridad las contraseñas no son visibles en texto plano "
        "(están hasheadas con bcrypt). Como administrador puedes "
        "REASIGNAR la contraseña del usuario desde el panel."
    )
