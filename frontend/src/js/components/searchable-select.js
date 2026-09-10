/**
 * Select con búsqueda: escribe y filtra las opciones al vuelo.
 */

/**
 * @param {{
 *   containerId?: string,
 *   container?: HTMLElement,
 *   name: string,
 *   items: { id: string, label: string }[],
 *   placeholder?: string,
 *   required?: boolean,
 *   inputId?: string,
 *   inputClass?: string,
 *   emptyMessage?: string,
 * }} options
 */
export function createSearchableSelect({
    containerId = null,
    container: containerEl = null,
    name,
    items,
    placeholder = "Escribe para buscar...",
    required = false,
    inputId = null,
    inputClass = "searchable-select-input",
    emptyMessage = "No hay coincidencias.",
}) {
    const container =
        containerEl || (containerId ? document.getElementById(containerId) : null);
    if (!container) {
        throw new Error(
            containerId
                ? `No se encontró el contenedor #${containerId}`
                : "No se encontró el contenedor del searchable-select"
        );
    }

    const uid = String(containerId || container.id || name || "searchable")
        .replace(/[^a-zA-Z0-9]+/g, "-");
    const listId = `${uid}-list`;
    const inputIdFinal = inputId || `${uid}-input`;
    const classes = ["searchable-select-input", inputClass]
        .filter(Boolean)
        .filter((c, i, arr) => arr.indexOf(c) === i)
        .join(" ");

    container.innerHTML = `
        <div class="searchable-select" data-searchable-select>
            <input
                type="text"
                id="${inputIdFinal}"
                class="${escapeAttr(classes)}"
                placeholder="${escapeAttr(placeholder)}"
                autocomplete="off"
                role="combobox"
                aria-expanded="false"
                aria-controls="${listId}"
                aria-autocomplete="list"
            />
            <input type="hidden" name="${escapeAttr(name)}" value="" ${required ? "required" : ""} />
            <ul
                id="${listId}"
                class="searchable-select-list"
                role="listbox"
                hidden
            ></ul>
        </div>
    `;

    const root = container.querySelector("[data-searchable-select]");
    const input = container.querySelector(".searchable-select-input");
    const hidden = container.querySelector(`input[name="${name}"]`);
    const list = container.querySelector(".searchable-select-list");

    let selectedItem = null;
    let activeIndex = -1;

    function normalize(str) {
        return String(str)
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "");
    }

    function filterItems(query) {
        const q = normalize(query.trim());
        if (!q) return items;
        return items.filter((item) => normalize(item.label).includes(q));
    }

    function positionList() {
        const rect = input.getBoundingClientRect();
        const minWidth = Math.max(rect.width, 180);
        const maxHeight = Math.min(260, Math.max(140, window.innerHeight - 24));
        const spaceBelow = window.innerHeight - rect.bottom - 8;
        const spaceAbove = rect.top - 8;
        const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;

        list.classList.add("is-portal");
        list.style.position = "fixed";
        list.style.left = `${Math.max(8, Math.min(rect.left, window.innerWidth - minWidth - 8))}px`;
        list.style.width = `${minWidth}px`;
        list.style.right = "auto";
        list.style.zIndex = "1200";
        list.style.maxHeight = `${maxHeight}px`;

        if (openUp) {
            list.style.top = "auto";
            list.style.bottom = `${window.innerHeight - rect.top + 2}px`;
            list.style.borderRadius = "var(--radius-md) var(--radius-md) 0 0";
            list.style.borderTop = "1px solid var(--color-primary)";
            list.style.borderBottom = "none";
        } else {
            list.style.top = `${rect.bottom}px`;
            list.style.bottom = "auto";
            list.style.borderRadius = "0 0 var(--radius-md) var(--radius-md)";
            list.style.borderTop = "none";
            list.style.borderBottom = "1px solid var(--color-primary)";
        }
    }

    function openList() {
        if (list.parentElement !== document.body) {
            document.body.appendChild(list);
        }
        list.hidden = false;
        positionList();
        input.setAttribute("aria-expanded", "true");
        root.classList.add("is-open");
    }

    function closeList() {
        list.hidden = true;
        list.classList.remove("is-portal");
        list.style.position = "";
        list.style.left = "";
        list.style.top = "";
        list.style.bottom = "";
        list.style.width = "";
        list.style.right = "";
        list.style.zIndex = "";
        list.style.maxHeight = "";
        list.style.borderRadius = "";
        list.style.borderTop = "";
        list.style.borderBottom = "";
        input.setAttribute("aria-expanded", "false");
        root.classList.remove("is-open");
        activeIndex = -1;
        renderList(filterItems(input.value));
    }

    function selectItem(item) {
        selectedItem = item;
        hidden.value = item.id;
        input.value = item.label;
        closeList();
        hidden.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function clearSelection() {
        selectedItem = null;
        hidden.value = "";
    }

    function renderList(filtered) {
        if (!filtered.length) {
            list.innerHTML = `<li class="searchable-select-empty">${escapeHtml(emptyMessage)}</li>`;
            return;
        }

        list.innerHTML = filtered
            .map(
                (item, index) => `
                <li
                    class="searchable-select-option${selectedItem?.id === item.id ? " is-selected" : ""}${index === activeIndex ? " is-active" : ""}"
                    role="option"
                    data-id="${escapeAttr(item.id)}"
                    data-index="${index}"
                >${escapeHtml(item.label)}</li>`
            )
            .join("");
    }

    function syncList() {
        const filtered = filterItems(input.value);
        renderList(filtered);
        openList();
    }

    input.addEventListener("focus", syncList);

    input.addEventListener("input", () => {
        if (selectedItem && input.value !== selectedItem.label) {
            clearSelection();
        }
        syncList();
    });

    input.addEventListener("keydown", (e) => {
        const options = list.querySelectorAll(".searchable-select-option");
        if (!options.length || list.hidden) {
            if (e.key === "ArrowDown") syncList();
            return;
        }

        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeIndex = Math.min(activeIndex + 1, options.length - 1);
            renderList(filterItems(input.value));
            positionList();
            options[activeIndex]?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            renderList(filterItems(input.value));
            positionList();
            options[activeIndex]?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "Enter" && activeIndex >= 0) {
            e.preventDefault();
            const id = options[activeIndex]?.dataset.id;
            const item = items.find((i) => i.id === id);
            if (item) selectItem(item);
        } else if (e.key === "Escape") {
            closeList();
        }
    });

    list.addEventListener("mousedown", (e) => {
        const option = e.target.closest(".searchable-select-option");
        if (!option?.dataset.id) return;
        e.preventDefault();
        const item = items.find((i) => i.id === option.dataset.id);
        if (item) selectItem(item);
    });

    document.addEventListener("click", (e) => {
        if (!root.contains(e.target) && !list.contains(e.target)) closeList();
    });

    window.addEventListener(
        "scroll",
        () => {
            if (!list.hidden) positionList();
        },
        true
    );
    window.addEventListener("resize", () => {
        if (!list.hidden) positionList();
    });

    function getValue() {
        return hidden.value;
    }

    function setValue(id) {
        const item = items.find((i) => String(i.id) === String(id));
        if (item) selectItem(item);
    }

    function getSelectedItem() {
        return selectedItem;
    }

    function clear() {
        input.value = "";
        clearSelection();
        closeList();
    }

    return { getValue, setValue, getSelectedItem, clear, hiddenInput: hidden, input };
}

function escapeAttr(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;");
}

function escapeHtml(str) {
    return escapeAttr(str);
}
