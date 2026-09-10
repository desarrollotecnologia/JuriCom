import {
    LIDERES_AREA,
} from "./mock-catalogos.js?v=2";
import { centrosCostosItems } from "../catalogos/centros-costos.js";
import { api, ApiError } from "../api/client.js";
import {
    createObservacionConAdjuntos,
    DETALLE_SERVICIO_ADJUNTOS_ACCEPT,
    DETALLE_SERVICIO_ADJUNTOS_HINT,
    OBSERVACION_ADJUNTOS_HINT,
} from "../components/observacion-editor.js";
import { createSearchableSelect } from "../components/searchable-select.js?v=2";
import { createProveedorPicker } from "../components/proveedor-picker.js";
import { formatFileSize } from "../utils/format.js";

function setupFilePicker(inputId, nameId) {
    const input = document.getElementById(inputId);
    const nameEl = document.getElementById(nameId);
    if (!input || !nameEl) return;

    input.addEventListener("change", () => {
        const file = input.files?.[0];
        nameEl.textContent = file ? `${file.name} (${formatFileSize(file.size)})` : "";
    });
}

function setupProgramadoToggle(form) {
    const fechaWrap = document.getElementById("fecha-programada-wrap");
    const fechaInput = document.getElementById("fecha-servicio-programado");
    if (!fechaWrap || !fechaInput) return;

    const sync = () => {
        const programado = form.querySelector('input[name="servicio_programado"]:checked')?.value;
        const visible = programado === "si";
        fechaWrap.hidden = !visible;
        fechaInput.required = visible;
        if (!visible) {
            fechaInput.value = "";
        }
    };

    form.querySelectorAll('input[name="servicio_programado"]').forEach((radio) => {
        radio.addEventListener("change", sync);
    });
    sync();
}

