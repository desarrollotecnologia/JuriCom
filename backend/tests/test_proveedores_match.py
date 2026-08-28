"""Ranking de proveedores por coincidencia de palabras."""

from app.infrastructure.catalogos.proveedores_match import rankear_proveedores


PROVEEDORES = [
    {"nombre": "Frío Industrial SAS", "sector": "Refrigeración industrial y aires", "para": "servicios"},
    {"nombre": "Metalmecánica del Norte", "sector": "Metalmecánico y soldadura", "para": "ambas"},
    {"nombre": "Papelería Central", "sector": "Papelería y útiles de oficina", "para": "compras"},
    {"nombre": "Aseo Total", "sector": "Servicios de aseo y limpieza", "para": "servicios"},
]


def test_ranking_prioriza_sector_afin():
    r = rankear_proveedores(
        "Mantenimiento de refrigeración en planta 2", PROVEEDORES
    )
    assert r, "debería sugerir al menos un proveedor"
    assert r[0]["nombre"] == "Frío Industrial SAS"


def test_solo_servicios_excluye_compras():
    # 'papeleria' solo existe en un proveedor de compras -> no debe aparecer.
    r = rankear_proveedores("compra de papelería", PROVEEDORES, solo_servicios=True)
    assert all(p["nombre"] != "Papelería Central" for p in r)


def test_incluye_compras_si_se_pide():
    r = rankear_proveedores(
        "papelería", PROVEEDORES, solo_servicios=False
    )
    assert any(p["nombre"] == "Papelería Central" for p in r)


def test_sin_coincidencias_retorna_vacio():
    assert rankear_proveedores("astronáutica cuántica", PROVEEDORES) == []


def test_ordena_por_score_desc():
    provs = [
        {"nombre": "A", "sector": "soldadura", "para": "servicios"},
        {"nombre": "B", "sector": "soldadura y metalmecanica", "para": "servicios"},
    ]
    r = rankear_proveedores("soldadura metalmecanica", provs)
    assert [p["nombre"] for p in r] == ["B", "A"]
    assert r[0]["_score"] >= r[1]["_score"]
