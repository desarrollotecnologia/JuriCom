import { api, ApiError } from "../api/client.js";
import { session } from "../auth/session.js";
import { LIDERES_COLBEEF } from "../catalogos/lideres-colbeef.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    COTIZACION_ACCEPT,
    hydrateInlineObservacionImages,
    MIN_COTIZACIONES,
    normalizarEstado,
    renderDetalleSolicitudHtml,
    renderPanelGestionHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js";

const GESTION_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

function buildLideresOptions(selectedId = "") {
    return LIDERES_COLBEEF.map(
        (l) =>
            `<option value="${escapeHtml(l.id)}" data-label="${escapeHtml(l.label)}"${
                l.id === selectedId ? " selected" : ""
            }>${escapeHtml(l.label)}</option>`
    ).join("");
}

function puedeGestionar(solicitud, userId) {
    const estado = normalizarEstado(solicitud.estado);
    if (estado === "primera_aprobacion") return true;
    if (estado === "cotizacion") {
        return !solicitud.gestor_id || solicitud.gestor_id === userId;
    }
    return false;
}

function contarCotizaciones(solicitud, nuevosArchivos = []) {
    const existentes = (solicitud.archivos || []).filter((a) => a.categoria === "cotizacion").length;
    return existentes + nuevosArchivos.length;
}

