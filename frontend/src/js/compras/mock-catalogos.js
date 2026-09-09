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
    { id: "LTS", label: "Litros (LTS)" },
    { id: "GLS", label: "Galones (GLS)" },
    { id: "MTS", label: "Metros (MTS)" },
    { id: "CJS", label: "Cajas (CJS)" },
    { id: "PQS", label: "Paquetes (PQS)" },
    { id: "LBS", label: "Libras (LBS)" },
    { id: "KGS", label: "Kilos (KGS)" },
    { id: "LM", label: "Lámina (LM)" },
    { id: "LMS", label: "Láminas (LMS)" },
    { id: "CHP", label: "Chipa (CHP)" },
    { id: "RL", label: "Rollo (RL)" },
    { id: "RLS", label: "Rollos (RLS)" },
    { id: "CM", label: "Centímetros (CM)" },
    { id: "MM", label: "Milímetros (MM)" },
    { id: "PAR", label: "Par (PAR)" },
    { id: "KIT", label: "Kit (KIT)" },
    { id: "TRM", label: "Tramo (TRM)" },
    { id: "TRS", label: "Tramos (TRS)" },
    { id: "CUN", label: "Cuñete (CUN)" },
    { id: "CUNS", label: "Cuñetes (CUNS)" },
    { id: "BT", label: "Bulto (BT)" },
    { id: "BTS", label: "Bultos (BTS)" },
    { id: "BAL", label: "Bala (BAL)" },
];

/**
 * Aprobadores del "Líder de Área" (1.ª aprobación): solo directores
 * (cargo DIRECTOR/DIRECTORA). Se excluye a Diego Serrano (id 13542263) porque
 * siempre es la 2.ª aprobación (gerencia financiera).
 * El catálogo completo sigue en LIDERES_COLBEEF para resolver etiquetas de
 * solicitudes existentes.
 */
const DIEGO_SERRANO_ID = "13542263";
export const LIDERES_AREA = LIDERES_COLBEEF.filter(
    (l) => /\bdirectora?\b/i.test(l.label) && l.id !== DIEGO_SERRANO_ID
);

export function buildSelectOptions(items, placeholder = "Selecciona una opción") {
    const opts = [`<option value="">${placeholder}</option>`];
    for (const item of items) {
        opts.push(`<option value="${item.id}">${item.label}</option>`);
    }
    return opts.join("");
}
