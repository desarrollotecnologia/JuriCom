// Panel compartido para los roles Contabilidad y Tesorería.
// Gestiona dos sub-flujos del contrato:
//   - Anticipo (antes de activar): anticipo_contabilidad → anticipo_tesoreria → anticipo_pagado
//   - Cierre final (tras informe/acta): cierre_contabilidad → cierre_tesoreria → completado

import { api, ApiError } from "../api/client.js";
import { formatMoney, escapeHtml } from "../utils/format.js";
import {
    renderObservacionesTrazabilidadHtml,
    attachGestionDownloadHandlers,
    hydrateInlineObservacionImages,
} from "../compras/gestion-solicitudes-common.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";

// Acciones disponibles por estado del contrato (fase + endpoint + textos).
const ACCIONES = {
    anticipo_contabilidad: {
        fase: "anticipo",
        faseLabel: "Anticipo",
        endpoint: (id) => `/contratos/${id}/anticipo/gestionar`,
        boton: "Gestionar y enviar a Tesorería",
        okMsg: "Anticipo gestionado y enviado a Tesorería.",
        ayuda:
            "Revisa la trazabilidad del contrato, gestiona el anticipo y adjunta la evidencia. " +
            "Al enviar, el contrato pasa a Tesorería.",
    },
    anticipo_tesoreria: {
        fase: "anticipo",
        faseLabel: "Anticipo",
        endpoint: (id) => `/contratos/${id}/anticipo/confirmar-pago`,
        boton: "Confirmar pago del anticipo",
        okMsg: "Pago confirmado. El contrato quedó en 'Anticipo pagado' y se avisó a Jurídica.",
        ayuda:
            "Revisa que todo esté correcto, realiza el pago y adjunta la evidencia. " +
            "Al confirmar, el contrato pasa a 'Anticipo pagado' y se notifica a Jurídica, Compras y al supervisor.",
    },
    cierre_contabilidad: {
        fase: "cierre",
        faseLabel: "Cierre",
        endpoint: (id) => `/contratos/${id}/cierre/gestionar`,
        boton: "Gestionar y enviar a Tesorería",
        okMsg: "Cierre gestionado y enviado a Tesorería para el pago final.",
        ayuda:
            "Revisa toda la trazabilidad y los archivos (contrato firmado, informe final o acta). " +
            "Adjunta tu comentario con el archivo; al enviar, el cierre pasa a Tesorería para el pago.",
    },
    cierre_tesoreria: {
        fase: "cierre",
        faseLabel: "Cierre",
        endpoint: (id) => `/contratos/${id}/cierre/confirmar`,
        boton: "Confirmar pago final",
        okMsg: "Pago final confirmado. El contrato quedó 'Completado' y se avisó a Jurídica, Compras y al supervisor.",
        ayuda:
            "Realiza el pago final y adjunta el soporte (por ejemplo, el screenshot del pago). " +
            "Al confirmar, el contrato queda 'Completado' y termina el proceso.",
    },
};

// Estados que cada rol atiende (anticipo + cierre).
const ESTADOS_POR_ROL = {
    contabilidad: ["anticipo_contabilidad", "cierre_contabilidad"],
    tesoreria: ["anticipo_tesoreria", "cierre_tesoreria"],
};

const TIPO_ARCHIVO_LABEL = {
    borrador_firmado: "Contrato firmado",
    borrador: "Borrador del contrato",
    poliza: "Póliza",
    informe_final: "Informe final",
    acta_liquidacion: "Acta de liquidación",
    radicacion: "Documento de radicación",
    juridica: "Documento de Jurídica",
    otrosi: "Otrosí",
};

let ctx = {
    user: null,
    rol: null,
    estados: [],
    items: [],
    detalle: null,
    fase: "todos",
    obsControl: null,
};

export function initPanelAnticipos({ user, rol }) {
    ctx.user = user;
    ctx.rol = rol;
    ctx.estados = ESTADOS_POR_ROL[rol] || [];
    document.getElementById("btn-detail-close").addEventListener("click", cerrarDetalle);
    document.getElementById("modal-detail").addEventListener("click", (e) => {
        if (e.target.id === "modal-detail") cerrarDetalle();
    });
    document.getElementById("ant-search").addEventListener("input", render);
    const faseSel = document.getElementById("ant-fase");
    if (faseSel) {
        faseSel.addEventListener("change", () => {
            ctx.fase = faseSel.value;
            render();
        });
    }
    // Descargas de evidencia/archivos + colapsables (componente compartido).
    attachGestionDownloadHandlers(document.getElementById("detail-content"), mostrarError);
    cargar();
}

