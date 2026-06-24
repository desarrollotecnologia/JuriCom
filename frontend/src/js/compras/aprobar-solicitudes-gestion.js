import { api, ApiError } from "../api/client.js";

import { escapeHtml, formatDate } from "../utils/format.js";

import { createObservacionConAdjuntos } from "../components/observacion-editor.js";

import {

    attachGestionDownloadHandlers,

    badgeEstado,

    hydrateInlineObservacionImages,

    normalizarEstado,

    renderDetalleSolicitudHtml,

    TIPO_LABEL,

} from "./gestion-solicitudes-common.js?v=3";



const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;



const APROBACION_HINT = {

    solicitud: "Primera aprobación — tu comentario quedará en el historial de observaciones.",

    en_aprobacion: "Segunda aprobación — comenta por qué apruebas, o usa «Solicitar recotización» para devolver la solicitud al gestor.",

};



function etiquetaAprobacion(estado) {

    const key = normalizarEstado(estado);

    if (key === "en_aprobacion") return "Segunda aprobación";

    return "Primera aprobación";

}



function esPrimeraAprobacion(estado) {

    return normalizarEstado(estado) === "solicitud";

}



function esSegundaAprobacion(estado) {
    return normalizarEstado(estado) === "en_aprobacion";
}



export function initAprobarSolicitudesGestion() {

    const tbody = document.getElementById("aprobacion-tbody");

    const searchInput = document.getElementById("aprobacion-search");

    const resultCount = document.getElementById("aprobacion-result-count");

    const alertError = document.getElementById("alert-error");

    const alertSuccess = document.getElementById("alert-success");

    const modal = document.getElementById("modal-aprobacion-detail");
    const modalBox = modal?.querySelector(".modal");

    const detailContent = document.getElementById("aprobacion-detail-content");

    const detailTitle = document.getElementById("aprobacion-detail-title");

    const btnAprobar = document.getElementById("btn-aprobar-solicitud");

    const btnRechazar = document.getElementById("btn-rechazar-solicitud");

    const btnRecotizar = document.getElementById("btn-solicitar-recotizacion");

    const motivoRechazo = document.getElementById("motivo-rechazo");

    const obsHint = document.getElementById("aprobacion-obs-hint");

    const primeraPanel = document.getElementById("aprobacion-primera-panel");

    const parcialHint = document.getElementById("aprobacion-parcial-hint");



    let items = [];

    let selectedId = null;

    let selectedEstado = null;

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



    function initObservacionEditor() {

        observacionControl?.destroy();

        observacionControl = createObservacionConAdjuntos({

            editorContainerId: "aprobacion-observacion-editor",

            fileInputId: "aprobacion-observacion-adjuntos",

            fileListId: "aprobacion-observacion-file-list",

            name: "observacion_aprobacion",

            placeholder: "Escribe tu observación como líder aprobador...",

            minHeight: 140,

        });

    }



    function destroyObservacionEditor() {

        observacionControl?.destroy();

        observacionControl = null;

    }



    function resetObservacionForm() {

        observacionControl?.clearAll();

    }



    function resetPrimeraAprobacionUI() {
        primeraPanel?.setAttribute("hidden", "");
        modalBox?.classList.remove("sg-modo-aprobacion-parcial");
        parcialHint?.setAttribute("hidden", "");
        const totalRadio = document.querySelector('input[name="tipo-aprobacion"][value="total"]');
        if (totalRadio) totalRadio.checked = true;
    }

    function syncTipoAprobacionUI() {
        const parcial =
            document.querySelector('input[name="tipo-aprobacion"][value="parcial"]')?.checked ??
            false;
        modalBox?.classList.toggle("sg-modo-aprobacion-parcial", parcial);
        if (parcial) {
            parcialHint?.removeAttribute("hidden");
        } else {
            parcialHint?.setAttribute("hidden", "");
            detailContent
                ?.querySelectorAll(".aprobacion-producto-check")
                .forEach((cb) => {
                    cb.checked = true;
                });
        }
    }



    function getProductosAprobadosIds() {

        return [...(detailContent?.querySelectorAll(".aprobacion-producto-check:checked") || [])].map(

            (cb) => Number(cb.value)

        );

    }



    function getProductosCantidades() {
        const cantidades = {};
        detailContent?.querySelectorAll(".sg-producto-cantidad-input").forEach((input) => {
            const id = Number(input.dataset.productoId);
            const val = Number(input.value);
            if (id) cantidades[id] = val;
        });
        return cantidades;
    }



    function validateCantidadesProductos() {
        const inputs = detailContent?.querySelectorAll(".sg-producto-cantidad-input") || [];
        for (const input of inputs) {
            const val = Number(input.value);
            if (!Number.isFinite(val) || val <= 0) {
                showError("Todas las cantidades deben ser mayores a cero.");
                return false;
            }
        }
        return true;
    }



    function filterLocal() {

        const q = searchInput?.value.trim().toLowerCase() ?? "";

        if (!q) return items;

        return items.filter((s) => {

            const haystack = [

                s.codigo,

                s.titulo,

                s.creado_por_username,

                s.lider_area_label,

                etiquetaAprobacion(s.estado),

            ]

                .filter(Boolean)

                .join(" ")

                .toLowerCase();

            return haystack.includes(q);

        });

    }



    function renderTable() {

        const visible = filterLocal();



        if (!visible.length) {

            tbody.innerHTML = `<tr><td colspan="7" class="muted text-center">

                No hay solicitudes de compra pendientes de aprobación.

            </td></tr>`;

            resultCount.textContent = "0 pendientes";

            return;

        }



        tbody.innerHTML = visible

            .map(

                (s) => `

            <tr>

                <td data-label="Consecutivo">

                    <span class="codigo-solicitud">${escapeHtml(s.codigo)}</span>

                </td>

                <td data-label="Solicitante">${escapeHtml(s.creado_por_username || "—")}</td>

                <td data-label="Título">${escapeHtml(s.titulo)}</td>

                <td data-label="Etapa">${badgeEstado(s.estado)}</td>

                <td data-label="Líder aprobador">${escapeHtml(s.lider_area_label || "—")}</td>

                <td data-label="Fecha de registro">${formatDate(s.created_at)}</td>

                <td data-label="Acciones" class="col-actions col-actions-wide">

                    <button type="button" class="btn btn-secondary btn-icon-view btn-ver-solicitud" data-id="${s.id}" data-estado="${escapeHtml(s.estado)}" title="Ver detalle">

                        ${EYE_ICON}<span>Ver</span>

                    </button>

                    <button type="button" class="btn btn-primary btn-sm btn-aprobar-rapido" data-id="${s.id}">Aprobar</button>

                </td>

            </tr>`

            )

            .join("");



        resultCount.textContent = `${visible.length} pendiente${visible.length === 1 ? "" : "s"}`;



        tbody.querySelectorAll(".btn-ver-solicitud").forEach((btn) => {

            btn.addEventListener("click", () =>

                openDetail(Number(btn.dataset.id), btn.dataset.estado)

            );

        });

        tbody.querySelectorAll(".btn-aprobar-rapido").forEach((btn) => {

            btn.addEventListener("click", () => aprobar(Number(btn.dataset.id)));

        });

    }



    async function load() {

        tbody.innerHTML =

            '<tr><td colspan="7" class="muted text-center">Cargando...</td></tr>';

        try {

            items = await api.get("/solicitudes-gestion/pendientes-aprobacion");

            renderTable();

        } catch (err) {

            const msg =

                err instanceof ApiError

                    ? err.message

                    : "No se pudieron cargar las solicitudes pendientes.";

            tbody.innerHTML = `<tr><td colspan="7" class="muted text-center">${escapeHtml(msg)}</td></tr>`;

            resultCount.textContent = "";

        }

    }



    function updateObservacionHint(estado) {

        const key = normalizarEstado(estado);

        if (obsHint) {

            obsHint.textContent =

                APROBACION_HINT[key] ||

                "Opcional. Tu comentario quedará registrado en el historial de observaciones.";

        }

        if (btnAprobar) {

            btnAprobar.textContent = `Aprobar (${etiquetaAprobacion(estado)})`;

        }

        if (btnRecotizar) {
            if (esSegundaAprobacion(estado)) {
                btnRecotizar.removeAttribute("hidden");
            } else {
                btnRecotizar.setAttribute("hidden", "");
            }
        }

    }



    async function openDetail(id, estadoPrecargado = null) {

        selectedId = id;

        selectedEstado = estadoPrecargado;

        selectedSolicitud = null;

        if (motivoRechazo) motivoRechazo.value = "";

        resetObservacionForm();

        resetPrimeraAprobacionUI();

        try {

            const s = await api.get(`/solicitudes-gestion/${id}`);

            selectedSolicitud = s;

            selectedEstado = s.estado;

            detailTitle.textContent = `${s.codigo} · ${TIPO_LABEL[s.tipo] || s.tipo} · ${etiquetaAprobacion(s.estado)}`;



            const isPrimera = esPrimeraAprobacion(s.estado);

            detailContent.innerHTML = renderDetalleSolicitudHtml(s, {

                showAprobacionParcialAlert: false,

                productosOptions: isPrimera

                    ? {

                          selectable: true,

                          cantidadEditable: true,

                          showEstado: false,

                          titulo: "Ítems de la solicitud",

                          panelId: "aprobacion-productos-panel",

                      }

                    : {
                          showEstado: Boolean(s.aprobacion_parcial),
                          cantidadEditable: false,
                      },

            });



            if (isPrimera) {
                primeraPanel?.removeAttribute("hidden");
                syncTipoAprobacionUI();
            }



            updateObservacionHint(s.estado);

            initObservacionEditor();

            await hydrateInlineObservacionImages(detailContent, s.id);

            modal.classList.add("show");

        } catch (err) {

            showError(

                err instanceof ApiError ? err.message : "No se pudo cargar el detalle."

            );

        }

    }



    function closeModal() {

        modal?.classList.remove("show");

        selectedId = null;

        selectedEstado = null;

        selectedSolicitud = null;

        destroyObservacionEditor();

        resetObservacionForm();

        resetPrimeraAprobacionUI();

        if (motivoRechazo) motivoRechazo.value = "";

        if (btnAprobar) btnAprobar.textContent = "Aprobar";

        btnRecotizar?.setAttribute("hidden", "");

    }



    async function aprobar(id) {

        const solicitudId = id ?? selectedId;

        if (!solicitudId) return;



        const esDesdeModal = solicitudId === selectedId;

        const etiqueta = etiquetaAprobacion(selectedEstado || "solicitud");

        const isPrimera = esPrimeraAprobacion(selectedEstado || "solicitud");



        let tipoAprobacion = "total";

        let productosAprobados = [];



        if (isPrimera && esDesdeModal) {

            tipoAprobacion =

                document.querySelector('input[name="tipo-aprobacion"]:checked')?.value || "total";

            if (!validateCantidadesProductos()) return;

            if (tipoAprobacion === "parcial") {

                productosAprobados = getProductosAprobadosIds();

                if (!productosAprobados.length) {

                    showError("Selecciona al menos un ítem para la aprobación parcial.");

                    return;

                }

            }

        }



        const confirmMsg =

            isPrimera && tipoAprobacion === "parcial"

                ? `¿Confirmas la aprobación parcial de ${productosAprobados.length} ítem(s)? Los no seleccionados quedarán como no aprobados.`

                : `¿Confirmas la ${etiqueta.toLowerCase()} de esta solicitud de compra?`;



        if (!confirm(confirmMsg)) {

            return;

        }



        observacionControl?.editor.syncHidden();

        const obsHtml = esDesdeModal ? (observacionControl?.editor.getHtml() ?? "") : "";

        const obsTexto = esDesdeModal ? (observacionControl?.editor.getText() ?? "") : "";

        const adjuntos = esDesdeModal ? observacionControl?.getFiles() ?? [] : [];



        const formData = new FormData();

        formData.append("observacion", obsHtml);

        formData.append("observacion_texto", obsTexto);

        formData.append("tipo_aprobacion", tipoAprobacion);

        formData.append("productos_aprobados", JSON.stringify(productosAprobados));

        if (isPrimera && esDesdeModal) {
            formData.append("productos_cantidades", JSON.stringify(getProductosCantidades()));
        }

        adjuntos.forEach((file) => formData.append("adjuntos", file));



        if (btnAprobar && esDesdeModal) {

            btnAprobar.disabled = true;

            btnAprobar.textContent = "Aprobando...";

        }



        try {

            await api.postForm(`/solicitudes-gestion/${solicitudId}/aprobar`, formData);

            const msgParcial =

                isPrimera && tipoAprobacion === "parcial"

                    ? `Aprobación parcial registrada (${productosAprobados.length} ítem(s)).`

                    : `Solicitud aprobada correctamente (${etiqueta}).`;

            showSuccess(msgParcial);

            closeModal();

            await load();

        } catch (err) {

            showError(

                err instanceof ApiError ? err.message : "No se pudo aprobar la solicitud."

            );

        } finally {

            if (btnAprobar) {

                btnAprobar.disabled = false;

                if (selectedEstado) {

                    btnAprobar.textContent = `Aprobar (${etiquetaAprobacion(selectedEstado)})`;

                } else {

                    btnAprobar.textContent = "Aprobar";

                }

            }

        }

    }



    async function rechazar() {

        if (!selectedId) return;

        const motivo = motivoRechazo?.value.trim() ?? "";

        if (!motivo) {

            showError("Indica el motivo de la cancelación.");

            return;

        }

        if (!confirm("¿Confirmas la cancelación de esta solicitud?")) return;



        try {

            await api.post(`/solicitudes-gestion/${selectedId}/rechazar`, { motivo });

            showSuccess("Solicitud cancelada.");

            closeModal();

            await load();

        } catch (err) {

            showError(

                err instanceof ApiError ? err.message : "No se pudo rechazar la solicitud."

            );

        }

    }



    async function solicitarRecotizacion() {

        if (!selectedId || !esSegundaAprobacion(selectedEstado)) return;

        observacionControl?.editor.syncHidden();

        const observacionHtml = observacionControl?.editor.getHtml() ?? "";

        const observacionTexto = observacionControl?.editor.getText() ?? "";

        if (!observacionTexto.trim() && !observacionHtml.trim()) {

            showError(

                "Indica en el comentario el motivo por el cual solicitas una nueva recotización."

            );

            return;

        }

        if (

            !confirm(

                "¿Confirmas devolver esta solicitud a Cotización para una nueva recotización?"

            )

        ) {

            return;

        }

        const formData = new FormData();

        formData.append("observacion", observacionHtml);

        formData.append("observacion_texto", observacionTexto);

        for (const file of observacionControl?.getFiles() ?? []) {

            formData.append("adjuntos", file);

        }

        try {

            await api.postForm(

                `/solicitudes-gestion/${selectedId}/solicitar-recotizacion`,

                formData

            );

            showSuccess(

                "Solicitud devuelta a Cotización. El gestor podrá cargar nuevas cotizaciones."

            );

            closeModal();

            await load();

        } catch (err) {

            showError(

                err instanceof ApiError

                    ? err.message

                    : "No se pudo solicitar la recotización."

            );

        }

    }



    attachGestionDownloadHandlers(detailContent, showError);



    document.getElementById("btn-aprobacion-detail-close")?.addEventListener("click", closeModal);

    modal?.addEventListener("click", (e) => {

        if (e.target === modal) closeModal();

    });

    btnAprobar?.addEventListener("click", () => aprobar());

    btnRechazar?.addEventListener("click", rechazar);

    btnRecotizar?.addEventListener("click", solicitarRecotizacion);

    document.querySelectorAll('input[name="tipo-aprobacion"]').forEach((radio) => {
        radio.addEventListener("change", syncTipoAprobacionUI);
    });

    let debounce;

    searchInput?.addEventListener("input", () => {

        clearTimeout(debounce);

        debounce = setTimeout(renderTable, 200);

    });



    load();

}


