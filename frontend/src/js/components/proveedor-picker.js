// Selector de proveedores reutilizable: buscador del catálogo, sugeridos,
// tarjetas de elegidos y alta manual con formato estructurado.

import { api } from "../api/client.js";
import { escapeHtml } from "../utils/format.js";
import { createSearchableSelect } from "./searchable-select.js";

let _seq = 0;

/**
 * @param {{
 *   container: HTMLElement,
 *   initialText?: string,
 *   soloServicios?: boolean,
 *   getQuery?: () => string,   // texto para sugeridos (título + descripción)
 * }} opts
 * @returns {{ serialize: () => string, refreshSugeridos: () => void, getSelected: () => object[] }}
 */
export function createProveedorPicker({
    container,
    initialText = "",
    soloServicios = true,
    getQuery = null,
}) {
    if (!container) throw new Error("proveedor-picker: falta el contenedor.");
    const cid = `prov-picker-${++_seq}`;
    let seleccionados = parseInitial(initialText);

    container.innerHTML = `
        <div class="prov-picker">
            <div id="${cid}-select"></div>
            <div id="${cid}-sug" class="sg-prov-sugeridos"></div>
            <div id="${cid}-eleg" class="sg-prov-elegidos"></div>
            <details class="sg-prov-manual">
                <summary>Agregar proveedor manualmente</summary>
                <div class="sg-prov-manual-form">
                    <input type="text" data-f="nombre" placeholder="Nombre del proveedor *" />
                    <input type="text" data-f="telefono" placeholder="Teléfono" />
                    <input type="email" data-f="correo" placeholder="Correo" />
                    <input type="text" data-f="contacto" placeholder="Contacto" />
                    <input type="text" data-f="ciudad" placeholder="Ciudad" />
                    <button type="button" class="btn btn-sm btn-secondary" data-add-manual>
                        Agregar proveedor
                    </button>
                </div>
            </details>
        </div>`;

    const elegidosEl = container.querySelector(`#${cid}-eleg`);
    const sugEl = container.querySelector(`#${cid}-sug`);

    function renderElegidos() {
        if (!seleccionados.length) {
            elegidosEl.innerHTML =
                '<p class="muted sg-prov-empty">Aún no has elegido proveedores.</p>';
            return;
        }
        const meta = (icon, value) =>
            value
                ? `<span class="sg-prov-meta-item">${icon} ${escapeHtml(value)}</span>`
                : "";
        elegidosEl.innerHTML = seleccionados
            .map((p, i) => {
                const metas = p._raw
                    ? ""
                    : `<div class="sg-prov-meta">
                            ${meta("📞", p.telefono)}
                            ${meta("✉️", p.correo)}
                            ${meta("👤", p.contacto)}
                            ${meta("📍", p.ciudad)}
                       </div>`;
                return `
                    <div class="sg-prov-elegido">
                        <div class="sg-prov-elegido-main">
                            <strong>${escapeHtml(p.nombre)}</strong>
                            ${
                                p.sector
                                    ? `<span class="sg-prov-sector">${escapeHtml(
                                          p.sector
                                      )}</span>`
                                    : ""
                            }
                            ${metas}
                        </div>
                        <button type="button" class="sg-prov-elegido-x"
                            data-idx="${i}" title="Quitar" aria-label="Quitar">×</button>
                    </div>`;
            })
            .join("");
        elegidosEl.querySelectorAll(".sg-prov-elegido-x").forEach((btn) => {
            btn.addEventListener("click", () => {
                seleccionados.splice(Number(btn.dataset.idx), 1);
                renderElegidos();
            });
        });
    }

    function add(p) {
        const nombre = (p.nombre || "").trim();
        if (!nombre) return;
        const dup = seleccionados.some(
            (x) => (x.nombre || "").toLowerCase() === nombre.toLowerCase()
        );
        if (!dup) seleccionados.push({ ...p, nombre });
        renderElegidos();
    }

    // Buscador del catálogo.
    const provItems = [];
    let select = null;
    try {
        select = createSearchableSelect({
            containerId: `${cid}-select`,
            name: `${cid}-catalogo-id`,
            items: provItems,
            placeholder: "Busca un proveedor por nombre o sector…",
            emptyMessage: "No hay proveedores que coincidan.",
        });
        select.hiddenInput.addEventListener("change", () => {
            const item = select.getSelectedItem();
            if (!item || !item.prov) return;
            add(item.prov);
            select.clear();
        });
        // En formularios donde el título/descripción se escriben en vivo,
        // recalcula los sugeridos al ir a buscar un proveedor.
        if (getQuery) {
            select.input.addEventListener("focus", () => refreshSugeridos());
        }
    } catch {
        /* contenedor ausente: sólo manual */
    }

    api.get(`/proveedores/opciones?solo_servicios=${soloServicios ? "true" : "false"}`)
        .then((opciones) => {
            opciones.forEach((p) =>
                provItems.push({
                    id: String(p.id),
                    label: p.sector ? `${p.nombre} — ${p.sector}` : p.nombre,
                    prov: p,
                })
            );
        })
        .catch(() => {
            container.querySelector(`#${cid}-select`)?.insertAdjacentHTML(
                "afterend",
                '<span class="hint" style="color:#b45309;">No se pudo cargar el catálogo; agrega el proveedor manualmente.</span>'
            );
        });

    // Alta manual estructurada.
    const manualForm = container.querySelector(".sg-prov-manual-form");
    const manualAdd = () => {
        const get = (f) =>
            (manualForm.querySelector(`[data-f="${f}"]`)?.value || "").trim();
        const nombre = get("nombre");
        if (!nombre) {
            manualForm.querySelector('[data-f="nombre"]')?.focus();
            return;
        }
        add({
            nombre,
            telefono: get("telefono"),
            correo: get("correo"),
            contacto: get("contacto"),
            ciudad: get("ciudad"),
        });
        manualForm
            .querySelectorAll("input")
            .forEach((i) => (i.value = ""));
        manualForm.querySelector('[data-f="nombre"]')?.focus();
    };
    manualForm.querySelector("[data-add-manual]")?.addEventListener("click", manualAdd);
    manualForm.querySelectorAll("input").forEach((inp) => {
        inp.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                manualAdd();
            }
        });
    });

    async function refreshSugeridos() {
        if (!sugEl) return;
        const q = (getQuery ? getQuery() : "").trim().slice(0, 300);
        if (!q) {
            sugEl.innerHTML = "";
            return;
        }
        let sugeridos = [];
        try {
            sugeridos = await api.get(
                `/proveedores/sugerencias?q=${encodeURIComponent(q)}&solo_servicios=${
                    soloServicios ? "true" : "false"
                }&top=6`
            );
        } catch {
            return;
        }
        if (!sugeridos.length) {
            sugEl.innerHTML = "";
            return;
        }
        sugEl.innerHTML = `
            <span class="sg-prov-sugeridos-label">Sugeridos:</span>
            <div class="sg-prov-chips">
                ${sugeridos
                    .map(
                        (p, i) => `
                    <button type="button" class="sg-prov-chip" data-idx="${i}"
                        title="${escapeHtml(p.sector || p.nombre)}">
                        <span class="sg-prov-chip-plus">+</span>${escapeHtml(p.nombre)}
                    </button>`
                    )
                    .join("")}
            </div>`;
        sugEl.querySelectorAll(".sg-prov-chip").forEach((btn) => {
            btn.addEventListener("click", () => add(sugeridos[Number(btn.dataset.idx)]));
        });
    }

    function serialize() {
        return seleccionados
            .map((p) =>
                p._raw
                    ? p.nombre
                    : [p.nombre, p.telefono, p.correo, p.contacto]
                          .filter(Boolean)
                          .join(" — ")
            )
            .join("\n");
    }

    function setText(texto) {
        seleccionados = parseInitial(texto);
        renderElegidos();
    }

    renderElegidos();
    if (getQuery) refreshSugeridos();

    return { serialize, refreshSugeridos, setText, getSelected: () => seleccionados };
}

function parseInitial(texto) {
    return (texto || "")
        .trim()
        .split(/\r?\n/)
        .map((l) => l.replace(/^-\s*/, "").trim())
        .filter(Boolean)
        .map((linea) => ({ nombre: linea, _raw: true }));
}