function accionDe(estado) {
    return ACCIONES[estado] || null;
}

async function cargar() {
    try {
        ctx.items = await api.get("/contratos");
        render();
    } catch (e) {
        mostrarError(e);
        document.getElementById("ant-tbody").innerHTML =
            '<tr><td colspan="5" class="muted text-center">No se pudo cargar.</td></tr>';
    }
}

function render() {
    const q = (document.getElementById("ant-search").value || "").toLowerCase().trim();
    // Cada rol ve los contratos en sus etapas de anticipo y cierre (aplica también
    // para admin, que de lo contrario recibiría todos los contratos del backend).
    const filtrados = ctx.items.filter((c) => {
        const accion = accionDe(c.estado);
        if (!accion || !ctx.estados.includes(c.estado)) return false;
        if (ctx.fase !== "todos" && accion.fase !== ctx.fase) return false;
        if (!q) return true;
        return (
            (c.codigo || "").toLowerCase().includes(q) ||
            (c.proveedor_contratista || "").toLowerCase().includes(q)
        );
    });
    document.getElementById("ant-result-count").textContent =
        `${filtrados.length} contrato(s)`;
    const tbody = document.getElementById("ant-tbody");
    if (!filtrados.length) {
        tbody.innerHTML =
            '<tr><td colspan="5" class="muted text-center">Nada pendiente por ahora.</td></tr>';
        return;
    }
    tbody.innerHTML = filtrados
        .map((c) => {
            const accion = accionDe(c.estado);
            const badge =
                accion.fase === "cierre"
                    ? '<span class="badge badge-cierre">Cierre</span>'
                    : '<span class="badge badge-anticipo">Anticipo</span>';
            return `
                <tr>
                    <td>
                        <span class="codigo-contrato">${escapeHtml(c.codigo || "")}</span>
                        ${badge}
                    </td>
                    <td>${escapeHtml(c.proveedor_contratista || "")}</td>
                    <td>${formatMoney(c.valor, c.moneda)}</td>
                    <td>${c.solicitud_gestion_codigo ? escapeHtml(c.solicitud_gestion_codigo) : "—"}</td>
                    <td>
                        <button class="btn btn-sm btn-primary" data-id="${c.id}">
                            Ver / gestionar
                        </button>
                    </td>
                </tr>`;
        })
        .join("");
    tbody.querySelectorAll("button[data-id]").forEach((b) => {
        b.addEventListener("click", () => abrirDetalle(Number(b.dataset.id)));
    });
}

async function abrirDetalle(id) {
    limpiarAlertas();
    let contrato;
    let solicitud = null;
    try {
        contrato = await api.get(`/contratos/${id}`);
        if (contrato.solicitud_gestion_id) {
            try {
                solicitud = await api.get(
                    `/solicitudes-gestion/${contrato.solicitud_gestion_id}`
                );
            } catch (_) {
                solicitud = null;
            }
        }
    } catch (e) {
        mostrarError(e);
        return;
    }
    ctx.detalle = { contrato, solicitud };
    document.getElementById("detail-title").textContent =
        `${contrato.codigo || ""} · ${contrato.proveedor_contratista || ""}`;
    const content = document.getElementById("detail-content");
    content.innerHTML = renderDetalle(contrato, solicitud);
    // Editor con barra de formato + clip para adjuntar (mismo componente del resto).
    // El autoguardado (por rol + contrato) lo maneja el propio componente.
    ctx.obsControl = createObservacionConAdjuntos({
        editorContainerId: "cierre-editor",
        fileInputId: "cierre-file-input",
        fileListId: "cierre-file-list",
        name: "observacion",
        placeholder: "Describe la gestión realizada y adjunta la evidencia...",
        minHeight: 140,
        autosaveKey: `cierre:${ctx.rol}:${contrato.id}`,
    });
    if (ctx.obsControl.draftRestored) {
        const note = document.getElementById("cierre-draft-note");
        if (note) note.hidden = false;
        if (ctx.detalle.solicitud) {
            // ponytail: reusa la hidratación de imágenes por si el borrador ya tenía
            // imágenes referenciadas (evita romper miniaturas restauradas).
            hydrateInlineObservacionImages(content, ctx.detalle.solicitud.id);
        }
    }
    const descartar = document.getElementById("cierre-draft-descartar");
    if (descartar) {
        descartar.addEventListener("click", () => {
            ctx.obsControl?.clearAll();
            const note = document.getElementById("cierre-draft-note");
            if (note) note.hidden = true;
        });
    }
    document
        .getElementById("btn-ant-accion")
        .addEventListener("click", () => enviarAccion(contrato.id));
    if (solicitud) hydrateInlineObservacionImages(content, solicitud.id);
    document.getElementById("modal-detail").classList.add("show");
}

