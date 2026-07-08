"""Catálogo de correos de líderes Colbeef 2026."""

EMAILS_LIDERES_COLBEEF: dict[str, str] = {
    "1977852": "director.surtidores@colbeef.com",
    "80424220": "gerencia.comercial@colbeef.com",
    "13542263": "gerencia.financiera@colbeef.com",
    "37747995": "gerencia.juridica@colbeef.com",
    "1098673651": "coordinacion.tesoreria@colbeef.com",
    "79249780": "gerencia.general@colbeef.com",
    "1127947335": "coordinacion.subproductos@colbeef.com",
    "91536323": "gerencia.comercial@colbeef.com",
    "73579178": "coordinacion.tecnologia@colbeef.com",
    "1098660251": "gerencia.comercial@colbeef.com",
    "91477701": "desposte@colbeef.com",
    "1098763171": "siso@colbeef.com",
    "1056908061": "gerencia.calidad@colbeef.com",
    "1098661407": "coordinacion.gestionhumana@colbeef.com",
    "63560912": "coordinacion.calidad@colbeef.com",
    "1102387740": "coordinacion.tesoreria@colbeef.com",
    "43536705": "coordinacion.contabilidad@colbeef.com",
    "1098738467": "coordinacion.linea@colbeef.com",
    "1095807041": "coordinacion.logistico@colbeef.com",
    "1098661799": "gerencia.comercial@colbeef.com",
    "52822147": "jefe.mercadeo@colbeef.com",
    "1098665901": "gerencia.financiera@colbeef.com",
    "1098725715": "gerencia.operaciones@colbeef.com",
}


def email_lider_catalogo(catalog_id: str) -> str:
    return EMAILS_LIDERES_COLBEEF.get((catalog_id or "").strip(), "")
