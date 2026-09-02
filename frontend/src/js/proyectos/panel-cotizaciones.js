// Panel del rol Proyectos: cotiza SRV con comité técnico y participa en el comité.

import { api, ApiError } from "../api/client.js";
import { escapeHtml, previewValorCotizacion } from "../utils/format.js";
import { createProveedorPicker } from "../components/proveedor-picker.js";
import {
    renderWorkflowTimelineHtml,
    renderObservacionesTrazabilidadHtml,
    renderArchivosHtml,
    renderCotizacionSlotHtml,
    renderVisitaProgramadaRowHtml,
    attachGestionDownloadHandlers,
    hydrateInlineObservacionImages,
} from "../compras/gestion-solicitudes-common.js?v=46";

const ESTADO_LABEL = {
    primera_aprobacion: "Primera aprobación",
    revision_proyectos: "Revisión de solicitud (Proyectos)",
    programacion_visita: "Programar visita",
    cotizacion_proyectos: "Cotización (Proyectos)",
    comite: "Comité técnico",
};

let ctx = { user: null, items: [], detalle: null };

export function initPanelProyectos({ user }) {
    ctx.user = user;
    document
        .getElementById("btn-proy-detail-close")
        .addEventListener("click", cerrarDetalle);
    document.getElementById("modal-proy-detail").addEventListener("click", (e) => {
        if (e.target.id === "modal-proy-detail") cerrarDetalle();
    });
    attachGestionDownloadHandlers(
        document.getElementById("proy-detail-content"),
        (msg) => mostrarError(msg)
    );
    const search = document.getElementById("proy-search");
    search.addEventListener("input", () => render());
    cargar();
}

async function cargar() {
    try {
        ctx.items = await api.get("/solicitudes-gestion/panel-proyectos");
        render();
    } catch (e) {
        mostrarError(e);
        document.getElementById("proy-tbody").innerHTML =
            '<tr><td colspan="5" class="muted text-center">No se pudo cargar.</td></tr>';
    }
}

