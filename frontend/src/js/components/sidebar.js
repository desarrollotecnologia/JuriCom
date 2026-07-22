// Renderiza la barra lateral con navegación según rol.

import { session } from "../auth/session.js";
import { enhancePageHeaderWithLogo } from "./page-header-brand.js";

const ROLE_LABEL = {
    admin: "Administrador",
    juridica: "Jurídica",
    compras: "Compras",
    solicitante: "Usuario Solicitante",
    anticipos: "Anticipos",
    lider_aprobador: "Líder Aprobador",
};

const GESTION_COMPRAS_HREF = "/app/compras/gestion-solicitudes.html";
const GESTION_JURIDICA_HREF = "/app/juridica/gestion-juridica.html";
const RADICAR_CONTRATO_HREF = "/app/compras/solicitud-radicar.html";
const NUEVA_SOLICITUD_HREF = "/app/compras/nueva-solicitud.html";
const MIS_SOLICITUDES_GESTION_HREF = "/app/compras/gestion-mis-solicitudes.html";
const GESTION_ANTICIPO_HREF = "/app/compras/gestion-anticipo.html";
const APROBAR_SOLICITUDES_HREF = "/app/compras/gestion-aprobar-solicitudes.html";

const GESTION_COMPRAS_PATHS = new Set([
    GESTION_COMPRAS_HREF,
    NUEVA_SOLICITUD_HREF,
    RADICAR_CONTRATO_HREF,
    "/app/compras/solicitud-compra.html",
    "/app/compras/salidas-almacen.html",
    "/app/compras/solicitud-insumos-servicios.html",
    MIS_SOLICITUDES_GESTION_HREF,
    APROBAR_SOLICITUDES_HREF,
    "/app/compras/gestion-panel-solicitudes.html",
    GESTION_ANTICIPO_HREF,
    "/app/compras/reporte-indicadores.html",
]);

const GESTION_SOLICITANTE_PATHS = new Set([
    NUEVA_SOLICITUD_HREF,
    "/app/compras/solicitud-compra.html",
    "/app/compras/salidas-almacen.html",
    "/app/compras/solicitud-insumos-servicios.html",
    MIS_SOLICITUDES_GESTION_HREF,
]);

const GESTION_ANTICIPOS_PATHS = new Set([
    GESTION_ANTICIPO_HREF,
    "/app/compras/solicitud-compra.html",
    MIS_SOLICITUDES_GESTION_HREF,
]);

const GESTION_JURIDICA_PATHS = new Set([
    GESTION_JURIDICA_HREF,
    "/app/juridica/pendientes.html",
    "/app/juridica/otrosies-pendientes.html",
    "/app/juridica/editar-contrato.html",
    "/app/buzon.html",
]);

const NAV_BY_ROLE = {
    admin: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: "/app/admin/usuarios.html", label: "Gestión de usuarios" },
        { href: GESTION_COMPRAS_HREF, label: "Gestión de Solicitudes a Compras" },
        { href: APROBAR_SOLICITUDES_HREF, label: "Aprobar solicitudes" },
        { href: GESTION_JURIDICA_HREF, label: "Gestión Jurídica" },
    ],
    juridica: [
        { href: GESTION_JURIDICA_HREF, label: "Gestión Jurídica" },
        { href: RADICAR_CONTRATO_HREF, label: "Radicar contrato" },
    ],
    compras: [
        { href: GESTION_COMPRAS_HREF, label: "Gestión de Solicitudes a Compras" },
        { href: "/app/compras/mis-solicitudes.html", label: "Mis solicitudes" },
    ],
    solicitante: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: NUEVA_SOLICITUD_HREF, label: "Nueva solicitud" },
        { href: MIS_SOLICITUDES_GESTION_HREF, label: "Mis solicitudes" },
    ],
    anticipos: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: GESTION_ANTICIPO_HREF, label: "Gestión de anticipos" },
        { href: "/app/compras/solicitud-compra.html", label: "Solicitud de compra" },
        { href: MIS_SOLICITUDES_GESTION_HREF, label: "Mis solicitudes" },
    ],
    lider_aprobador: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: APROBAR_SOLICITUDES_HREF, label: "Aprobar solicitudes" },
    ],
};

export function renderSidebar(containerId = "sidebar") {
    const user = session.getUser();
    if (!user) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    const path = window.location.pathname;
    const navItems = (NAV_BY_ROLE[user.role] || [])
        .map((item) => {
            let active = path === item.href;
            if (item.href === GESTION_COMPRAS_HREF && GESTION_COMPRAS_PATHS.has(path)) {
                active = true;
            }
            if (
                item.href === NUEVA_SOLICITUD_HREF &&
                GESTION_SOLICITANTE_PATHS.has(path)
            ) {
                active = true;
            }
            if (
                item.href === GESTION_ANTICIPO_HREF &&
                GESTION_ANTICIPOS_PATHS.has(path)
            ) {
                active = true;
            }
            if (
                item.href === "/app/compras/solicitud-compra.html" &&
                GESTION_ANTICIPOS_PATHS.has(path)
            ) {
                active = true;
            }
            if (
                item.href === MIS_SOLICITUDES_GESTION_HREF &&
                (GESTION_SOLICITANTE_PATHS.has(path) || GESTION_ANTICIPOS_PATHS.has(path))
            ) {
                active = true;
            }
            if (
                item.href === APROBAR_SOLICITUDES_HREF &&
                (GESTION_ANTICIPOS_PATHS.has(path) || path === APROBAR_SOLICITUDES_HREF)
            ) {
                active = true;
            }
            if (
                item.href === GESTION_JURIDICA_HREF &&
                (GESTION_JURIDICA_PATHS.has(path) ||
                    (path === "/app/compras/mis-solicitudes.html" &&
                        (user.role === "juridica" || user.role === "admin")))
            ) {
                active = true;
            }
            return `<a href="${item.href}" class="${active ? "active" : ""}">${item.label}</a>`;
        })
        .join("");

    container.innerHTML = `
        <div class="brand">
            <div class="brand-name">JURICOM_BEEF</div>
            <div class="brand-sub">Colbeef</div>
        </div>
        <nav>${navItems}</nav>
        <div class="user-box">
            <div class="username">${escapeHtml(user.username)}</div>
            <div class="role">${ROLE_LABEL[user.role] || user.role}</div>
            <button class="btn btn-sm logout-btn" id="logout-btn">Cerrar sesión</button>
        </div>
    `;

    document.getElementById("logout-btn").addEventListener("click", () => {
        session.clear();
        window.location.href = "/app/login.html";
    });

    enhancePageHeaderWithLogo();
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}
