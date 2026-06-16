import { api, ApiError } from "../api/client.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    hydrateInlineObservacionImages,
    renderDetalleSolicitudHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js";

const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

export function initMisSolicitudesGestion({ esAdmin }) {
    const tbody = document.getElementById("gestion-tbody");
    const searchInput = document.getElementById("gestion-search");
    const filterTipo = document.getElementById("gestion-filter-tipo");
    const resultCount = document.getElementById("gestion-result-count");
    const alertError = document.getElementById("alert-error");
    const modal = document.getElementById("modal-gestion-detail");
    const detailContent = document.getElementById("gestion-detail-content");
    const detailTitle = document.getElementById("gestion-detail-title");

    function showError(msg) {
        if (!alertError) return;
        alertError.textContent = msg;
        alertError.classList.add("show");
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
                <td data-label="Estado">${badgeEstado(s.estado)}</td>
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

    async function openDetail(id) {
        try {
            const s = await api.get(`/solicitudes-gestion/${id}`);
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            detailContent.innerHTML = renderDetalleSolicitudHtml(s, {
                productosOptions: {
                    resaltarNoAprobados: true,
                    showEstado: true,
                },
            });
            await hydrateInlineObservacionImages(detailContent, s.id);
            modal.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
    }

    load();

    try {
        attachGestionDownloadHandlers(detailContent, showError);
    } catch (err) {
        showError("No se pudieron habilitar las descargas de archivos.");
    }

    document.getElementById("btn-gestion-detail-close")?.addEventListener("click", () => {
        modal.classList.remove("show");
    });
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) modal.classList.remove("show");
    });

    let debounce;
    searchInput?.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(load, 300);
    });
    filterTipo?.addEventListener("change", load);
}
