/** Días hábiles Colombia: lun-vie, sin festivos (Ley Emiliani). */

function pascua(anio) {
    const a = anio % 19;
    const b = Math.floor(anio / 100);
    const c = anio % 100;
    const d = Math.floor(b / 4);
    const e = b % 4;
    const f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3);
    const h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4);
    const k = c % 4;
    const l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const mesDia = h + l - 7 * m + 114;
    const mes = Math.floor(mesDia / 31);
    const dia = (mesDia % 31) + 1;
    return utcDate(anio, mes, dia);
}

function utcDate(y, m, d) {
    return new Date(Date.UTC(y, m - 1, d));
}

function addDays(dt, n) {
    const x = new Date(dt);
    x.setUTCDate(x.getUTCDate() + n);
    return x;
}

function siguienteLunes(dt) {
    const wd = dt.getUTCDay();
    if (wd === 1) return dt;
    const extra = wd === 0 ? 1 : 8 - wd;
    return addDays(dt, extra);
}

function ymd(dt) {
    return dt.toISOString().slice(0, 10);
}

const cacheFestivos = new Map();

function festivosColombia(anio) {
    if (cacheFestivos.has(anio)) return cacheFestivos.get(anio);
    const p = pascua(anio);
    const fijos = [
        utcDate(anio, 1, 1),
        utcDate(anio, 5, 1),
        utcDate(anio, 7, 20),
        utcDate(anio, 8, 7),
        utcDate(anio, 12, 8),
        utcDate(anio, 12, 25),
        addDays(p, -3),
        addDays(p, -2),
    ];
    const trasladables = [
        utcDate(anio, 1, 6),
        utcDate(anio, 3, 19),
        utcDate(anio, 6, 29),
        utcDate(anio, 8, 15),
        utcDate(anio, 10, 12),
        utcDate(anio, 11, 1),
        utcDate(anio, 11, 11),
        addDays(p, 39),
        addDays(p, 60),
        addDays(p, 68),
    ];
    const set = new Set([...fijos.map(ymd), ...trasladables.map((d) => ymd(siguienteLunes(d)))]);
    cacheFestivos.set(anio, set);
    return set;
}

export function esDiaHabil(dt) {
    const wd = dt.getUTCDay();
    if (wd === 0 || wd === 6) return false;
    return !festivosColombia(dt.getUTCFullYear()).has(ymd(dt));
}

export function siguienteDiaHabil(dt) {
    let d = dt;
    while (!esDiaHabil(d)) d = addDays(d, 1);
    return d;
}

export function sumarDiasHabiles(inicio, dias) {
    let d = inicio;
    let restantes = dias;
    while (restantes > 0) {
        d = addDays(d, 1);
        if (esDiaHabil(d)) restantes -= 1;
    }
    return d;
}

export function calcularFechaFin(inicioStr, cantidad, unidad) {
    if (!inicioStr || !cantidad || cantidad < 1) return "";
    const [y, m, d] = inicioStr.split("-").map(Number);
    const inicio = utcDate(y, m, d);
    if (unidad === "dias_calendario") {
        return ymd(addDays(inicio, cantidad));
    }
    if (unidad === "dias") {
        return ymd(sumarDiasHabiles(inicio, cantidad));
    }
    const meses = unidad === "anios" ? cantidad * 12 : cantidad;
    const base = m - 1 + meses;
    const anio = y + Math.floor(base / 12);
    const mes = (base % 12) + 1;
    const ultimoDia = new Date(Date.UTC(anio, mes, 0)).getUTCDate();
    const dia = Math.min(d, ultimoDia);
    return ymd(siguienteDiaHabil(utcDate(anio, mes, dia)));
}
