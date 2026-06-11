// Renderiza la barra lateral con navegación según rol.



import { session } from "../auth/session.js";



const ROLE_LABEL = {

    admin: "Administrador",

    juridica: "Jurídica",

    compras: "Compras",

};



const NAV_BY_ROLE = {

    admin: [

        { href: "/app/dashboard.html", label: "Inicio" },

        { href: "/app/admin/usuarios.html", label: "Gestión de usuarios" },

        { href: "/app/compras/solicitud-radicar.html", label: "Radicar solicitud" },

        { href: "/app/juridica/pendientes.html", label: "Pendientes Jurídica" },

        { href: "/app/juridica/otrosies-pendientes.html", label: "Otrosíes pendientes" },

        { href: "/app/juridica/editar-contrato.html", label: "Edición contrato" },

        { href: "/app/compras/mis-solicitudes.html", label: "Contratos" },

    ],

    juridica: [

        { href: "/app/dashboard.html", label: "Inicio" },

        { href: "/app/juridica/pendientes.html", label: "Pendientes" },

        { href: "/app/juridica/otrosies-pendientes.html", label: "Otrosíes pendientes" },

        { href: "/app/juridica/editar-contrato.html", label: "Edición contrato" },

        { href: "/app/compras/mis-solicitudes.html", label: "Contratos" },

    ],

    compras: [

        { href: "/app/compras/solicitud-radicar.html", label: "Radicar solicitud" },

        { href: "/app/compras/mis-solicitudes.html", label: "Mis solicitudes" },

    ],

};



export function renderSidebar(containerId = "sidebar") {

    const user = session.getUser();

    if (!user) return;



    const container = document.getElementById(containerId);

    if (!container) return;



    const navItems = (NAV_BY_ROLE[user.role] || [])

        .map((item) => {

            const active = window.location.pathname === item.href ? "active" : "";

            return `<a href="${item.href}" class="${active}">${item.label}</a>`;

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

}



function escapeHtml(str) {

    return String(str)

        .replace(/&/g, "&amp;")

        .replace(/</g, "&lt;")

        .replace(/>/g, "&gt;")

        .replace(/"/g, "&quot;");

}