function render() {
    const q = (document.getElementById("proy-search").value || "").toLowerCase().trim();
    const filtrados = ctx.items.filter((s) => {
        if (!q) return true;
        return (
            (s.codigo || "").toLowerCase().includes(q) ||
            (s.titulo || "").toLowerCase().includes(q)
        );
    });
    document.getElementById("proy-result-count").textContent =
        `${filtrados.length} solicitud(es)`;
    const tbody = document.getElementById("proy-tbody");
    if (!filtrados.length) {
        tbody.innerHTML =
            '<tr><td colspan="5" class="muted text-center">Sin solicitudes por ahora.</td></tr>';
        return;
    }
    tbody.innerHTML = filtrados
        .map((s) => {
            const estado = ESTADO_LABEL[s.estado] || s.estado_label || s.estado;
            const accion =
                s.estado === "comite"
                    ? s.comite_proyectos_ok
                        ? "Esperando supervisor"
                        : "Ver comité"
                    : s.estado === "revision_proyectos"
                    ? "Revisar solicitud"
                    : s.estado === "programacion_visita"
                    ? "Programar visita"
                    : "Cotizar";
            return `
                <tr>
                    <td><strong>${escapeHtml(s.codigo || "")}</strong></td>
                    <td>${escapeHtml(s.titulo || "")}</td>
                    <td>${escapeHtml(s.centro_costo_area || "")}</td>
                    <td><span class="badge">${escapeHtml(estado)}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" data-id="${s.id}">
                            ${accion}
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
    try {
        ctx.detalle = await api.get(`/solicitudes-gestion/${id}`);
    } catch (e) {
        mostrarError(e);
        return;
    }
    const s = ctx.detalle;
    document.getElementById("proy-detail-title").textContent =
        `${s.codigo || ""} · ${s.titulo || ""}`;
    const content = document.getElementById("proy-detail-content");
    content.innerHTML = renderDetalle(s);
    conectarFormulario(s);
    hydrateInlineObservacionImages(content, s.id);
    document.getElementById("modal-proy-detail").classList.add("show");
}

function cerrarDetalle() {
    document.getElementById("modal-proy-detail").classList.remove("show");
    ctx.detalle = null;
}

function cotizacionesActuales(s) {
    return (s.archivos || []).filter((a) => a.categoria === "cotizacion");
}

function renderDetalle(s) {
    const cots = cotizacionesActuales(s);
    const panelCots = cots.length
        ? renderArchivosHtml(s, {
              categoria: "cotizacion",
              titulo: "Cotizaciones registradas",
              seleccionable: false,
          })
        : `<div class="sg-detail-panel">
                <h3 class="sg-detail-panel-title">Cotizaciones registradas</h3>
                <p class="muted">Aún no hay cotizaciones.</p>
           </div>`;

    const descripcion = s.descripcion_servicio_texto || s.descripcion_servicio || "";
    const cabecera = `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Información</h3>
            <dl class="sg-detail-grid">
                <div class="sg-detail-field">
                    <dt>Área</dt>
                    <dd>${escapeHtml(s.centro_costo_area || "—")}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Estado</dt>
                    <dd><span class="badge">${escapeHtml(
                        ESTADO_LABEL[s.estado] || s.estado
                    )}</span></dd>
                </div>
            </dl>
            ${
                descripcion
                    ? `<p style="margin-top:8px;"><strong>Descripción:</strong> ${escapeHtml(
                          descripcion
                      )}</p>`
                    : ""
            }
        </div>
        ${panelCots}`;

    const traza = renderWorkflowTimelineHtml(s) + renderObservacionesTrazabilidadHtml(s);

    if (s.estado === "revision_proyectos") {
        return cabecera + traza + renderFormRevision(s);
    }
    if (s.estado === "programacion_visita") {
        return cabecera + traza + renderFormVisita(s);
    }
    if (s.estado === "comite") {
        return cabecera + traza + renderComite(s);
    }
    if (s.estado === "cotizacion_proyectos") {
        return cabecera + traza + renderFormCotizacion(s);
    }
    // Estados terminales/de contrato (contrato_completado, finalizado, cancelado…):
    // la SRV ya no admite acciones de Proyectos, solo lectura.
    return (
        cabecera +
        traza +
        `<div class="sg-detail-panel">
            <p class="muted">
                Esta solicitud ya está cerrada (el contrato finalizó su ciclo).
                No hay acciones pendientes para Proyectos.
            </p>
        </div>`
    );
}

function documentosSolicitud(s) {
    return (s.archivos || []).filter(
        (a) =>
            !a.observacion_id &&
            !["cotizacion", "observacion_inline"].includes(a.categoria || "")
    );
}

const CATEGORIA_LABEL = {
    ficha_tecnica: "Ficha técnica",
    hoja_vida_equipo: "Hoja de vida del equipo",
    detalle_servicio: "Detalle del servicio",
    observacion: "Adjunto",
    solicitud: "Documento",
};

function renderDocumentosSolicitudHtml(s) {
    const docs = documentosSolicitud(s);
    if (!docs.length) {
        return `
            <div class="sg-detail-panel">
                <h3 class="sg-detail-panel-title">Documentos de la solicitud</h3>
                <p class="muted">La solicitud no tiene documentos adjuntos.</p>
            </div>`;
    }
    const items = docs
        .map((a) => {
            const cat = CATEGORIA_LABEL[a.categoria || "solicitud"] || "Documento";
            return `
                <li class="sg-attachment-item">
                    <span class="sg-attachment-icon" aria-hidden="true">📎</span>
                    <div class="sg-attachment-info">
                        <strong>${escapeHtml(a.nombre_original)}</strong>
                        <span class="muted">${escapeHtml(cat)}</span>
                    </div>
                    <a href="#" class="btn btn-secondary btn-sm"
                        data-download-url="/solicitudes-gestion/${s.id}/archivos/${a.id}"
                        data-filename="${escapeHtml(a.nombre_original)}"
                        data-mime-type="${escapeHtml(a.mime_type || "")}">Ver</a>
                </li>`;
        })
        .join("");
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Documentos de la solicitud (${docs.length})</h3>
            <ul class="sg-attachment-list">${items}</ul>
        </div>`;
}

function renderFormRevision(s) {
    const val = (x) => escapeHtml(x || "");
    return `
        ${renderDocumentosSolicitudHtml(s)}
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Revisar y reescribir la solicitud</h3>
            <p class="muted sg-detail-panel-hint">
                Ajusta lo que necesites de la solicitud. Al confirmar, la solicitud
                pasa a Cotización (Proyectos) para adjuntar las cotizaciones.
            </p>
            <div class="field">
                <label for="rev-titulo">Título</label>
                <input type="text" id="rev-titulo" value="${val(s.titulo)}" />
            </div>
            <div class="field">
                <label for="rev-area">Área / centro de costo</label>
                <input type="text" id="rev-area" value="${val(s.centro_costo_area)}" />
            </div>

            <div class="field">
                <label>Proveedores</label>
                <p class="muted sg-detail-panel-hint" style="margin-top:0">
                    Busca en el catálogo, elige uno de los sugeridos o agrégalo manualmente.
                    Puedes elegir varios.
                </p>
                <div id="rev-prov-picker"></div>
            </div>

            <div class="field">
                <label for="rev-descripcion">Descripción del servicio</label>
                <textarea id="rev-descripcion" rows="4">${val(
                    s.descripcion_servicio_texto || s.descripcion_servicio
                )}</textarea>
            </div>
            <div class="field">
                <label for="rev-observaciones">Observaciones de la solicitud</label>
                <textarea id="rev-observaciones" rows="3">${val(
                    s.observaciones_texto || s.observaciones
                )}</textarea>
            </div>
            <div class="field" style="margin-top:12px">
                <label for="rev-nota">Nota del cambio (opcional)</label>
                <textarea id="rev-nota" rows="2"
                    placeholder="Qué ajustaste y por qué..."></textarea>
            </div>
            <div class="field">
                <label for="rev-adjuntos">Adjuntos (opcional)</label>
                <input type="file" id="rev-adjuntos" multiple />
            </div>
            <div class="modal-actions" style="margin-top:12px">
                <button type="button" class="btn btn-primary" id="btn-confirmar-revision">
                    Confirmar y pasar a cotización
                </button>
            </div>
        </div>`;
}

let revProvPicker = null;

function setupProveedorRevision(s) {
    const cont = document.getElementById("rev-prov-picker");
    if (!cont) return;
    revProvPicker = createProveedorPicker({
        container: cont,
        initialText: s.proveedor_sugerido || "",
        soloServicios: true,
        // Sólo título + descripción: incluir el área metía palabras genéricas
        // (p. ej. "control", "procesos") que traían proveedores irrelevantes.
        getQuery: () =>
            [s.titulo, s.descripcion_servicio_texto || s.descripcion_servicio]
                .filter(Boolean)
                .join(" "),
    });
}

function renderFormCotizacion(s) {
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Agregar cotizaciones</h3>
            <p class="muted sg-detail-panel-hint">
                Adjunta al menos una cotización con su valor. Puedes guardar y volver
                luego, o enviar a Compras cuando termines (Compras completará hasta 3).
            </p>
            <div id="cot-rows"></div>
            <button type="button" class="btn btn-sm btn-secondary" id="btn-add-cot">
                + Agregar cotización
            </button>
            <div class="field" style="margin-top:12px">
                <label for="cot-observacion">Observación (opcional)</label>
                <textarea id="cot-observacion" rows="2"
                    placeholder="Notas sobre las cotizaciones..."></textarea>
            </div>
            <div class="field">
                <label for="cot-adjuntos">Adjuntos de observación (opcional)</label>
                <input type="file" id="cot-adjuntos" multiple />
            </div>
            <div class="modal-actions" style="margin-top:12px">
                <button type="button" class="btn btn-secondary" id="btn-guardar-cot">
                    Guardar cotizaciones
                </button>
                <button type="button" class="btn btn-primary" id="btn-enviar-cot">
                    Enviar a Compras
                </button>
            </div>
        </div>`;
}

function renderFormVisita(s) {
    const visitas = s.visitas_programadas || [];
    const iniciales = visitas.length ? visitas : [{}];
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Programar visita</h3>
            <p class="muted sg-detail-panel-hint">
                Antes de cotizar, agenda la visita: datos del proveedor, día y hora.
                Al confirmar, la solicitud pasa a Cotización (Proyectos).
            </p>
            <input type="radio" name="programar_visita" value="si" checked hidden />
            <div class="sg-visitas-programadas-wrap" id="sg-visitas-programadas-wrap">
                <div class="sg-visitas-programadas-header">
                    <p class="hint muted">Registra proveedor, fecha y hora de cada visita.</p>
                    <button type="button" class="btn btn-secondary btn-sm"
                        id="btn-agregar-visita-programada">
                        + Agregar visita
                    </button>
                </div>
                <div id="sg-visitas-programadas-list">
                    ${iniciales.map((v) => renderVisitaProgramadaRowHtml(v)).join("")}
                </div>
            </div>
            <div class="field" style="margin-top:12px">
                <label for="visita-observacion">Observación (opcional)</label>
                <textarea id="visita-observacion" rows="2"
                    placeholder="Notas de la visita / acuerdos..."></textarea>
            </div>
            <div class="field">
                <label for="visita-adjuntos">Adjuntos (opcional)</label>
                <input type="file" id="visita-adjuntos" multiple />
            </div>
            <div class="modal-actions" style="margin-top:12px">
                <button type="button" class="btn btn-primary" id="btn-confirmar-visita">
                    Confirmar visita y continuar
                </button>
            </div>
        </div>`;
}

function renderComite(s) {
    const supOk = s.comite_supervisor_ok;
    const proyOk = s.comite_proyectos_ok;
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Comité técnico</h3>
            <p class="muted sg-detail-panel-hint">
                Tras la reunión, el supervisor y Proyectos deben aceptar para continuar.
                Si no hay acuerdo, se devuelve a Proyectos para recotizar.
            </p>
            <dl class="sg-detail-grid">
                <div class="sg-detail-field">
                    <dt>Supervisor</dt>
                    <dd>${supOk ? "✓ De acuerdo" : "Pendiente"}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Proyectos</dt>
                    <dd>${proyOk ? "✓ De acuerdo" : "Pendiente"}</dd>
                </div>
            </dl>
            ${
                proyOk
                    ? `<p class="muted" style="margin-top:12px">
                        Ya registraste tu acuerdo. Esperando la aceptación del supervisor.
                    </p>`
                    : `<div class="field" style="margin-top:12px">
                <label for="comite-observacion">Acta / observación (opcional)</label>
                <textarea id="comite-observacion" rows="2"
                    placeholder="Lo hablado en la reunión..."></textarea>
            </div>
            <div class="field">
                <label for="comite-adjuntos">Adjuntos (opcional)</label>
                <input type="file" id="comite-adjuntos" multiple />
            </div>
            <div class="modal-actions" style="margin-top:12px">
                <button type="button" class="btn btn-danger" id="btn-recotizar">
                    No estoy de acuerdo / recotizar
                </button>
                <button type="button" class="btn btn-primary" id="btn-aceptar-comite">
                    Estoy de acuerdo
                </button>
            </div>`
            }
        </div>`;
}

function conectarFormulario(s) {
    if (s.estado === "revision_proyectos") {
        document
            .getElementById("btn-confirmar-revision")
            .addEventListener("click", () => responderRevision(s.id));
        setupProveedorRevision(s);
        return;
    }
    if (s.estado === "programacion_visita") {
        conectarVisita(s);
        return;
    }
    if (s.estado === "comite") {
        const btnAceptar = document.getElementById("btn-aceptar-comite");
        const btnRecotizar = document.getElementById("btn-recotizar");
        if (btnAceptar)
            btnAceptar.addEventListener("click", () => aceptarComite(s.id));
        if (btnRecotizar)
            btnRecotizar.addEventListener("click", () => recotizarComite(s.id));
        return;
    }
    if (s.estado !== "cotizacion_proyectos") return; // SRV cerrada: sin formulario
    const rows = document.getElementById("cot-rows");
    let cotSeq = 0;
    const renumerar = () => {
        rows.querySelectorAll(".sg-cotizacion-slot-label").forEach((el, i) => {
            el.textContent = `Cotización ${i + 1}`;
        });
    };
    const wireSlot = (slot) => {
        const wrap = slot.querySelector(".cotizacion-anticipo-pct-wrap");
        const vivo = slot.querySelector(".sg-cotizacion-valor-vivo");
        const valorInput = slot.querySelector(".cotizacion-valor");
        const monedaSelect = slot.querySelector(".cotizacion-moneda");
        const syncAnticipo = () => {
            if (wrap) wrap.hidden = !slot.querySelector(".cotizacion-anticipo-si")?.checked;
        };
        const syncValorVivo = () => {
            if (vivo) vivo.textContent = previewValorCotizacion(valorInput?.value, monedaSelect?.value || "COP");
        };
        slot.querySelectorAll('input[name^="cotizacion-anticipo-"]').forEach((r) =>
            r.addEventListener("change", syncAnticipo)
        );
        valorInput?.addEventListener("input", syncValorVivo);
        monedaSelect?.addEventListener("change", syncValorVivo);
        const fileInput = slot.querySelector(".gestion-cotizacion-input");
        const nameEl = slot.querySelector(".sg-cotizacion-slot-name");
        const btnClear = slot.querySelector(".btn-cotizacion-clear");
        const syncFile = () => {
            const f = fileInput?.files?.[0];
            if (nameEl) nameEl.textContent = f ? f.name : "Sin archivo";
            if (btnClear) btnClear.hidden = !f;
        };
        fileInput?.addEventListener("change", syncFile);
        btnClear?.addEventListener("click", () => {
            if (fileInput) fileInput.value = "";
            syncFile();
        });
        syncAnticipo();
        syncValorVivo();
    };
    const addRow = () => {
        const tpl = document.createElement("template");
        tpl.innerHTML = renderCotizacionSlotHtml(cotSeq, { conDatosEconomicos: true }).trim();
        const slot = tpl.content.firstElementChild;
        const head = slot.querySelector(".sg-cotizacion-slot-head");
        if (!slot.querySelector(".sg-cotizacion-quitar-x")) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "sg-cotizacion-quitar-x cot-del";
            btn.setAttribute("aria-label", "Quitar cotización");
            btn.title = "Quitar cotización";
            btn.textContent = "×";
            head.appendChild(btn);
        }
        slot.querySelector(".sg-cotizacion-quitar-x").addEventListener("click", () => {
            slot.remove();
            renumerar();
        });
        rows.appendChild(slot);
        wireSlot(slot);
        cotSeq += 1;
        renumerar();
    };
    document.getElementById("btn-add-cot").addEventListener("click", addRow);
    addRow();
    document
        .getElementById("btn-guardar-cot")
        .addEventListener("click", () => enviarCotizaciones(s.id, false));
    document
        .getElementById("btn-enviar-cot")
        .addEventListener("click", () => enviarCotizaciones(s.id, true));
}

function recolectarCotizaciones() {
    const rows = Array.from(document.querySelectorAll("#cot-rows .sg-cotizacion-slot"));
    const files = [];
    const meta = [];
    for (const row of rows) {
        const file = row.querySelector(".gestion-cotizacion-input")?.files?.[0];
        if (!file) continue;
        const valor = row.querySelector(".cotizacion-valor")?.value.trim() ?? "";
        const moneda = row.querySelector(".cotizacion-moneda")?.value || "COP";
        const requiereAnticipo = Boolean(row.querySelector(".cotizacion-anticipo-si")?.checked);
        const porcentajeAnticipo = requiereAnticipo
            ? row.querySelector(".cotizacion-anticipo-pct")?.value.trim() ?? ""
            : "";
        files.push(file);
        meta.push({
            valor,
            moneda,
            requiere_anticipo: requiereAnticipo,
            porcentaje_anticipo: porcentajeAnticipo,
        });
    }
    return { files, meta };
}

async function enviarCotizaciones(id, enviar) {
    limpiarAlertas();
    const { files, meta } = recolectarCotizaciones();
    if (enviar && files.length === 0) {
        const cots = cotizacionesActuales(ctx.detalle);
        if (cots.length === 0) {
            mostrarError("Adjunta al menos una cotización antes de enviar a Compras.");
            return;
        }
    }
    for (let i = 0; i < files.length; i++) {
        if (!meta[i].valor || Number(meta[i].valor) <= 0) {
            mostrarError(`Indica el valor de la cotización ${i + 1}.`);
            return;
        }
        if (meta[i].requiere_anticipo) {
            const pct = Number(meta[i].porcentaje_anticipo);
            if (!pct || pct <= 0 || pct > 100) {
                mostrarError(`Indica el porcentaje de anticipo de la cotización ${i + 1} (1 a 100).`);
                return;
            }
        }
    }
    const fd = new FormData();
    files.forEach((f) => fd.append("cotizaciones", f));
    fd.append("cotizaciones_meta", JSON.stringify(meta));
    fd.append("enviar", enviar ? "true" : "false");
    const obs = (document.getElementById("cot-observacion").value || "").trim();
    if (obs) fd.append("nueva_observacion_texto", obs);
    const adjuntos = document.getElementById("cot-adjuntos").files;
    for (const a of adjuntos) fd.append("adjuntos", a);

    await ejecutar(
        () => api.postForm(`/solicitudes-gestion/${id}/cotizar-proyectos`, fd),
        enviar ? "Cotizaciones enviadas a Compras." : "Cotizaciones guardadas."
    );
}

function conectarVisita(s) {
    const list = document.getElementById("sg-visitas-programadas-list");
    document
        .getElementById("btn-agregar-visita-programada")
        ?.addEventListener("click", () => {
            const wrapper = document.createElement("div");
            wrapper.innerHTML = renderVisitaProgramadaRowHtml({});
            const row = wrapper.firstElementChild;
            if (row) list.appendChild(row);
        });
    list?.addEventListener("click", (e) => {
        const btn = e.target.closest(".btn-quitar-visita");
        if (!btn) return;
        const rows = list.querySelectorAll("[data-visita-row]");
        if (rows.length <= 1) {
            mostrarError("Debe quedar al menos una fila de visita.");
            return;
        }
        btn.closest("[data-visita-row]")?.remove();
    });
    document
        .getElementById("btn-confirmar-visita")
        .addEventListener("click", () => confirmarVisita(s.id));
}

function recolectarVisitas() {
    const list = document.getElementById("sg-visitas-programadas-list");
    const visitas = [];
    list?.querySelectorAll("[data-visita-row]").forEach((row) => {
        const proveedor = row.querySelector(".sg-visita-proveedor")?.value.trim() || "";
        const fecha = row.querySelector(".sg-visita-fecha")?.value.trim() || "";
        const hora = row.querySelector(".sg-visita-hora")?.value.trim() || "";
        if (!proveedor && !fecha && !hora) return;
        visitas.push({
            programador_visita: "",
            proveedor_visita: proveedor,
            fecha_visita: fecha || null,
            hora_visita: hora || null,
        });
    });
    return visitas;
}

async function confirmarVisita(id) {
    limpiarAlertas();
    const visitas = recolectarVisitas();
    if (!visitas.length) {
        mostrarError("Registra al menos una visita con proveedor y fecha.");
        return;
    }
    for (let i = 0; i < visitas.length; i += 1) {
        if (!visitas[i].proveedor_visita || !visitas[i].fecha_visita) {
            mostrarError(`Visita ${i + 1}: indica proveedor y fecha.`);
            return;
        }
    }
    const fd = new FormData();
    fd.append("visitas_json", JSON.stringify(visitas));
    const obs = (document.getElementById("visita-observacion").value || "").trim();
    if (obs) fd.append("nueva_observacion_texto", obs);
    for (const a of document.getElementById("visita-adjuntos").files)
        fd.append("adjuntos", a);
    await ejecutar(
        () => api.postForm(`/solicitudes-gestion/${id}/guardar-gestion-servicios`, fd),
        "Visita programada. Ahora puedes cargar las cotizaciones."
    );
}

async function responderRevision(id) {
    limpiarAlertas();
    const fd = new FormData();
    const g = (x) => (document.getElementById(x)?.value || "").trim();
    fd.append("titulo", g("rev-titulo"));
    fd.append("centro_costo_area", g("rev-area"));
    fd.append("proveedor_sugerido", revProvPicker ? revProvPicker.serialize() : "");
    fd.append("descripcion_servicio_texto", g("rev-descripcion"));
    fd.append("observaciones_texto", g("rev-observaciones"));
    const nota = g("rev-nota");
    if (nota) fd.append("observacion_texto", nota);
    for (const a of document.getElementById("rev-adjuntos").files)
        fd.append("adjuntos", a);
    await ejecutar(
        () => api.postForm(`/solicitudes-gestion/${id}/revisar-proyectos`, fd),
        "Solicitud revisada. Ahora puedes cargar las cotizaciones."
    );
}

async function aceptarComite(id) {
    limpiarAlertas();
    const fd = new FormData();
    const obs = (document.getElementById("comite-observacion").value || "").trim();
    if (obs) fd.append("observacion_texto", obs);
    for (const a of document.getElementById("comite-adjuntos").files)
        fd.append("adjuntos", a);
    await ejecutar(
        () => api.postForm(`/solicitudes-gestion/${id}/comite/aceptar`, fd),
        "Registramos tu aceptación del comité."
    );
}

async function recotizarComite(id) {
    limpiarAlertas();
    if (!confirm("¿Devolver la solicitud a Proyectos para recotizar?")) return;
    const fd = new FormData();
    const obs = (document.getElementById("comite-observacion").value || "").trim();
    if (obs) fd.append("motivo_texto", obs);
    for (const a of document.getElementById("comite-adjuntos").files)
        fd.append("adjuntos", a);
    await ejecutar(
        () => api.postForm(`/solicitudes-gestion/${id}/comite/recotizar`, fd),
        "Solicitud devuelta a cotización de proyectos."
    );
}

async function ejecutar(accion, mensajeOk) {
    try {
        await accion();
        mostrarExito(mensajeOk);
        cerrarDetalle();
        await cargar();
    } catch (e) {
        mostrarError(e);
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