export function initPanelSolicitudesGestion() {
    const tbody = document.getElementById("panel-tbody");
    const searchInput = document.getElementById("panel-search");
    const filterTipo = document.getElementById("panel-filter-tipo");
    const resultCount = document.getElementById("panel-result-count");
    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const modal = document.getElementById("modal-panel-detail");
    const detailContent = document.getElementById("panel-detail-content");
    const detailTitle = document.getElementById("panel-detail-title");
    const btnClose = document.getElementById("btn-panel-detail-close");
    const btnEnviar = document.getElementById("btn-panel-enviar-aprobacion");
    const modalActionsGestion = document.getElementById("panel-modal-actions-gestion");

    const currentUser = session.getUser();

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
        showError("No se pudo inicializar el panel de solicitudes.");
        return;
    }

    let items = [];
    let selectedSolicitud = null;
    let modoGestion = false;
    let observacionControl = null;

    function initObservacionesEditor() {
        observacionControl?.destroy();
        observacionControl = createObservacionConAdjuntos({
            editorContainerId: "gestion-nueva-observacion-editor",
            fileInputId: "gestion-comentario-adjuntos",
            fileListId: "gestion-comentario-file-list",
            name: "nueva_observacion",
            placeholder: "Comentarios del gestor sobre esta solicitud...",
            minHeight: 160,
        });
    }

    function destroyObservacionesEditor() {
        observacionControl?.destroy();
        observacionControl = null;
    }

    function buildQuery() {
        const params = new URLSearchParams();
        const q = searchInput?.value.trim() ?? "";
        const tipo = filterTipo?.value ?? "";
        if (q) params.set("q", q);
        if (tipo) params.set("tipo", tipo);
        const qs = params.toString();
        return `/solicitudes-gestion/panel-gestion${qs ? `?${qs}` : ""}`;
    }

    function renderTable() {
        if (!Array.isArray(items) || !items.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="muted text-center">
                No hay solicitudes aprobadas para gestionar.
                <br />Las solicitudes aparecen aquí después de ser aprobadas en
                <a href="/app/compras/gestion-aprobar-solicitudes.html">Aprobar solicitudes</a>.
            </td></tr>`;
            if (resultCount) resultCount.textContent = "0 solicitudes";
            return;
        }

        tbody.innerHTML = items
            .map((s) => {
                const gestionar = puedeGestionar(s, currentUser?.id);
                const btnClass = gestionar ? "btn btn-primary btn-icon-view" : "btn btn-secondary btn-icon-view";
                const btnLabel = gestionar ? "Gestionar" : "Ver";
                const btnIcon = gestionar ? GESTION_ICON : EYE_ICON;
                const action = gestionar ? "gestionar" : "ver";

                return `
            <tr>
                <td data-label="Consecutivo">
                    <span class="codigo-solicitud">${escapeHtml(s.codigo)}</span>
                </td>
                <td data-label="Solicitante">${escapeHtml(s.creado_por_username || "—")}</td>
                <td data-label="Tipo">${badgeTipo(s.tipo)}</td>
                <td data-label="Estado">${badgeEstado(s.estado)}</td>
                <td data-label="Fecha">${formatDate(s.created_at)}</td>
                <td data-label="Acciones" class="col-actions">
                    <button
                        type="button"
                        class="${btnClass} btn-panel-action"
                        data-id="${s.id}"
                        data-action="${action}"
                        title="${btnLabel} solicitud"
                    >
                        ${btnIcon}
                        <span>${btnLabel}</span>
                    </button>
                </td>
            </tr>`;
            })
            .join("");

        if (resultCount) {
            resultCount.textContent = `${items.length} solicitud${items.length === 1 ? "" : "es"}`;
        }

        tbody.querySelectorAll(".btn-panel-action").forEach((btn) => {
            btn.addEventListener("click", () => {
                const id = Number(btn.dataset.id);
                if (btn.dataset.action === "gestionar") {
                    iniciarGestion(id);
                } else {
                    abrirDetalle(id);
                }
            });
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
                    : "No se pudieron cargar las solicitudes del panel.";
            tbody.innerHTML = `<tr><td colspan="6" class="muted text-center">${escapeHtml(msg)}</td></tr>`;
            if (resultCount) resultCount.textContent = "";
            showError(msg);
        }
    }

    function closeModal() {
        modal?.classList.remove("show");
        destroyObservacionesEditor();
        selectedSolicitud = null;
        modoGestion = false;
        modalActionsGestion?.setAttribute("hidden", "");
        btnClose?.removeAttribute("hidden");
    }

    function bindGestionFormEvents() {
        const uploadRoot = document.getElementById("gestion-cotizaciones-upload");
        const extrasContainer = document.getElementById("gestion-cotizaciones-extras");
        const btnAgregarMas = document.getElementById("btn-gestion-cotizacion-mas");

        uploadRoot?.querySelectorAll(".gestion-cotizacion-input").forEach((input) => {
            input.addEventListener("change", () => updateCotizacionSlotUI(input));
        });

        uploadRoot?.addEventListener("click", (e) => {
            const btnClear = e.target.closest(".btn-cotizacion-clear");
            if (btnClear) {
                const slot = btnClear.closest(".sg-cotizacion-slot");
                const input = slot?.querySelector(".gestion-cotizacion-input");
                if (input) input.value = "";
                updateCotizacionSlotUI(input);
                return;
            }

            const btnRemove = e.target.closest(".btn-cotizacion-quitar-slot");
            if (btnRemove) {
                btnRemove.closest(".sg-cotizacion-slot")?.remove();
                renumberCotizacionSlots();
                refreshCotizacionesUI();
            }
        });

        btnAgregarMas?.addEventListener("click", () => {
            if (!extrasContainer) return;
            const index =
                document.querySelectorAll("#gestion-cotizaciones-upload .sg-cotizacion-slot")
                    .length;
            const wrapper = document.createElement("div");
            wrapper.innerHTML = renderCotizacionSlotMarkup(index);
            const slot = wrapper.firstElementChild;
            if (!slot) return;
            extrasContainer.appendChild(slot);
            slot.querySelector(".gestion-cotizacion-input")?.addEventListener("change", (e) => {
                updateCotizacionSlotUI(e.target);
            });
            refreshCotizacionesUI();
        });

        refreshCotizacionesUI();
    }

    function updateCotizacionSlotUI(input) {
        const slot = input?.closest(".sg-cotizacion-slot");
        if (!slot) return;
        const file = input.files?.[0];
        const nameEl = slot.querySelector(".sg-cotizacion-slot-name");
        const btnClear = slot.querySelector(".btn-cotizacion-clear");
        if (nameEl) nameEl.textContent = file ? file.name : "Sin archivo";
        if (btnClear) btnClear.hidden = !file;
        refreshCotizacionesUI();
    }

    function renderCotizacionSlotMarkup(index) {
        const removable = index >= MIN_COTIZACIONES;
        return `
            <div class="sg-cotizacion-slot" data-slot="${index}">
                <span class="sg-cotizacion-slot-label">Cotización ${index + 1}</span>
                <div class="sg-cotizacion-slot-row">
                    <input
                        type="file"
                        class="gestion-cotizacion-input"
                        id="gestion-cotizacion-${index}"
                        accept="${COTIZACION_ACCEPT}"
                    />
                    <span class="sg-cotizacion-slot-name muted">Sin archivo</span>
                    <button type="button" class="btn btn-sm btn-secondary btn-cotizacion-clear" hidden>
                        Quitar archivo
                    </button>
                    ${
                        removable
                            ? `<button type="button" class="btn btn-sm btn-secondary btn-cotizacion-quitar-slot">
                        Quitar
                    </button>`
                            : ""
                    }
                </div>
            </div>`;
    }

    function renumberCotizacionSlots() {
        const extras = document.querySelectorAll("#gestion-cotizaciones-extras .sg-cotizacion-slot");
        extras.forEach((slot, i) => {
            const index = MIN_COTIZACIONES + i;
            slot.dataset.slot = String(index);
            const label = slot.querySelector(".sg-cotizacion-slot-label");
            if (label) label.textContent = `Cotización ${index + 1}`;

            const input = slot.querySelector(".gestion-cotizacion-input");
            if (input) input.id = `gestion-cotizacion-${index}`;

            if (!slot.querySelector(".btn-cotizacion-quitar-slot")) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.className = "btn btn-sm btn-secondary btn-cotizacion-quitar-slot";
                btn.textContent = "Quitar";
                slot.querySelector(".sg-cotizacion-slot-row")?.appendChild(btn);
            }
        });
    }

    function getSelectedCotizacionFiles() {
        const files = [];
        detailContent?.querySelectorAll(".gestion-cotizacion-input").forEach((input) => {
            if (input.files?.[0]) files.push(input.files[0]);
        });
        return files;
    }

    function refreshCotizacionesUI() {
        if (!selectedSolicitud) return;
        const countLabel = document.getElementById("gestion-cotizaciones-count");
        const justificacionWrap = document.getElementById("gestion-justificacion-wrap");
        const nuevos = getSelectedCotizacionFiles();
        const total = contarCotizaciones(selectedSolicitud, nuevos);

        if (countLabel) {
            countLabel.textContent = `Cotizaciones registradas: ${total} (mínimo: ${MIN_COTIZACIONES}) · Nuevas seleccionadas: ${nuevos.length}`;
        }
        if (justificacionWrap) {
            justificacionWrap.hidden = total >= MIN_COTIZACIONES;
        }
    }

    async function abrirDetalle(id, solicitudPrecargada = null) {
        try {
            const s = solicitudPrecargada || (await api.get(`/solicitudes-gestion/${id}`));
            selectedSolicitud = s;
            modoGestion = false;
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            detailContent.innerHTML = renderDetalleSolicitudHtml(s, {
                productosOptions: {
                    excluirNoAprobados: true,
                    titulo: "Productos aprobados",
                },
            });
            modalActionsGestion?.setAttribute("hidden", "");
            btnClose?.removeAttribute("hidden");
            await hydrateInlineObservacionImages(detailContent, s.id);
            modal.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
    }

    async function abrirGestion(solicitud) {
        selectedSolicitud = solicitud;
        modoGestion = true;
        detailTitle.textContent = `Gestionar · ${solicitud.codigo}`;
        detailContent.innerHTML = renderPanelGestionHtml(
            solicitud,
            buildLideresOptions(solicitud.lider_segunda_aprobacion_id || "")
        );
        modalActionsGestion?.removeAttribute("hidden");
        btnClose?.removeAttribute("hidden");
        bindGestionFormEvents();
        initObservacionesEditor();
        await hydrateInlineObservacionImages(detailContent, solicitud.id);
        modal.classList.add("show");
    }

    async function iniciarGestion(id) {
        try {
            const solicitud = await api.post(`/solicitudes-gestion/${id}/gestionar`, {});
            showSuccess(`Solicitud ${solicitud.codigo} en estado Cotización.`);
            await load();
            await abrirGestion(solicitud);
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo iniciar la gestión."
            );
        }
    }

    async function enviarParaAprobacion() {
        if (!selectedSolicitud || !modoGestion) return;

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";
        const justificacion = document.getElementById("gestion-justificacion")?.value.trim() ?? "";
        const liderSelect = document.getElementById("gestion-lider-aprobacion");
        const liderId = liderSelect?.value ?? "";
        const liderLabel = liderSelect?.selectedOptions?.[0]?.dataset.label ?? "";

        if (!liderId) {
            showError("Selecciona un líder Colbeef para la segunda aprobación.");
            return;
        }

        const nuevos = getSelectedCotizacionFiles();
        const total = contarCotizaciones(selectedSolicitud, nuevos);
        if (total < MIN_COTIZACIONES && !justificacion) {
            showError(
                `Debes adjuntar al menos ${MIN_COTIZACIONES} cotizaciones o indicar una justificación.`
            );
            return;
        }

        if (
            !confirm(
                "¿Confirmas el envío de la solicitud a segunda aprobación (En Aprobación)?"
            )
        ) {
            return;
        }

        const formData = new FormData();
        formData.append("nueva_observacion", nuevaObsHtml);
        formData.append("nueva_observacion_texto", nuevaObsTexto);
        formData.append("justificacion", justificacion);
        formData.append("lider_segunda_aprobacion_id", liderId);
        formData.append("lider_segunda_aprobacion_label", liderLabel);
        nuevos.forEach((file) => formData.append("cotizaciones", file));
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnEnviar.disabled = true;
        btnEnviar.textContent = "Enviando...";

        try {
            const solicitud = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/enviar-cotizacion`,
                formData
            );
            showSuccess(
                `Solicitud ${solicitud.codigo} enviada a En Aprobación correctamente.`
            );
            closeModal();
            await load();
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo enviar la cotización."
            );
        } finally {
            btnEnviar.disabled = false;
            btnEnviar.textContent = "Enviar para aprobación";
        }
    }

    load();

    try {
        attachGestionDownloadHandlers(detailContent, showError);
    } catch {
        showError("No se pudieron habilitar las descargas de archivos.");
    }

    btnClose?.addEventListener("click", closeModal);
    btnEnviar?.addEventListener("click", enviarParaAprobacion);
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
