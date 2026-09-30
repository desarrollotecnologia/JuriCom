import { api, ApiError } from "../api/client.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js?v=2";
import { createSearchableSelect } from "../components/searchable-select.js";
import {
    LIDERES_AREA,
    UNIDADES_MEDIDA,
    buildSelectOptions,
} from "./mock-catalogos.js";
import {
    opcionesCentrosCostosHtml,
    poblarCentrosCostos,
} from "../catalogos/centros-costos.js";
import { escapeHtml, formatDate } from "../utils/format.js";
import {
    attachGestionDownloadHandlers,
    badgeEstado,
    badgeTipo,
    ESTADO_LABEL,
    hydrateInlineObservacionImages,
    hydrateComunicacionJuridica,
    normalizarEstado,
    puedeComentarPosteriorCotizacion,
    puedeEnviarEvidenciaCierreServicio,
    renderAgregarComentarioHtml,
    renderDetalleSolicitudHtml,
    TIPO_LABEL,
} from "./gestion-solicitudes-common.js?v=65";

const EYE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;

const COMENTARIO_EDITOR_ID = "mis-sol-comentario-cotizacion-editor";
const COMENTARIO_FILE_INPUT_ID = "mis-sol-comentario-cotizacion-adjuntos";
const COMENTARIO_FILE_LIST_ID = "mis-sol-comentario-cotizacion-file-list";
const COMENTARIO_BTN_ID = "btn-mis-sol-guardar-comentario-cotizacion";
const REVISION_BTN_ID = "btn-mis-sol-responder-revision";

