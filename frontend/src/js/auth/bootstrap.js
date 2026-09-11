import { api } from "../api/client.js";
import { session } from "./session.js";

/** Restaura el usuario en localStorage si hay token pero falta el objeto user. */
export async function ensureSessionUser() {
    if (!session.isAuthenticated()) {
        window.location.href = "/app/login.html";
        return null;
    }

    let user = session.getUser();
    if (user) return user;

    try {
        user = await api.get("/auth/me");
        session.setUser(user);
        return user;
    } catch {
        session.clear();
        window.location.href = "/app/login.html";
        return null;
    }
}

/** Valida sesión y rol; devuelve el usuario o null si redirige. */
export async function requireSessionRole(roles, redirectTo = "/app/dashboard.html") {
    const user = await ensureSessionUser();
    if (!user) return null;
    // Multi-rol: el rol principal (user.role) más los adicionales (user.roles[]).
    const misRoles = user.roles?.length ? user.roles : [user.role];
    if (!roles.some((r) => misRoles.includes(r))) {
        window.location.href = redirectTo;
        return null;
    }
    return user;
}
