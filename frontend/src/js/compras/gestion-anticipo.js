import { api, ApiError } from "../api/client.js";
import { session } from "../auth/session.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    hydrateInlineObservacionImages,
    renderDetalleSolicitudHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js?v=18";

const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

const OBS_EDITOR_ID = "anticipo-observacion-editor";
const OBS_FILE_INPUT_ID = "anticipo-observacion-adjuntos";
const OBS_FILE_LIST_ID = "anticipo-observacion-file-list";

export function initGestionAnticipo() {
    const tbody = document.getElementById("anticipo-tbody");
    const searchInput = document.getElementById("anticipo-search");
    const resultCount = document.getElementById("anticipo-result-count");
    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const modal = document.getElementById("modal-anticipo-detail");
    const detailContent = document.getElementById("anticipo-detail-content");
    const detailTitle = document.getElementById("anticipo-detail-title");
    const btnClose = document.getElementById("btn-anticipo-detail-close");
    const btnGestionar = document.getElementById("btn-anticipo-gestionar");
    const gestionPanel = document.getElementById("anticipo-gestion-panel");

    const currentUser = session.getUser();
    const isAdmin = currentUser?.role === "admin";

    let items = [];
    let selectedSolicitud = null;
    let observacionControl = null;

    function showError(msg) {
        if (!alertError) return;
        alertError.textContent = msg;
        alertError.classList.add("show");
        alertSuccess?.classList.remove("show");
    }

    function showSuccess(msg) {
        if (!alertSuccess) return;
        alertSuccess.textContent = msg;
        alertSuccess.classList.add("show");
        alertError?.classList.remove("show");
    }

    if (!tbody) {
        showError("No se pudo inicializar el módulo de anticipos.");
        return;
    }

    function initObservacionEditor() {
        observacionControl?.destroy();
        observacionControl = createObservacionConAdjuntos({
            editorContainerId: OBS_EDITOR_ID,
            fileInputId: OBS_FILE_INPUT_ID,
            fileListId: OBS_FILE_LIST_ID,
            name: "anticipo_observacion",
            placeholder: "Comentarios sobre la gestión del anticipo...",
            minHeight: 160,
        });
    }

    function destroyObservacionEditor() {
        observacionControl?.destroy();
        observacionControl = null;
    }

    function buildQuery() {
        const params = new URLSearchParams();
        const q = searchInput?.value.trim() ?? "";
        if (q) params.set("q", q);
        const qs = params.toString();
        return `/solicitudes-gestion/gestion-anticipo${qs ? `?${qs}` : ""}`;
    }

    function puedeGestionar(s) {
        return isAdmin || !s.gestor_anticipo_id || s.gestor_anticipo_id === currentUser?.id;
    }

    function renderTable() {
        if (!items.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="muted text-center">
                No hay anticipos pendientes de gestión.
                <br />Aparecen aquí después de que el líder aprueba el anticipo en
                <a href="/app/compras/gestion-aprobar-solicitudes.html">Aprobar solicitudes</a>.
            </td></tr>`;
            if (resultCount) resultCount.textContent = "0 anticipos";
            return;
        }

        tbody.innerHTML = items
            .map((s) => {
                const gestionar = puedeGestionar(s);
                return `
            <tr>
                <td data-label="Consecutivo"><span class="codigo-solicitud">${escapeHtml(s.codigo)}</span></td>
                <td data-label="Solicitante">${escapeHtml(s.creado_por_username || "—")}</td>
                <td data-label="Tipo">${badgeTipo(s.tipo)}</td>
                <td data-label="Anticipo">${escapeHtml(
                    s.porcentaje_anticipo != null ? `${s.porcentaje_anticipo}%` : "—"
                )}</td>
                <td data-label="Estado">${badgeEstado(s.estado, s)}</td>
                <td data-label="Fecha">${formatDate(s.created_at)}</td>
                <td data-label="Acciones" class="col-actions">
                    <button type="button" class="btn ${gestionar ? "btn-primary" : "btn-secondary"} btn-icon-view btn-anticipo-action" data-id="${s.id}" data-gestionar="${gestionar ? "1" : "0"}">
                        ${EYE_ICON}
                        <span>${gestionar ? "Gestionar" : "Ver"}</span>
                    </button>
                </td>
            </tr>`;
            })
            .join("");

        if (resultCount) {
            resultCount.textContent = `${items.length} anticipo${items.length === 1 ? "" : "s"}`;
        }

        tbody.querySelectorAll(".btn-anticipo-action").forEach((btn) => {
            btn.addEventListener("click", () =>
                abrirDetalle(Number(btn.dataset.id), btn.dataset.gestionar === "1")
            );
        });
    }

    async function load() {
        tbody.innerHTML =
            '<tr><td colspan="7" class="muted text-center">Cargando...</td></tr>';
        try {
            const data = await api.get(buildQuery());
            items = Array.isArray(data) ? data : [];
            alertError?.classList.remove("show");
            renderTable();
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : "No se pudieron cargar los anticipos.";
            tbody.innerHTML = `<tr><td colspan="7" class="muted text-center">${escapeHtml(msg)}</td></tr>`;
            showError(msg);
        }
    }

    function closeModal() {
        modal?.classList.remove("show");
        destroyObservacionEditor();
        selectedSolicitud = null;
        gestionPanel?.setAttribute("hidden", "");
        btnGestionar?.setAttribute("hidden", "");
    }

    async function abrirDetalle(id, modoGestion) {
        destroyObservacionEditor();
        try {
            const s = await api.get(`/solicitudes-gestion/${id}`);
            selectedSolicitud = s;
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            detailContent.innerHTML = renderDetalleSolicitudHtml(s, {
                productosOptions: {
                    excluirNoAprobados: true,
                    titulo: "Productos aprobados",
                },
            });

            if (modoGestion) {
                gestionPanel?.removeAttribute("hidden");
                btnGestionar?.removeAttribute("hidden");
                initObservacionEditor();
            } else {
                gestionPanel?.setAttribute("hidden", "");
                btnGestionar?.setAttribute("hidden", "");
            }

            await hydrateInlineObservacionImages(detailContent, s.id);
            modal?.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
    }

    async function cerrarGestion() {
        if (!selectedSolicitud) return;

        if (
            !confirm(
                "¿Marcar el anticipo como gestionado y continuar el flujo de la solicitud?"
            )
        ) {
            return;
        }

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";

        const formData = new FormData();
        formData.append("nueva_observacion", nuevaObsHtml);
        formData.append("nueva_observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnGestionar.disabled = true;
        btnGestionar.textContent = "Guardando...";

        try {
            await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/gestionar-anticipo`,
                formData
            );
            showSuccess(`Anticipo gestionado — ${selectedSolicitud.codigo}.`);
            closeModal();
            await load();
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo gestionar el anticipo."
            );
        } finally {
            btnGestionar.disabled = false;
            btnGestionar.textContent = "Anticipo gestionado";
        }
    }

    searchInput?.addEventListener("input", () => load());
    btnClose?.addEventListener("click", closeModal);
    btnGestionar?.addEventListener("click", cerrarGestion);
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    attachGestionDownloadHandlers(document, showError);
    load();
}
