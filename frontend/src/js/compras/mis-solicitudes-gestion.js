import { api, ApiError } from "../api/client.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    hydrateInlineObservacionImages,
    puedeComentarPosteriorCotizacion,
    puedeEnviarEvidenciaCierreServicio,
    renderAgregarComentarioHtml,
    renderDetalleSolicitudHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js?v=26";

const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

const COMENTARIO_EDITOR_ID = "mis-sol-comentario-cotizacion-editor";
const COMENTARIO_FILE_INPUT_ID = "mis-sol-comentario-cotizacion-adjuntos";
const COMENTARIO_FILE_LIST_ID = "mis-sol-comentario-cotizacion-file-list";
const COMENTARIO_BTN_ID = "btn-mis-sol-guardar-comentario-cotizacion";

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
    let observacionControl = null;

    function destroyObservacionEditor() {
        observacionControl?.destroy();
        observacionControl = null;
    }

    function initObservacionEditor() {
        destroyObservacionEditor();
        if (!document.getElementById(COMENTARIO_EDITOR_ID)) return;
        observacionControl = createObservacionConAdjuntos({
            editorContainerId: COMENTARIO_EDITOR_ID,
            fileInputId: COMENTARIO_FILE_INPUT_ID,
            fileListId: COMENTARIO_FILE_LIST_ID,
            name: "comentario_cotizacion",
            placeholder: "Escribe un comentario sobre la cotización o el proceso de compra...",
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
            tbody.innerHTML = `<tr><td colspan="5" class="muted text-center">
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
            '<tr><td colspan="5" class="muted text-center">Cargando...</td></tr>';
        try {
            const data = await api.get(buildQuery());
            items = Array.isArray(data) ? data : [];
            renderTable();
        } catch (err) {
            const msg =
                err instanceof ApiError
                    ? err.message
                    : "No se pudieron cargar las solicitudes.";
            tbody.innerHTML = `<tr><td colspan="5" class="muted text-center">${escapeHtml(msg)}</td></tr>`;
            if (resultCount) resultCount.textContent = "";
            showError(msg);
        }
    }

    function renderDetalleConComentario(s) {
        const puedeEvidencia = puedeEnviarEvidenciaCierreServicio(s.estado, s);
        const puedeComentar =
            puedeEvidencia || puedeComentarPosteriorCotizacion(s.estado);
        const detalle = renderDetalleSolicitudHtml(s, {
            productosOptions: {
                resaltarNoAprobados: true,
                showEstado: true,
                titulo: "Productos solicitados",
            },
        });
        if (!puedeComentar) return detalle;

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

    async function openDetail(id) {
        try {
            const s = await api.get(`/solicitudes-gestion/${id}`);
            selectedSolicitudId = s.id;
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            detailContent.innerHTML = renderDetalleConComentario(s);
            initObservacionEditor();
            await hydrateInlineObservacionImages(detailContent, s.id);
            modal.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
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
            detailContent.innerHTML = renderDetalleConComentario(s);
            initObservacionEditor();
            await hydrateInlineObservacionImages(detailContent, s.id);
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

    load();

    try {
        attachGestionDownloadHandlers(detailContent, showError);
    } catch (err) {
        showError("No se pudieron habilitar las descargas de archivos.");
    }

    detailContent?.addEventListener("click", (e) => {
        if (e.target.closest(`#${COMENTARIO_BTN_ID}`)) {
            guardarComentarioCotizacion();
        }
    });

    function closeModal() {
        modal.classList.remove("show");
        destroyObservacionEditor();
        selectedSolicitudId = null;
    }

    document.getElementById("btn-gestion-detail-close")?.addEventListener("click", closeModal);
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