const TRASH_ICON_EDIT = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>`;

export function initMisSolicitudesGestion({ esAdmin, currentUserId = null }) {
    const tbody = document.getElementById("gestion-tbody");
    const searchInput = document.getElementById("gestion-search");
    const filterTipo = document.getElementById("gestion-filter-tipo");
    const filterEstado = document.getElementById("gestion-filter-estado");
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
    let modoEdicionLibre = false;
    let liderEditControl = null;
    let observacionControl = null;

    function esProductoTipo(s) {
        return (s?.tipo || "") !== "insumos_servicios";
    }

    function puedeEditar(s) {
        if (!s) return false;
        const esCreador =
            currentUserId != null && Number(s.creado_por_id) === Number(currentUserId);
        return esCreador && normalizarEstado(s.estado) === "solicitud";
    }

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

    function populateEstadoOptions() {
        if (!filterEstado) return;
        const previo = filterEstado.value;
        const estados = new Map();
        for (const s of items) {
            const key = normalizarEstado(s.estado) || s.estado || "";
            if (!key || estados.has(key)) continue;
            estados.set(
                key,
                ESTADO_LABEL[key] || (s.estado_label || "").trim() || key
            );
        }
        const opciones = [...estados.entries()].sort((a, b) =>
            a[1].localeCompare(b[1], "es")
        );
        filterEstado.innerHTML =
            '<option value="">Todos los estados</option>' +
            opciones
                .map(
                    ([value, label]) =>
                        `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`
                )
                .join("");
        filterEstado.value = estados.has(previo) ? previo : "";
    }

    function itemsVisibles() {
        const estadoSel = filterEstado?.value ?? "";
        if (!estadoSel) return items;
        return items.filter((s) => normalizarEstado(s.estado) === estadoSel);
    }

    function renderTable() {
        const visibles = itemsVisibles();
        if (!visibles.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="muted text-center">
                No hay solicitudes que coincidan con los filtros.
                <br /><a href="/app/compras/nueva-solicitud.html">Crear nueva solicitud</a>
            </td></tr>`;
            if (resultCount) resultCount.textContent = "0 solicitudes";
            return;
        }

        tbody.innerHTML = visibles
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
            resultCount.textContent = `${visibles.length} solicitud${visibles.length === 1 ? "" : "es"}`;
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
            populateEstadoOptions();
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

    function renderPanelEdicionHtml(s) {
        const esServicio = !esProductoTipo(s);
        const esCompra = (s.tipo || "") === "compra";
        const esConsumibles = (s.tipo || "") === "salida_consumibles";
        const limpiar = (html) =>
            String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
        const obsTexto = (s.observaciones_texto || "").trim() || limpiar(s.observaciones);
        const descTexto =
            (s.descripcion_servicio_texto || "").trim() || limpiar(s.descripcion_servicio);
        return `
            <div class="sg-detail-panel" id="panel-edicion-libre">
                <h3 class="sg-detail-panel-title">Editar solicitud</h3>
                <p class="muted sg-detail-panel-hint">
                    Corrige los datos antes de la primera aprobación. El cambio quedará
                    registrado en la trazabilidad.
                </p>
                <div class="field">
                    <label for="edit-titulo">Asunto / título</label>
                    <input id="edit-titulo" type="text" value="${escapeHtml(s.titulo || "")}" />
                </div>
                <div class="field">
                    <label for="edit-centro-costo">Centro de costo</label>
                    <select id="edit-centro-costo"></select>
                </div>
                ${
                    esCompra
                        ? `<div class="field">
                    <label>Presupuestado</label>
                    <div>
                        <label style="margin-right:16px;"><input type="radio" name="edit-presupuestado" value="si" ${s.presupuestado ? "checked" : ""}/> Sí</label>
                        <label><input type="radio" name="edit-presupuestado" value="no" ${!s.presupuestado ? "checked" : ""}/> No</label>
                    </div>
                </div>`
                        : ""
                }
                ${
                    esCompra || esConsumibles
                        ? `<div class="field">
                    <label for="edit-prioridad">Prioridad</label>
                    <select id="edit-prioridad">
                        <option value="alta" ${s.prioridad === "alta" ? "selected" : ""}>Alta</option>
                        <option value="media" ${!s.prioridad || s.prioridad === "media" ? "selected" : ""}>Media</option>
                        <option value="baja" ${s.prioridad === "baja" ? "selected" : ""}>Baja</option>
                    </select>
                </div>`
                        : ""
                }
                <div class="field">
                    <label for="edit-lider-input">Líder de área</label>
                    <div id="edit-lider-host"></div>
                </div>
                ${
                    esServicio
                        ? `<div class="field">
                    <label for="edit-proveedor">Proveedor sugerido</label>
                    <textarea id="edit-proveedor" rows="2">${escapeHtml(s.proveedor_sugerido || "")}</textarea>
                </div>
                <div class="field">
                    <label for="edit-descripcion">Descripción del servicio</label>
                    <textarea id="edit-descripcion" rows="4">${escapeHtml(descTexto)}</textarea>
                </div>`
                        : `<div class="field">
                    <label>Ítems / productos</label>
                    <div class="table-responsive">
                        <table class="table">
                            <thead><tr>
                                <th>Código</th><th>Unidad</th><th>Descripción</th>
                                <th>Centro de costo</th><th>Cantidad</th><th></th>
                            </tr></thead>
                            <tbody id="edit-items-tbody"></tbody>
                        </table>
                    </div>
                    <button type="button" class="btn btn-secondary btn-sm" id="edit-add-item">+ Agregar ítem</button>`
                }
                <div class="field">
                    <label for="edit-observaciones">Observaciones</label>
                    <textarea id="edit-observaciones" rows="2">${escapeHtml(obsTexto)}</textarea>
                </div>
            </div>`;
    }

    function setSelectValue(sel, value) {
        if (!sel) return;
        sel.value = value;
        if (sel.value !== value && value) {
            const opt = document.createElement("option");
            opt.value = value;
            opt.textContent = value;
            sel.appendChild(opt);
            sel.value = value;
        }
    }

    function agregarFilaItem(tbody, p = {}) {
        const tr = document.createElement("tr");
        tr.className = "edit-item-row";
        tr.innerHTML = `
            <td><input type="text" class="input-table edit-codigo" value="${escapeHtml(p.codigo_siimed || "")}" placeholder="Ej. 100234" inputmode="numeric" /></td>
            <td><select class="input-table edit-unidad"></select></td>
            <td><textarea class="input-table edit-descripcion" rows="1" placeholder="Descripción" required>${escapeHtml(p.descripcion || "")}</textarea></td>
            <td><select class="input-table edit-centro"></select></td>
            <td><input type="number" class="input-table-cantidad edit-cantidad" min="0.0001" step="any" value="${escapeHtml(String(p.cantidad ?? 1))}" aria-label="Cantidad" /></td>
            <td class="table-actions"><button type="button" class="btn btn-icon-danger edit-remove-row" title="Eliminar fila">${TRASH_ICON_EDIT}</button></td>`;
        const uni = tr.querySelector(".edit-unidad");
        uni.innerHTML = buildSelectOptions(UNIDADES_MEDIDA, "Unidad");
        setSelectValue(uni, (p.unidad || "").trim());
        poblarCentrosCostos(tr.querySelector(".edit-centro"), (p.centro_costo || "").trim());
        tr.querySelector(".edit-remove-row").addEventListener("click", () => {
            if (tbody.querySelectorAll("tr").length <= 1) {
                showError("Debe quedar al menos un ítem en la solicitud.");
                return;
            }
            tr.remove();
        });
        tbody.appendChild(tr);
    }

    function initEdicionLibre(s) {
        poblarCentrosCostos(
            document.getElementById("edit-centro-costo"),
            s.centro_costo_area || ""
        );

        const liderItems = [...LIDERES_AREA];
        const actualId = (s.lider_area_id || "").trim();
        if (actualId && !liderItems.some((l) => String(l.id) === actualId)) {
            liderItems.unshift({
                id: actualId,
                label: s.lider_area_label || actualId,
            });
        }
        liderEditControl = createSearchableSelect({
            container: document.getElementById("edit-lider-host"),
            name: "edit_lider_area_id",
            items: liderItems,
            placeholder: "Escribe nombre o cargo del líder...",
            inputId: "edit-lider-input",
            emptyMessage: "No se encontró ningún líder con ese texto.",
        });
        if (actualId) liderEditControl.setValue(actualId);

        if (esProductoTipo(s)) {
            const tbody = document.getElementById("edit-items-tbody");
            const productos = s.productos && s.productos.length ? s.productos : [{}];
            for (const p of productos) agregarFilaItem(tbody, p);
            document
                .getElementById("edit-add-item")
                ?.addEventListener("click", () => agregarFilaItem(tbody, {}));
        }
    }

    function collectEdicion(s) {
        const titulo = (document.getElementById("edit-titulo")?.value || "").trim();
        if (!titulo) {
            showError("El asunto o título no puede quedar vacío.");
            return null;
        }
        const centro = document.getElementById("edit-centro-costo")?.value || "";
        if (!centro) {
            showError("Selecciona un centro de costo.");
            return null;
        }
        const liderId = liderEditControl?.getValue() || "";
        if (!liderId) {
            showError("Selecciona un líder de área de la lista.");
            return null;
        }

        const fd = new FormData();
        fd.append("titulo", titulo);
        fd.append("centro_costo_area", centro);
        fd.append("lider_area_id", liderId);
        fd.append("lider_area_label", liderEditControl?.getSelectedItem()?.label || "");
        const obs = document.getElementById("edit-observaciones")?.value || "";
        fd.append("observaciones_texto", obs);
        fd.append("observaciones", "");

        const presRadio = document.querySelector(
            'input[name="edit-presupuestado"]:checked'
        );
        if (presRadio) {
            fd.append("presupuestado", presRadio.value === "si" ? "true" : "false");
        }
        const prioridad = document.getElementById("edit-prioridad");
        if (prioridad) fd.append("prioridad", prioridad.value);

        if (!esProductoTipo(s)) {
            fd.append("proveedor_sugerido", document.getElementById("edit-proveedor")?.value || "");
            const desc = document.getElementById("edit-descripcion")?.value || "";
            fd.append("descripcion_servicio_texto", desc);
            fd.append("descripcion_servicio", "");
            return fd;
        }

        const productos = [];
        const rows = document.querySelectorAll("#edit-items-tbody .edit-item-row");
        for (const row of rows) {
            const descripcion = (row.querySelector(".edit-descripcion")?.value || "").trim();
            const unidad = row.querySelector(".edit-unidad")?.value || "";
            const centroCosto = row.querySelector(".edit-centro")?.value || "";
            const cantidad = row.querySelector(".edit-cantidad")?.value ?? "1";
            const codigo = (row.querySelector(".edit-codigo")?.value || "").trim();
            if (!descripcion && !unidad && !centroCosto && !codigo) continue;
            if (!descripcion) {
                showError("Cada ítem requiere descripción.");
                return null;
            }
            if (!unidad) {
                showError(`El ítem «${descripcion}» requiere unidad.`);
                return null;
            }
            if (!centroCosto) {
                showError(`El ítem «${descripcion}» requiere centro de costo.`);
                return null;
            }
            const n = Number(String(cantidad).replace(",", "."));
            if (!Number.isFinite(n) || n <= 0) {
                showError(`El ítem «${descripcion}» requiere una cantidad mayor a cero.`);
                return null;
            }
            productos.push({
                codigo_siimed: codigo,
                unidad,
                descripcion,
                centro_costo: centroCosto,
                cantidad: String(cantidad),
            });
        }
        if (!productos.length) {
            showError("Agrega al menos un ítem con descripción.");
            return null;
        }
        fd.append("productos_json", JSON.stringify(productos));
        return fd;
    }

    async function guardarEdicion() {
        if (!selectedSolicitudId || !puedeEditar(selectedSolicitud)) return;
        const fd = collectEdicion(selectedSolicitud);
        if (!fd) return;

        const btn = document.getElementById("btn-mis-sol-guardar-edicion");
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Guardando...";
        }
        try {
            await api.postForm(`/solicitudes-gestion/${selectedSolicitudId}/editar`, fd);
            showSuccess("Solicitud actualizada. El cambio quedó registrado en la trazabilidad.");
            modoEdicionLibre = false;
            const s = await api.get(`/solicitudes-gestion/${selectedSolicitudId}`);
            await renderDetalle(s);
            await load();
        } catch (err) {
            showError(err instanceof ApiError ? err.message : "No se pudieron guardar los cambios.");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Guardar cambios";
            }
        }
    }

    function syncBotonesEdicion(s) {
        const editarBtn = document.getElementById("btn-mis-sol-editar");
        const guardarBtn = document.getElementById("btn-mis-sol-guardar-edicion");
        const editable = puedeEditar(s);
        if (editarBtn) {
            if (editable) {
                editarBtn.removeAttribute("hidden");
                editarBtn.textContent = modoEdicionLibre ? "Cancelar edición" : "Editar";
            } else {
                editarBtn.setAttribute("hidden", "");
            }
        }
        if (guardarBtn) {
            if (editable && modoEdicionLibre) guardarBtn.removeAttribute("hidden");
            else guardarBtn.setAttribute("hidden", "");
        }
    }

    async function toggleEdicionLibre() {
        if (!puedeEditar(selectedSolicitud)) return;
        modoEdicionLibre = !modoEdicionLibre;
        await renderDetalle(selectedSolicitud);
    }

    function renderDetalleConComentario(s) {
        const puedeEvidencia = puedeEnviarEvidenciaCierreServicio(s.estado, s);
        const puedeComentar =
            puedeEvidencia || puedeComentarPosteriorCotizacion(s.estado);

        if (modoEdicionLibre && puedeEditar(s)) {
            return renderPanelEdicionHtml(s);
        }

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
        liderEditControl = null;
        detailContent.innerHTML = renderDetalleConComentario(s);
        if (modoEdicionLibre && puedeEditar(s)) {
            initEdicionLibre(s);
        }
        syncBotonesEdicion(s);
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
            modoEdicionLibre = false;
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
        modoEdicionLibre = false;
        liderEditControl = null;
        syncGear(null);
    }

    document.getElementById("btn-mis-sol-editar")?.addEventListener("click", toggleEdicionLibre);
    document.getElementById("btn-mis-sol-guardar-edicion")?.addEventListener("click", guardarEdicion);
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
    filterEstado?.addEventListener("change", renderTable);
}
