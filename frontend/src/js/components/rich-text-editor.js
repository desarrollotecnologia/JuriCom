/**
 * Editor de texto enriquecido (estilo redactar correo).
 * Reutilizable en cualquier formulario del proyecto.
 */

const CLIP_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>`;

const IMAGE_ICON = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/></svg>`;

const FORMAT_COMMANDS = [
    { cmd: "bold", label: "B", title: "Negrilla (Ctrl+B)", style: "font-weight:700" },
    { cmd: "italic", label: "I", title: "Cursiva (Ctrl+I)", style: "font-style:italic" },
    { cmd: "underline", label: "U", title: "Subrayado (Ctrl+U)", style: "text-decoration:underline" },
    { cmd: "strikeThrough", label: "S", title: "Tachado", style: "text-decoration:line-through" },
    { type: "sep" },
    { cmd: "insertUnorderedList", label: "•", title: "Lista con viñetas" },
    { cmd: "insertOrderedList", label: "1.", title: "Lista numerada" },
    { type: "sep" },
    { cmd: "justifyLeft", label: "⯇", title: "Alinear izquierda" },
    { cmd: "justifyCenter", label: "☰", title: "Centrar", className: "is-center" },
    { type: "sep" },
    { cmd: "removeFormat", label: "✕", title: "Quitar formato" },
];

/**
 * @param {{
 *   containerId: string,
 *   name?: string,
 *   placeholder?: string,
 *   minHeight?: number,
 *   onAttachFiles?: () => void,
 *   enableInlineImages?: boolean,
 * }} options
 */
export function createRichTextEditor({
    containerId,
    name = "observaciones",
    placeholder = "Escribe aquí...",
    minHeight = 160,
    onAttachFiles = null,
    enableInlineImages = true,
}) {
    const container = document.getElementById(containerId);
    if (!container) {
        throw new Error(`No se encontró el contenedor #${containerId}`);
    }

    const commands = [...FORMAT_COMMANDS];
    const removeIdx = commands.findIndex((c) => c.cmd === "removeFormat");

    if (enableInlineImages) {
        commands.splice(removeIdx, 0, {
            action: "insertImage",
            title: "Insertar imagen en el texto",
            icon: true,
            imageIcon: true,
        });
        commands.splice(removeIdx, 0, { type: "sep" });
    }

    if (onAttachFiles) {
        const idx = commands.findIndex((c) => c.cmd === "removeFormat");
        commands.splice(idx, 0, {
            action: "attach",
            title: "Adjuntar archivos",
            icon: true,
        });
        commands.splice(idx, 0, { type: "sep" });
    }

    const editorId = `${containerId}-body`;
    const hiddenId = `${containerId}-hidden`;
    const imageInputId = `${containerId}-image-input`;

    container.innerHTML = `
        <div class="richtext-editor" data-richtext>
            <div class="richtext-toolbar" role="toolbar" aria-label="Formato de texto">
                ${commands
                    .map((item) => {
                        if (item.type === "sep") {
                            return `<span class="richtext-sep" aria-hidden="true"></span>`;
                        }
                        if (item.action === "attach") {
                            return `<button
                                type="button"
                                class="richtext-btn richtext-btn-icon"
                                data-action="attach"
                                title="${item.title}"
                                aria-label="${item.title}"
                            >${CLIP_ICON}</button>`;
                        }
                        if (item.action === "insertImage") {
                            return `<button
                                type="button"
                                class="richtext-btn richtext-btn-icon"
                                data-action="insertImage"
                                title="${item.title}"
                                aria-label="${item.title}"
                            >${IMAGE_ICON}</button>`;
                        }
                        const cls = item.className ? ` ${item.className}` : "";
                        const style = item.style ? ` style="${item.style}"` : "";
                        return `<button
                            type="button"
                            class="richtext-btn${cls}"
                            data-cmd="${item.cmd}"
                            title="${item.title}"
                            aria-label="${item.title}"
                        ><span${style}>${item.label}</span></button>`;
                    })
                    .join("")}
            </div>
            <div
                id="${editorId}"
                class="richtext-body"
                contenteditable="true"
                role="textbox"
                aria-multiline="true"
                data-placeholder="${escapeAttr(placeholder)}"
                style="min-height:${minHeight}px"
            ></div>
            <input type="hidden" id="${hiddenId}" name="${escapeAttr(name)}" />
            ${
                enableInlineImages
                    ? `<input type="file" id="${imageInputId}" accept="image/png,image/jpeg,image/gif,image/webp" hidden />`
                    : ""
            }
        </div>
    `;

    const root = container.querySelector(".richtext-editor");
    const body = container.querySelector(`#${editorId}`);
    const hidden = container.querySelector(`#${hiddenId}`);
    const toolbar = container.querySelector(".richtext-toolbar");
    const imageInput = container.querySelector(`#${imageInputId}`);

    function syncHidden() {
        hidden.value = getHtml();
    }

    function getHtml() {
        const html = body.innerHTML.trim();
        if (!html || html === "<br>") return "";
        return html;
    }

    function getText() {
        return (body.textContent || "").trim();
    }

    function setHtml(html) {
        body.innerHTML = html || "";
        syncHidden();
    }

    function clear() {
        body.innerHTML = "";
        syncHidden();
    }

    function focus() {
        body.focus();
    }

    function exec(cmd, value = null) {
        body.focus();
        document.execCommand(cmd, false, value);
        syncHidden();
    }

    function insertImageDataUrl(dataUrl, alt = "Imagen") {
        body.focus();
        const img = `<img src="${dataUrl}" alt="${escapeAttr(alt)}" class="richtext-inline-image" />`;
        document.execCommand("insertHTML", false, img);
        syncHidden();
    }

    function insertImageFile(file) {
        if (!file?.type?.startsWith("image/")) return;
        const reader = new FileReader();
        reader.onload = () => {
            if (typeof reader.result === "string") {
                insertImageDataUrl(reader.result, file.name);
            }
        };
        reader.readAsDataURL(file);
    }

    toolbar.addEventListener("click", (e) => {
        const btn = e.target.closest(".richtext-btn");
        if (!btn) return;
        e.preventDefault();

        if (btn.dataset.action === "attach") {
            onAttachFiles?.();
            return;
        }

        if (btn.dataset.action === "insertImage") {
            imageInput?.click();
            return;
        }

        exec(btn.dataset.cmd);
    });

    imageInput?.addEventListener("change", () => {
        const file = imageInput.files?.[0];
        if (file) insertImageFile(file);
        imageInput.value = "";
    });

    body.addEventListener("input", syncHidden);
    body.addEventListener("blur", syncHidden);

    body.addEventListener("keydown", (e) => {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === "b") {
                e.preventDefault();
                exec("bold");
            } else if (e.key === "i") {
                e.preventDefault();
                exec("italic");
            } else if (e.key === "u") {
                e.preventDefault();
                exec("underline");
            }
        }
    });

    body.addEventListener("paste", (e) => {
        const items = e.clipboardData?.items;
        if (items && enableInlineImages) {
            for (const item of items) {
                if (item.type.startsWith("image/")) {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) insertImageFile(file);
                    return;
                }
            }
        }

        e.preventDefault();
        const html = e.clipboardData.getData("text/html");
        const limpio = html ? sanitizeClipboardHtml(html) : "";
        if (limpio) {
            document.execCommand("insertHTML", false, limpio);
        } else {
            const text = e.clipboardData.getData("text/plain");
            document.execCommand("insertHTML", false, plainTextToHtml(text));
        }
        syncHidden();
    });

    return { getHtml, getText, setHtml, clear, focus, syncHidden, hiddenInput: hidden, root };
}

