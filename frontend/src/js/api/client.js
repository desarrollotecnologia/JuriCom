// Cliente HTTP minimalista para la API.
// Inyecta el token JWT, maneja errores y devuelve JSON.

import { API_BASE } from "../utils/config.js";
import { session } from "../auth/session.js";

async function request(path, { method = "GET", body, isFormData = false } = {}) {
    const headers = {};
    const token = session.getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!isFormData && body !== undefined) headers["Content-Type"] = "application/json";

    const response = await fetch(`${API_BASE}${path}`, {
        method,
        headers,
        body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    });

    if (response.status === 401) {
        session.clear();
        if (!window.location.pathname.endsWith("/login.html")) {
            window.location.href = "/app/login.html";
        }
        throw new ApiError("Sesión expirada. Inicia sesión nuevamente.", 401);
    }

    if (response.status === 204) return null;

    let payload = null;
    try {
        payload = await response.json();
    } catch {
        /* respuesta sin JSON */
    }

    if (!response.ok) {
        const message = formatApiError(payload, response.status);
        throw new ApiError(message, response.status, payload);
    }
    return payload;
}

function formatApiError(payload, status) {
    const detail = payload?.detail;
    if (typeof detail === "string" && detail.trim()) return detail;
    if (Array.isArray(detail)) {
        return detail
            .map((item) => item?.msg || item?.message)
            .filter(Boolean)
            .join(". ");
    }
    return `Error ${status}`;
}

export class ApiError extends Error {
    constructor(message, status, payload = null) {
        super(message);
        this.status = status;
        this.payload = payload;
    }
}

export const api = {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: "POST", body }),
    put: (path, body) => request(path, { method: "PUT", body }),
    delete: (path) => request(path, { method: "DELETE" }),
    postForm: (path, formData) =>
        request(path, { method: "POST", body: formData, isFormData: true }),
};
