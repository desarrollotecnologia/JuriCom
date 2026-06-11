import { api } from "../api/client.js";

const BUZON_SVG = `
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
        <path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8l7 5 7-5v11zm0-13l-7 5-7-5h14z"/>
    </svg>
`;

export function renderBuzonBtn(containerId = "buzon-btn-slot") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const active = window.location.pathname === "/app/buzon.html" ? "active" : "";

    container.innerHTML = `
        <a
            href="/app/buzon.html"
            class="btn btn-secondary buzon-icon-btn ${active}"
            id="buzon-icon-btn"
            title="Buzón de pendientes"
            aria-label="Buzón de pendientes"
        >
            ${BUZON_SVG}
            <span class="buzon-badge" id="buzon-badge"></span>
        </a>
    `;

    loadBuzonBadge();
}

async function loadBuzonBadge() {
    const badge = document.getElementById("buzon-badge");
    const btn = document.getElementById("buzon-icon-btn");
    if (!badge || !btn) return;

    try {
        const data = await api.get("/tareas/buzon");
        if (data.total > 0) {
            badge.textContent = data.total > 99 ? "99+" : String(data.total);
            badge.classList.add("show");
            btn.classList.add("has-pending");
            if (data.alta_prioridad > 0) btn.classList.add("has-urgent");
            btn.title =
                data.total === 1
                    ? "1 pendiente en el buzón"
                    : `${data.total} pendientes en el buzón`;
        }
    } catch {
        /* sin badge si falla la API */
    }
}
