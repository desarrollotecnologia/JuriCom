import {
    AREAS_CONSUMO,
    CENTROS_COSTO,
    LIDERES_AREA,
    buildSelectOptions,
} from "./mock-catalogos.js";
import { api, ApiError } from "../api/client.js";
import { createObservacionConAdjuntos } from "../components/observacion-editor.js";
import { createSearchableSelect } from "../components/searchable-select.js";

const TRASH_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>`;

export function initSalidasAlmacenForm() {
    const form = document.getElementById("form-salidas-almacen");
    if (!form) return;

    const tbody = document.getElementById("salidas-tbody");
    const btnAdd = document.getElementById("btn-agregar-item-salida");
    const alertError = document.getElementById("alert-error");
    const alertSuccess = document.getElementById("alert-success");
    const submitBtn = document.getElementById("btn-submit");
    const selectCentroCosto = document.getElementById("centro-costo-area");

    const observacionControl = createObservacionConAdjuntos({
        editorContainerId: "observaciones-editor",
        fileInputId: "file-input",
        fileListId: "file-list",
        name: "observaciones",
        placeholder: "Información adicional relevante para la salida de almacén...",
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
                <input
                    type="text"
                    class="input-table"
                    name="codigo_siimed_${rowId}"
                    placeholder="Ej. 100234"
                    inputmode="numeric"
                />
            </td>
            <td class="cell-descripcion">
                <textarea
                    class="input-table input-table-autogrow"
                    name="descripcion_${rowId}"
                    placeholder="Descripción del producto"
                    rows="1"
                    required
                ></textarea>
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
            <td>
                <select class="input-table" name="area_consumo_${rowId}" required>
                    ${buildSelectOptions(AREAS_CONSUMO, "Área consumo")}
                </select>
            </td>
            <td>
                <select class="input-table" name="centro_costo_${rowId}" required>
                    ${buildSelectOptions(CENTROS_COSTO, "Centro de costo")}
                </select>
            </td>
            <td class="table-actions cell-accion">
                <button
                    type="button"
                    class="btn btn-icon-danger btn-remove-row"
                    title="Eliminar fila"
                    aria-label="Eliminar ítem"
                >
                    ${TRASH_ICON}
                </button>
            </td>
        `;
        tr.querySelector(".btn-remove-row").addEventListener("click", () => removeRow(tr));
        const desc = tr.querySelector("textarea[name^='descripcion_']");
        if (desc) setupAutoGrowTextarea(desc);
        tbody.appendChild(tr);
        updateRemoveButtons();
    }

    function removeRow(tr) {
        if (tbody.querySelectorAll("tr").length <= 1) {
            showError("Debe existir al menos un ítem en el detalle de la salida.");
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
                btn.title = disable ? "Debe quedar al menos un ítem" : "Eliminar fila";
            }
        });
    }

    function collectItems() {
        const items = [];
        const rows = tbody.querySelectorAll("tr");
        for (const row of rows) {
            const codigo = row.querySelector('input[name^="codigo_siimed_"]')?.value.trim() || "";
            const descripcion = row.querySelector('textarea[name^="descripcion_"]')?.value.trim() || "";
            const cantidadRaw = row.querySelector('input[name^="cantidad_"]')?.value ?? "1";
            const areaConsumo = row.querySelector('select[name^="area_consumo_"]')?.value || "";
            const centroCosto = row.querySelector('select[name^="centro_costo_"]')?.value || "";

            if (!descripcion && !codigo && !areaConsumo && !centroCosto) continue;

            items.push({
                codigo_siimed: codigo,
                descripcion,
                cantidad: cantidadRaw,
                area_consumo: areaConsumo,
                centro_costo: centroCosto,
            });
        }
        return items;
    }

    function validateItems(items) {
        if (!items.length) {
            showError("Agrega al menos un ítem con descripción.");
            return false;
        }
        for (let i = 0; i < items.length; i += 1) {
            const item = items[i];
            if (!item.descripcion) {
                showError(`La fila ${i + 1} requiere descripción.`);
                return false;
            }
            if (!item.area_consumo) {
                showError(`La fila ${i + 1} requiere área de consumo.`);
                return false;
            }
            if (!item.centro_costo) {
                showError(`La fila ${i + 1} requiere centro de costo.`);
                return false;
            }
            const cantidad = Number(item.cantidad);
            if (!Number.isFinite(cantidad) || cantidad <= 0) {
                showError(`La fila ${i + 1} requiere una cantidad mayor a cero.`);
                return false;
            }
        }
        return true;
    }

    function resetForm() {
        form.reset();
        liderSelect.clear();
        observacionControl.clearAll();
        tbody.innerHTML = "";
        createItemRow();
    }

    btnAdd.addEventListener("click", createItemRow);

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

        const items = collectItems();
        if (!validateItems(items)) return;

        observacionesEditor.syncHidden();
        const lider = liderSelect.getSelectedItem();
        const formData = new FormData();
        formData.append("titulo", form.titulo.value.trim());
        formData.append("centro_costo_area", form.centro_costo_area.value);
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
            const data = await api.postForm("/solicitudes-gestion/salidas-almacen", formData);
            showSuccess(
                `Salida de almacén registrada con código ${data.codigo}. ` +
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

    createItemRow();
}

function setupAutoGrowTextarea(textarea) {
    const resize = () => {
        textarea.style.height = "auto";
        textarea.style.height = `${textarea.scrollHeight}px`;
    };
    textarea.addEventListener("input", resize);
    resize();
}
