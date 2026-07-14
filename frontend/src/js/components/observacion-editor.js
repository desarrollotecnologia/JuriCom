/**
 * Editor de observaciones con adjuntos (mismo patrón que registro de solicitud).
 */

import { createRichTextEditor } from "./rich-text-editor.js";
import { escapeHtml, formatFileSize } from "../utils/format.js";

export const OBSERVACION_ADJUNTOS_HINT =
    "Usa el clip en la barra del editor para adjuntar archivos (también puedes arrastrarlos sobre el área de texto). " +
    "Usa el botón de imagen para insertar una foto dentro del comentario.";

export const OBSERVACION_ADJUNTOS_ACCEPT =
    ".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.doc,.docx,.webp,.gif";

export const DETALLE_SERVICIO_ADJUNTOS_ACCEPT =
    ".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.doc,.docx,.webp,.gif,.mp4,.mov,.avi,.mkv,.webm,.mp3,.wav";

export const DETALLE_SERVICIO_ADJUNTOS_HINT =
    "Adjunta imágenes, documentos o videos desde el clip o arrastrándolos al editor. " +
    "Usa el botón de imagen para insertar fotos dentro del texto.";

export function renderObservacionAdjuntosFieldHtml({
    editorContainerId,
    fileInputId,
    fileListId,
    label = "Comentario",
    hint = OBSERVACION_ADJUNTOS_HINT,
    showHint = true,
    accept = OBSERVACION_ADJUNTOS_ACCEPT,
} = {}) {
    return `
        <div class="field sg-observacion-field">
            <label for="${escapeHtml(editorContainerId)}">${escapeHtml(label)}</label>
            <div id="${escapeHtml(editorContainerId)}"></div>
            <input
                type="file"
                id="${escapeHtml(fileInputId)}"
                multiple
                hidden
                accept="${escapeHtml(accept)}"
            />
            <ul class="file-list" id="${escapeHtml(fileListId)}" hidden></ul>
            ${showHint ? `<span class="hint">${escapeHtml(hint)}</span>` : ""}
        </div>`;
}

/**
 * @param {{
 *   editorContainerId: string,
 *   fileInputId: string,
 *   fileListId: string,
 *   name?: string,
 *   placeholder?: string,
 *   minHeight?: number,
 *   accept?: string,
 * }} options
 */
export function createObservacionConAdjuntos({
    editorContainerId,
    fileInputId,
    fileListId,
    name = "observacion",
    placeholder = "Escribe tu observación...",
    minHeight = 160,
    accept = OBSERVACION_ADJUNTOS_ACCEPT,
}) {
    const fileInput = document.getElementById(fileInputId);
    const fileListEl = document.getElementById(fileListId);
    const editorHost = document.getElementById(editorContainerId);

    if (fileInput && accept) {
        fileInput.accept = accept;
    }

    if (!editorHost) {
        throw new Error(`No se encontró el contenedor #${editorContainerId}`);
    }

    /** @type {File[]} */
    let archivos = [];

    function renderFileList() {
        if (!fileListEl) return;
        if (!archivos.length) {
            fileListEl.innerHTML = "";
            fileListEl.hidden = true;
            return;
        }
        fileListEl.hidden = false;
        fileListEl.innerHTML = archivos
            .map(
                (file, index) => `
            <li class="file-list-item">
                <span class="file-list-name" title="${escapeHtml(file.name)}">
                    ${escapeHtml(file.name)}
                </span>
                <span class="file-list-size muted">${formatFileSize(file.size)}</span>
                <button
                    type="button"
                    class="btn btn-sm btn-secondary btn-remove-file"
                    data-index="${index}"
                >
                    Quitar
                </button>
            </li>`
            )
            .join("");

        fileListEl.querySelectorAll(".btn-remove-file").forEach((btn) => {
            btn.addEventListener("click", () => {
                const idx = Number(btn.dataset.index);
                archivos.splice(idx, 1);
                renderFileList();
            });
        });
    }

    function addFiles(fileListInput) {
        const incoming = Array.from(fileListInput || []);
        for (const file of incoming) {
            const exists = archivos.some((f) => f.name === file.name && f.size === file.size);
            if (!exists) archivos.push(file);
        }
        renderFileList();
    }

    editorHost.innerHTML = "";

    const editor = createRichTextEditor({
        containerId: editorContainerId,
        name,
        placeholder,
        minHeight,
        enableInlineImages: true,
        onAttachFiles: () => fileInput?.click(),
    });

    const root = editor.root;

    fileInput?.addEventListener("change", () => {
        addFiles(fileInput.files);
        fileInput.value = "";
    });

    if (root) {
        root.addEventListener("dragover", (e) => {
            e.preventDefault();
            root.classList.add("is-dragover");
        });
        root.addEventListener("dragleave", (e) => {
            if (!root.contains(e.relatedTarget)) {
                root.classList.remove("is-dragover");
            }
        });
        root.addEventListener("drop", (e) => {
            e.preventDefault();
            root.classList.remove("is-dragover");
            addFiles(e.dataTransfer.files);
        });
    }

    return {
        editor,
        getFiles: () => [...archivos],
        clearAttachments: () => {
            archivos = [];
            renderFileList();
        },
        clearAll: () => {
            editor.clear();
            archivos = [];
            renderFileList();
        },
        destroy: () => {
            archivos = [];
            if (fileListEl) {
                fileListEl.innerHTML = "";
                fileListEl.hidden = true;
            }
            editorHost.innerHTML = "";
        },
    };
}
