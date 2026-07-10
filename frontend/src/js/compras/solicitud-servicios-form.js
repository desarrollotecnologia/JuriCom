import {
    CENTROS_COSTO,
    LIDERES_AREA,
    buildSelectOptions,
} from "./mock-catalogos.js";
import { api, ApiError } from "../api/client.js";
import {
    createObservacionConAdjuntos,
    DETALLE_SERVICIO_ADJUNTOS_ACCEPT,
    DETALLE_SERVICIO_ADJUNTOS_HINT,
    OBSERVACION_ADJUNTOS_HINT,
} from "../components/observacion-editor.js";
import { createSearchableSelect } from "../components/searchable-select.js";
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
    const selectCentroCosto = document.getElementById("centro-costo-area");

    const descripcionControl = createObservacionConAdjuntos({
        editorContainerId: "descripcion-servicio-editor",
        fileInputId: "descripcion-servicio-files",
        fileListId: "descripcion-servicio-file-list",
        name: "descripcion_servicio",
        placeholder: "Describe el servicio requerido, alcance, ubicación, condiciones, etc.",
        minHeight: 200,
        accept: DETALLE_SERVICIO_ADJUNTOS_ACCEPT,
    });
    const descripcionEditor = descripcionControl.editor;

    const observacionControl = createObservacionConAdjuntos({
        editorContainerId: "observaciones-editor",
        fileInputId: "file-input",
        fileListId: "file-list",
        name: "observaciones",
        placeholder: "Información adicional relevante para la solicitud...",
        minHeight: 180,
    });
    const observacionesEditor = observacionControl.editor;

    selectCentroCosto.innerHTML = buildSelectOptions(
        CENTROS_COSTO,
        "Selecciona el centro de costo"
    );

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
        liderSelect.clear();
        descripcionControl.clearAll();
        observacionControl.clearAll();
        document.getElementById("archivo-ficha-tecnica-name").textContent = "";
        document.getElementById("archivo-hoja-vida-name").textContent = "";
        setupProgramadoToggle(form);
    }

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        alertError.classList.remove("show");
        alertSuccess.classList.remove("show");

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

        const lider = liderSelect.getSelectedItem();
        const formData = new FormData();
        formData.append("titulo", form.titulo.value.trim());
        formData.append("requiere_visita", requiereVisita ? "true" : "false");
        formData.append("servicio_programado", servicioProgramado ? "true" : "false");
        if (servicioProgramado) {
            formData.append("fecha_servicio_programado", form.fecha_servicio_programado.value);
        }
        formData.append("descripcion_servicio", descripcionHtml);
        formData.append("descripcion_servicio_texto", descripcionTexto);
        formData.append("proveedor_sugerido", form.proveedor_sugerido.value.trim());
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
}
