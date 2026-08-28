/** Catálogos de prueba — reemplazar por API cuando esté disponible. */

import { LIDERES_COLBEEF } from "../catalogos/lideres-colbeef.js";

export const AREAS_CONSUMO = [
    { id: "AC-ADM", label: "AC-ADM · Administración" },
    { id: "AC-PROD", label: "AC-PROD · Producción" },
    { id: "AC-LOG", label: "AC-LOG · Logística" },
    { id: "AC-COM", label: "AC-COM · Comercial" },
    { id: "AC-TI", label: "AC-TI · Tecnología" },
    { id: "AC-GH", label: "AC-GH · Gestión Humana" },
    { id: "AC-CAL", label: "AC-CAL · Calidad y SST" },
    { id: "AC-MNT", label: "AC-MNT · Mantenimiento" },
];

export const UNIDADES_MEDIDA = [
    { id: "UND", label: "Unidad (UND)" },
    { id: "KG", label: "Kilogramo (KG)" },
    { id: "LB", label: "Libra (LB)" },
    { id: "LT", label: "Litro (LT)" },
    { id: "GL", label: "Galón (GL)" },
    { id: "MT", label: "Metro (MT)" },
    { id: "CJ", label: "Caja (CJ)" },
    { id: "PQ", label: "Paquete (PQ)" },
];

/** Lista oficial Líderes Colbeef 2026 (misma que Radicar Solicitud). */
export const LIDERES_AREA = LIDERES_COLBEEF;

export function buildSelectOptions(items, placeholder = "Selecciona una opción") {
    const opts = [`<option value="">${placeholder}</option>`];
    for (const item of items) {
        opts.push(`<option value="${item.id}">${item.label}</option>`);
    }
    return opts.join("");
}
