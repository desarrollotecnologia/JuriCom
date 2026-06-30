import { api, ApiError } from "../api/client.js";
import { session } from "../auth/session.js";
import { LIDERES_COLBEEF } from "../catalogos/lideres-colbeef.js";
import { createObservacionConAdjuntos, renderObservacionAdjuntosFieldHtml } from "../components/observacion-editor.js";
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
    renderPanelTramiteOcHtml,
    renderFacturasHistorialHtml,
    esGestionEntrega,
    esSolicitudSalidasAlmacen,
    esEstadoRecepcion,
    esEstadoEntregaSolicitante,
    solicitudEntregaCompleta,
    solicitudTieneEntregaPendiente,
    solicitudTieneRecepcionPendiente,
    solicitudTieneDisponibleEntrega,
    solicitudPuedeEntregaTotal,
    solicitudPuedeCerrarConPendientes,
    solicitudTieneOcRegistrada,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js?v=22";

const GESTION_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`;
const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
const FACTURA_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`;

function buildLideresOptions(selectedId = "") {
    return LIDERES_COLBEEF.map(
        (l) =>
            `<option value="${escapeHtml(l.id)}" data-label="${escapeHtml(l.label)}"${
                l.id === selectedId ? " selected" : ""
            }>${escapeHtml(l.label)}</option>`
    ).join("");
}

function esGestorAsignado(solicitud, userId, isAdmin = false) {
    if (isAdmin) return true;
    if (!solicitud.gestor_id && !solicitud.gestor_anticipo_id) return true;
    return solicitud.gestor_id === userId || solicitud.gestor_anticipo_id === userId;
}

function puedeGestionar(solicitud, userId, isAdmin = false) {
    const estado = normalizarEstado(solicitud.estado);
    if (estado === "primera_aprobacion") return true;
    if (estado === "tramitando_oc") {
        return esGestorAsignado(solicitud, userId, isAdmin);
    }
    if (estado === "cotizacion" || estado === "items_en_camino" || estado === "recepcion_insumos" || estado === "tramitada_oc" || estado === "entregado_parcial") {
        return esGestorAsignado(solicitud, userId, isAdmin);
    }
    return false;
}

function contarCotizaciones(solicitud, nuevosArchivos = []) {
    const existentes = (solicitud.archivos || []).filter((a) => a.categoria === "cotizacion").length;
    return existentes + nuevosArchivos.length;
}

function esSolicitudFacturaCerrada(solicitud) {
    return (
        normalizarEstado(solicitud?.estado) === "facturada" ||
        Boolean(solicitud?.factura_registrada || solicitud?.factura_registrada_at)
    );
}

function puedeGestionarFactura(solicitud) {
    const estado = normalizarEstado(solicitud?.estado);
    return estado === "entregado" || estado === "facturada";
}

function tieneFacturasRegistradas(solicitud) {
    return (
        Number(solicitud?.cantidad_facturas || 0) > 0 || esSolicitudFacturaCerrada(solicitud)
    );
}

function esSalidasAlmacenEntregada(solicitud) {
    return (
        esSolicitudSalidasAlmacen(solicitud) &&
        normalizarEstado(solicitud?.estado) === "entregado"
    );
}

function esPanelFilaCerrada(solicitud) {
    return esSolicitudFacturaCerrada(solicitud) || esSalidasAlmacenEntregada(solicitud);
}

