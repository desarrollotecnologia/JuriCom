/**
 * Select con búsqueda: escribe y filtra las opciones al vuelo.
 */

/**
 * @param {{
 *   containerId: string,
 *   name: string,
 *   items: { id: string, label: string }[],
 *   placeholder?: string,
 *   required?: boolean,
 *   inputId?: string,
 *   emptyMessage?: string,
 * }} options
 */
export function createSearchableSelect({
    containerId,
    name,
    items,
    placeholder = "Escribe para buscar...",
    required = false,
    inputId = null,
    emptyMessage = "No hay coincidencias.",
}) {
    const container = document.getElementById(containerId);
    if (!container) {
        throw new Error(`No se encontró el contenedor #${containerId}`);
    }

    const uid = containerId.replace(/[^a-zA-Z0-9]/g, "-");
    const listId = `${uid}-list`;
    const inputIdFinal = inputId || `${uid}-input`;

    container.innerHTML = `
        <div class="searchable-select" data-searchable-select>
            <input
                type="text"
                id="${inputIdFinal}"
                class="searchable-select-input"
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

    function openList() {
        list.hidden = false;
        input.setAttribute("aria-expanded", "true");
        root.classList.add("is-open");
    }

    function closeList() {
        list.hidden = true;
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
            options[activeIndex]?.scrollIntoView({ block: "nearest" });
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeIndex = Math.max(activeIndex - 1, 0);
            renderList(filterItems(input.value));
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
        if (!root.contains(e.target)) closeList();
    });

    function getValue() {
        return hidden.value;
    }

    function getSelectedItem() {
        return selectedItem;
    }

    function clear() {
        input.value = "";
        clearSelection();
        closeList();
    }

    return { getValue, getSelectedItem, clear, hiddenInput: hidden, input };
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
