// Helpers de formato.

const MONEDA_SYMBOL = { COP: "$", USD: "US$", EUR: "€" };
const UNIDAD_LABEL = {
    dias: "días hábiles",
    dias_calendario: "días calendario",
    meses: "meses",
    anios: "años",
};

export function formatMoney(amount, moneda) {
    const symbol = MONEDA_SYMBOL[moneda] || "";
    const num = Number(amount).toLocaleString("es-CO", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    });
    return `${symbol} ${num}`;
}

function _fmtEscala(n) {
    return n.toLocaleString("es-CO", {
        maximumFractionDigits: 2,
        minimumFractionDigits: 0,
    });
}

/** Escala en vivo: mil / millones / billones (billón = 1.000 millones). */
export function etiquetaEscalaMonto(amount) {
    const n = Number(amount);
    if (!Number.isFinite(n) || n <= 0) return "";
    if (n >= 1_000_000_000) {
        const v = n / 1_000_000_000;
        return `${_fmtEscala(v)} ${Math.abs(v - 1) < 1e-9 ? "billón" : "billones"}`;
    }
    if (n >= 1_000_000) {
        const v = n / 1_000_000;
        return `${_fmtEscala(v)} ${Math.abs(v - 1) < 1e-9 ? "millón" : "millones"}`;
    }
    if (n >= 1_000) {
        return `${_fmtEscala(n / 1_000)} mil`;
    }
    return _fmtEscala(n);
}

const MONEDA_NOMBRE = { COP: "pesos", USD: "dólares", EUR: "euros" };

export function previewValorCotizacion(amount, moneda = "COP") {
    const n = Number(amount);
    if (!Number.isFinite(n) || n <= 0) return "";
    const code = MONEDA_SYMBOL[moneda] ? moneda : "COP";
    const escala = etiquetaEscalaMonto(n);
    const nombre = MONEDA_NOMBRE[code] || code;
    return `${formatMoney(n, code)}  ·  ${escala} ${nombre}`;
}

export function formatValorTramiteOc(amount) {
    if (amount === null || amount === undefined || amount === "") return "—";
    const num = Number(amount);
    if (Number.isNaN(num)) return "—";
    return num.toLocaleString("es-CO", {
        style: "currency",
        currency: "COP",
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
    });
}

export function formatPlazo(cantidad, unidad) {
    return `${cantidad} ${UNIDAD_LABEL[unidad] || unidad}`;
}

export function formatDate(iso) {
    if (!iso) return "";
    const value = String(iso);
    const dateOnly = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:T00:00:00(?:\.000)?(?:Z)?)?$/);
    if (dateOnly) {
        const [, year, month, day] = dateOnly.map(Number);
        return new Date(year, month - 1, day).toLocaleDateString("es-CO", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        });
    }
    const d = new Date(iso);
    return d.toLocaleString("es-CO", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

/** Fecha calendario sin hora (evita desfase UTC en valores YYYY-MM-DD). */
export function formatDateOnly(iso) {
    if (!iso) return "";
    const raw = String(iso).trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (match) {
        const [, year, month, day] = match;
        const d = new Date(Number(year), Number(month) - 1, Number(day));
        return d.toLocaleDateString("es-CO", {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
        });
    }
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) return "";
    return d.toLocaleDateString("es-CO", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    });
}

export function formatFileSize(bytes) {
    const n = Number(bytes);
    if (!n) return "—";
    if (n < 1024) return `${n} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatCantidad(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    if (Number.isInteger(n)) return String(n);
    return n.toLocaleString("es-CO", { maximumFractionDigits: 4 });
}

export function escapeHtml(str) {
    return String(str ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
