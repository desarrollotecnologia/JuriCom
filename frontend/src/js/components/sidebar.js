// Renderiza la barra lateral con navegación según rol.

import { session } from "../auth/session.js";
import { enhancePageHeaderWithLogo } from "./page-header-brand.js";

const ROLE_LABEL = {
    admin: "Administrador",
    juridica: "Jurídica",
    compras: "Compras",
    solicitante: "Supervisor",
    anticipos: "Anticipos",
    lider_aprobador: "Líder Aprobador",
    proyectos: "Proyectos",
    contabilidad: "Contabilidad",
    tesoreria: "Tesorería",
};

const PANEL_PROYECTOS_HREF = "/app/proyectos/panel-cotizaciones.html";
const PANEL_CONTABILIDAD_HREF = "/app/contabilidad/panel-anticipos.html";
const PANEL_TESORERIA_HREF = "/app/tesoreria/panel-anticipos.html";

const GESTION_COMPRAS_HREF = "/app/compras/gestion-solicitudes.html";
const GESTION_JURIDICA_HREF = "/app/juridica/gestion-juridica.html";
const DASHBOARD_RADICACIONES_HREF = "/app/juridica/dashboard-radicaciones.html";
const TRAZABILIDAD_SRV_HREF = "/app/juridica/trazabilidad-srv.html";
const RADICAR_CONTRATO_HREF = "/app/compras/solicitud-radicar.html";
const NUEVA_SOLICITUD_HREF = "/app/compras/nueva-solicitud.html";
const MIS_SOLICITUDES_GESTION_HREF = "/app/compras/gestion-mis-solicitudes.html";
const GESTION_ANTICIPO_HREF = "/app/compras/gestion-anticipo.html";
const APROBAR_SOLICITUDES_HREF = "/app/compras/gestion-aprobar-solicitudes.html";
const CATALOGO_PROVEEDORES_HREF = "/app/compras/catalogo-proveedores.html";

const GESTION_COMPRAS_PATHS = new Set([
    GESTION_COMPRAS_HREF,
    NUEVA_SOLICITUD_HREF,
    RADICAR_CONTRATO_HREF,
    "/app/compras/solicitud-compra.html",
    "/app/compras/f1-compra.html",
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
    "/app/compras/f1-compra.html",
    "/app/compras/salidas-almacen.html",
    "/app/compras/solicitud-insumos-servicios.html",
    MIS_SOLICITUDES_GESTION_HREF,
]);

const GESTION_ANTICIPOS_PATHS = new Set([
    GESTION_ANTICIPO_HREF,
    "/app/compras/solicitud-compra.html",
    "/app/compras/f1-compra.html",
    MIS_SOLICITUDES_GESTION_HREF,
]);

const GESTION_JURIDICA_PATHS = new Set([
    GESTION_JURIDICA_HREF,
    "/app/juridica/pendientes.html",
    "/app/juridica/otrosies-pendientes.html",
    "/app/juridica/editar-contrato.html",
    TRAZABILIDAD_SRV_HREF,
    "/app/buzon.html",
]);

const NAV_BY_ROLE = {
    admin: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: "/app/admin/usuarios.html", label: "Gestión de usuarios" },
        { href: GESTION_COMPRAS_HREF, label: "Gestión de Solicitudes a Compras" },
        { href: APROBAR_SOLICITUDES_HREF, label: "Aprobar solicitudes" },
        { href: PANEL_PROYECTOS_HREF, label: "Panel de proyectos" },
        { href: GESTION_JURIDICA_HREF, label: "Gestión Jurídica" },
        { href: CATALOGO_PROVEEDORES_HREF, label: "Catálogo de proveedores" },
        { href: PANEL_CONTABILIDAD_HREF, label: "Anticipos · Contabilidad" },
        { href: PANEL_TESORERIA_HREF, label: "Anticipos · Tesorería" },
        { href: "/app/compras/finalizar-contrato.html", label: "Finalizar contrato" },
    ],
    juridica: [
        { href: GESTION_JURIDICA_HREF, label: "Gestión Jurídica" },
        { href: TRAZABILIDAD_SRV_HREF, label: "Trazabilidad SRV" },
        { href: DASHBOARD_RADICACIONES_HREF, label: "Dashboard de radicaciones" },
        { href: RADICAR_CONTRATO_HREF, label: "Radicar contrato" },
    ],
    compras: [
        { href: GESTION_COMPRAS_HREF, label: "Gestión de Solicitudes a Compras" },
        { href: "/app/compras/mis-solicitudes.html", label: "Mis solicitudes" },
        { href: CATALOGO_PROVEEDORES_HREF, label: "Catálogo de proveedores" },
    ],
    solicitante: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: NUEVA_SOLICITUD_HREF, label: "Nueva solicitud" },
        { href: MIS_SOLICITUDES_GESTION_HREF, label: "Mis solicitudes" },
        { href: "/app/compras/finalizar-contrato.html", label: "Finalizar contrato" },
    ],
    anticipos: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: GESTION_ANTICIPO_HREF, label: "Gestión de anticipos" },
        { href: "/app/compras/f1-compra.html", label: "Solicitud de compra" },
        { href: MIS_SOLICITUDES_GESTION_HREF, label: "Mis solicitudes" },
    ],
    lider_aprobador: [
        { href: "/app/dashboard.html", label: "Inicio" },
        { href: APROBAR_SOLICITUDES_HREF, label: "Aprobar solicitudes" },
    ],
    proyectos: [
        { href: PANEL_PROYECTOS_HREF, label: "Panel de cotizaciones" },
        { href: NUEVA_SOLICITUD_HREF, label: "Nueva solicitud" },
        { href: MIS_SOLICITUDES_GESTION_HREF, label: "Mis solicitudes" },
    ],
    contabilidad: [
        { href: PANEL_CONTABILIDAD_HREF, label: "Anticipos por gestionar" },
    ],
    tesoreria: [
        { href: PANEL_TESORERIA_HREF, label: "Anticipos por pagar" },
    ],
};

export function renderSidebar(containerId = "sidebar") {
    const user = session.getUser();
    if (!user) return;

    const container = document.getElementById(containerId);
    if (!container) return;

    const path = window.location.pathname;
    const roles = session.getRoles();
    const seenHrefs = new Set();
    const mergedNav = [];
    roles.forEach((r) => {
        (NAV_BY_ROLE[r] || []).forEach((item) => {
            if (!seenHrefs.has(item.href)) {
                seenHrefs.add(item.href);
                mergedNav.push(item);
            }
        });
    });
    const navItems = mergedNav
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
                item.href === "/app/compras/f1-compra.html" &&
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
                        (roles.includes("juridica") || roles.includes("admin"))))
            ) {
                active = true;
            }
            return `<a href="${item.href}" class="${active ? "active" : ""}">${item.label}</a>`;
        })
        .join("");

    container.innerHTML = `
        <div class="brand">
            <div class="brand-name">JURICOM</div>
            <div class="brand-sub">Colbeef</div>
        </div>
        <nav>${navItems}</nav>
        <div class="user-box">
            <div class="username">${escapeHtml(user.username)}</div>
            <div class="role">${roles.map((r) => ROLE_LABEL[r] || r).join(" · ")}</div>
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
