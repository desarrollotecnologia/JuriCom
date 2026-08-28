/**
 * Centros de costos Colbeef — fuente única para formularios del proyecto.
 * Tomado de "CENTROS DE COSTOS 1.xlsx" (CC = centro, SC = subcentro).
 */

export const CENTROS_COSTOS = [
    { depto: "DPTO CONTROLLER", cc: "211", items: [
        [1, "CONTROLLER"],
        [2, "CONTROL DE PROCESOS"],
        [3, "PMO"],
        [4, "CONTROL DE PROCESOS (4)"],
    ] },
    { depto: "DPTO ADMON Y FINANCIERO", cc: "212", items: [
        [1, "GERENCIA ADMON Y FINANCIERA"],
        [2, "CONTABILIDAD"],
        [3, "COMPRAS"],
        [4, "TESORERIA"],
        [6, "PLANEACION Y PROYECTOS"],
        [7, "TIC'S"],
        [9, "GESTION HUMANA"],
    ] },
    { depto: "CORPORATIVOS", cc: "213", items: [
        [1, "GERENCIA GENERAL"],
        [2, "JUNTA DIRECTIVA"],
        [3, "REVISORIA FISCAL"],
    ] },
    { depto: "DPTO COMERCIAL", cc: "214", items: [
        [1, "GERENCIA COMERCIAL"],
        [2, "MERCADEO"],
        [10, "TRANSPORTES"],
    ] },
    { depto: "DPTO JURIDICO Y GESTION HUMANA", cc: "215", items: [
        [1, "GERENCIA JURIDICA Y GESTION HUMANA"],
        [2, "JURIDICA"],
    ] },
    { depto: "DPTO CALIDAD", cc: "306", items: [
        [1, "GERENCIA CALIDAD"],
        [2, "LIMPIEZA Y DESINFECCION"],
        [3, "LAVANDERIA"],
        [7, "LABORATORIO"],
        [9, "INVIMA"],
        [10, "INNOVACIÓN (IDI)"],
        [11, "SST - SISO"],
    ] },
    { depto: "DPTO DE PRODUCCION", cc: "307", items: [
        [1, "PRODUCCION BENEFICIO"],
        [3, "LINEA DE SACRIFICIO"],
        [4, "SUBPRODUCTOS COMESTIBLES"],
        [6, "LOGISTICA"],
        [9, "MANTENIMIENTO"],
        [10, "PTAR"],
        [11, "PTAP"],
        [12, "AMBIENTAL"],
        [13, "ABONO"],
    ] },
    { depto: "DESPOSTE", cc: "309", items: [
        [1, "PRODUCCION DESPOSTE"],
        [2, "LINEA DESPOSTE"],
        [3, "LOGISTICA DESPOSTE"],
        [4, "CALIDAD DESPOSTE"],
        [5, "LIMPIEZA Y DESINFECCIÓN DESPOSTE"],
        [6, "LAVANDERIA DESPOSTE"],
        [7, "PTAR DESPOSTE"],
        [8, "PTAP DESPOSTE"],
        [9, "MANTENIMIENTO DESPOSTE"],
        [10, "PORCIONADO"],
    ] },
    { depto: "SURTIDORES", cc: "317", items: [
        [1, "DIRECCION SURTIDORES"],
        [2, "PLANILLAJE Y FACTURACION"],
        [3, "RECEPCION Y PESAJE"],
    ] },
    { depto: "ASURCARNES", cc: "413", items: [
        [1, "INSPECTORES"],
    ] },
    { depto: "COLBEEF", cc: "600", items: [
        [1, "CARNES COLBEEF"],
    ] },
];

/** Valor almacenado (legible): "CC-SC NOMBRE". */
export function valorCentro(cc, sc, nombre) {
    return `${cc}-${sc} ${nombre}`;
}

/**
 * Items para un buscador (searchable-select): permite filtrar por número
 * (cc, sc) o por nombre/departamento. El `id` conserva el valor almacenado.
 * @returns {{ id: string, label: string }[]}
 */
export function centrosCostosItems() {
    const items = [];
    for (const grupo of CENTROS_COSTOS) {
        for (const [sc, nombre] of grupo.items) {
            items.push({
                id: valorCentro(grupo.cc, sc, nombre),
                label: `${grupo.cc}-${sc} · ${nombre} · ${grupo.depto}`,
            });
        }
    }
    return items;
}

/**
 * Devuelve el HTML de <optgroup>/<option> del catálogo, para usarlo en
 * selects construidos con template literals (filas de tablas, etc.).
 * @param {string} [placeholder]
 */
export function opcionesCentrosCostosHtml(placeholder = "Selecciona un centro de costos…") {
    const escapar = (t) =>
        String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    const partes = [`<option value="">${escapar(placeholder)}</option>`];
    for (const grupo of CENTROS_COSTOS) {
        partes.push(`<optgroup label="${escapar(`${grupo.cc} · ${grupo.depto}`)}">`);
        for (const [sc, nombre] of grupo.items) {
            const value = escapar(valorCentro(grupo.cc, sc, nombre));
            partes.push(`<option value="${value}">${escapar(`${grupo.cc}-${sc} · ${nombre}`)}</option>`);
        }
        partes.push("</optgroup>");
    }
    return partes.join("");
}

/**
 * Llena un <select> con optgroups por departamento.
 * @param {HTMLSelectElement} select
 * @param {string} [seleccionado] valor previamente guardado a preseleccionar.
 */
export function poblarCentrosCostos(select, seleccionado = "") {
    select.innerHTML = '<option value="">Selecciona un centro de costos…</option>';
    for (const grupo of CENTROS_COSTOS) {
        const og = document.createElement("optgroup");
        og.label = `${grupo.cc} · ${grupo.depto}`;
        for (const [sc, nombre] of grupo.items) {
            const value = valorCentro(grupo.cc, sc, nombre);
            const opt = document.createElement("option");
            opt.value = value;
            opt.textContent = `${grupo.cc}-${sc} · ${nombre}`;
            og.appendChild(opt);
        }
        select.appendChild(og);
    }
    // Si el valor guardado no está en la lista (dato histórico), lo añadimos.
    if (seleccionado && !select.querySelector(`option[value="${CSS.escape(seleccionado)}"]`)) {
        const opt = document.createElement("option");
        opt.value = seleccionado;
        opt.textContent = seleccionado;
        select.appendChild(opt);
    }
    if (seleccionado) select.value = seleccionado;
}
