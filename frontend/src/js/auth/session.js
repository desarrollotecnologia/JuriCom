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
        }
    },
    requireRole(roles, redirectTo = "/app/dashboard.html") {
        const user = this.getUser();
        if (!user || !roles.includes(user.role)) {
            window.location.href = redirectTo;
        }
    },
};