export function initSolicitudServiciosForm() {
    const form = document.getElementById("form-solicitud-servicios");
    if (!form) return;

    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const submitBtn = document.getElementById("btn-submit");
    const centroCostoSelect = createSearchableSelect({
        containerId: "centro-costo-area-select",
        name: "centro_costo_area",
        items: centrosCostosItems(),
        placeholder: "Busca por número o nombre… (ej. 212 o compras)",
        required: true,
        emptyMessage: "No hay centros de costo que coincidan.",
    });

    const descripcionControl = createObservacionConAdjuntos({
        editorContainerId: "descripcion-servicio-editor",
        fileInputId: "descripcion-servicio-files",
        fileListId: "descripcion-servicio-file-list",
        name: "descripcion_servicio",
        placeholder: "Describe el servicio requerido, alcance, ubicación, condiciones, etc.",
        minHeight: 200,
        accept: DETALLE_SERVICIO_ADJUNTOS_ACCEPT,
        autosaveKey: "srv-nueva:descripcion",
    });
    const descripcionEditor = descripcionControl.editor;

    const observacionControl = createObservacionConAdjuntos({
        editorContainerId: "observaciones-editor",
        fileInputId: "file-input",
        fileListId: "file-list",
        name: "observaciones",
        placeholder: "Información adicional relevante para la solicitud...",
        minHeight: 180,
        autosaveKey: "srv-nueva:observaciones",
    });
    const observacionesEditor = observacionControl.editor;

    const liderSelect = createSearchableSelect({
        containerId: "lider-area-select",
        name: "lider_area_id",
        items: LIDERES_AREA,
        placeholder: "Escribe nombre o cargo del líder...",
        required: true,
        inputId: "lider-area-input",
        emptyMessage: "No se encontró ningún líder con ese texto.",
    });

    setupFilePicker("archivo-ficha-tecnica", "archivo-ficha-tecnica-name");
    setupFilePicker("archivo-hoja-vida", "archivo-hoja-vida-name");
    setupProgramadoToggle(form);

    const hintDetalle = document.getElementById("hint-descripcion-servicio");
    if (hintDetalle) {
        hintDetalle.textContent = DETALLE_SERVICIO_ADJUNTOS_HINT;
    }
    const hintObs = document.getElementById("hint-observaciones");
    if (hintObs) {
        hintObs.textContent = OBSERVACION_ADJUNTOS_HINT;
    }

    function showError(msg) {
        alertSuccess.classList.remove("show");
        alertError.textContent = msg;
        alertError.classList.add("show");
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function showSuccess(msg) {
        alertError.classList.remove("show");
        alertSuccess.textContent = msg;
        alertSuccess.classList.add("show");
        window.scrollTo({ top: 0, behavior: "smooth" });
    }

    function resetForm() {
        form.reset();
        centroCostoSelect.clear();
        liderSelect.clear();
        descripcionControl.clearAll();
        observacionControl.clearAll();
        document.getElementById("archivo-ficha-tecnica-name").textContent = "";
        document.getElementById("archivo-hoja-vida-name").textContent = "";
        proveedorPicker?.setText("");
        setupProgramadoToggle(form);
    }

    const proveedorPicker = createProveedorPicker({
        container: document.getElementById("proveedor-picker"),
        soloServicios: true,
        getQuery: () =>
            [form.titulo.value, descripcionEditor.getText()].filter(Boolean).join(" "),
    });

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        alertError.classList.remove("show");
        alertSuccess.classList.remove("show");

        if (!centroCostoSelect.getValue()) {
            showError("Selecciona un centro de costo de la lista.");
            centroCostoSelect.input.focus();
            return;
        }

        if (!liderSelect.getValue()) {
            showError("Selecciona un líder aprobador de la lista.");
            liderSelect.input.focus();
            return;
        }

        if (!form.reportValidity()) return;

        descripcionEditor.syncHidden();
        observacionesEditor.syncHidden();

        const descripcionTexto = descripcionEditor.getText();
        const descripcionHtml = descripcionEditor.getHtml();
        if (!descripcionTexto && !descripcionHtml) {
            showError("La descripción del servicio es obligatoria.");
            return;
        }

        const servicioProgramado =
            form.querySelector('input[name="servicio_programado"]:checked')?.value === "si";
        const requiereVisita =
            form.querySelector('input[name="requiere_visita"]:checked')?.value === "si";
        const requiereComiteTecnico =
            form.querySelector('input[name="requiere_comite_tecnico"]:checked')?.value === "si";

        const lider = liderSelect.getSelectedItem();
        const formData = new FormData();
        formData.append("titulo", form.titulo.value.trim());
        formData.append("requiere_visita", requiereVisita ? "true" : "false");
        formData.append("requiere_comite_tecnico", requiereComiteTecnico ? "true" : "false");
        formData.append("servicio_programado", servicioProgramado ? "true" : "false");
        if (servicioProgramado) {
            formData.append("fecha_servicio_programado", form.fecha_servicio_programado.value);
        }
        formData.append("descripcion_servicio", descripcionHtml);
        formData.append("descripcion_servicio_texto", descripcionTexto);
        formData.append("proveedor_sugerido", proveedorPicker.serialize());
        formData.append("centro_costo_area", form.centro_costo_area.value);
        formData.append("lider_area_id", form.lider_area_id.value);
        formData.append("lider_area_label", lider?.label || "");
        formData.append("observaciones", observacionesEditor.getHtml());
        formData.append("observaciones_texto", observacionesEditor.getText());

        for (const file of descripcionControl.getFiles()) {
            formData.append("archivos_detalle", file);
        }
        for (const file of observacionControl.getFiles()) {
            formData.append("archivos", file);
        }

        const ficha = document.getElementById("archivo-ficha-tecnica")?.files?.[0];
        if (ficha) formData.append("archivo_ficha_tecnica", ficha);

        const hoja = document.getElementById("archivo-hoja-vida")?.files?.[0];
        if (hoja) formData.append("archivo_hoja_vida", hoja);

        submitBtn.disabled = true;
        submitBtn.textContent = "Enviando...";

        try {
            const data = await api.postForm("/solicitudes-gestion/servicios", formData);
            showSuccess(
                `Solicitud de servicios registrada con código ${data.codigo}. ` +
                    "Estado inicial: Solicitud. Puedes consultar el flujo en Mis solicitudes."
            );
            resetForm();
        } catch (err) {
            const msg =
                err instanceof ApiError ? err.message : "No se pudo enviar la solicitud.";
            showError(msg);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Enviar Solicitud";
        }
    });

    // -------- Borradores locales con etiqueta (localStorage) --------
    // Guarda varios borradores, cada uno con un nombre/etiqueta. No incluye archivos:
    // el navegador no permite volver a cargar un <input file> por código; se avisa que
    // deben re-adjuntarse. ponytail: borradores por navegador; si se quiere
    // multi-dispositivo, migrar a borrador en el servidor.
    const DRAFT_KEY = "srv_borradores_v1";

    function collectDraft() {
        return {
            titulo: form.titulo.value,
            requiere_visita: form.querySelector('input[name="requiere_visita"]:checked')?.value || "",
            requiere_comite_tecnico:
                form.querySelector('input[name="requiere_comite_tecnico"]:checked')?.value || "",
            servicio_programado:
                form.querySelector('input[name="servicio_programado"]:checked')?.value || "",
            fecha_servicio_programado: form.fecha_servicio_programado?.value || "",
            centro_costo_area: centroCostoSelect.getValue(),
            centro_costo_label: centroCostoSelect.getSelectedItem()?.label || "",
            lider_area_id: liderSelect.getValue(),
            lider_area_label: liderSelect.getSelectedItem()?.label || "",
            proveedor_sugerido: proveedorPicker.serialize(),
            descripcion_servicio: descripcionEditor.getHtml(),
            observaciones: observacionesEditor.getHtml(),
        };
    }

    function draftVacio(d) {
        return !(
            d.titulo ||
            d.centro_costo_area ||
            d.lider_area_id ||
            d.proveedor_sugerido ||
            d.descripcion_servicio ||
            d.observaciones ||
            d.fecha_servicio_programado
        );
    }

    function loadDrafts() {
        try {
            const raw = localStorage.getItem(DRAFT_KEY);
            const list = raw ? JSON.parse(raw) : [];
            return Array.isArray(list) ? list : [];
        } catch {
            return [];
        }
    }

    function saveDrafts(list) {
        localStorage.setItem(DRAFT_KEY, JSON.stringify(list));
    }

    function setRadio(name, value) {
        if (!value) return;
        const el = form.querySelector(`input[name="${name}"][value="${value}"]`);
        if (el) el.checked = true;
    }

    function setSelect(select, id, label) {
        if (!id) return;
        if (typeof select.setValue === "function") {
            select.setValue(id);
        } else {
            // Fallback si el componente en caché aún no expone setValue.
            select.hiddenInput.value = id;
            select.input.value = label || id;
        }
    }

    function applyDraft(d) {
        if (d.titulo) form.titulo.value = d.titulo;
        setRadio("requiere_visita", d.requiere_visita);
        setRadio("requiere_comite_tecnico", d.requiere_comite_tecnico);
        setRadio("servicio_programado", d.servicio_programado);
        if (d.fecha_servicio_programado && form.fecha_servicio_programado) {
            form.fecha_servicio_programado.value = d.fecha_servicio_programado;
        }
        // Recalcula la visibilidad de la fecha según "servicio programado".
        form.querySelector('input[name="servicio_programado"]:checked')
            ?.dispatchEvent(new Event("change", { bubbles: true }));
        setSelect(centroCostoSelect, d.centro_costo_area, d.centro_costo_label);
        setSelect(liderSelect, d.lider_area_id, d.lider_area_label);
        if (d.proveedor_sugerido) {
            proveedorPicker.setText(d.proveedor_sugerido);
        }
        if (d.descripcion_servicio) descripcionEditor.setHtml(d.descripcion_servicio);
        if (d.observaciones) observacionesEditor.setHtml(d.observaciones);
    }

    document.getElementById("btn-guardar-borrador")?.addEventListener("click", () => {
        descripcionEditor.syncHidden();
        observacionesEditor.syncHidden();
        const d = collectDraft();
        if (draftVacio(d)) {
            showError("No hay información para guardar todavía.");
            return;
        }
        const etiqueta = (prompt("Ponle un nombre o etiqueta a este borrador:", d.titulo || "") || "").trim();
        if (!etiqueta) return;
        const list = loadDrafts();
        const existente = list.find((b) => b.etiqueta.toLowerCase() === etiqueta.toLowerCase());
        if (existente) {
            if (!confirm(`Ya existe un borrador "${existente.etiqueta}". ¿Reemplazarlo?`)) return;
            Object.assign(existente, { datos: d, _ts: Date.now() });
        } else {
            list.push({ id: String(Date.now()), etiqueta, datos: d, _ts: Date.now() });
        }
        saveDrafts(list);
        showSuccess(`Borrador "${etiqueta}" guardado en este navegador. Los archivos no se guardan.`);
    });

    document.getElementById("btn-cargar-borrador")?.addEventListener("click", abrirModalBorradores);

    function abrirModalBorradores() {
        document.getElementById("srv-draft-modal")?.remove();
        const MAX_SIN_BUSQUEDA = 8;

        const overlay = document.createElement("div");
        overlay.id = "srv-draft-modal";
        overlay.style.cssText =
            "position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;" +
            "align-items:center;justify-content:center;z-index:1000;padding:16px;";

        const panel = document.createElement("div");
        panel.style.cssText =
            "background:#fff;border-radius:12px;max-width:520px;width:100%;max-height:80vh;" +
            "overflow:auto;padding:20px;box-shadow:0 10px 40px rgba(0,0,0,.2);";
        panel.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <h3 style="margin:0;">Borradores guardados</h3>
                <button type="button" class="btn btn-sm btn-secondary" data-accion="cerrar">Cerrar</button>
            </div>
            <input type="text" id="srv-draft-search" placeholder="Busca por nombre… (ej. mouse)" autocomplete="off"
                style="width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:12px;font-size:.95rem;box-sizing:border-box;" />
            <div id="srv-draft-list"></div>
        `;
        overlay.appendChild(panel);
        document.body.appendChild(overlay);

        const searchEl = panel.querySelector("#srv-draft-search");
        const listEl = panel.querySelector("#srv-draft-list");

        function renderList(query) {
            const q = (query || "").trim().toLowerCase();
            const all = loadDrafts().sort((a, b) => (b._ts || 0) - (a._ts || 0));
            if (!all.length) {
                listEl.innerHTML =
                    '<p style="color:#64748b;margin:8px 0 0;">No hay borradores guardados en este navegador.</p>';
                return;
            }
            let filtrados = q ? all.filter((b) => b.etiqueta.toLowerCase().includes(q)) : all;
            if (!filtrados.length) {
                listEl.innerHTML =
                    '<p style="color:#64748b;margin:8px 0 0;">Ningún borrador coincide con la búsqueda.</p>';
                return;
            }
            const limitado = !q && filtrados.length > MAX_SIN_BUSQUEDA;
            if (limitado) filtrados = filtrados.slice(0, MAX_SIN_BUSQUEDA);
            listEl.innerHTML =
                filtrados
                    .map(
                        (b) => `
                <div class="srv-draft-row" data-id="${b.id}"
                    style="display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:8px;">
                    <div style="flex:1;min-width:0;">
                        <div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeAttr(b.etiqueta)}</div>
                        <div style="color:#64748b;font-size:.85rem;">${b._ts ? new Date(b._ts).toLocaleString() : ""}</div>
                    </div>
                    <button type="button" class="btn btn-sm btn-primary" data-accion="cargar" data-id="${b.id}">Cargar</button>
                    <button type="button" class="btn btn-sm btn-secondary" data-accion="eliminar" data-id="${b.id}">Eliminar</button>
                </div>`
                    )
                    .join("") +
                (limitado
                    ? `<p style="color:#94a3b8;font-size:.85rem;margin:4px 0 0;">Mostrando los ${MAX_SIN_BUSQUEDA} más recientes. Escribe para buscar el resto.</p>`
                    : "");
        }

        searchEl.addEventListener("input", () => renderList(searchEl.value));
        renderList("");
        searchEl.focus();

        overlay.addEventListener("click", (e) => {
            const t = e.target;
            if (t === overlay || t.dataset?.accion === "cerrar") {
                overlay.remove();
                return;
            }
            const accion = t.dataset?.accion;
            const id = t.dataset?.id;
            if (!accion || !id) return;
            const drafts = loadDrafts();
            const b = drafts.find((x) => x.id === id);
            if (!b) return;
            if (accion === "cargar") {
                applyDraft(b.datos);
                overlay.remove();
                showSuccess(`Borrador "${b.etiqueta}" cargado. Recuerda volver a adjuntar los archivos.`);
            } else if (accion === "eliminar") {
                if (!confirm(`¿Eliminar el borrador "${b.etiqueta}"?`)) return;
                saveDrafts(drafts.filter((x) => x.id !== id));
                renderList(searchEl.value);
            }
        });
    }
}

function escapeAttr(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
