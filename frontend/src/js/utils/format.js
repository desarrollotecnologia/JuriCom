// Helpers de formato.

const MONEDA_SYMBOL = { COP: "$", USD: "US$", EUR: "€" };
const UNIDAD_LABEL = { dias: "días", meses: "meses", anios: "años" };

export function formatMoney(amount, moneda) {
    const symbol = MONEDA_SYMBOL[moneda] || "";
    const num = Number(amount).toLocaleString("es-CO", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return `${symbol} ${num}`;
}

export function formatPlazo(cantidad, unidad) {
    return `${cantidad} ${UNIDAD_LABEL[unidad] || unidad}`;
}

export function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString("es-CO", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

export function formatFileSize(bytes) {
    const n = Number(bytes);
    if (!n) return "—";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function escapeHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
