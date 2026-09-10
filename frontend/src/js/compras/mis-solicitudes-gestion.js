import { api, ApiError } from "../api/client.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    hydrateInlineObservacionImages,
    hydrateComunicacionJuridica,
    puedeComentarPosteriorCotizacion,
    puedeEnviarEvidenciaCierreServicio,
    renderAgregarComentarioHtml,
    renderDetalleSolicitudHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js?v=47";

const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

const COMENTARIO_EDITOR_ID = "mis-sol-comentario-cotizacion-editor";
const COMENTARIO_FILE_INPUT_ID = "mis-sol-comentario-cotizacion-adjuntos";
const COMENTARIO_FILE_LIST_ID = "mis-sol-comentario-cotizacion-file-list";
const COMENTARIO_BTN_ID = "btn-mis-sol-guardar-comentario-cotizacion";
const REVISION_BTN_ID = "btn-mis-sol-responder-revision";

export function initMisSolicitudesGestion({ esAdmin }) {
    const tbody = document.getElementById("gestion-tbody");
    const searchInput = document.getElementById("gestion-search");
    const filterTipo = document.getElementById("gestion-filter-tipo");
    const resultCount = document.getElementById("gestion-result-count");
    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const modal = document.getElementById("modal-gestion-detail");
    const detailContent = document.getElementById("gestion-detail-content");
    const detailTitle = document.getElementById("gestion-detail-title");

    function showError(msg) {
        alertSuccess?.classList.remove("show");
        if (!alertError) return;
        alertError.textContent = msg;
        alertError.classList.add("show");
    }

    function showSuccess(msg) {
        alertError?.classList.remove("show");
        if (!alertSuccess) return;
        alertSuccess.textContent = msg;
        alertSuccess.classList.add("show");
        setTimeout(() => alertSuccess.classList.remove("show"), 4000);
    }

    if (!tbody) {
        showError("No se pudo inicializar la tabla de solicitudes.");
        return;
    }

    const subtitle = document.getElementById("page-subtitle");
    if (subtitle) {
        subtitle.textContent = esAdmin
            ? "Consulta todas las solicitudes registradas, incluidas las pendientes de aprobación."
            : "Tus solicitudes registradas en el módulo, incluidas las pendientes de aprobación.";
    }

    let items = [];
    let selectedSolicitudId = null;
    let selectedSolicitud = null;
    let modoEdicion = false;
    let observacionControl = null;

    function destroyObservacionEditor() {
        observacionControl?.destroy();
        observacionControl = null;
    }

    function initObservacionEditor() {
        destroyObservacionEditor();
        if (!document.getElementById(COMENTARIO_EDITOR_ID)) return;
        const enRevision = Boolean(document.getElementById("panel-revision-solicitante"));
        observacionControl = createObservacionConAdjuntos({
            editorContainerId: COMENTARIO_EDITOR_ID,
            fileInputId: COMENTARIO_FILE_INPUT_ID,
            fileListId: COMENTARIO_FILE_LIST_ID,
            name: "comentario_cotizacion",
            placeholder: enRevision
                ? "Describe qué corregiste para el aprobador…"
                : "Escribe un comentario sobre la cotización o el proceso de compra...",
            autosaveKey: selectedSolicitudId
                ? `mis-sol:${enRevision ? "revision" : "comentario"}:${selectedSolicitudId}`
                : "",
        });
    }

    function buildQuery() {
        const params = new URLSearchParams();
        const q = searchInput?.value.trim() ?? "";
        const tipo = filterTipo?.value ?? "";
        if (q) params.set("q", q);
        if (tipo) params.set("tipo", tipo);
        const qs = params.toString();
        return `/solicitudes-gestion${qs ? `?${qs}` : ""}`;
    }

    function renderTable() {
        if (!Array.isArray(items) || !items.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="muted text-center">
                No hay solicitudes registradas en Gestión de Solicitudes a Compras.
                <br /><a href="/app/compras/nueva-solicitud.html">Crear nueva solicitud</a>
            </td></tr>`;
            if (resultCount) resultCount.textContent = "0 solicitudes";
            return;
        }

        tbody.innerHTML = items
            .map(
                (s) => `
            <tr>
                <td data-label="Consecutivo">
                    <span class="codigo-solicitud">${escapeHtml(s.codigo)}</span>
                </td>
                <td data-label="Título">${escapeHtml(s.titulo || "—")}</td>
                <td data-label="Tipo">${badgeTipo(s.tipo)}</td>
                <td data-label="Estado">${badgeEstado(s.estado, s)}</td>
                <td data-label="Fecha">${formatDate(s.created_at)}</td>
                <td data-label="Acciones" class="col-actions">
                    <button
                        type="button"
                        class="btn btn-secondary btn-icon-view"
                        data-id="${s.id}"
                        title="Ver detalle"
                        aria-label="Ver solicitud ${escapeHtml(s.codigo)}"
                    >
                        ${EYE_ICON}
                        <span>Ver</span>
                    </button>
                </td>
            </tr>`
            )
            .join("");

        if (resultCount) {
            resultCount.textContent = `${items.length} solicitud${items.length === 1 ? "" : "es"}`;
        }

        tbody.querySelectorAll(".btn-icon-view").forEach((btn) => {
            btn.addEventListener("click", () => openDetail(Number(btn.dataset.id)));
        });
    }

    async function load() {
        tbody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">Cargando...</td></tr>';
        try {
            const data = await api.get(buildQuery());
            items = Array.isArray(data) ? data : [];
            renderTable();
        } catch (err) {
            const msg =
                err instanceof ApiError
                    ? err.message
                    : "No se pudieron cargar las solicitudes.";
            tbody.innerHTML = `<tr><td colspan="6" class="muted text-center">${escapeHtml(msg)}</td></tr>`;
            if (resultCount) resultCount.textContent = "";
            showError(msg);
        }
    }

    function esEnRevision(s) {
        const estado = String(s?.estado || "").toLowerCase();
        const label = String(s?.estado_label || "").toLowerCase();
        return estado === "revision" || label.includes("revisi");
    }

    function renderCamposAjusteHtml(s) {
        const esSrv = (s.tipo || "") === "insumos_servicios";
        if (!esSrv) return "";
        const desc =
            (s.descripcion_servicio_texto || "").trim() ||
            String(s.descripcion_servicio || "")
                .replace(/<[^>]+>/g, " ")
                .replace(/\s+/g, " ")
                .trim();
        const obs =
            (s.observaciones_texto || "").trim() ||
            String(s.observaciones || "")
                .replace(/<[^>]+>/g, " ")
                .replace(/\s+/g, " ")
                .trim();
        return `
            <div class="field">
                <label for="rev-titulo">Asunto / título</label>
                <input id="rev-titulo" type="text" value="${escapeHtml(s.titulo || "")}" />
            </div>
            <div class="field">
                <label for="rev-centro-costo">Centro de costo</label>
                <input id="rev-centro-costo" type="text" value="${escapeHtml(s.centro_costo_area || "")}" />
            </div>
            <div class="field">
                <label for="rev-proveedor">Proveedor sugerido</label>
                <textarea id="rev-proveedor" rows="2">${escapeHtml(s.proveedor_sugerido || "")}</textarea>
            </div>
            <div class="field">
                <label for="rev-descripcion">Descripción del servicio</label>
                <textarea id="rev-descripcion" rows="4">${escapeHtml(desc)}</textarea>
            </div>
            <div class="field">
                <label for="rev-observaciones">Observaciones</label>
                <textarea id="rev-observaciones" rows="2">${escapeHtml(obs)}</textarea>
            </div>`;
    }

    function renderPanelRevisionHtml(s) {
        return `
            <div class="sg-detail-panel" id="panel-revision-solicitante">
                <h3 class="sg-detail-panel-title">Editar y reenviar</h3>
                <p class="muted sg-detail-panel-hint">
                    Corrige los datos, comenta qué ajustaste y reenvía a primera aprobación.
                </p>
                ${renderCamposAjusteHtml(s)}
                ${renderAgregarComentarioHtml({
                    editorContainerId: COMENTARIO_EDITOR_ID,
                    fileInputId: COMENTARIO_FILE_INPUT_ID,
                    fileListId: COMENTARIO_FILE_LIST_ID,
                    btnId: REVISION_BTN_ID,
                    title: "Comentario para el aprobador",
                    label: "Qué ajustaste (obligatorio)",
                    showIntro: false,
                    showHint: true,
                    showSaveButton: true,
                })}
            </div>`;
    }

    function renderPanelComiteHtml(s) {
        const supOk = s.comite_supervisor_ok;
        const proyOk = s.comite_proyectos_ok;
        return `
            <div class="sg-detail-panel" id="panel-comite-supervisor">
                <h3 class="sg-detail-panel-title">Comité técnico</h3>
                <p class="muted sg-detail-panel-hint">
                    Tras la reunión del comité, confirma si estás de acuerdo para continuar.
                    Si no hay acuerdo, la solicitud vuelve a Proyectos para recotizar.
                </p>
                <p><strong>Supervisor:</strong> ${supOk ? "✓ De acuerdo" : "pendiente"}</p>
                <p><strong>Proyectos:</strong> ${proyOk ? "✓ De acuerdo" : "pendiente"}</p>
                <div class="form-group">
                    <label for="comite-sup-observacion">Acta / observación (opcional)</label>
                    <textarea id="comite-sup-observacion" rows="2"
                        placeholder="Lo hablado en la reunión..."></textarea>
                </div>
                <div class="form-group">
                    <label for="comite-sup-adjuntos">Adjuntos (opcional)</label>
                    <input type="file" id="comite-sup-adjuntos" multiple />
                </div>
                <div class="modal-actions" style="margin-top:8px">
                    <button type="button" class="btn btn-danger" id="btn-comite-recotizar">
                        No estoy de acuerdo / recotizar
                    </button>
                    <button type="button" class="btn btn-primary" id="btn-comite-aceptar">
                        Estoy de acuerdo
                    </button>
                </div>
            </div>`;
    }

    function renderDetalleConComentario(s) {
        const puedeEvidencia = puedeEnviarEvidenciaCierreServicio(s.estado, s);
        const puedeComentar =
            puedeEvidencia || puedeComentarPosteriorCotizacion(s.estado);

        if (esEnRevision(s) && modoEdicion) {
            return renderPanelRevisionHtml(s);
        }

        const detalle = renderDetalleSolicitudHtml(s, {
            productosOptions: {
                resaltarNoAprobados: true,
                showEstado: true,
                titulo: "Productos solicitados",
            },
        });

        if (s.estado === "comite") {
            return detalle + renderPanelComiteHtml(s);
        }

        if (esEnRevision(s) || !puedeComentar) return detalle;

        return (
            detalle +
            renderAgregarComentarioHtml({
                editorContainerId: COMENTARIO_EDITOR_ID,
                fileInputId: COMENTARIO_FILE_INPUT_ID,
                fileListId: COMENTARIO_FILE_LIST_ID,
                btnId: COMENTARIO_BTN_ID,
                title: puedeEvidencia
                    ? "Evidencia y observación de cierre"
                    : "Comentario sobre la cotización",
                label: puedeEvidencia ? "Evidencia y comentario de cierre" : "Nuevo comentario",
                showIntro: true,
                showHint: true,
                showSaveButton: true,
                introHtml: puedeEvidencia
                    ? `<p class="muted sg-detail-panel-hint">
                        El gestor solicitó evidencia para cerrar el servicio. Adjunta archivos
                        (facturas, actas, fotos, etc.) y describe la observación de cierre.
                    </p>`
                    : "",
            })
        );
    }

    function syncGear(s) {
        const gear = document.getElementById("btn-editar-revision");
        const footerBtn = document.getElementById("btn-mis-sol-reenviar-revision-footer");
        const enRevision = esEnRevision(s);
        if (gear) {
            if (enRevision) {
                gear.hidden = false;
                gear.classList.toggle("is-open", modoEdicion);
                gear.classList.toggle("is-pending", !modoEdicion);
                gear.setAttribute("aria-pressed", modoEdicion ? "true" : "false");
                gear.title = modoEdicion
                    ? "Volver al detalle"
                    : "Editar y reenviar ajustes";
            } else {
                gear.hidden = true;
                gear.classList.remove("is-open", "is-pending");
            }
        }
        if (footerBtn) {
            if (enRevision && modoEdicion) footerBtn.removeAttribute("hidden");
            else footerBtn.setAttribute("hidden", "");
        }
    }

    async function renderDetalle(s) {
        selectedSolicitud = s;
        detailContent.innerHTML = renderDetalleConComentario(s);
        initObservacionEditor();
        const revBtn = document.getElementById(REVISION_BTN_ID);
        if (revBtn) {
            revBtn.textContent = "Ajustar y reenviar a aprobación";
            revBtn.classList.remove("btn-secondary", "btn-sm");
            revBtn.classList.add("btn-primary");
        }
        syncGear(s);
        const btnComiteOk = document.getElementById("btn-comite-aceptar");
        if (btnComiteOk) {
            btnComiteOk.addEventListener("click", () => resolverComite(s.id, false));
        }
        const btnComiteReco = document.getElementById("btn-comite-recotizar");
        if (btnComiteReco) {
            btnComiteReco.addEventListener("click", () => resolverComite(s.id, true));
        }
        await hydrateInlineObservacionImages(detailContent, s.id);
        await hydrateComunicacionJuridica(showError);
    }

    async function resolverComite(id, recotizar) {
        if (recotizar && !confirm("¿Devolver la solicitud a Proyectos para recotizar?")) {
            return;
        }
        const obs = (document.getElementById("comite-sup-observacion")?.value || "").trim();
        const adjuntos = document.getElementById("comite-sup-adjuntos")?.files || [];
        const fd = new FormData();
        if (recotizar) {
            if (obs) fd.append("motivo_texto", obs);
        } else if (obs) {
            fd.append("observacion_texto", obs);
        }
        for (const a of adjuntos) fd.append("adjuntos", a);
        const url = recotizar
            ? `/solicitudes-gestion/${id}/comite/recotizar`
            : `/solicitudes-gestion/${id}/comite/aceptar`;
        try {
            await api.postForm(url, fd);
            showSuccess(
                recotizar
                    ? "Solicitud devuelta a Proyectos para recotizar."
                    : "Registramos tu aceptación del comité."
            );
            modal.classList.remove("show");
            await load();
        } catch (err) {
            showError(err instanceof ApiError ? err.message : "No se pudo procesar la acción.");
        }
    }

    async function openDetail(id) {
        try {
            const s = await api.get(`/solicitudes-gestion/${id}`);
            selectedSolicitudId = s.id;
            modoEdicion = false;
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            await renderDetalle(s);
            modal.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
    }

    async function toggleEdicion() {
        if (!esEnRevision(selectedSolicitud)) return;
        modoEdicion = !modoEdicion;
        await renderDetalle(selectedSolicitud);
    }

    async function guardarComentarioCotizacion() {
        if (!selectedSolicitudId || !observacionControl) return;

        observacionControl.editor.syncHidden();
        const contenido = observacionControl.editor.getHtml() ?? "";
        const contenidoTexto = observacionControl.editor.getText() ?? "";
        const adjuntos = observacionControl.getFiles() ?? [];

        if (!contenidoTexto.trim() && !contenido.trim() && !adjuntos.length) {
            showError("Escribe un comentario o adjunta al menos un archivo.");
            return;
        }
        observacionControl.clearDraft();

        const btn = document.getElementById(COMENTARIO_BTN_ID);
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Guardando...";
        }

        const formData = new FormData();
        formData.append("contenido", contenido);
        formData.append("contenido_texto", contenidoTexto);
        formData.append("contexto_rol", "solicitante");
        adjuntos.forEach((file) => formData.append("adjuntos", file));

        try {
            await api.postForm(
                `/solicitudes-gestion/${selectedSolicitudId}/observaciones`,
                formData
            );
            const s = await api.get(`/solicitudes-gestion/${selectedSolicitudId}`);
            showSuccess(
                puedeEnviarEvidenciaCierreServicio(s.estado, s)
                    ? "Evidencia y observación de cierre registradas."
                    : "Comentario registrado en el historial de la solicitud."
            );
            await renderDetalle(s);
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo guardar el comentario."
            );
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Guardar comentario";
            }
        }
    }

    async function responderRevision() {
        if (!selectedSolicitudId || !observacionControl) return;

        observacionControl.editor.syncHidden();
        const contenido = observacionControl.editor.getHtml() ?? "";
        const contenidoTexto = observacionControl.editor.getText() ?? "";
        const adjuntos = observacionControl.getFiles() ?? [];

        if (!contenidoTexto.trim() && !contenido.trim()) {
            showError("Describe los ajustes realizados antes de reenviar.");
            return;
        }
        observacionControl.clearDraft();

        const btn = document.getElementById(REVISION_BTN_ID);
        const footerBtn = document.getElementById("btn-mis-sol-reenviar-revision-footer");
        const setBusy = (busy) => {
            [btn, footerBtn].forEach((b) => {
                if (!b) return;
                b.disabled = busy;
                if (busy) b.textContent = "Enviando...";
                else if (b.id === REVISION_BTN_ID || b.id === "btn-mis-sol-reenviar-revision-footer") {
                    b.textContent = "Ajustar y reenviar a aprobación";
                }
            });
        };
        setBusy(true);

        const formData = new FormData();
        formData.append("observacion", contenido);
        formData.append("observacion_texto", contenidoTexto);
        const titulo = document.getElementById("rev-titulo");
        if (titulo) formData.append("titulo", titulo.value.trim());
        const centro = document.getElementById("rev-centro-costo");
        if (centro) formData.append("centro_costo_area", centro.value.trim());
        const proveedor = document.getElementById("rev-proveedor");
        if (proveedor) formData.append("proveedor_sugerido", proveedor.value);
        const descripcion = document.getElementById("rev-descripcion");
        if (descripcion) {
            formData.append("descripcion_servicio_texto", descripcion.value);
            formData.append("descripcion_servicio", "");
        }
        const obs = document.getElementById("rev-observaciones");
        if (obs) {
            formData.append("observaciones_texto", obs.value);
            formData.append("observaciones", "");
        }
        adjuntos.forEach((file) => formData.append("adjuntos", file));

        try {
            await api.postForm(
                `/solicitudes-gestion/${selectedSolicitudId}/responder-revision`,
                formData
            );
            showSuccess("Ajustes enviados. Tu solicitud volvió a primera aprobación.");
            const s = await api.get(`/solicitudes-gestion/${selectedSolicitudId}`);
            modoEdicion = false;
            await renderDetalle(s);
            await load();
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudieron enviar los ajustes."
            );
            setBusy(false);
        }
    }

    load();

    try {
        attachGestionDownloadHandlers(detailContent, showError);
    } catch (err) {
        showError("No se pudieron habilitar las descargas de archivos.");
    }

    detailContent?.addEventListener("click", (e) => {
        if (e.target.closest(`#${COMENTARIO_BTN_ID}`)) {
            guardarComentarioCotizacion();
        } else if (e.target.closest(`#${REVISION_BTN_ID}`)) {
            responderRevision();
        }
    });

    function closeModal() {
        modal.classList.remove("show");
        destroyObservacionEditor();
        selectedSolicitudId = null;
        selectedSolicitud = null;
        modoEdicion = false;
        syncGear(null);
    }

    document.getElementById("btn-editar-revision")?.addEventListener("click", toggleEdicion);
    document.getElementById("btn-gestion-detail-close")?.addEventListener("click", closeModal);
    document.getElementById("btn-mis-sol-reenviar-revision-footer")?.addEventListener(
        "click",
        responderRevision
    );
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    let debounce;
    searchInput?.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(load, 300);
    });
    filterTipo?.addEventListener("change", load);
}