function sortPanelItems(list) {
    return [...list].sort((a, b) => {
        const aCerrada = esPanelFilaCerrada(a);
        const bCerrada = esPanelFilaCerrada(b);
        if (aCerrada !== bCerrada) return aCerrada ? 1 : -1;
        if (aCerrada && bCerrada) {
            const aDate = a.factura_registrada_at || a.updated_at || a.created_at || 0;
            const bDate = b.factura_registrada_at || b.updated_at || b.created_at || 0;
            return new Date(aDate) - new Date(bDate);
        }
        return (b.id || 0) - (a.id || 0);
    });
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
    const btnGuardarTramite = document.getElementById("btn-panel-guardar-tramite-oc");
    const btnEntregado = document.getElementById("btn-panel-entregado");
    const btnEntregadoParcial = document.getElementById("btn-panel-entregado-parcial");
    const btnCerrarPendientes = document.getElementById("btn-panel-cerrar-pendientes");
    const btnConfirmarEntregaParcial = document.getElementById("btn-panel-confirmar-entrega-parcial");
    const btnRegistrarRecepcion = document.getElementById("btn-panel-registrar-recepcion");
    const btnConfirmarRecepcion = document.getElementById("btn-panel-confirmar-recepcion");
    const modalActionsGestion = document.getElementById("panel-modal-actions-gestion");
    const modalFactura = document.getElementById("modal-panel-factura");
    const facturaTitle = document.getElementById("panel-factura-title");
    const facturaIntro = document.getElementById("panel-factura-intro");
    const facturaContent = document.getElementById("panel-factura-content");
    const btnFacturaCancel = document.getElementById("btn-panel-factura-cancel");
    const btnFacturaGuardar = document.getElementById("btn-panel-factura-guardar");
    const facturaAlert = document.getElementById("panel-factura-alert");
    const modalFacturaDetalle = document.getElementById("modal-panel-factura-detalle");
    const facturaDetalleContent = document.getElementById("panel-factura-detalle-content");
    const facturaDetalleCodigo = document.getElementById("panel-factura-detalle-codigo");
    const btnFacturaDetalleCerrar = document.getElementById("btn-panel-factura-detalle-cerrar");
    const btnFacturaDetalleAgregar = document.getElementById("btn-panel-factura-detalle-agregar");

    const currentUser = session.getUser();
    const isAdmin = currentUser?.role === "admin";

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
    let facturaObservacionControl = null;
    let selectedFacturaSolicitudId = null;
    let selectedFacturaDetalleId = null;
    let facturaEsAdicional = false;

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

    function destroyFacturaEditor() {
        facturaObservacionControl?.destroy();
        facturaObservacionControl = null;
    }

    function initFacturaEditor() {
        destroyFacturaEditor();
        facturaObservacionControl = createObservacionConAdjuntos({
            editorContainerId: "panel-factura-editor",
            fileInputId: "panel-factura-adjuntos",
            fileListId: "panel-factura-file-list",
            name: "factura_observacion",
            placeholder: "Comentario interno sobre la factura (opcional)...",
            minHeight: 140,
        });
    }

    function clearFacturaAlert() {
        if (!facturaAlert) return;
        facturaAlert.textContent = "";
        facturaAlert.classList.remove("show", "alert-error", "alert-success");
    }

    function showFacturaAlert(msg, type = "error") {
        if (!facturaAlert) {
            showError(msg);
            return;
        }
        facturaAlert.textContent = msg;
        facturaAlert.classList.remove("alert-error", "alert-success");
        facturaAlert.classList.add(type === "success" ? "alert-success" : "alert-error", "show");
    }

    function closeFacturaModal() {
        modalFactura?.classList.remove("show");
        destroyFacturaEditor();
        selectedFacturaSolicitudId = null;
        facturaEsAdicional = false;
        clearFacturaAlert();
        if (facturaContent) facturaContent.innerHTML = "";
        if (btnFacturaGuardar) btnFacturaGuardar.textContent = "Guardar factura";
        if (facturaTitle) facturaTitle.textContent = "Registrar factura";
    }

    function closeFacturaDetalleModal() {
        modalFacturaDetalle?.classList.remove("show");
        selectedFacturaDetalleId = null;
        if (facturaDetalleContent) facturaDetalleContent.innerHTML = "";
    }

    async function openFacturaDetalleModal(solicitudId) {
        const s = items.find((item) => item.id === solicitudId);
        if (!s || !puedeGestionarFactura(s)) return;

        selectedFacturaDetalleId = solicitudId;
        if (facturaDetalleCodigo) facturaDetalleCodigo.textContent = s.codigo || `#${s.id}`;
        if (facturaDetalleContent) {
            facturaDetalleContent.innerHTML =
                '<p class="muted text-center">Cargando historial de facturas...</p>';
        }
        modalFacturaDetalle?.classList.add("show");

        try {
            const full = await api.get(`/solicitudes-gestion/${solicitudId}`);
            if (facturaDetalleContent) {
                facturaDetalleContent.innerHTML = renderFacturasHistorialHtml(full);
                attachGestionDownloadHandlers(facturaDetalleContent, showError);
                hydrateInlineObservacionImages(facturaDetalleContent);
            }
            if (btnFacturaDetalleAgregar) {
                const cantidad = Number(full.cantidad_facturas || 0);
                btnFacturaDetalleAgregar.hidden = !puedeGestionarFactura(full);
                btnFacturaDetalleAgregar.textContent =
                    cantidad > 0 ? "Agregar factura" : "Registrar factura";
            }
        } catch (err) {
            const msg =
                err instanceof ApiError
                    ? err.message
                    : "No se pudo cargar el historial de facturas.";
            if (facturaDetalleContent) {
                facturaDetalleContent.innerHTML = `<p class="muted text-center">${escapeHtml(msg)}</p>`;
            }
            showError(msg);
        }
    }

    function openFacturaModal(solicitudId, esAdicional = false) {
        const s = items.find((item) => item.id === solicitudId);
        if (!s || !puedeGestionarFactura(s)) return;

        facturaEsAdicional = esAdicional || tieneFacturasRegistradas(s);
        clearFacturaAlert();
        selectedFacturaSolicitudId = solicitudId;
        const codigo = s.codigo || `#${s.id}`;
        if (facturaTitle) {
            facturaTitle.textContent = facturaEsAdicional ? "Agregar factura" : "Registrar factura";
        }
        if (facturaIntro) {
            facturaIntro.innerHTML = facturaEsAdicional
                ? `Nueva factura para la solicitud <strong>${escapeHtml(codigo)}</strong>. Se añadirá al historial existente.`
                : `Cierre administrativo interno. La solicitud <strong>${escapeHtml(codigo)}</strong> pasará al final de la lista con fondo verde.`;
        }
        if (btnFacturaGuardar) {
            btnFacturaGuardar.textContent = facturaEsAdicional ? "Agregar factura" : "Guardar factura";
        }
        if (facturaContent) {
            facturaContent.innerHTML = renderObservacionAdjuntosFieldHtml({
                editorContainerId: "panel-factura-editor",
                fileInputId: "panel-factura-adjuntos",
                fileListId: "panel-factura-file-list",
                label: "Comentario de factura",
                hint: "Adjunta uno o más archivos de la factura (PDF, imagen, Excel). El comentario es opcional.",
            });
        }
        initFacturaEditor();
        modalFactura?.classList.add("show");
    }

    async function guardarFactura() {
        if (!selectedFacturaSolicitudId || !facturaObservacionControl) return;

        const archivos = facturaObservacionControl.getFiles() ?? [];
        if (!archivos.length) {
            showFacturaAlert("Debes adjuntar al menos un archivo de la factura.");
            return;
        }

        facturaObservacionControl.editor?.syncHidden();
        const observacionHtml = facturaObservacionControl.editor?.getHtml() ?? "";
        const observacionTexto = facturaObservacionControl.editor?.getText() ?? "";

        const formData = new FormData();
        formData.append("observacion", observacionHtml);
        formData.append("observacion_texto", observacionTexto);
        archivos.forEach((file) => formData.append("adjuntos", file));

        if (btnFacturaGuardar) {
            btnFacturaGuardar.disabled = true;
            btnFacturaGuardar.textContent = "Guardando...";
        }

        try {
            const idGuardada = selectedFacturaSolicitudId;
            await api.postForm(
                `/solicitudes-gestion/${selectedFacturaSolicitudId}/registrar-factura`,
                formData
            );
            const msg = facturaEsAdicional
                ? "Factura agregada al historial."
                : "Factura registrada. La solicitud quedó cerrada administrativamente.";
            closeFacturaModal();
            await load();
            showSuccess(msg);
            if (idGuardada) {
                await openFacturaDetalleModal(idGuardada);
            }
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : "No se pudo registrar la factura.";
            showFacturaAlert(msg);
            showError(msg);
        } finally {
            if (btnFacturaGuardar) {
                btnFacturaGuardar.disabled = false;
                btnFacturaGuardar.textContent = "Guardar factura";
            }
        }
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
                const salidasEntregada = esSalidasAlmacenEntregada(s);
                const cerrada = esSolicitudFacturaCerrada(s);
                const rowClasses = [];
                if (cerrada) rowClasses.push("sg-row-factura-cerrada");
                if (salidasEntregada) rowClasses.push("sg-row-salidas-entregada");
                const rowClass = rowClasses.join(" ");
                const esSalidas = esSolicitudSalidasAlmacen(s);
                const tieneFacturas =
                    !esSalidas &&
                    (Number(s.cantidad_facturas || 0) > 0 || esSolicitudFacturaCerrada(s));
                const estado = normalizarEstado(s.estado);
                const mostrarFactura = !esSalidas && estado === "entregado" && !tieneFacturas;
                const mostrarVerFactura = !esSalidas && tieneFacturas;
                const enFlujoFactura = mostrarFactura || mostrarVerFactura;
                const gestionar =
                    !enFlujoFactura && puedeGestionar(s, currentUser?.id, isAdmin);
                const btnClass = gestionar
                    ? "btn btn-primary btn-icon-view"
                    : "btn btn-secondary btn-icon-view";
                const btnLabel = gestionar ? "Gestionar" : "Ver";
                const btnIcon = gestionar ? GESTION_ICON : EYE_ICON;
                const action = gestionar ? "gestionar" : "ver";
                const accionesClass = enFlujoFactura ? "col-actions col-actions-wide" : "col-actions";

                return `
            <tr class="${rowClass}">
                <td data-label="Consecutivo">
                    <span class="codigo-solicitud">${escapeHtml(s.codigo)}</span>
                </td>
                <td data-label="Solicitante">${escapeHtml(s.creado_por_username || "—")}</td>
                <td data-label="Tipo">${badgeTipo(s.tipo)}</td>
                <td data-label="Estado">${badgeEstado(s.estado, s)}</td>
                <td data-label="Fecha">${formatDate(s.created_at)}</td>
                <td data-label="Acciones" class="${accionesClass}">
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
                    ${
                        mostrarFactura
                            ? `<button
                        type="button"
                        class="btn btn-secondary btn-sm btn-icon-view btn-panel-factura-accion"
                        data-id="${s.id}"
                        title="Registrar factura"
                    >
                        ${FACTURA_ICON}
                        <span>Factura</span>
                    </button>`
                            : ""
                    }
                    ${
                        mostrarVerFactura
                            ? `<button
                        type="button"
                        class="btn btn-secondary btn-sm btn-icon-view btn-panel-factura-accion"
                        data-id="${s.id}"
                        title="Ver historial de facturas"
                    >
                        ${EYE_ICON}
                        <span>Ver Factura</span>
                    </button>`
                            : ""
                    }
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

        tbody.querySelectorAll(".btn-panel-factura-accion").forEach((btn) => {
            btn.addEventListener("click", () => openFacturaDetalleModal(Number(btn.dataset.id)));
        });
    }

    async function load() {
        tbody.innerHTML =
            '<tr><td colspan="6" class="muted text-center">Cargando...</td></tr>';
        try {
            const data = await api.get(buildQuery());
            items = sortPanelItems(Array.isArray(data) ? data : []);
            renderTable();
            alertError?.classList.remove("show");
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
        setModalBtnHidden(btnEnviar, false);
        setModalBtnHidden(btnGuardarTramite, true);
        setModalBtnHidden(btnEntregado, true);
        setModalBtnHidden(btnEntregadoParcial, true);
        setModalBtnHidden(btnCerrarPendientes, true);
        setModalBtnHidden(btnConfirmarEntregaParcial, true);
        setModalBtnHidden(btnRegistrarRecepcion, true);
        setModalBtnHidden(btnConfirmarRecepcion, true);
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
            const estado = normalizarEstado(s.estado);
            const esLogistica = esGestionEntrega(estado) && estado !== "tramitada_oc";
            const puedeActuar = puedeGestionar(s, currentUser?.id, isAdmin);

            if (esLogistica && puedeActuar) {
                await abrirGestion(s);
                return;
            }

            modoGestion = false;
            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo}`;
            detailContent.innerHTML = renderDetalleSolicitudHtml(s, {
                productosOptions: {
                    excluirNoAprobados: true,
                    titulo: "Productos aprobados",
                },
            });
            modalActionsGestion?.setAttribute("hidden", "");
            setModalBtnHidden(btnRegistrarRecepcion, true);
            setModalBtnHidden(btnConfirmarRecepcion, true);
            btnClose?.removeAttribute("hidden");
            await hydrateInlineObservacionImages(detailContent, s.id);
            modal.classList.add("show");
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."
            );
        }
    }

    function formTieneTramiteOc() {
        const general =
            document.getElementById("gestion-tramite-oc-general")?.value.trim() ?? "";
        if (general) return true;
        return Array.from(
            detailContent?.querySelectorAll(".sg-tramite-oc-parcial-input") ?? []
        ).some((input) => input.value.trim());
    }

    function setModalBtnHidden(btn, hidden) {
        if (!btn) return;
        btn.hidden = hidden;
        if (hidden) {
            btn.setAttribute("hidden", "");
        } else {
            btn.removeAttribute("hidden");
        }
    }

    function bindTramiteOcFormEvents() {
        const generalInput = document.getElementById("gestion-tramite-oc-general");
        generalInput?.addEventListener("input", updateAccionesEntrega);
        detailContent?.querySelectorAll(".sg-tramite-oc-parcial-input").forEach((input) => {
            input.addEventListener("input", updateAccionesEntrega);
        });
        bindAnticipoFormEvents();
    }

    function bindAnticipoFormEvents() {
        const check = document.getElementById("gestion-requiere-anticipo");
        const panel = document.getElementById("gestion-anticipo-campos");
        if (!check || !panel) return;
        const sync = () => {
            panel.hidden = !check.checked;
        };
        check.addEventListener("change", sync);
        sync();
    }

    function getAnticipoFormData() {
        const requiere = document.getElementById("gestion-requiere-anticipo")?.checked ?? false;
        const pct = document.getElementById("gestion-porcentaje-anticipo")?.value.trim() ?? "";
        const liderSelect = document.getElementById("gestion-lider-anticipo");
        const liderId = liderSelect?.value ?? "";
        const liderLabel =
            liderSelect?.selectedOptions?.[0]?.dataset?.label ??
            liderSelect?.selectedOptions?.[0]?.textContent?.trim() ??
            "";
        const obs = document.getElementById("gestion-observaciones-anticipo")?.value.trim() ?? "";
        return { requiere, pct, liderId, liderLabel, obs };
    }

    function validarAnticipoForm() {
        const { requiere, pct, liderId } = getAnticipoFormData();
        if (!requiere) return true;
        const pctNum = Number(pct);
        if (!pct || Number.isNaN(pctNum) || pctNum <= 0 || pctNum > 100) {
            showError("Indica un porcentaje de anticipo válido (0.01 – 100).");
            return false;
        }
        if (!liderId) {
            showError("Selecciona el líder aprobador del anticipo.");
            return false;
        }
        return true;
    }

    function bindEntregaParcialFormEvents() {
        detailContent?.querySelectorAll(".entrega-parcial-check").forEach((check) => {
            check.addEventListener("change", () => {
                const row = check.closest("tr");
                const input = row?.querySelector(".sg-entrega-parcial-cantidad");
                if (!input) return;
                if (check.checked && !input.value) {
                    input.value = check.dataset.pendiente || "1";
                }
                if (!check.checked) {
                    input.value = "";
                }
            });
        });

        detailContent?.querySelectorAll(".sg-entrega-parcial-cantidad").forEach((input) => {
            input.addEventListener("input", () => {
                const row = input.closest("tr");
                const check = row?.querySelector(".entrega-parcial-check");
                const cantidad = Number(input.value);
                if (!check) return;
                if (cantidad > 0) {
                    check.checked = true;
                } else if (!input.value) {
                    check.checked = false;
                }
            });
        });
    }

    function updateAccionesEntrega() {
        if (!selectedSolicitud) return;
        const estado = normalizarEstado(selectedSolicitud.estado);
        const esEntrega = esGestionEntrega(estado);
        if (!esEntrega) {
            setModalBtnHidden(btnEntregado, true);
            setModalBtnHidden(btnEntregadoParcial, true);
            setModalBtnHidden(btnCerrarPendientes, true);
            setModalBtnHidden(btnConfirmarEntregaParcial, true);
            setModalBtnHidden(btnRegistrarRecepcion, true);
            setModalBtnHidden(btnConfirmarRecepcion, true);
            return;
        }

        const ocOk = solicitudTieneOcRegistrada(selectedSolicitud);
        const esTramiteOc = estado === "tramitando_oc";
        const esRecepcion = esEstadoRecepcion(estado);
        const esEntregaSolicitante = esEstadoEntregaSolicitante(estado);

        setModalBtnHidden(btnGuardarTramite, !esTramiteOc);

        const puedeRecepcion = ocOk && solicitudTieneRecepcionPendiente(selectedSolicitud);
        setModalBtnHidden(btnRegistrarRecepcion, !esRecepcion || !puedeRecepcion);

        const panelRecepcion = document.getElementById("panel-recepcion-parcial-wrap");
        const recepcionVisible = panelRecepcion && !panelRecepcion.hidden;
        setModalBtnHidden(btnConfirmarRecepcion, !recepcionVisible);

        if (esEntregaSolicitante) {
            const puedeParcial = ocOk && solicitudTieneDisponibleEntrega(selectedSolicitud);
            setModalBtnHidden(btnEntregadoParcial, !puedeParcial);

            const puedeCerrar = ocOk && solicitudPuedeEntregaTotal(selectedSolicitud);
            setModalBtnHidden(btnEntregado, !puedeCerrar);

            const puedeCerrarPendientes =
                ocOk && solicitudPuedeCerrarConPendientes(selectedSolicitud);
            setModalBtnHidden(btnCerrarPendientes, !puedeCerrarPendientes);
        } else {
            setModalBtnHidden(btnEntregadoParcial, true);
            setModalBtnHidden(btnEntregado, true);
            setModalBtnHidden(btnCerrarPendientes, true);
        }

        const panelEntrega = document.getElementById("panel-entrega-parcial-wrap");
        const panelVisible = panelEntrega && !panelEntrega.hidden;
        setModalBtnHidden(btnConfirmarEntregaParcial, !panelVisible);
    }

    function updateAccionesGestionModal(esEntrega) {
        setModalBtnHidden(btnEnviar, esEntrega);
        if (esEntrega) {
            updateAccionesEntrega();
        } else {
            setModalBtnHidden(btnGuardarTramite, true);
            setModalBtnHidden(btnEntregado, true);
            setModalBtnHidden(btnEntregadoParcial, true);
            setModalBtnHidden(btnCerrarPendientes, true);
            setModalBtnHidden(btnConfirmarEntregaParcial, true);
            setModalBtnHidden(btnRegistrarRecepcion, true);
            setModalBtnHidden(btnConfirmarRecepcion, true);
        }
    }

    async function refrescarPanelEntrega(solicitud) {
        selectedSolicitud = solicitud;
        destroyObservacionesEditor();
        detailContent.innerHTML = renderPanelTramiteOcHtml(solicitud);
        initObservacionesEditor();
        if (normalizarEstado(solicitud.estado) === "tramitando_oc") {
            bindTramiteOcFormEvents();
        }
        updateAccionesEntrega();
        await hydrateInlineObservacionImages(detailContent, solicitud.id);
    }

    function bindRecepcionParcialFormEvents() {
        detailContent?.querySelectorAll(".recepcion-parcial-check").forEach((check) => {
            check.addEventListener("change", () => {
                const row = check.closest("tr");
                const input = row?.querySelector(".sg-recepcion-parcial-cantidad");
                if (!input) return;
                if (!check.checked) {
                    input.value = "";
                }
            });
        });

        detailContent?.querySelectorAll(".sg-recepcion-parcial-cantidad").forEach((input) => {
            input.addEventListener("input", () => {
                const row = input.closest("tr");
                const check = row?.querySelector(".recepcion-parcial-check");
                const cantidad = Number(input.value);
                if (!check) return;
                if (cantidad > 0) {
                    check.checked = true;
                } else if (!input.value) {
                    check.checked = false;
                }
            });
        });
    }

    function abrirFormularioRecepcion() {
        const panel = document.getElementById("panel-recepcion-parcial-wrap");
        if (!panel) {
            showError("No hay ítems pendientes de recepción.");
            return;
        }
        panel.hidden = false;
        bindRecepcionParcialFormEvents();
        updateAccionesEntrega();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function getProductosRecepcionParcial() {
        const map = {};
        detailContent?.querySelectorAll(".sg-recepcion-parcial-cantidad").forEach((input) => {
            const id = Number(input.dataset.productoId);
            const cantidad = Number(input.value);
            if (!id || !cantidad || cantidad <= 0) return;
            map[id] = cantidad;
        });
        return map;
    }

    async function confirmarRecepcionParcial() {
        if (!selectedSolicitud || !modoGestion) return;

        const productos = getProductosRecepcionParcial();
        if (!Object.keys(productos).length) {
            showError("Selecciona al menos un ítem e indica la cantidad recibida.");
            return;
        }

        if (
            !confirm(
                `¿Confirmas la recepción física de ${Object.keys(productos).length} ítem(s)? ` +
                    "El solicitante será notificado de que puede reclamar los insumos."
            )
        ) {
            return;
        }

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";

        const formData = new FormData();
        formData.append("productos_recepcion", JSON.stringify(productos));
        formData.append("observacion", nuevaObsHtml);
        formData.append("observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnConfirmarRecepcion.disabled = true;
        btnConfirmarRecepcion.textContent = "Registrando...";

        try {
            const result = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/recepcion-insumos`,
                formData
            );
            const solicitud = result?.solicitud || result;
            showSuccess(
                result?.email_enviado
                    ? `Recepción registrada — insumos disponibles para el solicitante.`
                    : `Recepción registrada. No se pudo enviar el correo (revisa SMTP y email del solicitante).`
            );
            await load();
            await refrescarPanelEntrega(solicitud);
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo registrar la recepción."
            );
        } finally {
            btnConfirmarRecepcion.disabled = false;
            btnConfirmarRecepcion.textContent = "Confirmar recepción";
        }
    }

    function abrirFormularioEntregaParcial() {
        const panel = document.getElementById("panel-entrega-parcial-wrap");
        if (!panel) {
            showError("No hay ítems pendientes de entrega.");
            return;
        }
        panel.hidden = false;
        bindEntregaParcialFormEvents();
        updateAccionesEntrega();
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function getProductosEntregaParcial() {
        const map = {};
        detailContent?.querySelectorAll(".sg-entrega-parcial-cantidad").forEach((input) => {
            const id = Number(input.dataset.productoId);
            const cantidad = Number(input.value);
            if (!id || !cantidad || cantidad <= 0) return;
            map[id] = cantidad;
        });
        return map;
    }

    async function confirmarEntregaParcial() {
        if (!selectedSolicitud || !modoGestion) return;

        const productos = getProductosEntregaParcial();
        if (!Object.keys(productos).length) {
            showError("Selecciona al menos un ítem e indica la cantidad a entregar.");
            return;
        }

        if (
            !confirm(
                `¿Confirmas registrar la entrega parcial de ${Object.keys(productos).length} ítem(s)? ` +
                    "Se notificará al solicitante por correo."
            )
        ) {
            return;
        }

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";

        const formData = new FormData();
        formData.append("productos_entrega", JSON.stringify(productos));
        formData.append("observacion", nuevaObsHtml);
        formData.append("observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnConfirmarEntregaParcial.disabled = true;
        btnConfirmarEntregaParcial.textContent = "Registrando...";

        try {
            const result = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/entrega-parcial`,
                formData
            );
            const solicitud = result?.solicitud || result;
            showSuccess(
                result?.email_enviado
                    ? `Entrega parcial registrada. Se notificó al solicitante por correo.`
                    : `Entrega parcial registrada. No se pudo enviar el correo (revisa SMTP y email del solicitante).`
            );
            await load();
            await refrescarPanelEntrega(solicitud);
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo registrar la entrega parcial."
            );
        } finally {
            btnConfirmarEntregaParcial.disabled = false;
            btnConfirmarEntregaParcial.textContent = "Confirmar entrega parcial";
        }
    }

    async function abrirGestion(solicitud) {
        selectedSolicitud = solicitud;
        modoGestion = true;
        const estado = normalizarEstado(solicitud.estado);
        const esEntrega = esGestionEntrega(estado);

        detailTitle.textContent = esEntrega
            ? esSolicitudSalidasAlmacen(solicitud)
                ? `Entrega de almacén · ${solicitud.codigo}`
                : estado === "tramitando_oc"
                  ? `Trámite OC · ${solicitud.codigo}`
                  : estado === "items_en_camino"
                    ? `Llegada de ítems · ${solicitud.codigo}`
                    : `Entrega · ${solicitud.codigo}`
            : esSolicitudSalidasAlmacen(solicitud)
              ? `Gestionar salida · ${solicitud.codigo}`
              : `Gestionar · ${solicitud.codigo}`;
        detailContent.innerHTML = esEntrega
            ? renderPanelTramiteOcHtml(solicitud)
            : renderPanelGestionHtml(
                  solicitud,
                  buildLideresOptions(solicitud.lider_segunda_aprobacion_id || "")
              );
        modalActionsGestion?.removeAttribute("hidden");
        updateAccionesGestionModal(esEntrega);
        btnClose?.removeAttribute("hidden");
        if (esEntrega) {
            if (estado === "tramitando_oc") {
                bindTramiteOcFormEvents();
            }
        } else {
            bindGestionFormEvents();
        }
        initObservacionesEditor();
        await hydrateInlineObservacionImages(detailContent, solicitud.id);
        modal.classList.add("show");
    }

    function getProductosTramiteOcParcial() {
        const map = {};
        detailContent?.querySelectorAll(".sg-tramite-oc-parcial-input").forEach((input) => {
            const id = Number(input.dataset.productoId);
            if (!id) return;
            map[id] = input.value.trim();
        });
        return map;
    }

    function getProductosValorTramiteOcParcial() {
        const map = {};
        detailContent?.querySelectorAll(".sg-tramite-oc-valor-input").forEach((input) => {
            const id = Number(input.dataset.productoId);
            if (!id) return;
            map[id] = input.value.trim();
        });
        return map;
    }

    async function iniciarGestion(id) {
        try {
            await api.post(`/solicitudes-gestion/${id}/gestionar`, {});
            const solicitud = await api.get(`/solicitudes-gestion/${id}`);
            const estado = normalizarEstado(solicitud.estado);
            if (estado === "tramitando_oc") {
                showSuccess(`Gestión de trámite OC — ${solicitud.codigo}`);
            } else if (estado === "items_en_camino") {
                showSuccess(`Recepción de ítems — ${solicitud.codigo}`);
            } else if (
                esSolicitudSalidasAlmacen(solicitud) &&
                (estado === "recepcion_insumos" || estado === "entregado_parcial")
            ) {
                showSuccess(`Gestión de entrega de almacén — ${solicitud.codigo}`);
            } else if (estado === "recepcion_insumos" || estado === "entregado_parcial") {
                showSuccess(`Gestión de entrega — ${solicitud.codigo}`);
            } else if (estado === "tramitada_oc") {
                showSuccess(`Gestión logística — ${solicitud.codigo}`);
            } else if (estado === "cotizacion") {
                showSuccess(`Solicitud ${solicitud.codigo} en estado Cotización.`);
            } else {
                showSuccess(`Solicitud ${solicitud.codigo} lista para gestionar.`);
            }
            await load();
            await abrirGestion(solicitud);
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo iniciar la gestión."
            );
        }
    }

    async function guardarTramiteOc() {
        if (!selectedSolicitud || !modoGestion) return;

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";
        const general =
            document.getElementById("gestion-tramite-oc-general")?.value.trim() ?? "";
        const valorGeneral =
            document.getElementById("gestion-tramite-oc-valor-general")?.value.trim() ?? "";
        const parciales = getProductosTramiteOcParcial();
        const valoresParciales = getProductosValorTramiteOcParcial();
        const tieneParcial = Object.values(parciales).some((v) => Boolean(v));

        if (!general && !tieneParcial) {
            showError(
                "Indica el número de trámite OC general o al menos uno parcial por ítem."
            );
            return;
        }

        if (!validarAnticipoForm()) return;

        const anticipo = getAnticipoFormData();
        const msgConfirm = anticipo.requiere
            ? "¿Guardar trámite OC y enviar anticipo a aprobación del líder?"
            : "¿Guardar el trámite OC y pasar la solicitud a Ítems en camino?";

        if (!confirm(msgConfirm)) {
            return;
        }

        const formData = new FormData();
        formData.append("numero_tramite_oc", general);
        formData.append("valor_tramite_oc", valorGeneral);
        formData.append("productos_tramite_oc", JSON.stringify(parciales));
        formData.append("productos_valor_tramite_oc", JSON.stringify(valoresParciales));
        formData.append("requiere_anticipo", anticipo.requiere ? "true" : "false");
        formData.append("porcentaje_anticipo", anticipo.pct);
        formData.append("lider_anticipo_id", anticipo.liderId);
        formData.append("lider_anticipo_label", anticipo.liderLabel);
        formData.append("observaciones_anticipo", anticipo.obs);
        formData.append("nueva_observacion", nuevaObsHtml);
        formData.append("nueva_observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnGuardarTramite.disabled = true;
        btnGuardarTramite.textContent = "Guardando...";

        try {
            const solicitud = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/tramite-oc`,
                formData
            );
            selectedSolicitud = solicitud;
            showSuccess(
                anticipo.requiere
                    ? `Trámite OC registrado — ${solicitud.codigo}. Anticipo enviado a aprobación.`
                    : `OC registrada — ${solicitud.codigo}. Los ítems quedan en camino.`
            );
            await load();
            if (anticipo.requiere) {
                closeModal();
            } else {
                await refrescarPanelEntrega(solicitud);
            }
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo guardar el trámite OC."
            );
        } finally {
            btnGuardarTramite.disabled = false;
            btnGuardarTramite.textContent = "Guardar trámite OC";
        }
    }

    async function marcarEntregaTotal() {
        if (!selectedSolicitud || !modoGestion) return;

        if (!solicitudTieneOcRegistrada(selectedSolicitud)) {
            showError('Primero guarda el trámite OC con el botón "Guardar trámite OC".');
            return;
        }

        if (!solicitudPuedeEntregaTotal(selectedSolicitud)) {
            showError(
                "Para entrega total deben estar recibidos todos los ítems y haber stock pendiente de entregar al solicitante."
            );
            return;
        }

        if (
            !confirm(
                `¿Confirmas la entrega total al solicitante y cerrar ${selectedSolicitud.codigo} como Entregado? ` +
                    "Se marcarán todas las cantidades recibidas como entregadas y se enviará un correo."
            )
        ) {
            return;
        }

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";

        const formData = new FormData();
        formData.append("observacion", nuevaObsHtml);
        formData.append("observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnEntregado.disabled = true;
        btnEntregado.textContent = "Procesando...";

        try {
            const result = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/marcar-entrega`,
                formData
            );
            const codigo = result?.solicitud?.codigo || selectedSolicitud.codigo;
            if (result?.email_enviado) {
                showSuccess(
                    `Solicitud ${codigo} cerrada como Entregado. Se notificó al solicitante por correo.`
                );
            } else {
                showSuccess(
                    `Solicitud ${codigo} cerrada como Entregado. No se pudo enviar el correo.`
                );
            }
            closeModal();
            await load();
        } catch (err) {
            showError(
                err instanceof ApiError ? err.message : "No se pudo registrar la entrega total."
            );
        } finally {
            btnEntregado.disabled = false;
            btnEntregado.textContent = "Entregado";
        }
    }

    async function cerrarConPendientes() {
        if (!selectedSolicitud || !modoGestion) return;

        if (!solicitudTieneOcRegistrada(selectedSolicitud)) {
            showError('Primero guarda el trámite OC con el botón "Guardar trámite OC".');
            return;
        }

        if (!solicitudPuedeCerrarConPendientes(selectedSolicitud)) {
            showError(
                "Sólo puedes cerrar con pendientes tras al menos una entrega parcial y con ítems aún sin entregar."
            );
            return;
        }

        if (
            !confirm(
                `¿Confirmas cerrar ${selectedSolicitud.codigo} como Entregado ` +
                    "dejando cantidades pendientes por entregar? " +
                    "Las cantidades no entregadas quedarán registradas en el historial."
            )
        ) {
            return;
        }

        observacionControl?.editor.syncHidden();
        const nuevaObsHtml = observacionControl?.editor.getHtml() ?? "";
        const nuevaObsTexto = observacionControl?.editor.getText() ?? "";

        const formData = new FormData();
        formData.append("observacion", nuevaObsHtml);
        formData.append("observacion_texto", nuevaObsTexto);
        (observacionControl?.getFiles() ?? []).forEach((file) =>
            formData.append("adjuntos", file)
        );

        btnCerrarPendientes.disabled = true;
        btnCerrarPendientes.textContent = "Procesando...";

        try {
            const result = await api.postForm(
                `/solicitudes-gestion/${selectedSolicitud.id}/cerrar-con-pendientes`,
                formData
            );
            const codigo = result?.solicitud?.codigo || selectedSolicitud.codigo;
            if (result?.email_enviado) {
                showSuccess(
                    `Solicitud ${codigo} cerrada con ítems pendientes. Se notificó al solicitante.`
                );
            } else {
                showSuccess(`Solicitud ${codigo} cerrada con ítems pendientes.`);
            }
            closeModal();
            await load();
        } catch (err) {
            let msg =
                err instanceof ApiError
                    ? err.message
                    : "No se pudo cerrar la solicitud con pendientes.";
            if (err instanceof ApiError && err.status === 404) {
                msg =
                    "El servidor no reconoce esta acción (404). Reinicia el backend con iniciar.bat y vuelve a intentar.";
            }
            showError(msg);
        } finally {
            btnCerrarPendientes.disabled = false;
            btnCerrarPendientes.textContent = "Cerrar con pendientes";
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
    btnGuardarTramite?.addEventListener("click", guardarTramiteOc);
    btnEntregado?.addEventListener("click", marcarEntregaTotal);
    btnEntregadoParcial?.addEventListener("click", abrirFormularioEntregaParcial);
    btnCerrarPendientes?.addEventListener("click", cerrarConPendientes);
    btnConfirmarEntregaParcial?.addEventListener("click", confirmarEntregaParcial);
    btnRegistrarRecepcion?.addEventListener("click", abrirFormularioRecepcion);
    btnConfirmarRecepcion?.addEventListener("click", confirmarRecepcionParcial);
    btnFacturaCancel?.addEventListener("click", closeFacturaModal);
    btnFacturaGuardar?.addEventListener("click", guardarFactura);
    btnFacturaDetalleCerrar?.addEventListener("click", closeFacturaDetalleModal);
    btnFacturaDetalleAgregar?.addEventListener("click", () => {
        if (!selectedFacturaDetalleId) return;
        const id = selectedFacturaDetalleId;
        closeFacturaDetalleModal();
        openFacturaModal(id, true);
    });
    modal?.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });
    modalFactura?.addEventListener("click", (e) => {
        if (e.target === modalFactura) closeFacturaModal();
    });
    modalFacturaDetalle?.addEventListener("click", (e) => {
        if (e.target === modalFacturaDetalle) closeFacturaDetalleModal();
    });

    let debounce;
    searchInput?.addEventListener("input", () => {
        clearTimeout(debounce);
        debounce = setTimeout(load, 300);
    });
    filterTipo?.addEventListener("change", load);
}