function cerrarDetalle() {
    document.getElementById("modal-detail").classList.remove("show");
    // Deja el borrador en localStorage a propósito: si cerró por accidente, al
    // reabrir sigue donde iba. Solo se limpia al enviar o al descartar.
    if (ctx.obsControl) {
        try {
            ctx.obsControl.destroy();
        } catch (_) {
            /* noop */
        }
        ctx.obsControl = null;
    }
    ctx.detalle = null;
}

function renderArchivosContratoHtml(c) {
    const archivos = c.archivos || [];
    if (!archivos.length) {
        return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Archivos del contrato</h3>
            <p class="muted">Este contrato no tiene archivos cargados.</p>
        </div>`;
    }
    const items = archivos
        .map((a) => {
            const label = TIPO_ARCHIVO_LABEL[a.tipo] || a.tipo || "Archivo";
            return `
            <li class="sg-archivo-item">
                <span class="sg-archivo-tipo">${escapeHtml(label)}</span>
                <a href="#" data-download-url="/archivos/${c.id}/${a.id}"
                   data-filename="${escapeHtml(a.nombre_original || "archivo")}"
                   ${a.mime_type ? `data-mime-type="${escapeHtml(a.mime_type)}"` : ""}>
                    ${escapeHtml(a.nombre_original || "archivo")}
                </a>
            </li>`;
        })
        .join("");
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Archivos del contrato</h3>
            <ul class="sg-archivo-list">${items}</ul>
        </div>`;
}

function renderDetalle(c, s) {
    const cfg = accionDe(c.estado);
    const filas = [
        ["Proveedor / Contratista", escapeHtml(c.proveedor_contratista || "—")],
        ["NIT", escapeHtml(c.nit_proveedor || "—")],
        ["Valor del contrato", formatMoney(c.valor, c.moneda)],
    ];
    if (c.monto_anticipo != null) {
        filas.push(["Monto del anticipo", formatMoney(c.monto_anticipo, c.moneda)]);
    }
    if (c.porcentaje_anticipo != null) {
        filas.push(["Porcentaje", `${Number(c.porcentaje_anticipo)}%`]);
    }
    if (c.solicitud_gestion_codigo) {
        filas.push(["SRV de origen", escapeHtml(c.solicitud_gestion_codigo)]);
    }

    const esCierre = cfg && cfg.fase === "cierre";
    const tituloDatos = esCierre ? "Datos del contrato" : "Datos del anticipo";

    const datos = `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">${tituloDatos}</h3>
            <dl class="sg-detail-grid">
                ${filas
                    .map(
                        ([k, v]) => `
                <div class="sg-detail-field">
                    <dt>${k}</dt>
                    <dd>${v}</dd>
                </div>`
                    )
                    .join("")}
            </dl>
            ${
                c.descripcion_servicio
                    ? `<p style="margin-top:8px;"><strong>Descripción:</strong> ${escapeHtml(
                          c.descripcion_servicio
                      )}</p>`
                    : ""
            }
            ${
                c.observaciones_anticipo
                    ? `<p style="margin-top:4px;"><strong>Observaciones del anticipo:</strong> ${escapeHtml(
                          c.observaciones_anticipo
                      )}</p>`
                    : ""
            }
        </div>`;

    // En el cierre mostramos también los archivos del contrato (contrato firmado,
    // informe final, acta de liquidación, etc.).
    const archivos = esCierre ? renderArchivosContratoHtml(c) : "";

    const traza = s
        ? renderFlujoHtml(s) + renderObservacionesTrazabilidadHtml(s)
        : `<div class="sg-detail-panel"><p class="muted">Este contrato no tiene una SRV vinculada para mostrar la trazabilidad.</p></div>`;

    const ayuda = cfg ? cfg.ayuda : "";
    const form = `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Registrar en la trazabilidad</h3>
            <p class="muted sg-detail-panel-hint">${escapeHtml(ayuda)}</p>
            <div class="sg-draft-note" id="cierre-draft-note" hidden>
                <span>Se restauró un borrador guardado automáticamente. Los archivos adjuntos debes volver a seleccionarlos.</span>
                <button type="button" class="btn btn-sm btn-secondary" id="cierre-draft-descartar">Descartar borrador</button>
            </div>
            <div class="field">
                <label for="cierre-editor">Comentario</label>
                <div id="cierre-editor"></div>
                <input type="file" id="cierre-file-input" multiple hidden />
                <ul class="file-list" id="cierre-file-list" hidden></ul>
                <span class="hint">Usa el clip de la barra para adjuntar archivos (o arrástralos sobre el editor). El botón de imagen inserta fotos dentro del comentario.</span>
            </div>
            <div class="modal-actions" style="margin-top:12px">
                <button type="button" class="btn btn-primary" id="btn-ant-accion">
                    ${escapeHtml(cfg ? cfg.boton : "Registrar")}
                </button>
            </div>
        </div>`;

    return datos + archivos + traza + form;
}

function renderFlujoHtml(s) {
    const historial = [...(s.historial_estados || [])].sort(
        (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0)
    );
    if (!historial.length) {
        return `
            <div class="sg-detail-panel sg-detail-panel--timeline">
                <h3 class="sg-detail-panel-title">Historial del flujo</h3>
                <p class="muted">Sin eventos registrados.</p>
            </div>`;
    }
    const pasos = historial
        .map((h, i) => {
            const status = i === historial.length - 1 ? "active" : "done";
            const meta = [];
            if (h.created_at) meta.push(fecha(h.created_at));
            if (h.usuario_username) meta.push(escapeHtml(h.usuario_username));
            if (h.comentario) meta.push(escapeHtml(h.comentario));
            return `
            <li class="sg-workflow-step sg-workflow-step--${status}">
                <span class="sg-workflow-marker" aria-hidden="true"></span>
                <div class="sg-workflow-body">
                    <strong>${escapeHtml(h.etapa_label || h.etapa)}</strong>
                    ${meta.length ? `<span class="sg-workflow-meta">${meta.join(" · ")}</span>` : ""}
                </div>
            </li>`;
        })
        .join("");
    return `
        <div class="sg-detail-panel sg-detail-panel--timeline">
            <h3 class="sg-detail-panel-title">Historial del flujo</h3>
            <ol class="sg-workflow-timeline sg-workflow-timeline--progressive">
                ${pasos}
            </ol>
        </div>`;
}

async function enviarAccion(id) {
    limpiarAlertas();
    const contrato = ctx.detalle?.contrato;
    const cfg = contrato ? accionDe(contrato.estado) : null;
    if (!cfg) {
        mostrarError("Este contrato ya no está en una etapa que puedas gestionar.");
        return;
    }
    const texto = (ctx.obsControl?.editor.getText() || "").trim();
    const html = ctx.obsControl?.editor.getHtml() || "";
    const adjuntos = ctx.obsControl?.getFiles() || [];
    if (!texto && adjuntos.length === 0) {
        mostrarError("Escribe un comentario o adjunta evidencia antes de continuar.");
        return;
    }
    const fd = new FormData();
    if (texto) fd.append("observacion", texto);
    if (html) fd.append("observacion_html", html);
    for (const a of adjuntos) fd.append("adjuntos", a);
    const btn = document.getElementById("btn-ant-accion");
    btn.disabled = true;
    try {
        await api.postForm(cfg.endpoint(id), fd);
        ctx.obsControl?.clearDraft();
        mostrarExito(cfg.okMsg);
        cerrarDetalle();
        await cargar();
    } catch (e) {
        mostrarError(e);
        btn.disabled = false;
    }
}

function fecha(iso) {
    try {
        return new Date(iso).toLocaleString("es-CO");
    } catch (_) {
        return iso;
    }
}

function mostrarError(e) {
    const el = document.getElementById("alert-error");
    el.textContent = e instanceof ApiError || e instanceof Error ? e.message : String(e);
    el.classList.add("show");
    document.getElementById("alert-success").classList.remove("show");
}

function mostrarExito(msg) {
    const el = document.getElementById("alert-success");
    el.textContent = msg;
    el.classList.add("show");
    document.getElementById("alert-error").classList.remove("show");
}

function limpiarAlertas() {
    document.getElementById("alert-error").classList.remove("show");
    document.getElementById("alert-success").classList.remove("show");
}