function escapeAttr(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;");
}

// Convierte texto plano a HTML conservando saltos de línea/párrafos.
function plainTextToHtml(text) {
    const esc = (s) =>
        String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    return (text || "")
        .replace(/\r\n?/g, "\n")
        .split(/\n{2,}/)
        .map((p) => `<p>${esc(p).replace(/\n/g, "<br>")}</p>`)
        .join("");
}

// Limpia HTML pegado (Word, Google Docs, web): conserva negrita/cursiva/
// subrayado/listas/párrafos y descarta estilos, clases y basura de Office.
const PASTE_KEEP = new Set([
    "B", "STRONG", "I", "EM", "U", "S", "STRIKE", "P", "BR",
    "UL", "OL", "LI", "DIV", "H1", "H2", "H3", "H4", "A",
]);

function sanitizeClipboardHtml(html) {
    const tpl = document.createElement("template");
    tpl.innerHTML = html;
    tpl.content
        .querySelectorAll("style,script,meta,link,title,o\\:p,xml")
        .forEach((n) => n.remove());

    const procesar = (parent) => {
        for (const node of [...parent.childNodes]) {
            if (node.nodeType !== 1) continue;
            procesar(node);
            const st = node.getAttribute("style") || "";
            const wraps = [];
            if (/font-weight\s*:\s*(bold(er)?|[6-9]00)/i.test(st)) wraps.push("b");
            if (/font-style\s*:\s*italic/i.test(st)) wraps.push("i");
            if (/text-decoration[^;]*underline/i.test(st)) wraps.push("u");

            if (PASTE_KEEP.has(node.tagName)) {
                for (const a of [...node.attributes]) {
                    if (!(node.tagName === "A" && a.name === "href")) {
                        node.removeAttribute(a.name);
                    }
                }
                for (const w of wraps) {
                    const e = document.createElement(w);
                    while (node.firstChild) e.appendChild(node.firstChild);
                    node.appendChild(e);
                }
            } else {
                let frag = document.createDocumentFragment();
                while (node.firstChild) frag.appendChild(node.firstChild);
                for (const w of wraps) {
                    const e = document.createElement(w);
                    e.appendChild(frag);
                    frag = document.createDocumentFragment();
                    frag.appendChild(e);
                }
                node.replaceWith(frag);
            }
        }
    };
    procesar(tpl.content);

    return tpl.innerHTML
        .replace(/(&nbsp;|\s)+/g, " ")
        .replace(/<(\w+)>\s*<\/\1>/g, "")
        .trim();
}
