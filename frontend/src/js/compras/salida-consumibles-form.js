import { LIDERES_AREA } from "./mock-catalogos.js?v=2";
import { centrosCostosItems } from "../catalogos/centros-costos.js";
import { consumiblesItems } from "../catalogos/consumibles.js";
import { api, ApiError } from "../api/client.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { createSearchableSelect } from "../components/searchable-select.js";

const TRASH_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`;

export function initSalidaConsumiblesForm() {
    const form = document.getElementById("form-salida-consumibles");
    if (!form) return;

    const tbody = document.getElementById("consumibles-tbody");
    const btnAdd = document.getElementById("btn-agregar-consumible");
    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const submitBtn = document.getElementById("btn-submit");
    const prioridadRow = document.getElementById("prioridad-row");

    const CATALOGO = consumiblesItems();

    const observacionControl = createObservacionConAdjuntos({
        editorContainerId: "observaciones-editor",
        fileInputId: "file-input",
        fileListId: "file-list",
        name: "observaciones",
        placeholder: "Información adicional relevante para la salida de consumibles...",
        minHeight: 160,
        autosaveKey: "salida-consumibles-nueva:observaciones",
    });
    const observacionesEditor = observacionControl.editor;

    const centroCostoSelect = createSearchableSelect({
        containerId: "centro-costo-select",
        name: "centro_costo_area",
        items: centrosCostosItems(),
        placeholder: "Escribe código o nombre del centro de costo...",
        required: true,
        inputId: "centro-costo-input",
        emptyMessage: "No se encontró ningún centro de costo con ese texto.",
    });
    // La prioridad solo aplica para centros de costo de mantenimiento.
    centroCostoSelect.hiddenInput.addEventListener("change", () => {
        if (!prioridadRow) return;
        const label = centroCostoSelect.getSelectedItem()?.label || "";
        const esMantenimiento = /mantenimiento/i.test(label);
        prioridadRow.hidden = !esMantenimiento;
        if (!esMantenimiento && form.prioridad) form.prioridad.value = "media";
    });

    const liderSelect = createSearchableSelect({
        containerId: "lider-area-select",
        name: "lider_area_id",
        items: LIDERES_AREA,
        placeholder: "Escribe nombre o cargo del líder...",
        required: true,
        inputId: "lider-area-input",
        emptyMessage: "No se encontró ningún líder con ese texto.",
    });

    let rowCounter = 0;

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

    function createItemRow() {
        rowCounter += 1;
        const rowId = `item-${rowCounter}`;
        const tr = document.createElement("tr");
        tr.dataset.rowId = rowId;
        tr.innerHTML = `
            <td>
                <div class="consumible-search-host" data-consumible-host></div>
            </td>
            <td class="cell-cantidad">
                <input
                    type="number"
                    class="input-table-cantidad"
                    name="cantidad_${rowId}"
                    value="1"
                    min="0.0001"
                    step="any"
                    required
                    aria-label="Cantidad"
                />
            </td>
            <td class="cell-unidad">
                <input
                    type="text"
                    class="input-table"
                    name="unidad_${rowId}"
                    readonly
                    placeholder="—"
                    aria-label="Unidad"
                />
            </td>
            <td class="table-actions cell-accion">
                <button
                    type="button"
                    class="btn btn-icon-danger btn-remove-row"
                    title="Eliminar fila"
                    aria-label="Eliminar consumible"
                >
                    ${TRASH_ICON}
                </button>
            </td>
        `;
        tr.querySelector(".btn-remove-row").addEventListener("click", () => removeRow(tr));

        const host = tr.querySelector("[data-consumible-host]");
        const unidadInput = tr.querySelector('input[name^="unidad_"]');
        const control = createSearchableSelect({
            container: host,
            name: `consumible_${rowId}`,
            items: CATALOGO,
            placeholder: "Buscar por código o nombre...",
            required: true,
            inputClass: "input-table",
            emptyMessage: "No hay consumibles con ese texto.",
        });
        control.hiddenInput.addEventListener("change", () => {
            const item = control.getSelectedItem();
            unidadInput.value = item?.unidad || "";
        });
        tr._consumibleControl = control;

        tbody.appendChild(tr);
        updateRemoveButtons();
    }

    function removeRow(tr) {
        if (tbody.querySelectorAll("tr").length <= 1) {
            showError("Debe existir al menos un consumible.");
            return;
        }
        tr.remove();
        updateRemoveButtons();
    }

    function updateRemoveButtons() {
        const rows = tbody.querySelectorAll("tr");
        const disable = rows.length <= 1;
        rows.forEach((row) => {
            const btn = row.querySelector(".btn-remove-row");
            if (btn) {
                btn.disabled = disable;
                btn.title = disable ? "Debe quedar al menos un consumible" : "Eliminar fila";
            }
        });
    }

    function collectItems() {
        const items = [];
        const rows = tbody.querySelectorAll("tr");
        for (const row of rows) {
            const control = row._consumibleControl;
            const seleccion = control?.getSelectedItem();
            const cantidadRaw = row.querySelector('input[name^="cantidad_"]')?.value ?? "1";
            if (!seleccion) continue;
            items.push({
                codigo_siimed: seleccion.codigo || "",
                descripcion: seleccion.descripcion || "",
                unidad: seleccion.unidad || "",
                cantidad: cantidadRaw,
            });
        }
        return items;
    }

    function validateItems(items) {
        if (!items.length) {
            showError("Agrega al menos un consumible de la lista.");
            return false;
        }
        for (let i = 0; i < items.length; i += 1) {
            const cantidad = Number(items[i].cantidad);
            if (!Number.isFinite(cantidad) || cantidad <= 0) {
                showError(`La fila ${i + 1} requiere una cantidad mayor a cero.`);
                return false;
            }
        }
        return true;
    }

    function resetForm() {
        form.reset();
        centroCostoSelect.clear();
        liderSelect.clear();
        if (prioridadRow) prioridadRow.hidden = true;
        observacionControl.clearAll();
        tbody.innerHTML = "";
        createItemRow();
    }

    btnAdd.addEventListener("click", createItemRow);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        alertError.classList.remove("show");
        alertSuccess.classList.remove("show");

        if (!centroCostoSelect.getValue()) {
            showError("Selecciona tu centro de costo.");
            centroCostoSelect.input.focus();
            return;
        }

        if (!liderSelect.getValue()) {
            showError("Selecciona un líder para notificar.");
            liderSelect.input.focus();
            return;
        }

        if (!form.reportValidity()) return;

        const items = collectItems();
        if (!validateItems(items)) return;

        observacionesEditor.syncHidden();
        const lider = liderSelect.getSelectedItem();
        const formData = new FormData();
        formData.append("titulo", form.titulo.value.trim());
        formData.append("centro_costo_area", form.centro_costo_area.value);
        formData.append("prioridad", form.prioridad?.value || "media");
        formData.append("area_consumo", form.centro_costo_area.value);
        formData.append("lider_area_id", form.lider_area_id.value);
        formData.append("lider_area_label", lider?.label || "");
        formData.append("observaciones", observacionesEditor.getHtml());
        formData.append("observaciones_texto", observacionesEditor.getText());
        formData.append("productos_json", JSON.stringify(items));
        for (const file of observacionControl.getFiles()) {
            formData.append("archivos", file);
        }

        submitBtn.disabled = true;
        submitBtn.textContent = "Enviando...";

        try {
            const data = await api.postForm(
                "/solicitudes-gestion/salida-consumibles",
                formData
            );
            showSuccess(
                `Salida de consumibles registrada con código ${data.codigo}. ` +
                    "Compras la entregará; puedes seguirla en Mis solicitudes."
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

    createItemRow();
}
