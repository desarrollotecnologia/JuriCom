// Gestión local de sesión: token + datos del usuario.

const TOKEN_KEY = "juridica.access_token";
const USER_KEY = "juridica.user";

export const session = {
    setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    },
    getToken() {
        return localStorage.getItem(TOKEN_KEY);
    },
    setUser(user) {
        localStorage.setItem(USER_KEY, JSON.stringify(user));
    },
    getUser() {
        const raw = localStorage.getItem(USER_KEY);
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch {
            return null;
        }
    },
    clear() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    },
    isAuthenticated() {
        return Boolean(this.getToken());
    },
    requireAuth(redirectTo = "/app/login.html") {
        if (!this.isAuthenticated()) {
            window.location.href = redirectTo;
            return false;
        }
        return true;
    },
    getRoles() {
        const user = this.getUser();
        if (!user) return [];
        return user.roles?.length ? user.roles : [user.role];
    },
    hasRole(...roles) {
        const mine = this.getRoles();
        return roles.some((r) => mine.includes(r));
    },
    requireRole(roles, redirectTo = "/app/dashboard.html") {
        if (!this.hasRole(...roles)) {
            window.location.href = redirectTo;
            return false;
        }
        return true;
    },
};
