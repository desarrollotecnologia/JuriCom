import { session } from "../auth/session.js";
import { api } from "../api/client.js";
import { LIDERES_COLBEEF } from "../catalogos/lideres-colbeef.js";
import { renderObservacionAdjuntosFieldHtml } from "../components/observacion-editor.js";
import { API_BASE } from "../utils/config.js";
import { escapeHtml, formatCantidad, formatDate, formatDateOnly, formatFileSize, formatValorTramiteOc, previewValorCotizacion } from "../utils/format.js?v=2";

export const TIPO_LABEL = {
    compra: "Solicitud de Compra",
    salidas_almacen: "Salidas de Almacén",
    insumos_servicios: "Solicitud de Servicios",
};

export const TIPO_BADGE = {
    compra: "badge-tipo-compra",
    salidas_almacen: "badge-tipo-salidas-almacen",
    insumos_servicios: "badge-tipo-insumos",
};

const LEGACY_ESTADO = {
    registrada: "solicitud",
    aprobada: "primera_aprobacion",
    rechazada: "cancelado",
    aprobacion_lider_area: "solicitud",
    aprobacion_gerencia: "primera_aprobacion",
    proceso_cotizacion: "cotizacion",
    en_proceso: "tramitada_oc",
    pendiente: "tramitada_oc",
    finalizada: "entregado",
};

export const ESTADO_LABEL = {
    solicitud: "Solicitud",
    revision: "En revisión",
    primera_aprobacion: "Primera Aprobación",
    revision_proyectos: "Revisión de solicitud (Proyectos)",
    programacion_visita: "Programar visita",
    cotizacion_proyectos: "Cotización (Proyectos)",
    cotizacion: "Cotización",
    comite: "Comité técnico",
    en_aprobacion: "En Aprobación",
    gestionando_servicio: "Gestionando servicio",
    en_juridica: "En Jurídica",
    solicitando_info: "Solicitando información",
    info_recibida: "Información recibida",
    elaborando_contrato: "Elaborando contrato",
    revision_polizas: "Revisión de pólizas",
    solicitud_firmas: "Solicitud de firmas",
    anticipo_contabilidad: "Anticipo en contabilidad",
    anticipo_tesoreria: "Anticipo en tesorería",
    anticipo_pagado: "Anticipo pagado",
    contrato_activo: "Contrato activo",
    contrato_finalizado: "Contrato finalizado",
    pendiente_evidencia_cierre: "Pendiente evidencia cierre",
    tramitada_oc: "Tramitada OC",
    items_en_camino: "Ítems en camino",
    recepcion_insumos: "Recepción de Insumos",
    tramitando_oc: "Tramitando OC",
    aprobacion_anticipo: "Aprobación anticipo",
    gestion_anticipo: "Gestión anticipo",
    cancelado: "Cancelado",
    entregado: "Entregado",
    entregado_parcial: "Entrega parcial realizada",
    facturada: "Facturada",
    registrada: "Solicitud",
    aprobada: "Primera Aprobación",
    rechazada: "Cancelado",
};

export const ESTADO_BADGE = {
    solicitud: "badge-sg-pendiente",
    revision: "badge-sg-rechazado",
    primera_aprobacion: "badge-sg-aprobacion",
    revision_proyectos: "badge-sg-aprobacion",
    programacion_visita: "badge-sg-aprobacion",
    cotizacion_proyectos: "badge-sg-aprobacion",
    cotizacion: "badge-sg-aprobacion",
    comite: "badge-sg-aprobacion",
    en_aprobacion: "badge-sg-aprobacion",
    gestionando_servicio: "badge-sg-aprobacion",
    en_juridica: "badge-sg-aprobacion",
    solicitando_info: "badge-sg-aprobacion",
    info_recibida: "badge-sg-aprobado",
    elaborando_contrato: "badge-sg-aprobacion",
    revision_polizas: "badge-sg-aprobacion",
    solicitud_firmas: "badge-sg-aprobacion",
    anticipo_contabilidad: "badge-sg-aprobacion",
    anticipo_tesoreria: "badge-sg-aprobacion",
    anticipo_pagado: "badge-sg-aprobado",
    contrato_activo: "badge-sg-aprobado",
    contrato_finalizado: "badge-sg-aprobado",
    cierre_contabilidad: "badge-sg-aprobacion",
    cierre_tesoreria: "badge-sg-aprobacion",
    contrato_completado: "badge-sg-aprobado",
    pendiente_evidencia_cierre: "badge-sg-aprobacion",
    tramitada_oc: "badge-sg-aprobado",
    items_en_camino: "badge-sg-aprobacion",
    recepcion_insumos: "badge-sg-aprobado",
    tramitando_oc: "badge-sg-aprobacion",
    aprobacion_anticipo: "badge-sg-aprobacion",
    gestion_anticipo: "badge-sg-aprobacion",
    cancelado: "badge-sg-rechazado",
    entregado: "badge-sg-aprobado",
    entregado_parcial: "badge-sg-aprobado",
    facturada: "badge-sg-facturada",
    registrada: "badge-sg-pendiente",
    aprobada: "badge-sg-aprobacion",
    rechazada: "badge-sg-rechazado",
};

/** Estados en los que el solicitante puede agregar comentarios sobre la cotización. */
const ESTADOS_COMENTARIO_COTIZACION = new Set([
    "cotizacion",
    "en_aprobacion",
    "tramitada_oc",
    "items_en_camino",
    "recepcion_insumos",
    "tramitando_oc",
    "entregado_parcial",
    "entregado",
    "pendiente_evidencia_cierre",
]);

export function puedeComentarPosteriorCotizacion(estado) {
    return ESTADOS_COMENTARIO_COTIZACION.has(normalizarEstado(estado));
}

export function puedeEnviarEvidenciaCierreServicio(estado, solicitud) {
    return (
        esSolicitudServicios(solicitud) &&
        normalizarEstado(estado) === "pendiente_evidencia_cierre"
    );
}

function fechaNotificacionEvidenciaCierre(solicitud) {
    const historial = [...(solicitud.historial_estados || [])].sort(
        (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0)
    );
    let maxFecha = null;
    for (const h of historial) {
        if (normalizarEstado(h.etapa) !== "pendiente_evidencia_cierre") continue;
        if (!h.created_at) continue;
        const d = new Date(h.created_at);
        if (!maxFecha || d > maxFecha) maxFecha = d;
    }
    return maxFecha;
}

export function obtenerEvidenciaSolicitanteCierre(solicitud) {
    const corte = fechaNotificacionEvidenciaCierre(solicitud);
    if (!corte) return [];
    const porObs = archivosPorObservacion(solicitud);
    return [...(solicitud.observaciones_trazabilidad || [])]
        .filter((o) => {
            const rol = (o.autor_rol || "").toLowerCase();
            if (!rol.includes("solicitante")) return false;
            if (!o.created_at) return false;
            return new Date(o.created_at) >= corte;
        })
        .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0))
        .map((item) => ({
            ...item,
            archivos:
                item.archivos?.length > 0 ? item.archivos : porObs.get(item.id) || [],
        }));
}

export function tieneEvidenciaSolicitanteCierre(solicitud) {
    return obtenerEvidenciaSolicitanteCierre(solicitud).length > 0;
}

function renderEvidenciaSolicitanteCierreHtml(solicitud) {
    const items = obtenerEvidenciaSolicitanteCierre(solicitud);
    if (!items.length) return "";

    const lista = items
        .map((item) => {
            const etiqueta = escapeHtml(
                item.autor_etiqueta ||
                    `${item.autor_nombre || "Usuario"} (${item.autor_rol || ""})`
            );
            const fecha = formatObservacionFecha(item.created_at);
            const adjuntos = renderObservacionArchivosHtml(solicitud.id, item.archivos);
            return `
                <li class="sg-obs-timeline-item">
                    <p class="sg-obs-timeline-meta">
                        <span class="sg-obs-timeline-fecha">[${escapeHtml(fecha)}]</span>
                        <strong>${etiqueta}:</strong>
                    </p>
                    <div class="sg-obs-timeline-content sg-observaciones-readonly">${item.contenido || ""}</div>
                    ${adjuntos}
                </li>`;
        })
        .join("");

    return `
        <div class="sg-detail-panel sg-evidencia-cierre-panel">
            <h3 class="sg-detail-panel-title">Evidencia del solicitante</h3>
            <p class="muted sg-detail-panel-hint">
                Revisa la evidencia adjunta. Si es correcta, confirma el cierre del servicio.
            </p>
            <ul class="sg-obs-timeline">${lista}</ul>
        </div>`;
}

export function normalizarEstado(estado) {
    return LEGACY_ESTADO[estado] || estado;
}

export const ESTADO_ENTREGA_LABEL = {
    pendiente: "Pendiente",
    parcial: "Parcial",
    entregado: "Entregado",
};

export const ESTADO_RECEPCION_LABEL = {
    pendiente: "En camino",
    parcial: "Recepción parcial",
    recibido: "Recibido",
};

export function esGestionEntrega(estado) {
    const key = normalizarEstado(estado);
    return (
        key === "tramitando_oc" ||
        key === "items_en_camino" ||
        key === "recepcion_insumos" ||
        key === "entregado_parcial" ||
        key === "tramitada_oc"
    );
}

export function esEstadoRecepcion(estado) {
    const key = normalizarEstado(estado);
    return (
        key === "items_en_camino" ||
        key === "recepcion_insumos" ||
        key === "entregado_parcial"
    );
}

export function esEstadoEntregaSolicitante(estado) {
    const key = normalizarEstado(estado);
    return key === "recepcion_insumos" || key === "entregado_parcial";
}

export function calcCantidadPendienteRecepcion(producto) {
    if (producto?.cantidad_pendiente_recepcion != null) {
        return Math.max(0, Number(producto.cantidad_pendiente_recepcion));
    }
    const total = Number(producto?.cantidad ?? 1);
    const recibida = Number(producto?.cantidad_recibida ?? 0);
    const pendiente = total - recibida;
    return pendiente > 0 ? pendiente : 0;
}

export function calcCantidadDisponibleEntrega(producto) {
    if (producto?.cantidad_disponible_entrega != null) {
        return Math.max(0, Number(producto.cantidad_disponible_entrega));
    }
    const recibida = Number(producto?.cantidad_recibida ?? 0);
    const entregada = Number(producto?.cantidad_entregada ?? 0);
    const disponible = recibida - entregada;
    return disponible > 0 ? disponible : 0;
}

export function solicitudTieneRecepcionPendiente(solicitud) {
    if (esSolicitudSalidasAlmacen(solicitud)) return false;
    if (typeof solicitud?.tiene_recepcion_pendiente === "boolean") {
        return solicitud.tiene_recepcion_pendiente;
    }
    return filtrarProductosParaGestion(solicitud?.productos || []).some(
        (p) => calcCantidadPendienteRecepcion(p) > 0
    );
}

export function solicitudTieneDisponibleEntrega(solicitud) {
    return filtrarProductosParaGestion(solicitud?.productos || []).some(
        (p) => calcCantidadDisponibleEntrega(p) > 0
    );
}

export function solicitudRecepcionCompleta(solicitud) {
    if (typeof solicitud?.recepcion_completa === "boolean") {
        return solicitud.recepcion_completa;
    }
    const productos = filtrarProductosParaGestion(solicitud?.productos || []);
    if (!productos.length) return false;
    return productos.every((p) => calcCantidadPendienteRecepcion(p) <= 0);
}

/** True si puede cerrarse con entrega total (todo recibido y aún hay stock por entregar). */
export function solicitudPuedeEntregaTotal(solicitud) {
    if (esSolicitudSalidasAlmacen(solicitud)) {
        return solicitudTieneDisponibleEntrega(solicitud);
    }
    if (!solicitudRecepcionCompleta(solicitud)) return false;
    return solicitudTieneDisponibleEntrega(solicitud);
}

export function calcCantidadPendiente(producto) {
    const total = Number(producto?.cantidad ?? 1);
    const entregada = Number(producto?.cantidad_entregada ?? 0);
    const pendiente = total - entregada;
    return pendiente > 0 ? pendiente : 0;
}

export function solicitudEntregaCompleta(solicitud) {
    if (solicitud?.entrega_completa) return true;
    const productos = filtrarProductosParaGestion(solicitud?.productos || []);
    if (!productos.length) return false;
    return productos.every((p) => calcCantidadPendiente(p) <= 0);
}

export function solicitudTieneEntregaPendiente(solicitud) {
    if (typeof solicitud?.tiene_entrega_pendiente === "boolean") {
        return solicitud.tiene_entrega_pendiente;
    }
    return filtrarProductosParaGestion(solicitud?.productos || []).some(
        (p) => calcCantidadPendiente(p) > 0
    );
}

export function solicitudTieneEntregaRegistrada(solicitud) {
    return filtrarProductosParaGestion(solicitud?.productos || []).some(
        (p) => Number(p.cantidad_entregada || 0) > 0
    );
}

/** True si el gestor puede cerrar la solicitud dejando cantidades sin entregar. */
export function solicitudPuedeCerrarConPendientes(solicitud) {
    if (!esEstadoEntregaSolicitante(normalizarEstado(solicitud?.estado))) return false;
    if (!solicitudTieneEntregaPendiente(solicitud)) return false;
    return solicitudTieneEntregaRegistrada(solicitud);
}

function badgeEstadoRecepcion(estado) {
    const key = estado || "pendiente";
    const cls =
        {
            pendiente: "badge-sg-aprobacion",
            parcial: "badge-sg-aprobacion",
            recibido: "badge-sg-aprobado",
        }[key] || "badge-sg-pendiente";
    const label = ESTADO_RECEPCION_LABEL[key] || key;
    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function badgeEstadoEntrega(estado) {
    const key = estado || "pendiente";
    const cls =
        {
            pendiente: "badge-sg-pendiente",
            parcial: "badge-sg-aprobacion",
            entregado: "badge-sg-aprobado",
        }[key] || "badge-sg-pendiente";
    const label = ESTADO_ENTREGA_LABEL[key] || key;
    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function formatObservacionFecha(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const fecha = d.toLocaleDateString("es-CO", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    });
    const hora = d.toLocaleTimeString("es-CO", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
    });
    return `${fecha} - ${hora}`;
}

function archivosPorObservacion(solicitud) {
    const map = new Map();
    for (const archivo of solicitud.archivos || []) {
        if (!archivo.observacion_id) continue;
        const key = archivo.observacion_id;
        if (!map.has(key)) map.set(key, []);
        map.get(key).push(archivo);
    }
    return map;
}

function archivosSinObservacion(solicitud, categoria = null) {
    return (solicitud.archivos || []).filter((a) => {
        if (a.observacion_id) return false;
        if (categoria) return (a.categoria || "solicitud") === categoria;
        return true;
    });
}

function renderObservacionArchivosHtml(solicitudId, archivos) {
    const visibles = (archivos || []).filter(
        (a) => a.categoria !== "observacion_inline" && a.categoria !== "cotizacion"
    );
    if (!visibles.length) return "";
    return `
        <ul class="sg-obs-attachment-list">
            ${visibles
                .map((a) => {
                    const esImagen = (a.mime_type || "").startsWith("image/");
                    const downloadAttrs = `
                        data-download-url="/solicitudes-gestion/${solicitudId}/archivos/${a.id}"
                        data-filename="${escapeHtml(a.nombre_original)}"
                        data-mime-type="${escapeHtml(a.mime_type || "")}"`;
                    // Las imágenes se muestran como miniatura (se hidratan con token);
                    // al hacer clic se abren completas.
                    if (esImagen) {
                        return `
            <li class="sg-obs-attachment-item sg-obs-attachment-item--image">
                <a href="#" class="sg-obs-attachment-thumb-link" ${downloadAttrs}>
                    <img
                        class="sg-obs-attachment-thumb"
                        data-sg-archivo-id="${a.id}"
                        alt="${escapeHtml(a.nombre_original)}"
                    />
                </a>
                <div class="sg-attachment-info">
                    <strong>${escapeHtml(a.nombre_original)}</strong>
                    <span class="muted">${formatFileSize(a.tamano_bytes)} · ${escapeHtml(a.mime_type || "imagen")}</span>
                </div>
            </li>`;
                    }
                    return `
            <li class="sg-obs-attachment-item">
                <span class="sg-attachment-icon" aria-hidden="true">📎</span>
                <div class="sg-attachment-info">
                    <strong>${escapeHtml(a.nombre_original)}</strong>
                    <span class="muted">${formatFileSize(a.tamano_bytes)} · ${escapeHtml(a.mime_type || "archivo")}</span>
                </div>
                <a href="#" class="btn btn-secondary btn-sm" ${downloadAttrs}>
                    Ver
                </a>
            </li>`;
                })
                .join("")}
        </ul>`;
}

function enrichObservacionesWithJustificacion(solicitud, items) {
    const just = (solicitud.justificacion_cotizaciones || "").trim();
    if (!just || !items.length) return items;

    const alreadyShown = items.some(
        (item) =>
            (item.contenido_texto || "").includes(just) ||
            (item.contenido || "").includes(just)
    );
    if (alreadyShown) return items;

    const enriched = items.map((item) => ({ ...item }));
    const gestorIdx = enriched.findLastIndex((item) =>
        (item.autor_rol || item.autor_etiqueta || "").toLowerCase().includes("gestor")
    );

    const blockHtml = `<p class="sg-justificacion-cotizaciones"><strong>Justificación cotizaciones:</strong> ${escapeHtml(just).replace(/\n/g, "<br>")}</p>`;
    const blockTexto = `Justificación cotizaciones: ${just}`;

    if (gestorIdx >= 0) {
        const item = enriched[gestorIdx];
        enriched[gestorIdx] = {
            ...item,
            contenido: `${item.contenido || ""}${blockHtml}`,
            contenido_texto: `${item.contenido_texto || ""}\n\n${blockTexto}`.trim(),
        };
        return enriched;
    }

    enriched.push({
        id: -1,
        autor_etiqueta: solicitud.gestor_username
            ? `${solicitud.gestor_username} (Gestor)`
            : "Gestor",
        contenido: blockHtml,
        contenido_texto: blockTexto,
        created_at: solicitud.updated_at || solicitud.created_at,
        archivos: [],
    });
    return enriched;
}

function collectObservacionesTrazabilidad(solicitud) {
    const porObs = archivosPorObservacion(solicitud);
    const items = [...(solicitud.observaciones_trazabilidad || [])];
    if (items.length) {
        return enrichObservacionesWithJustificacion(
            solicitud,
            items
                .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0))
                .map((item) => ({
                    ...item,
                    archivos:
                        item.archivos?.length > 0
                            ? item.archivos
                            : porObs.get(item.id) || [],
                }))
        );
    }

    const legacy = [];
    if (solicitud.observaciones_texto || solicitud.observaciones) {
        legacy.push({
            id: 0,
            autor_etiqueta: solicitud.creado_por_username
                ? `${solicitud.creado_por_username} (Supervisor)`
                : "Supervisor",
            contenido: solicitud.observaciones || escapeHtml(solicitud.observaciones_texto),
            created_at: solicitud.created_at,
            archivos: archivosSinObservacion(solicitud, "solicitud"),
        });
    }
    if (solicitud.observaciones_gestion) {
        legacy.push({
            id: 0,
            autor_etiqueta: solicitud.gestor_username
                ? `${solicitud.gestor_username} (Gestor)`
                : "Gestor",
            contenido: renderObservacionesGestionHtml(solicitud.observaciones_gestion),
            created_at: solicitud.updated_at || solicitud.created_at,
            archivos: archivosSinObservacion(solicitud, "cotizacion"),
        });
    }
    return enrichObservacionesWithJustificacion(solicitud, legacy);
}

export function renderObservacionesTrazabilidadHtml(
    solicitud,
    { titulo = "Historial de observaciones", panelId = "sg-obs-trazabilidad-panel" } = {}
) {
    const items = collectObservacionesTrazabilidad(solicitud);
    const bodyId = `${panelId}-body`;
    const countLabel = items.length === 1 ? "1 observación" : `${items.length} observaciones`;

    const lista =
        items.length > 0
            ? `<ul class="sg-obs-timeline">
                ${items
                    .map((item) => {
                        const etiqueta = escapeHtml(
                            item.autor_etiqueta ||
                                `${item.autor_nombre || "Usuario"} (${item.autor_rol || ""})`
                        );
                        const fecha = formatObservacionFecha(item.created_at);
                        const adjuntos = renderObservacionArchivosHtml(solicitud.id, item.archivos);
                        return `
                <li class="sg-obs-timeline-item">
                    <p class="sg-obs-timeline-meta">
                        <span class="sg-obs-timeline-fecha">[${escapeHtml(fecha)}]</span>
                        <strong>${etiqueta}:</strong>
                    </p>
                    <div class="sg-obs-timeline-content sg-observaciones-readonly">${item.contenido || ""}</div>
                    ${adjuntos}
                </li>`;
                    })
                    .join("")}
            </ul>`
            : `<p class="muted sg-obs-timeline-empty">Sin observaciones registradas.</p>`;

    const obsPanel = `
        <div class="sg-detail-panel sg-obs-collapsible" id="${escapeHtml(panelId)}">
            <button
                type="button"
                class="sg-obs-collapsible-toggle"
                aria-expanded="false"
                aria-controls="${escapeHtml(bodyId)}"
            >
                <span class="sg-detail-panel-title">${escapeHtml(titulo)}</span>
                <span class="sg-obs-collapsible-count muted">${escapeHtml(countLabel)}</span>
                <svg
                    class="sg-obs-collapsible-chevron"
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                >
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </button>
            <div class="sg-obs-collapsible-body" id="${escapeHtml(bodyId)}" hidden>
                ${lista}
            </div>
        </div>`;

    return obsPanel + renderProveedoresColapsableHtml(solicitud);
}

/** Panel desplegable con los proveedores sugeridos, debajo de las observaciones. */
export function renderProveedoresColapsableHtml(solicitud) {
    const lineas = String(solicitud?.proveedor_sugerido || "")
        .split(/\r?\n/)
        .map((l) => l.replace(/^-\s*/, "").trim())
        .filter(Boolean);
    if (!lineas.length) return "";

    const bodyId = "sg-prov-trazabilidad-panel-body";
    const countLabel =
        lineas.length === 1 ? "1 proveedor" : `${lineas.length} proveedores`;
    const lista = `<ul class="sg-prov-lista">${lineas
        .map((l) => `<li>${escapeHtml(l)}</li>`)
        .join("")}</ul>`;

    return `
        <div class="sg-detail-panel sg-obs-collapsible" id="sg-prov-trazabilidad-panel">
            <button
                type="button"
                class="sg-obs-collapsible-toggle"
                aria-expanded="false"
                aria-controls="${bodyId}"
            >
                <span class="sg-detail-panel-title">Proveedores sugeridos</span>
                <span class="sg-obs-collapsible-count muted">${escapeHtml(countLabel)}</span>
                <svg class="sg-obs-collapsible-chevron" xmlns="http://www.w3.org/2000/svg"
                    width="18" height="18" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" stroke-width="2" stroke-linecap="round"
                    stroke-linejoin="round" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
            </button>
            <div class="sg-obs-collapsible-body" id="${bodyId}" hidden>
                ${lista}
            </div>
        </div>`;
}

export function extraerObservacionesFactura(solicitud) {
    return (solicitud?.observaciones_trazabilidad || [])
        .filter((o) => {
            const archivos = o.archivos || [];
            if (archivos.some((a) => a.categoria === "factura")) return true;
            const texto = `${o.contenido_texto || ""} ${o.contenido || ""}`.toLowerCase();
            return texto.includes("factura registrada") && archivos.length > 0;
        })
        .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
}

export function renderFacturasHistorialHtml(solicitud) {
    const items = extraerObservacionesFactura(solicitud);
    const sid = solicitud?.id;
    if (!items.length) {
        return `<p class="muted sg-facturas-empty">Sin facturas registradas.</p>`;
    }
    return `<ul class="sg-facturas-timeline sg-obs-timeline">
        ${items
            .map((item, idx) => {
                const numero = idx + 1;
                const etiqueta = escapeHtml(
                    item.autor_etiqueta ||
                        `${item.autor_nombre || "Usuario"} (${item.autor_rol || "Gestor"})`
                );
                const fecha = formatObservacionFecha(item.created_at);
                const adjuntos = renderObservacionArchivosHtml(sid, item.archivos);
                const tituloFactura = numero > 1 ? `Factura #${numero}` : "Factura #1";
                return `
                <li class="sg-obs-timeline-item sg-factura-timeline-item">
                    <p class="sg-obs-timeline-meta">
                        <span class="sg-factura-numero badge badge-sg-facturada">${escapeHtml(tituloFactura)}</span>
                        <span class="sg-obs-timeline-fecha">[${escapeHtml(fecha)}]</span>
                        <strong>${etiqueta}</strong>
                    </p>
                    <div class="sg-obs-timeline-content sg-observaciones-readonly">${item.contenido || ""}</div>
                    ${adjuntos}
                </li>`;
            })
            .join("")}
    </ul>`;
}

function renderObservacionesGestionHtml(raw) {
    if (!raw) return "";
    if (raw.includes("sg-obs-gestion-entry")) return raw;
    return escapeHtml(raw).replace(/\n/g, "<br>");
}

export const MIN_COTIZACIONES = 3;
export const COTIZACION_ACCEPT = ".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx";

export function renderAgregarComentarioHtml({
    editorContainerId = "gestion-nueva-observacion-editor",
    fileInputId = "gestion-comentario-adjuntos",
    fileListId = "gestion-comentario-file-list",
    btnId = "btn-gestion-guardar-comentario",
    title = "Agregar comentario",
    label = "Nuevo comentario",
    showIntro = true,
    introHtml = "",
    showHint = true,
    showSaveButton = true,
} = {}) {
    return `
        <div class="sg-detail-panel sg-obs-nuevo-comentario-panel">
            <h3 class="sg-detail-panel-title">${escapeHtml(title)}</h3>
            ${
                introHtml
                    ? introHtml
                    : showIntro
                      ? `<p class="muted sg-detail-panel-hint">
                El comentario se añadirá al historial sin modificar entradas anteriores.
            </p>`
                      : ""
            }
            ${renderObservacionAdjuntosFieldHtml({
                editorContainerId,
                fileInputId,
                fileListId,
                label,
                showHint,
            })}
            ${
                showSaveButton
                    ? `<button type="button" class="btn btn-secondary btn-sm" id="${escapeHtml(btnId)}">
                Guardar comentario
            </button>`
                    : ""
            }
        </div>`;
}

export function renderCotizacionSlotHtml(index, { conDatosEconomicos = false } = {}) {
    const removable = index >= MIN_COTIZACIONES;
    const datos = conDatosEconomicos
        ? `
            <div class="sg-cotizacion-datos">
                <div class="row-2">
                    <div class="field">
                        <label for="cotizacion-valor-${index}">Valor <span class="required">*</span></label>
                        <div class="sg-cotizacion-valor-row">
                            <select class="cotizacion-moneda input-table" id="cotizacion-moneda-${index}" aria-label="Moneda">
                                <option value="COP" selected>COP — Peso</option>
                                <option value="USD">USD — Dólar</option>
                                <option value="EUR">EUR — Euro</option>
                            </select>
                            <input
                                type="number"
                                class="cotizacion-valor input-table"
                                id="cotizacion-valor-${index}"
                                min="0.01"
                                step="0.01"
                                placeholder="Ej: 1000000"
                            />
                        </div>
                        <p class="sg-cotizacion-valor-vivo muted" aria-live="polite"></p>
                    </div>
                    <div class="field">
                        <label>¿Anticipo?</label>
                        <div class="radio-group">
                            <label class="radio-option">
                                <input type="radio" class="cotizacion-anticipo-no" name="cotizacion-anticipo-${index}" value="no" checked />
                                No
                            </label>
                            <label class="radio-option">
                                <input type="radio" class="cotizacion-anticipo-si" name="cotizacion-anticipo-${index}" value="si" />
                                Sí
                            </label>
                        </div>
                    </div>
                </div>
                <div class="field cotizacion-anticipo-pct-wrap" hidden>
                    <label for="cotizacion-anticipo-pct-${index}">Anticipo (%) <span class="required">*</span></label>
                    <input
                        type="number"
                        class="cotizacion-anticipo-pct input-table"
                        id="cotizacion-anticipo-pct-${index}"
                        min="0.01"
                        max="100"
                        step="0.01"
                        placeholder="Ej: 30"
                    />
                </div>
            </div>`
        : "";
    return `
        <div class="sg-cotizacion-slot" data-slot="${index}">
            <div class="sg-cotizacion-slot-head">
                <span class="sg-cotizacion-slot-label">Cotización ${index + 1}</span>
                ${
                    removable
                        ? `<button type="button" class="sg-cotizacion-quitar-x btn-cotizacion-quitar-slot" aria-label="Quitar cotización" title="Quitar cotización">×</button>`
                        : ""
                }
            </div>
            <div class="sg-cotizacion-slot-row">
                <input
                    type="file"
                    class="gestion-cotizacion-input"
                    id="gestion-cotizacion-${index}"
                    accept="${COTIZACION_ACCEPT}"
                />
                <span class="sg-cotizacion-slot-name muted">Sin archivo</span>
                <button type="button" class="btn btn-sm btn-secondary btn-cotizacion-clear" hidden>
                    Quitar archivo
                </button>
            </div>
            ${datos}
        </div>`;
}

export function renderCotizacionesUploadHtml(existentesCount = 0, { conDatosEconomicos = false } = {}) {
    // Las cotizaciones ya registradas (p. ej. las que sube Proyectos) cuentan para
    // el mínimo: sólo pintamos los slots faltantes y continuamos la numeración.
    const faltantes = Math.max(0, MIN_COTIZACIONES - existentesCount);
    const principales = Array.from({ length: faltantes }, (_, i) =>
        renderCotizacionSlotHtml(existentesCount + i, { conDatosEconomicos })
    ).join("");

    return `
        <div class="field sg-cotizaciones-field">
            <label>
                Carga de cotizaciones
                <span class="hint">Adjunta al menos ${MIN_COTIZACIONES} archivos o indica una justificación.</span>
            </label>
            <div id="gestion-cotizaciones-upload" class="sg-cotizaciones-upload">
                <div id="gestion-cotizaciones-principales" class="sg-cotizaciones-principales">
                    ${principales}
                </div>
                <button type="button" class="btn btn-secondary btn-sm" id="btn-gestion-cotizacion-mas">
                    Agregar más
                </button>
                <div id="gestion-cotizaciones-extras" class="sg-cotizaciones-extras"></div>
            </div>
            <p class="info" id="gestion-cotizaciones-count">
                Cotizaciones registradas: ${existentesCount} · Nuevas seleccionadas: 0
            </p>
        </div>`;
}

export function badgeTipo(tipo) {
    const cls = TIPO_BADGE[tipo] || "badge-tipo-compra";
    return `<span class="badge ${cls}">${escapeHtml(TIPO_LABEL[tipo] || tipo)}</span>`;
}

export function solicitudTieneOcRegistrada(solicitud) {
    if (!solicitud) return false;
    if (esSolicitudSalidasAlmacen(solicitud)) return true;
    if (solicitud.tiene_tramite_oc_registrado) return true;
    if ((solicitud.numero_tramite_oc || "").trim()) return true;
    return (solicitud.productos || []).some((p) => (p.numero_tramite_oc || "").trim());
}

export function badgeEstado(estado, solicitud = null) {
    const key = normalizarEstado(estado);
    const cls = ESTADO_BADGE[key] || ESTADO_BADGE[estado] || "badge-sg-pendiente";
    let label =
        ESTADO_LABEL[key] ||
        ESTADO_LABEL[estado] ||
        (solicitud?.estado_label || "").trim() ||
        estado;
    if (key === "tramitando_oc") {
        label = "Tramitando OC";
    }
    if (key === "items_en_camino") {
        label = "Ítems en camino";
    }
    if (key === "recepcion_insumos") {
        label = esSolicitudSalidasAlmacen(solicitud)
            ? "Gestión de entrega"
            : "Recepción de Insumos";
    }
    if (key === "entregado_parcial") {
        label = esSolicitudSalidasAlmacen(solicitud)
            ? "Entrega parcial — pendientes"
            : "Entrega parcial realizada";
    }
    if (key === "facturada") {
        label = "Facturada";
    }
    if (key === "gestionando_servicio") {
        const clasif = labelClasificacionDocumentoServicio(solicitud);
        if (clasif) {
            label = `Gestionando… · ${clasif}`;
        } else {
            label = "Gestionando…";
        }
    }
    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function etiquetaPasoHistorial(h) {
    const key = normalizarEstado(h.etapa);
    if (ESTADO_LABEL[key] && ETAPAS_TRAZA_JURIDICA.has(key)) {
        return ESTADO_LABEL[key];
    }
    const c = h.comentario || "";
    if (/solicitó información/i.test(c)) return "Solicitando información";
    if (/respondió a Jurídica/i.test(c)) return "Información recibida";
    if (/actualizó el estado/i.test(c)) {
        const m = c.match(/→\s*(.+)$/);
        if (m) {
            const dest = m[1].trim();
            if (dest === "Pendiente") return "En Jurídica";
            if (dest === "Activo") return "Contrato activo";
            if (dest === "Finalizado") return "Contrato finalizado";
            return dest;
        }
        return "En Jurídica";
    }
    if (/finalizó/i.test(c) && /contrato|OS-|C-/i.test(c)) return "Contrato finalizado";
    if (/radicado y vinculado/i.test(c)) return "En Jurídica";
    return h.etapa_label || ESTADO_LABEL[key] || key;
}

const ETAPAS_TRAZA_JURIDICA = new Set([
    "en_juridica",
    "solicitando_info",
    "info_recibida",
    "elaborando_contrato",
    "revision_polizas",
    "solicitud_firmas",
    "anticipo_contabilidad",
    "anticipo_tesoreria",
    "anticipo_pagado",
    "contrato_activo",
    "contrato_finalizado",
]);

function esPasoTrazabilidadJuridica(h) {
    if (!h) return false;
    if (ETAPAS_TRAZA_JURIDICA.has(normalizarEstado(h.etapa))) return true;
    const c = h.comentario || "";
    return (
        /solicitó información/i.test(c) ||
        /respondió a Jurídica/i.test(c) ||
        /actualizó el estado/i.test(c) ||
        /radicado y vinculado/i.test(c) ||
        (/finalizó/i.test(c) && /contrato|OS-|C-/i.test(c))
    );
}

function buildTimelineItems(solicitud) {
    const historial = [...(solicitud.historial_estados || [])].sort(
        (a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0)
    );
    const current = normalizarEstado(solicitud.estado);
    const finalizadoEnHistorial = (solicitud.historial_estados || []).some(
        (h) => normalizarEstado(h?.etapa) === "contrato_finalizado"
    );
    const terminal =
        ["cancelado", "entregado", "facturada", "contrato_finalizado"].includes(current) ||
        finalizadoEnHistorial;

    if (!historial.length) {
        return [
            {
                label: ESTADO_LABEL[current] || "Solicitud",
                fecha: solicitud.created_at,
                usuario: solicitud.creado_por_username,
                comentario: "Solicitud registrada",
                status:
                    current === "cancelado"
                        ? "rejected"
                        : terminal
                          ? "done"
                          : "active",
            },
        ];
    }

    const lastH = historial[historial.length - 1];
    const overlayJuridica = esPasoTrazabilidadJuridica(lastH);

    return historial.map((h, i) => {
        const key = normalizarEstado(h.etapa);
        const isLast = i === historial.length - 1;
        let status = "done";

        if (isLast) {
            if (key === "cancelado" || current === "cancelado") status = "rejected";
            else if (terminal || key === "contrato_finalizado") status = "done";
            else status = "active";
        }

        return {
            label: etiquetaPasoHistorial(h),
            fecha: h.created_at,
            usuario: h.usuario_username,
            comentario: h.comentario,
            status,
        };
    }).concat(
        !terminal &&
            historial.length &&
            !overlayJuridica &&
            normalizarEstado(lastH.etapa) !== current
            ? [
                  {
                      label: ESTADO_LABEL[current] || current,
                      fecha: solicitud.updated_at || solicitud.created_at,
                      usuario: solicitud.gestor_username || "",
                      comentario: "",
                      status: "active",
                  },
              ]
            : []
    );
}

export function renderWorkflowTimelineHtml(solicitud) {
    const items = buildTimelineItems(solicitud);

    if (!items.length) {
        return "";
    }

    const pasos = items
        .map((item) => {
            const meta = [];
            if (item.fecha) meta.push(formatDate(item.fecha));
            if (item.usuario) meta.push(escapeHtml(item.usuario));
            if (item.comentario && item.comentario !== item.label) {
                meta.push(escapeHtml(item.comentario));
            }

            return `
            <li class="sg-workflow-step sg-workflow-step--${item.status}">
                <span class="sg-workflow-marker" aria-hidden="true"></span>
                <div class="sg-workflow-body">
                    <strong>${escapeHtml(item.label)}</strong>
                    ${meta.length ? `<span class="sg-workflow-meta">${meta.join(" · ")}</span>` : ""}
                </div>
            </li>`;
        })
        .join("");

    return `
        <div class="sg-detail-panel sg-detail-panel--timeline">
            <h3 class="sg-detail-panel-title">Historial del flujo</h3>
            <p class="muted sg-detail-panel-hint">
                Los estados aparecen aquí a medida que avanza tu solicitud.
            </p>
            <ol class="sg-workflow-timeline sg-workflow-timeline--progressive">
                ${pasos}
            </ol>
        </div>
        ${renderComunicacionJuridicaPlaceholderHtml(solicitud)}`;
}

function esVistaJuridicaComunicacion() {
    const role = session.getUser()?.role;
    return role === "juridica" || role === "admin";
}

const ESTADOS_COMUNICACION_CERRADA = new Set([
    "contrato_finalizado",
    "cancelado",
    "entregado",
    "facturada",
]);

function renderComunicacionJuridicaPlaceholderHtml(solicitud) {
    if (!solicitud?.contrato_id) return "";
    const codigo = escapeHtml(solicitud.contrato_codigo || "el contrato");
    const esJuridica = esVistaJuridicaComunicacion();
    const historialCerrado = (solicitud.historial_estados || []).some((h) =>
        ESTADOS_COMUNICACION_CERRADA.has(String(h?.etapa || "").toLowerCase())
    );
    const cerrada =
        ESTADOS_COMUNICACION_CERRADA.has(String(solicitud.estado || "").toLowerCase()) ||
        historialCerrado;
    const titulo = esJuridica ? "Comunicación con el supervisor" : "Comunicación con Jurídica";
    const hint = cerrada
        ? `La operación de ${codigo} quedó finalizada. Este canal queda como historial (ya no se puede escribir).`
        : esJuridica
          ? `Este es el canal con el supervisor de ${codigo}. El supervisor recibe aviso y tiene 2 días hábiles. Queda en el historial de esta SRV.`
          : `Conversación con Jurídica sobre ${codigo}. También queda en el historial de esta solicitud.`;
    const composer = (esJuridica && !cerrada)
        ? `<div class="sg-comunicacion-juridica-composer" style="margin-top:16px;padding-top:14px;border-top:1px solid var(--color-border, #e2e8f0);">
               <div class="field">
                   <label for="info-mensaje">Escribe al supervisor</label>
                   <textarea id="info-mensaje" placeholder="Ej.: Falta el RUT actualizado y la certificación bancaria."></textarea>
               </div>
               <div class="field">
                   <label for="info-archivos">Fotos u otros archivos</label>
                   <input type="file" id="info-archivos" multiple accept="image/*,.pdf,.doc,.docx" />
                   <span class="hint">Opcional. El supervisor los ve en este hilo.</span>
               </div>
               <div style="display:flex;justify-content:flex-end;margin-top:8px;">
                   <button type="button" class="btn btn-primary" id="btn-enviar-supervisor">Enviar al supervisor</button>
               </div>
           </div>`
        : "";
    return `
        <div class="sg-detail-panel" id="sg-comunicacion-juridica" hidden data-contrato-id="${solicitud.contrato_id}">
            <h3 class="sg-detail-panel-title">${titulo}</h3>
            <p class="muted sg-detail-panel-hint">${hint}</p>
            <div id="sg-comunicacion-juridica-hilo"></div>
            ${composer}
        </div>`;
}

function puedeResponderComunicacionJuridica() {
    const role = session.getUser()?.role;
    return role === "solicitante" || role === "admin";
}

export async function hydrateComunicacionJuridica(onError) {
    const root = document.getElementById("sg-comunicacion-juridica");
    if (!root) return;
    const contratoId = root.dataset.contratoId;
    const hilo = document.getElementById("sg-comunicacion-juridica-hilo");
    if (!contratoId || !hilo) return;
    let items = [];
    try {
        items = await api.get(`/contratos/${contratoId}/solicitudes-informacion`);
    } catch {
        return;
    }
    root.hidden = false;
    // La comunicación va al final del detalle (chat abajo), no justo bajo el timeline.
    const layout = root.parentElement;
    if (layout && layout.lastElementChild !== root) layout.appendChild(root);
    const cronologico = [...items].sort((a, b) => (a.id || 0) - (b.id || 0));
    const puedeResponder = puedeResponderComunicacionJuridica();
    const vacio = esVistaJuridicaComunicacion()
        ? "Aún no hay mensajes con el supervisor."
        : "Aún no hay mensajes con Jurídica.";
    hilo.innerHTML = cronologico.length
        ? cronologico.map((s) => renderComunicacionJuridicaItemHtml(s, puedeResponder)).join("")
        : `<p class="muted" style="margin:0;">${vacio}</p>`;
    const btnEnviar = document.getElementById("btn-enviar-supervisor");
    if (btnEnviar && !btnEnviar.dataset.bound) {
        btnEnviar.dataset.bound = "1";
        btnEnviar.addEventListener("click", () =>
            enviarSolicitudInformacionJuridica(contratoId, onError)
        );
    }

    if (!puedeResponder) return;
    cronologico
        .filter((s) => s.estado !== "respondida")
        .forEach((s) => {
            const btn = document.getElementById(`btn-sg-resp-info-${s.id}`);
            if (!btn) return;
            btn.addEventListener("click", () =>
                enviarRespuestaComunicacionJuridica(contratoId, s.id, onError)
            );
        });
}

async function enviarSolicitudInformacionJuridica(contratoId, onError) {
    const textarea = document.getElementById("info-mensaje");
    const mensaje = (textarea?.value || "").trim();
    if (!mensaje) {
        onError?.("Escribe qué información falta.");
        return;
    }
    const btn = document.getElementById("btn-enviar-supervisor");
    if (btn) btn.disabled = true;
    try {
        const fd = new FormData();
        fd.append("mensaje", mensaje);
        const files = document.getElementById("info-archivos")?.files;
        for (const f of files || []) fd.append("archivos", f);
        await api.postForm(`/contratos/${contratoId}/solicitudes-informacion`, fd);
        if (textarea) textarea.value = "";
        const inputFiles = document.getElementById("info-archivos");
        if (inputFiles) inputFiles.value = "";
        await hydrateComunicacionJuridica(onError);
    } catch (err) {
        onError?.(err.message || "No se pudo enviar al supervisor.");
    } finally {
        if (btn) btn.disabled = false;
    }
}

function adjuntosHiloHtml(archivos, contratoId) {
    if (!archivos.length) return "";
    return `<div style="margin-top:6px;"><strong>Adjuntos:</strong> ${archivos
        .map(
            (a) =>
                `<a href="#" data-download-url="/archivos/${contratoId}/${a.id}" data-filename="${escapeHtml(a.nombre_original)}">${escapeHtml(a.nombre_original)}</a>`
        )
        .join(" · ")}</div>`;
}

function renderComunicacionJuridicaItemHtml(s, puedeResponder) {
    const respondida = s.estado === "respondida";
    const borde = respondida ? "#16a34a" : s.vencida ? "#dc2626" : "#f59e0b";
    const limite = s.fecha_limite_respuesta ? formatDate(s.fecha_limite_respuesta) : "—";
    const deJuridica = s.solicitado_por_username || "Jurídica";
    const deSupervisor = s.respondido_por_username || "el supervisor";
    const estadoTxt = respondida
        ? `Respondida por el supervisor (${escapeHtml(deSupervisor)})`
        : s.vencida
          ? "Pendiente del supervisor — plazo vencido"
          : `Pendiente del supervisor — ${s.dias_para_responder ?? "?"} día(s) hábiles`;
    const adjuntosJuridica = (s.archivos || []).filter((a) => a.tipo === "solicitud_informacion");
    const adjuntosSupervisor = (s.archivos || []).filter((a) => a.tipo !== "solicitud_informacion");
    const archivosJuridicaHtml = adjuntosHiloHtml(adjuntosJuridica, s.contrato_id);
    const archivosSupervisorHtml = adjuntosHiloHtml(adjuntosSupervisor, s.contrato_id);
    const respuestaHtml = respondida
        ? `<div style="margin-top:8px;padding:8px 10px;background:#f0fdf4;border-radius:6px;">
               <strong>Supervisor (${escapeHtml(deSupervisor)}):</strong><br>${escapeHtml(s.respuesta || "").replace(/\n/g, "<br>")}
               ${archivosSupervisorHtml}
           </div>`
        : "";
    const formHtml =
        !respondida && puedeResponder
            ? `<div style="margin-top:10px;">
                   <textarea id="sg-resp-info-${s.id}" rows="3" style="width:100%;" placeholder="Escribe la respuesta para Jurídica..."></textarea>
                   <input type="file" id="sg-files-info-${s.id}" multiple style="margin-top:6px;" />
                   <div style="display:flex;justify-content:flex-end;margin-top:6px;">
                       <button type="button" class="btn btn-sm btn-primary" id="btn-sg-resp-info-${s.id}">Responder a Jurídica</button>
                   </div>
               </div>`
            : "";
    return `
        <div style="border-left:4px solid ${borde};background:#f8fafc;border-radius:6px;padding:10px 12px;margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;">
                <strong>${escapeHtml(estadoTxt)}</strong>
                <span class="muted">Límite: ${limite}</span>
            </div>
            <div style="margin-top:6px;"><strong>Jurídica (${escapeHtml(deJuridica)}):</strong> ${escapeHtml(s.mensaje || "").replace(/\n/g, "<br>")}</div>
            ${archivosJuridicaHtml}
            ${respuestaHtml}
            ${formHtml}
        </div>`;
}

async function enviarRespuestaComunicacionJuridica(contratoId, solicitudId, onError) {
    const textarea = document.getElementById(`sg-resp-info-${solicitudId}`);
    const respuesta = (textarea?.value || "").trim();
    if (!respuesta) {
        onError?.("Escribe la respuesta para Jurídica.");
        return;
    }
    const fd = new FormData();
    fd.append("respuesta", respuesta);
    const files = document.getElementById(`sg-files-info-${solicitudId}`)?.files;
    for (const f of files || []) fd.append("archivos", f);
    const btn = document.getElementById(`btn-sg-resp-info-${solicitudId}`);
    if (btn) btn.disabled = true;
    try {
        await api.postForm(
            `/contratos/${contratoId}/solicitudes-informacion/${solicitudId}/responder`,
            fd
        );
        await hydrateComunicacionJuridica(onError);
    } catch (err) {
        if (btn) btn.disabled = false;
        onError?.(err.message || "No se pudo enviar la respuesta.");
    }
}

export function renderArchivosHtml(solicitud, { categoria = null, titulo = "Archivos adjuntos", seleccionable = false } = {}) {
    let archivos = solicitud.archivos || [];
    if (categoria) {
        archivos = archivos.filter((a) => (a.categoria || "solicitud") === categoria);
    } else {
        archivos = archivos.filter((a) => !a.observacion_id);
        archivos = archivos.filter((a) => (a.categoria || "solicitud") !== "cotizacion");
        if (esSolicitudServicios(solicitud)) {
            archivos = archivos.filter(
                (a) =>
                    !["detalle_servicio", "ficha_tecnica", "hoja_vida_equipo"].includes(
                        a.categoria || ""
                    )
            );
        }
    }
    if (!archivos.length) {
        return "";
    }

    const hint = seleccionable
        ? `<p class="muted sg-detail-panel-hint">
                Elige la cotización. Su valor define si sigue como orden de servicio,
                orden de trabajo o contrato. Si ninguna te sirve, solicita recotización.
           </p>`
        : "";

    const esCotizacion = categoria === "cotizacion";
    const lista = esCotizacion
        ? `<ul class="sg-cotizaciones-principales sg-cotizaciones-vista">
                ${archivos
                    .map((a, i) => renderCotizacionVistaCardHtml(solicitud.id, a, i, seleccionable))
                    .join("")}
            </ul>`
        : `<ul class="sg-attachment-list">
                ${archivos
                    .map((a) => renderArchivoAdjuntoItemHtml(solicitud.id, a))
                    .join("")}
            </ul>`;

    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">${escapeHtml(titulo)} (${archivos.length})</h3>
            ${hint}
            ${lista}
            ${
                seleccionable
                    ? `<p class="sg-cotizacion-clasif-viva" id="sg-cotizacion-clasif-viva"></p>`
                    : ""
            }
        </div>`;
}

function renderArchivoAdjuntoItemHtml(solicitudId, a) {
    return `
                <li class="sg-attachment-item">
                    <span class="sg-attachment-icon" aria-hidden="true">📎</span>
                    <div class="sg-attachment-info">
                        <strong>${escapeHtml(a.nombre_original)}</strong>
                        <span class="muted">${formatFileSize(a.tamano_bytes)} · ${escapeHtml(a.mime_type || "archivo")}</span>
                    </div>
                    <a
                        href="#"
                        class="btn btn-secondary btn-sm"
                        data-download-url="/solicitudes-gestion/${solicitudId}/archivos/${a.id}"
                        data-filename="${escapeHtml(a.nombre_original)}"
                        data-mime-type="${escapeHtml(a.mime_type || "")}"
                    >
                        Ver
                    </a>
                </li>`;
}

function renderCotizacionVistaCardHtml(solicitudId, a, index, seleccionable) {
    const clasifKey =
        (a.moneda_cotizacion || "COP") === "COP" && a.valor_cotizacion
            ? clasificarDocumentoServicio(a.valor_cotizacion)
            : "";
    const clasifLabel = clasifKey ? labelClasificacionDocumentoServicio(clasifKey) : "";
    const valorTxt = a.valor_cotizacion
        ? previewValorCotizacion(a.valor_cotizacion, a.moneda_cotizacion || "COP")
        : "Sin valor";
    const anticipoTxt = a.requiere_anticipo
        ? `Sí · ${a.porcentaje_anticipo ?? ""}%`
        : "No";
    const radio = seleccionable
        ? `<label class="sg-cotizacion-elegir">
                    <input
                        type="radio"
                        name="cotizacion-elegida"
                        value="${a.id}"
                        data-valor="${escapeHtml(String(a.valor_cotizacion ?? ""))}"
                        data-moneda="${escapeHtml(a.moneda_cotizacion || "COP")}"
                        ${index === 0 ? "checked" : ""}
                    />
                    <span>Elegir</span>
                </label>`
        : a.propuesta
          ? `<span class="sg-cotizacion-elegida-badge">Elegida</span>`
          : "";

    return `
                <li class="sg-cotizacion-slot sg-cotizacion-slot--vista">
                    <div class="sg-cotizacion-slot-head">
                        <span class="sg-cotizacion-slot-label">Cotización ${index + 1}</span>
                        ${radio}
                    </div>
                    <div class="sg-cotizacion-slot-row">
                        <span class="sg-cotizacion-slot-name">${escapeHtml(a.nombre_original)} · ${formatFileSize(a.tamano_bytes)}</span>
                        <a
                            href="#"
                            class="btn btn-secondary btn-sm"
                            data-download-url="/solicitudes-gestion/${solicitudId}/archivos/${a.id}"
                            data-filename="${escapeHtml(a.nombre_original)}"
                            data-mime-type="${escapeHtml(a.mime_type || "")}"
                        >
                            Ver
                        </a>
                    </div>
                    <div class="sg-cotizacion-datos">
                        <div class="row-2">
                            <div class="field">
                                <label>Valor</label>
                                <p class="sg-cotizacion-valor-vivo">${escapeHtml(valorTxt)}</p>
                            </div>
                            <div class="field">
                                <label>¿Anticipo?</label>
                                <p class="sg-cotizacion-anticipo-vivo">${escapeHtml(anticipoTxt)}</p>
                            </div>
                        </div>
                        ${
                            clasifLabel
                                ? `<p class="sg-cotizacion-clasif-tag">${escapeHtml(clasifLabel)}</p>`
                                : ""
                        }
                    </div>
                </li>`;
}

export const ESTADO_APROBACION_PRODUCTO_LABEL = {
    pendiente: "Pendiente",
    aprobado: "Aprobado",
    no_aprobado: "No aprobado",
};

export function tieneProductosNoAprobados(productos) {
    return (productos || []).some((p) => p.estado_aprobacion === "no_aprobado");
}

export function filtrarProductosParaGestion(productos) {
    return (productos || []).filter(
        (p) => (p.estado_aprobacion || "pendiente") !== "no_aprobado"
    );
}

function badgeEstadoProducto(estado) {
    const key = estado || "pendiente";
    const cls =
        {
            pendiente: "badge-sg-pendiente",
            aprobado: "badge-sg-aprobado",
            no_aprobado: "badge-sg-rechazado",
        }[key] || "badge-sg-pendiente";
    const label = ESTADO_APROBACION_PRODUCTO_LABEL[key] || key;
    return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

export function renderAprobacionParcialAlertHtml(s) {
    if (!s?.aprobacion_parcial) return "";
    const rechazados = (s.productos || []).filter(
        (p) => p.estado_aprobacion === "no_aprobado"
    ).length;
    return `
        <div class="alert alert-info sg-aprobacion-parcial-alert">
            Esta solicitud tuvo <strong>aprobación parcial</strong>.
            ${rechazados} ítem${rechazados === 1 ? "" : "s"} no ${rechazados === 1 ? "fue aprobado" : "fueron aprobados"}
            y no continúa${rechazados === 1 ? "" : "n"} en el proceso de compra.
        </div>`;
}

export function renderOrdenOcRegistradaAlertHtml(s, options = {}) {
    const { contexto = "gestor" } = options;
    if (esSolicitudSalidasAlmacen(s)) return "";
    const estado = normalizarEstado(s?.estado);
    if (
        ![
            "tramitada_oc",
            "items_en_camino",
            "recepcion_insumos",
            "entregado_parcial",
        ].includes(estado)
    ) {
        return "";
    }
    if (!solicitudTieneOcRegistrada(s)) return "";
    if (estado === "recepcion_insumos") {
        if (contexto === "solicitante") {
            return `
        <div class="alert alert-success sg-orden-oc-alert">
            <strong>Insumos disponibles.</strong> Compras recibió físicamente ítems de tu solicitud.
            Puedes pasar a reclamarlos; Compras registrará la entrega cuando te los haga llegar.
        </div>`;
        }
        return `
        <div class="alert alert-success sg-orden-oc-alert">
            Recepción registrada. Usa <strong>Entrega total</strong> o <strong>Entrega parcial</strong>
            cuando entregues los ítems al solicitante.
        </div>`;
    }
    if (estado === "items_en_camino") {
        if (contexto === "solicitante") {
            return `
        <div class="alert alert-info sg-orden-oc-alert">
            Tu solicitud tiene <strong>orden de compra (OC)</strong> registrada.
            Los ítems están <strong>en camino</strong>; te avisaremos cuando lleguen físicamente a Compras.
        </div>`;
        }
        return `
        <div class="alert alert-info sg-orden-oc-alert">
            OC registrada (estado <em>Tramitada OC</em> completado). Los ítems están <strong>en camino</strong>.
            Cuando lleguen físicamente, registra la recepción indicando qué ítems recibiste.
        </div>`;
    }
    if (estado === "entregado_parcial") {
        if (contexto === "solicitante") {
            return `
        <div class="alert alert-info sg-orden-oc-alert">
            Se registró una <strong>entrega parcial realizada</strong>.
            ${solicitudTieneRecepcionPendiente(s) ? "Aún hay ítems en camino hacia Compras." : ""}
            ${solicitudTieneDisponibleEntrega(s) ? "Hay insumos recibidos pendientes de entrega." : ""}
            ${!solicitudTieneRecepcionPendiente(s) && !solicitudTieneDisponibleEntrega(s) && solicitudTieneEntregaPendiente(s) ? "Falta completar la entrega de algunos ítems." : ""}
        </div>`;
        }
        return `
        <div class="alert alert-info sg-orden-oc-alert">
            <strong>Entrega parcial realizada.</strong>
            ${solicitudTieneRecepcionPendiente(s) ? "Puedes registrar la llegada de ítems pendientes con <strong>Registrar llegada</strong>." : ""}
            ${solicitudTieneDisponibleEntrega(s) ? " Hay stock recibido para nueva entrega parcial o total." : ""}
            ${solicitudPuedeEntregaTotal(s) ? " Si ya está todo recibido, usa <strong>Entrega total</strong> para cerrar." : ""}
        </div>`;
    }
    if (contexto === "solicitante") {
        return `
        <div class="alert alert-info sg-orden-oc-alert">
            Tu solicitud ya tiene <strong>orden de compra (OC)</strong> registrada.
            Los ítems están en camino hacia Compras.
        </div>`;
    }
    return `
        <div class="alert alert-info sg-orden-oc-alert">
            Esta solicitud ya tiene <strong>orden de compra (OC)</strong> registrada.
            El solicitante ve el avance en el historial del flujo.
        </div>`;
}

export function renderTramitandoOcAlertHtml(s, options = {}) {
    const { contexto = "solicitante" } = options;
    if (esSolicitudSalidasAlmacen(s)) return "";
    const estado = normalizarEstado(s?.estado);
    if (estado !== "tramitando_oc") return "";

    if (contexto === "gestor") {
        return `
        <div class="alert alert-info sg-tramitando-oc-alert">
            Esta solicitud está lista para <strong>registrar la orden de compra (OC)</strong>.
            Indica el número y valor del trámite (general o por ítem) y guarda para continuar
            el proceso hacia entrega.
        </div>`;
    }

    return `
        <div class="alert alert-info sg-tramitando-oc-alert">
            Tu solicitud fue aprobada y está <strong>en trámite de orden de compra (OC)</strong>.
            Compras registrará el número y valor; recibirás notificación cuando la OC quede registrada.
        </div>`;
}

export function buildLideresOptionsHtml(selectedId = "") {
    return LIDERES_COLBEEF.map(
        (l) =>
            `<option value="${escapeHtml(l.id)}" data-label="${escapeHtml(l.label)}"${
                l.id === selectedId ? " selected" : ""
            }>${escapeHtml(l.label)}</option>`
    ).join("");
}

export function renderAnticipoDetalleHtml(s) {
    if (!s?.requiere_anticipo) return "";
    const pct =
        s.porcentaje_anticipo !== null && s.porcentaje_anticipo !== undefined
            ? `${Number(s.porcentaje_anticipo)}%`
            : "—";
    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Anticipo</h3>
            <dl class="sg-detail-grid">
                <div class="sg-detail-field">
                    <dt>Porcentaje</dt>
                    <dd>${escapeHtml(pct)}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Monto estimado</dt>
                    <dd>${formatValorTramiteOc(s.monto_anticipo)}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Líder aprobador</dt>
                    <dd>${escapeHtml(s.lider_anticipo_label || "—")}</dd>
                </div>
                ${
                    s.observaciones_anticipo
                        ? `<div class="sg-detail-field sg-detail-field-full">
                    <dt>Observaciones</dt>
                    <dd>${escapeHtml(s.observaciones_anticipo)}</dd>
                </div>`
                        : ""
                }
            </dl>
        </div>`;
}

export function renderAnticipoTramiteFormHtml(lideresOptionsHtml = "") {
    return `
        <div class="sg-detail-panel sg-gestion-form-panel sg-anticipo-panel" id="panel-anticipo-tramite">
            <h3 class="sg-detail-panel-title">Anticipo</h3>
            <p class="muted sg-detail-panel-hint">
                Indica si esta orden de compra requiere anticipo. Si aplica, el líder seleccionado
                deberá aprobarlo antes de pasar al módulo de Gestión anticipo.
            </p>
            <label class="sg-checkbox-row">
                <input type="checkbox" id="gestion-requiere-anticipo" />
                Requiere anticipo
            </label>
            <div id="gestion-anticipo-campos" class="sg-anticipo-campos" hidden>
                <div class="row-2">
                    <div class="field">
                        <label for="gestion-porcentaje-anticipo">Porcentaje de anticipo (%)</label>
                        <input
                            type="number"
                            id="gestion-porcentaje-anticipo"
                            class="input-table"
                            min="0.01"
                            max="100"
                            step="0.01"
                            placeholder="Ej: 30"
                            autocomplete="off"
                        />
                    </div>
                    <div class="field">
                        <label for="gestion-lider-anticipo">Líder aprobador del anticipo</label>
                        <select id="gestion-lider-anticipo" class="input-table">
                            <option value="">Seleccione líder...</option>
                            ${lideresOptionsHtml}
                        </select>
                    </div>
                </div>
                <div class="field">
                    <label for="gestion-observaciones-anticipo">Observaciones del anticipo</label>
                    <textarea
                        id="gestion-observaciones-anticipo"
                        rows="3"
                        class="input-table"
                        placeholder="Detalle o soporte del anticipo (opcional)"
                    ></textarea>
                </div>
            </div>
        </div>`;
}

export function esGestionServiciosPostAprobacion(estado) {
    return normalizarEstado(estado) === "gestionando_servicio";
}

export function anticipoServicioGestionado(s) {
    return Boolean(s?.anticipo_gestionado);
}

export function gestionValorServicioRegistrada(s) {
    return Boolean(s?.gestion_valor_registrada);
}

export const CLASIFICACION_DOCUMENTO_SERVICIO_LABEL = {
    orden_servicio: "Orden de Servicio",
    orden_trabajo: "Orden de Trabajo",
    contrato: "Contrato",
};

export const UMBRAL_ORDEN_SERVICIO = 5_000_000;
export const UMBRAL_CONTRATO = 10_000_000;

export function clasificarDocumentoServicio(valor) {
    const n = Number(valor);
    if (!Number.isFinite(n) || n <= 0) return "";
    if (n < UMBRAL_ORDEN_SERVICIO) return "orden_servicio";
    if (n <= UMBRAL_CONTRATO) return "orden_trabajo";
    return "contrato";
}

export function bindClasifCotizacionElegida() {
    const vivo = document.getElementById("sg-cotizacion-clasif-viva");
    if (!vivo) return;
    const sync = () => {
        const radio = document.querySelector('input[name="cotizacion-elegida"]:checked');
        if (!radio) {
            vivo.textContent = "";
            return;
        }
        const moneda = radio.dataset.moneda || "COP";
        const valor = radio.dataset.valor;
        if (moneda !== "COP") {
            vivo.textContent =
                "El valor no está en pesos: al aprobar se guarda el monto, pero no se aplica el umbral de orden de trabajo / contrato.";
            return;
        }
        const key = clasificarDocumentoServicio(valor);
        const label = labelClasificacionDocumentoServicio(key);
        if (!label) {
            vivo.textContent = "";
            return;
        }
        const monto = previewValorCotizacion(valor, "COP");
        if (key === "orden_servicio") {
            vivo.textContent = `${monto} → Orden de Servicio. Compras cierra el servicio; no se radica en Jurídica.`;
        } else if (key === "orden_trabajo") {
            vivo.textContent = `${monto} → Orden de Trabajo. Tras aprobar, Compras la radica en Jurídica.`;
        } else {
            vivo.textContent = `${monto} → Contrato. Tras aprobar, Compras lo radica en Jurídica.`;
        }
    };
    document.querySelectorAll('input[name="cotizacion-elegida"]').forEach((radio) => {
        radio.addEventListener("change", sync);
        const card = radio.closest(".sg-cotizacion-slot--vista");
        card?.addEventListener("click", (ev) => {
            if (ev.target.closest("a, input, label")) return;
            radio.checked = true;
            radio.dispatchEvent(new Event("change"));
        });
    });
    sync();
}

export function labelClasificacionDocumentoServicio(keyOrSolicitud) {
    if (keyOrSolicitud && typeof keyOrSolicitud === "object") {
        const fromApi = (keyOrSolicitud.clasificacion_documento_servicio_label || "").trim();
        if (fromApi) return fromApi;
        const key = keyOrSolicitud.clasificacion_documento_servicio || "";
        return CLASIFICACION_DOCUMENTO_SERVICIO_LABEL[key] || "";
    }
    return CLASIFICACION_DOCUMENTO_SERVICIO_LABEL[keyOrSolicitud] || "";
}

/** Fase capturar valor o completar anticipo (aún no omitido/gestionado). */
export function esGestionServiciosCapturaValor(s) {
    return false;
}

export function esGestionServiciosSolicitarAnticipo(s) {
    return false;
}

export function esGestionServiciosContinuacionPostAnticipo(s) {
    const estado = normalizarEstado(s?.estado);
    if (!esSolicitudServicios(s)) return false;
    if (estado === "pendiente_evidencia_cierre") return true;
    if (estado !== "gestionando_servicio") return false;
    return (
        anticipoServicioGestionado(s) ||
        gestionValorServicioRegistrada(s) ||
        Boolean(s.valor_tramite_oc)
    );
}

export function puedeRadicarContratoDesdeServicio(s) {
    const clasif = s?.clasificacion_documento_servicio || "";
    return (
        esSolicitudServicios(s) &&
        (clasif === "orden_trabajo" || clasif === "contrato") &&
        (gestionValorServicioRegistrada(s) || anticipoServicioGestionado(s)) &&
        !s.contrato_id
    );
}

export function esGestionServiciosPanelActivo(s) {
    const estado = normalizarEstado(s?.estado);
    return (
        esSolicitudServicios(s) &&
        (esGestionServiciosPostAprobacion(estado) || estado === "pendiente_evidencia_cierre")
    );
}

export function renderClasificacionDocumentoBadgeHtml(key) {
    const label = labelClasificacionDocumentoServicio(key);
    if (!label) return "";
    return `<span class="badge badge-sg-aprobacion sg-clasificacion-doc-badge">${escapeHtml(label)}</span>`;
}

export function renderPanelServiciosPostAnticipoGestionadoHtml(s) {
    const esperandoEvidencia =
        normalizarEstado(s.estado) === "pendiente_evidencia_cierre";
    const evidenciaHtml = esperandoEvidencia ? renderEvidenciaSolicitanteCierreHtml(s) : "";
    const conEvidencia = tieneEvidenciaSolicitanteCierre(s);
    const clasifLabel = labelClasificacionDocumentoServicio(s);
    const clasifBadge = clasifLabel
        ? `<p class="sg-clasificacion-doc-live">
                <span class="muted">Clasificación:</span>
                ${renderClasificacionDocumentoBadgeHtml(s.clasificacion_documento_servicio)}
           </p>`
        : "";
    const vinculoHtml =
        s.contrato_codigo || s.contrato_id
            ? `<p class="sg-clasificacion-doc-live">
                    <span class="muted">Documento vinculado:</span>
                    <strong class="codigo-contrato">${escapeHtml(s.contrato_codigo || `ID ${s.contrato_id}`)}</strong>
               </p>`
            : "";

    let hintHtml;
    if (esperandoEvidencia && conEvidencia) {
        hintHtml = `<p class="muted sg-detail-panel-hint">
            El solicitante registró evidencia de cierre. Revísala y confirma el cierre del servicio.
        </p>`;
    } else if (esperandoEvidencia) {
        hintHtml = `<p class="muted sg-detail-panel-hint">
            El solicitante fue notificado para adjuntar evidencia y observación de cierre.
            La solicitud quedará en este estado hasta que responda desde
            <strong>Mis solicitudes</strong>.
        </p>`;
    } else if (anticipoServicioGestionado(s)) {
        hintHtml = `<p class="muted sg-detail-panel-hint">
            El anticipo ya fue gestionado. Registra tu observación y notifica al solicitante
            para que adjunte evidencia y comentario de cierre.
        </p>`;
    } else {
        hintHtml = `<p class="muted sg-detail-panel-hint">
            Continúa con la observación del gestor y notifica al solicitante para evidencia de cierre.
        </p>`;
    }

    return `
        <div class="sg-detail-panel sg-gestion-form-panel sg-servicio-post-anticipo-panel">
            <h3 class="sg-detail-panel-title">Continuar gestión del servicio</h3>
            ${hintHtml}
            ${clasifBadge}
            ${vinculoHtml}
            ${evidenciaHtml}
            ${renderAnticipoDetalleHtml(s)}
        </div>`;
}

export function renderAnticipoServicioGestionHtml(s, lideresOptionsHtml = "") {
    const valor =
        s.valor_tramite_oc !== null && s.valor_tramite_oc !== undefined
            ? String(s.valor_tramite_oc)
            : "";
    const pct =
        s.porcentaje_anticipo !== null && s.porcentaje_anticipo !== undefined
            ? String(s.porcentaje_anticipo)
            : "";
    const clasifGuardada = s.clasificacion_documento_servicio || clasificarDocumentoServicio(valor);
    const labelClasif = labelClasificacionDocumentoServicio(clasifGuardada) || "—";
    const requiere = Boolean(s.requiere_anticipo);

    return `
        <div class="sg-detail-panel sg-gestion-form-panel sg-anticipo-servicio-panel">
            <h3 class="sg-detail-panel-title">Gestión del servicio</h3>
            <p class="muted sg-detail-panel-hint">
                Registra el <strong>valor total de la cotización</strong>. Según el monto se asigna
                automáticamente la etiqueta documental. El anticipo es opcional.
            </p>
            <div class="field">
                <label for="gestion-valor-servicio">
                    Valor total de la cotización
                    <span class="required">*</span>
                </label>
                <input
                    type="number"
                    id="gestion-valor-servicio"
                    class="input-table"
                    min="0.01"
                    step="0.01"
                    placeholder="Valor acordado / cotizado del servicio"
                    value="${escapeHtml(valor)}"
                    autocomplete="off"
                />
            </div>
            <div class="sg-clasificacion-doc-live" id="sg-clasificacion-doc-live">
                <span class="muted">Clasificación documental:</span>
                <span id="sg-clasificacion-doc-badge" class="badge badge-sg-aprobacion">
                    ${escapeHtml(labelClasif)}
                </span>
            </div>
            <fieldset class="sg-radio-group" id="sg-requiere-anticipo-servicio-group">
                <legend>
                    ¿Requiere anticipo?
                    <span class="required">*</span>
                </legend>
                <label class="sg-radio-option">
                    <input
                        type="radio"
                        name="requiere_anticipo_servicio"
                        value="si"
                        ${requiere ? "checked" : ""}
                    />
                    Sí
                </label>
                <label class="sg-radio-option">
                    <input
                        type="radio"
                        name="requiere_anticipo_servicio"
                        value="no"
                        ${!requiere ? "checked" : ""}
                    />
                    No
                </label>
            </fieldset>
            <div id="gestion-anticipo-servicio-campos" class="sg-anticipo-campos" ${requiere ? "" : "hidden"}>
                <div class="row-2">
                    <div class="field">
                        <label for="gestion-porcentaje-anticipo">
                            Porcentaje de anticipo (%)
                            <span class="required">*</span>
                        </label>
                        <input
                            type="number"
                            id="gestion-porcentaje-anticipo"
                            class="input-table"
                            min="0.01"
                            max="100"
                            step="0.01"
                            placeholder="Ej: 30"
                            value="${escapeHtml(pct)}"
                            autocomplete="off"
                        />
                    </div>
                    <div class="field">
                        <label for="gestion-lider-anticipo">
                            Líder aprobador del anticipo
                            <span class="required">*</span>
                        </label>
                        <select id="gestion-lider-anticipo" class="input-table">
                            <option value="">Seleccione líder...</option>
                            ${lideresOptionsHtml}
                        </select>
                    </div>
                </div>
                <div class="field">
                    <label for="gestion-observaciones-anticipo">Observaciones del anticipo</label>
                    <textarea
                        id="gestion-observaciones-anticipo"
                        rows="3"
                        class="input-table"
                        placeholder="Detalle o soporte del anticipo (opcional)"
                    >${escapeHtml(s.observaciones_anticipo || "")}</textarea>
                </div>
            </div>
        </div>`;
}

export function renderPanelGestionServiciosPostAprobacionHtml(s, lideresOptionsHtml) {
    const cotizaciones = (s.archivos || []).filter((a) => a.categoria === "cotizacion");
    const panelGestion = esGestionServiciosContinuacionPostAnticipo(s)
        ? renderPanelServiciosPostAnticipoGestionadoHtml(s)
        : renderAnticipoServicioGestionHtml(s, lideresOptionsHtml);

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}
            ${renderInformacionGeneralHtml(s, {
                showPresupuestado: false,
                showServiciosCampos: true,
                showFechaRegistro: true,
                showCreadoPor: true,
                showValorServicio: Boolean(s.valor_tramite_oc),
            })}
            ${renderServiciosDetalleHtml(s)}

            ${
                cotizaciones.length
                    ? renderArchivosHtml(s, {
                          categoria: "cotizacion",
                          titulo: "Cotizaciones registradas",
                      })
                    : ""
            }

            ${renderObservacionesTrazabilidadHtml(s)}
            ${renderArchivosHtml(s)}

            ${renderAgregarComentarioHtml({
                showIntro: false,
                showHint: false,
                showSaveButton: false,
                title: "Observación del gestor",
                label: "Comentario",
            })}

            ${panelGestion}
        </div>`;
}

export function esSolicitudSalidasAlmacen(solicitud) {
    return (solicitud?.tipo || "") === "salidas_almacen";
}

export function esSolicitudServicios(solicitud) {
    return (solicitud?.tipo || "") === "insumos_servicios";
}

function renderArchivosCategoriaHtml(archivos, categoria, titulo, solicitudId) {
    const list = (archivos || []).filter((a) => (a.categoria || "") === categoria);
    if (!list.length) return "";
    return `
        <div class="sg-detail-field sg-detail-field-full">
            <dt>${escapeHtml(titulo)}</dt>
            <dd>
                <ul class="sg-attachment-list">
                    ${list
                        .map(
                            (a) => `
                        <li class="sg-attachment-item">
                            <span class="sg-attachment-icon" aria-hidden="true">📎</span>
                            <div class="sg-attachment-info">
                                <strong>${escapeHtml(a.nombre_original)}</strong>
                                <span class="muted">${formatFileSize(a.tamano_bytes)}</span>
                            </div>
                            <a
                                href="#"
                                class="btn btn-secondary btn-sm"
                                data-download-url="/solicitudes-gestion/${solicitudId}/archivos/${a.id}"
                                data-filename="${escapeHtml(a.nombre_original)}"
                                data-mime-type="${escapeHtml(a.mime_type || "")}"
                            >Descargar</a>
                        </li>`
                        )
                        .join("")}
                </ul>
            </dd>
        </div>`;
}

export function renderInformacionGeneralHtml(s, options = {}) {
    const {
        liderTitulo = "Líder aprobador",
        showPresupuestado = true,
        showServiciosCampos = false,
        showFechaRegistro = false,
        showCreadoPor = false,
        showGestor = false,
        showTramiteOc = false,
        showValorServicio = false,
    } = options;

    const presupuestado =
        s.presupuestado === null || s.presupuestado === undefined
            ? "—"
            : s.presupuestado
              ? "Sí"
              : "No";
    const tramiteGeneral = (s.numero_tramite_oc || "").trim();
    const mostrarServicios = showServiciosCampos && esSolicitudServicios(s);
    const fechaProgramada =
        mostrarServicios && s.servicio_programado && s.fecha_servicio_programado
            ? formatDateOnly(s.fecha_servicio_programado)
            : "—";

    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Información general</h3>
            <dl class="sg-detail-grid">
                <div class="sg-detail-field">
                    <dt>Título</dt>
                    <dd>${escapeHtml(s.titulo)}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Estado actual</dt>
                    <dd>${badgeEstado(s.estado, s)}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Centro de costo</dt>
                    <dd>${escapeHtml(s.centro_costo_area)}</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>${escapeHtml(liderTitulo)}</dt>
                    <dd>${escapeHtml(s.lider_area_label || "—")}</dd>
                </div>
                ${
                    showPresupuestado && s.tipo === "compra"
                        ? `<div class="sg-detail-field">
                    <dt>Presupuestado</dt>
                    <dd>${presupuestado}</dd>
                </div>`
                        : ""
                }
                ${
                    mostrarServicios
                        ? `<div class="sg-detail-field">
                    <dt>Requiere visita</dt>
                    <dd>${
                        s.requiere_visita === null || s.requiere_visita === undefined
                            ? "—"
                            : s.requiere_visita
                              ? "Sí"
                              : "No"
                    }</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Necesita comité técnico</dt>
                    <dd>${
                        s.requiere_comite_tecnico === null || s.requiere_comite_tecnico === undefined
                            ? "—"
                            : s.requiere_comite_tecnico
                              ? "Sí"
                              : "No"
                    }</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Servicio programado</dt>
                    <dd>${
                        s.servicio_programado === null || s.servicio_programado === undefined
                            ? "—"
                            : s.servicio_programado
                              ? "Sí"
                              : "No"
                    }</dd>
                </div>
                <div class="sg-detail-field">
                    <dt>Fecha programada</dt>
                    <dd>${fechaProgramada}</dd>
                </div>`
                        : ""
                }
                ${
                    showGestor && s.gestor_username
                        ? `<div class="sg-detail-field">
                    <dt>Gestor asignado</dt>
                    <dd>${escapeHtml(s.gestor_username)}</dd>
                </div>`
                        : ""
                }
                ${
                    showFechaRegistro
                        ? `<div class="sg-detail-field">
                    <dt>Fecha de registro</dt>
                    <dd>${formatDate(s.created_at)}</dd>
                </div>`
                        : ""
                }
                ${
                    showCreadoPor && s.creado_por_username
                        ? `<div class="sg-detail-field">
                    <dt>Registrada por</dt>
                    <dd>${escapeHtml(s.creado_por_username)}</dd>
                </div>`
                        : ""
                }
                ${
                    showValorServicio &&
                    mostrarServicios &&
                    s.valor_tramite_oc !== null &&
                    s.valor_tramite_oc !== undefined
                        ? `<div class="sg-detail-field">
                    <dt>Valor del servicio</dt>
                    <dd>${formatValorTramiteOc(s.valor_tramite_oc)}</dd>
                </div>`
                        : ""
                }
                ${
                    showValorServicio &&
                    mostrarServicios &&
                    labelClasificacionDocumentoServicio(s)
                        ? `<div class="sg-detail-field">
                    <dt>Clasificación documental</dt>
                    <dd>${renderClasificacionDocumentoBadgeHtml(s.clasificacion_documento_servicio)}</dd>
                </div>`
                        : ""
                }
                ${
                    showValorServicio &&
                    mostrarServicios &&
                    (s.contrato_codigo || s.contrato_id)
                        ? `<div class="sg-detail-field">
                    <dt>Documento vinculado</dt>
                    <dd>
                        <a
                            class="codigo-contrato"
                            href="/app/compras/mis-solicitudes.html?q=${encodeURIComponent(s.contrato_codigo || "")}"
                            title="Ver documento radicado"
                        >${escapeHtml(s.contrato_codigo || `ID ${s.contrato_id}`)}</a>
                        <span class="muted"> (radicado desde esta SRV)</span>
                    </dd>
                </div>`
                        : ""
                }
                ${
                    showTramiteOc && tramiteGeneral
                        ? `<div class="sg-detail-field">
                    <dt>Trámite Orden de Compra</dt>
                    <dd>${escapeHtml(tramiteGeneral)}</dd>
                </div>`
                        : ""
                }
                ${
                    showTramiteOc &&
                    s.valor_tramite_oc !== null &&
                    s.valor_tramite_oc !== undefined
                        ? `<div class="sg-detail-field">
                    <dt>Valor trámite OC</dt>
                    <dd>${formatValorTramiteOc(s.valor_tramite_oc)}</dd>
                </div>`
                        : ""
                }
            </dl>
        </div>`;
}

export function renderProveedorSugeridoListaHtml(texto) {
    const lineas = String(texto || "")
        .split(/\r?\n/)
        .map((l) => l.replace(/^-\s*/, "").trim())
        .filter(Boolean);
    if (!lineas.length) return "";
    if (lineas.length === 1) return escapeHtml(lineas[0]);
    return `<ul class="sg-prov-lista">${lineas
        .map((l) => `<li>${escapeHtml(l)}</li>`)
        .join("")}</ul>`;
}

export function renderServiciosDetalleHtml(s) {
    if (!esSolicitudServicios(s)) return "";

    const descripcionHtml = (s.descripcion_servicio || "").trim();
    const archivos = s.archivos || [];

    return `
        <div class="sg-detail-panel">
            <h3 class="sg-detail-panel-title">Detalle del servicio</h3>
            <dl class="sg-detail-grid">
                ${
                    (s.proveedor_sugerido || "").trim()
                        ? `<div class="sg-detail-field sg-detail-field-full">
                    <dt>Proveedor(es) sugerido(s)</dt>
                    <dd>${renderProveedorSugeridoListaHtml(s.proveedor_sugerido)}</dd>
                </div>`
                        : ""
                }
                ${
                    descripcionHtml
                        ? `<div class="sg-detail-field sg-detail-field-full">
                    <dt>Descripción del servicio</dt>
                    <dd class="sg-rich-content">${descripcionHtml}</dd>
                </div>`
                        : ""
                }
                ${renderArchivosCategoriaHtml(archivos, "detalle_servicio", "Adjuntos del detalle", s.id)}
                ${renderArchivosCategoriaHtml(archivos, "ficha_tecnica", "Ficha técnica", s.id)}
                ${renderArchivosCategoriaHtml(archivos, "hoja_vida_equipo", "Hoja de vida del equipo", s.id)}
                ${renderVisitasProgramadasDetalleHtml(s)}
            </dl>
        </div>`;
}

function formatHoraVisita(hora) {
    if (!hora) return "—";
    const text = String(hora);
    return text.length >= 5 ? text.slice(0, 5) : text;
}

function etiquetaRolVisita(v) {
    const rol = (v.rol_programador || "").toLowerCase();
    if (rol === "proyectos") return "Proyectos";
    if (rol === "compras") return "Compras";
    return v.programador_visita || "";
}

export function renderVisitasProgramadasDetalleHtml(s) {
    if (!esSolicitudServicios(s)) return "";
    const visitas = s.visitas_programadas || [];
    if (!visitas.length) return "";
    return `
        <div class="sg-detail-field sg-detail-field-full">
            <dt>Visitas programadas</dt>
            <dd>
                <ul class="sg-visitas-detalle-list">
                    ${visitas
                        .map((v, i) => {
                            const rol = (v.rol_programador || "").toLowerCase();
                            const etiqueta = etiquetaRolVisita(v);
                            const badge = etiqueta
                                ? `<span class="sg-visita-rol-badge sg-visita-rol-${
                                      rol || "otro"
                                  }">${escapeHtml(etiqueta)}</span>`
                                : "";
                            return `
                        <li>
                            <strong>Visita ${i + 1}</strong> ${badge} —
                            Proveedor: ${escapeHtml(v.proveedor_visita || "—")}
                            ${
                                v.fecha_visita
                                    ? ` · Fecha: ${formatDateOnly(v.fecha_visita)}`
                                    : ""
                            }
                            ${v.hora_visita ? ` · Hora: ${formatHoraVisita(v.hora_visita)}` : ""}
                        </li>`;
                        })
                        .join("")}
                </ul>
            </dd>
        </div>`;
}

export function renderVisitaProgramadaRowHtml(visita = {}, { removable = true } = {}) {
    const fecha = visita.fecha_visita ? String(visita.fecha_visita).slice(0, 10) : "";
    const hora = visita.hora_visita ? formatHoraVisita(visita.hora_visita) : "";
    return `
        <div class="sg-visita-row sg-visita-row-compact" data-visita-row>
            <div class="sg-visita-row-fields">
                <div class="field sg-visita-field-proveedor">
                    <label>Proveedor que visita</label>
                    <input
                        type="text"
                        class="sg-visita-proveedor"
                        placeholder="Proveedor asignado"
                        value="${escapeHtml(visita.proveedor_visita || "")}"
                    />
                </div>
                <div class="field sg-visita-field-fecha">
                    <label>Fecha</label>
                    <input
                        type="date"
                        class="sg-visita-fecha input-date-compact"
                        value="${escapeHtml(fecha)}"
                    />
                </div>
                <div class="field sg-visita-field-hora">
                    <label>Hora</label>
                    <input type="time" class="sg-visita-hora" value="${escapeHtml(hora)}" />
                </div>
                ${
                    removable
                        ? `<button
                            type="button"
                            class="btn btn-sm btn-secondary btn-quitar-visita"
                            title="Quitar visita"
                            aria-label="Quitar visita"
                        >
                            ×
                        </button>`
                        : ""
                }
            </div>
        </div>`;
}

export function renderPanelGestionServiciosHtml(s, lideresOptionsHtml) {
    const cotizaciones = (s.archivos || []).filter((a) => a.categoria === "cotizacion");
    const adjuntarCotizacionesInicial = cotizaciones.length > 0;

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}
            ${renderInformacionGeneralHtml(s, {
                showPresupuestado: false,
                showServiciosCampos: true,
                showFechaRegistro: true,
                showCreadoPor: true,
            })}
            ${renderServiciosDetalleHtml(s)}

            ${renderObservacionesTrazabilidadHtml(s)}
            ${renderArchivosHtml(s)}

            ${renderAgregarComentarioHtml({
                showIntro: false,
                showHint: false,
                showSaveButton: false,
                title: "Observación del gestor",
                label: "Comentario",
            })}

            <div class="sg-detail-panel sg-gestion-form-panel">
                <h3 class="sg-detail-panel-title">Gestión del servicio</h3>

                <div class="field sg-adjuntar-cotizaciones-field">
                    <label>¿Adjuntar cotizaciones ahora?</label>
                    <div class="radio-group" id="sg-adjuntar-cotizaciones-group">
                        <label class="radio-option">
                            <input
                                type="radio"
                                name="adjuntar_cotizaciones"
                                value="no"
                                ${adjuntarCotizacionesInicial ? "" : "checked"}
                            />
                            No
                        </label>
                        <label class="radio-option">
                            <input
                                type="radio"
                                name="adjuntar_cotizaciones"
                                value="si"
                                ${adjuntarCotizacionesInicial ? "checked" : ""}
                            />
                            Sí
                        </label>
                    </div>
                    <p class="hint muted" id="sg-adjuntar-cotizaciones-hint">
                        Si eliges <strong>Sí</strong>, adjunta al menos 3 cotizaciones con su valor
                        y anticipo. Diego Serrano (Financiera) elige cuál aprueba o pide recotización.
                    </p>
                </div>

                <div
                    id="sg-cotizaciones-gestion-wrap"
                    class="sg-cotizaciones-gestion-wrap"
                    ${adjuntarCotizacionesInicial ? "" : "hidden"}
                >
                ${renderCotizacionesUploadHtml(cotizaciones.length, { conDatosEconomicos: true })}

                ${
                    cotizaciones.length
                        ? renderArchivosHtml(s, {
                              categoria: "cotizacion",
                              titulo: "Cotizaciones ya registradas",
                          })
                        : ""
                }

                <div class="field" id="gestion-justificacion-wrap" hidden>
                    <label for="gestion-justificacion">
                        Justificación
                        <span class="required">*</span>
                    </label>
                    <textarea
                        id="gestion-justificacion"
                        rows="3"
                        placeholder="Indica por qué se adjuntan menos de 3 cotizaciones..."
                    >${escapeHtml(s.justificacion_cotizaciones || "")}</textarea>
                </div>

                <p class="hint" id="sg-segunda-aprobacion-diego">
                    La segunda aprobación se envía automáticamente a
                    <strong>Diego Serrano — Dirección Administrativa y Financiera</strong>.
                    Él elige una cotización o pide recotización si ninguna le sirve.
                </p>
                </div>
            </div>
        </div>`;
}

export function renderPanelProgramarVisitaHtml(s) {
    // El formulario siempre inicia con una fila vacía: cada rol (Compras/Proyectos)
    // agenda su propia visita. Las visitas previas ya se ven en el detalle de arriba.
    const visitasIniciales = [{}];
    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}
            ${renderInformacionGeneralHtml(s, {
                showPresupuestado: false,
                showServiciosCampos: true,
                showFechaRegistro: true,
                showCreadoPor: true,
            })}
            ${renderServiciosDetalleHtml(s)}
            ${renderObservacionesTrazabilidadHtml(s)}
            ${renderArchivosHtml(s)}

            <div class="sg-detail-panel sg-gestion-form-panel">
                <h3 class="sg-detail-panel-title">Programar visita</h3>
                <p class="hint">
                    Antes de cotizar, agenda la visita: datos del proveedor, día y hora.
                    Al confirmar, la solicitud pasa a cotización.
                </p>
                <input type="radio" name="programar_visita" value="si" checked hidden />
                <div id="sg-visitas-programadas-wrap" class="sg-visitas-programadas-wrap">
                    <div class="sg-visitas-programadas-header">
                        <p class="hint muted" id="sg-visitas-hint">
                            Registra proveedor, fecha y hora de cada visita.
                        </p>
                        <button
                            type="button"
                            class="btn btn-secondary btn-sm"
                            id="btn-agregar-visita-programada"
                        >
                            + Agregar visita
                        </button>
                    </div>
                    <div id="sg-visitas-programadas-list">
                        ${visitasIniciales.map((v) => renderVisitaProgramadaRowHtml(v)).join("")}
                    </div>
                </div>

                <div class="field" style="margin-top:12px">
                    <label for="sg-visita-observacion">Observación (opcional)</label>
                    <textarea id="sg-visita-observacion" rows="2"
                        placeholder="Notas de la visita / acuerdos..."></textarea>
                </div>
                <div class="field">
                    <label for="sg-visita-adjuntos">Adjuntos (opcional)</label>
                    <input type="file" id="sg-visita-adjuntos" multiple />
                </div>
                <div class="modal-actions" style="margin-top:12px">
                    <button type="button" class="btn btn-primary" id="btn-confirmar-visita-programada">
                        Confirmar visita y continuar a cotización
                    </button>
                </div>
            </div>
        </div>`;
}

export function renderSalidasEntregaAlertHtml(s, options = {}) {
    const { contexto = "gestor" } = options;
    if (!esSolicitudSalidasAlmacen(s)) return "";
    const estado = normalizarEstado(s?.estado);
    if (!["recepcion_insumos", "entregado_parcial"].includes(estado)) return "";

    if (estado === "recepcion_insumos") {
        if (contexto === "solicitante") {
            return `
        <div class="alert alert-success sg-salidas-entrega-alert">
            <strong>Productos en almacén.</strong> Compras gestionará la entrega de los ítems
            aprobados de tu solicitud.
        </div>`;
        }
        return `
        <div class="alert alert-success sg-salidas-entrega-alert">
            Los productos ya están en almacén. Usa <strong>Entrega total</strong> o
            <strong>Entrega parcial</strong> cuando los entregues al solicitante.
        </div>`;
    }

    if (contexto === "solicitante") {
        return `
        <div class="alert alert-info sg-salidas-entrega-alert">
            Se registró una <strong>entrega parcial</strong>.
            ${solicitudTieneDisponibleEntrega(s) ? "Aún hay ítems pendientes de entrega." : ""}
            La solicitud permanece abierta hasta completar todos los insumos.
        </div>`;
    }
    return `
        <div class="alert alert-info sg-salidas-entrega-alert">
            <strong>Entrega parcial registrada.</strong>
            ${solicitudTieneDisponibleEntrega(s) ? "Quedan ítems pendientes por entregar." : "Revisa si falta cerrar con entrega total."}
        </div>`;
}

export function renderProductosTableHtml(productos, options = {}) {
    const {
        titulo = "Productos",
        modoSalidas = false,
        selectable = false,
        showEstado = false,
        soloAprobados = false,
        excluirNoAprobados = false,
        resaltarNoAprobados = false,
        cantidadEditable = false,
        showTramiteOcParcial = false,
        tramiteOcParcialEditable = false,
        showValorTramiteOcParcial = false,
        tramiteValorOcParcialEditable = false,
        showEntregaInfo = false,
        entregaParcialEditable = false,
        showRecepcionInfo = false,
        recepcionParcialEditable = false,
        panelId = null,
    } = options;

    let list = [...(productos || [])];
    if (excluirNoAprobados) {
        list = list.filter((p) => (p.estado_aprobacion || "pendiente") !== "no_aprobado");
    }
    if (soloAprobados) {
        list = list.filter((p) => (p.estado_aprobacion || "pendiente") === "aprobado");
    }

    if (!list.length) {
        if (soloAprobados) {
            return `<div class="sg-detail-panel"><p class="muted">No hay ítems aprobados para gestionar.</p></div>`;
        }
        return "";
    }

    const checkCol = selectable
        ? `<th class="col-check sg-aprobacion-check-col">Aprobar</th>`
        : "";
    const estadoCol = showEstado ? `<th>Estado aprobación</th>` : "";
    const tramiteParcialCol =
        showTramiteOcParcial || tramiteOcParcialEditable
            ? `<th>Trámite OC parcial</th>`
            : "";
    const valorTramiteParcialCol =
        showValorTramiteOcParcial || tramiteValorOcParcialEditable || tramiteOcParcialEditable
            ? `<th>Valor trámite OC</th>`
            : "";
    const entregaCols = showEntregaInfo
        ? `<th class="col-cantidad">Entregada</th>
           <th class="col-cantidad">Pendiente</th>
           <th>Estado entrega</th>`
        : "";
    const entregaParcialCols = entregaParcialEditable
        ? `<th class="col-check sg-entrega-parcial-check-col">Entregar</th>
           <th class="col-cantidad">Cant. a entregar</th>`
        : "";
    const recepcionCols = showRecepcionInfo
        ? `<th class="col-cantidad">Recibida</th>
           <th class="col-cantidad">Pend. recepción</th>
           <th>Estado recepción</th>`
        : "";
    const recepcionParcialCols = recepcionParcialEditable
        ? `<th class="col-check sg-recepcion-parcial-check-col">Recibió</th>
           <th class="col-cantidad">Cant. recibida</th>`
        : "";

    return `
        <div class="sg-detail-panel"${panelId ? ` id="${escapeHtml(panelId)}"` : ""}>
            <h3 class="sg-detail-panel-title">${escapeHtml(titulo)} (${list.length})</h3>
            <div class="table-responsive">
                <table class="table-gestion-solicitudes">
                    <thead>
                        <tr>
                            ${checkCol}
                            <th>Código Siimed</th>
                            ${modoSalidas ? "" : "<th>Unidad</th>"}
                            <th>Descripción</th>
                            ${modoSalidas ? "<th>Área consumo</th>" : ""}
                            <th>Centro costo</th>
                            <th class="col-cantidad">Cantidad</th>
                            ${estadoCol}
                            ${tramiteParcialCol}
                            ${valorTramiteParcialCol}
                            ${entregaCols}
                            ${entregaParcialCols}
                            ${recepcionCols}
                            ${recepcionParcialCols}
                        </tr>
                    </thead>
                    <tbody>
                        ${list
                            .map((p) => {
                                const noAprobado = p.estado_aprobacion === "no_aprobado";
                                const rowClass = noAprobado ? "sg-producto-no-aprobado" : "";
                                const cellClass = noAprobado && resaltarNoAprobados
                                    ? "sg-producto-no-aprobado-cell"
                                    : "";
                                const checkCell = selectable
                                    ? `<td class="col-check sg-aprobacion-check-col" data-label="Aprobar">
                                        <input
                                            type="checkbox"
                                            class="aprobacion-producto-check"
                                            value="${p.id}"
                                            checked
                                            aria-label="Aprobar ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                    : "";
                                const estadoCell = showEstado
                                    ? `<td data-label="Estado">${badgeEstadoProducto(p.estado_aprobacion)}</td>`
                                    : "";
                                const msgNoAprobado =
                                    noAprobado && resaltarNoAprobados
                                        ? `<p class="sg-producto-no-aprobado-msg">El líder no aprobó este ítem</p>`
                                        : "";
                                const cantidadVal = formatCantidad(p.cantidad ?? 1);
                                const cantidadCell = cantidadEditable
                                    ? `<td data-label="Cantidad">
                                        <input
                                            type="number"
                                            class="input-table sg-producto-cantidad-input"
                                            data-producto-id="${p.id}"
                                            value="${escapeHtml(cantidadVal)}"
                                            min="0.0001"
                                            step="any"
                                            aria-label="Cantidad de ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                    : `<td class="${cellClass} sg-producto-cantidad-cell" data-label="Cantidad">${escapeHtml(cantidadVal)}</td>`;
                                const tramiteParcialVal = (p.numero_tramite_oc || "").trim();
                                const valorTramiteVal =
                                    p.valor_tramite_oc !== null && p.valor_tramite_oc !== undefined
                                        ? String(p.valor_tramite_oc)
                                        : "";
                                const tramiteParcialCell =
                                    tramiteOcParcialEditable
                                        ? `<td data-label="Trámite OC parcial">
                                        <input
                                            type="text"
                                            class="input-table sg-tramite-oc-parcial-input"
                                            data-producto-id="${p.id}"
                                            value="${escapeHtml(tramiteParcialVal)}"
                                            placeholder="Nº trámite parcial"
                                            aria-label="Trámite OC parcial de ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                        : showTramiteOcParcial
                                          ? `<td data-label="Trámite OC parcial">${escapeHtml(tramiteParcialVal || "—")}</td>`
                                          : "";
                                const valorTramiteParcialCell =
                                    tramiteValorOcParcialEditable || tramiteOcParcialEditable
                                        ? `<td data-label="Valor trámite OC">
                                        <input
                                            type="number"
                                            class="input-table sg-tramite-oc-valor-input"
                                            data-producto-id="${p.id}"
                                            value="${escapeHtml(valorTramiteVal)}"
                                            min="0"
                                            step="0.01"
                                            placeholder="Valor OC"
                                            aria-label="Valor trámite OC de ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                        : showValorTramiteOcParcial || showTramiteOcParcial
                                          ? `<td data-label="Valor trámite OC">${formatValorTramiteOc(p.valor_tramite_oc)}</td>`
                                          : "";
                                const entregadaVal = formatCantidad(p.cantidad_entregada ?? 0);
                                const pendienteVal = formatCantidad(
                                    p.cantidad_pendiente ?? calcCantidadPendiente(p)
                                );
                                const entregaInfoCells = showEntregaInfo
                                    ? `<td class="sg-producto-cantidad-cell" data-label="Entregada">${escapeHtml(entregadaVal)}</td>
                                       <td class="sg-producto-cantidad-cell" data-label="Pendiente">${escapeHtml(pendienteVal)}</td>
                                       <td data-label="Estado entrega">${badgeEstadoEntrega(p.estado_entrega || (Number(p.cantidad_entregada || 0) <= 0 ? "pendiente" : Number(p.cantidad_entregada) >= Number(p.cantidad || 1) ? "entregado" : "parcial"))}</td>`
                                    : "";
                                const pendienteNum = calcCantidadPendiente(p);
                                const disponibleEntregaNum = calcCantidadDisponibleEntrega(p);
                                const entregaParcialCells =
                                    entregaParcialEditable && disponibleEntregaNum > 0
                                        ? `<td class="col-check sg-entrega-parcial-check-col" data-label="Entregar">
                                        <input
                                            type="checkbox"
                                            class="entrega-parcial-check"
                                            value="${p.id}"
                                            data-pendiente="${disponibleEntregaNum}"
                                            aria-label="Entregar ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>
                                    <td data-label="Cant. a entregar">
                                        <input
                                            type="number"
                                            class="input-table sg-entrega-parcial-cantidad"
                                            data-producto-id="${p.id}"
                                            data-pendiente="${disponibleEntregaNum}"
                                            value=""
                                            min="0.0001"
                                            max="${disponibleEntregaNum}"
                                            step="any"
                                            placeholder="Máx. ${escapeHtml(formatCantidad(disponibleEntregaNum))}"
                                            aria-label="Cantidad a entregar de ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                        : entregaParcialEditable
                                          ? `<td colspan="2" class="muted" data-label="Entrega">Sin stock recibido</td>`
                                          : "";
                                const recibidaVal = formatCantidad(p.cantidad_recibida ?? 0);
                                const pendienteRecepcionVal = formatCantidad(
                                    p.cantidad_pendiente_recepcion ??
                                        calcCantidadPendienteRecepcion(p)
                                );
                                const recepcionInfoCells = showRecepcionInfo
                                    ? `<td class="sg-producto-cantidad-cell" data-label="Recibida">${escapeHtml(recibidaVal)}</td>
                                       <td class="sg-producto-cantidad-cell" data-label="Pend. recepción">${escapeHtml(pendienteRecepcionVal)}</td>
                                       <td data-label="Estado recepción">${badgeEstadoRecepcion(
                                           p.estado_recepcion ||
                                               (Number(p.cantidad_recibida || 0) <= 0
                                                   ? "pendiente"
                                                   : Number(p.cantidad_recibida) >=
                                                       Number(p.cantidad || 1)
                                                     ? "recibido"
                                                     : "parcial")
                                       )}</td>`
                                    : "";
                                const pendienteRecepcionNum = calcCantidadPendienteRecepcion(p);
                                const recepcionParcialCells =
                                    recepcionParcialEditable && pendienteRecepcionNum > 0
                                        ? `<td class="col-check sg-recepcion-parcial-check-col" data-label="Recibió">
                                        <input
                                            type="checkbox"
                                            class="recepcion-parcial-check"
                                            value="${p.id}"
                                            data-pendiente="${pendienteRecepcionNum}"
                                            aria-label="Recibir ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>
                                    <td data-label="Cant. recibida">
                                        <input
                                            type="number"
                                            class="input-table sg-recepcion-parcial-cantidad"
                                            data-producto-id="${p.id}"
                                            data-pendiente="${pendienteRecepcionNum}"
                                            value=""
                                            min="0.0001"
                                            max="${pendienteRecepcionNum}"
                                            step="any"
                                            placeholder="Máx. ${escapeHtml(pendienteRecepcionVal)}"
                                            aria-label="Cantidad recibida de ${escapeHtml(p.descripcion)}"
                                        />
                                    </td>`
                                        : recepcionParcialEditable
                                          ? `<td colspan="2" class="muted" data-label="Recepción">Completo</td>`
                                          : "";
                                return `
                            <tr class="${rowClass}" data-producto-id="${p.id}">
                                ${checkCell}
                                <td class="${cellClass}" data-label="Código Siimed">${escapeHtml(p.codigo_siimed || "—")}</td>
                                ${modoSalidas ? "" : `<td class="${cellClass}" data-label="Unidad">${escapeHtml(p.unidad)}</td>`}
                                <td class="${cellClass}" data-label="Descripción">
                                    <span class="${noAprobado && resaltarNoAprobados ? "sg-producto-no-aprobado-text" : ""}">${escapeHtml(p.descripcion)}</span>
                                    ${msgNoAprobado}
                                </td>
                                ${modoSalidas ? `<td class="${cellClass}" data-label="Área consumo">${escapeHtml(p.area_consumo || "—")}</td>` : ""}
                                <td class="${cellClass}" data-label="Centro costo">${escapeHtml(p.centro_costo)}</td>
                                ${cantidadCell}
                                ${estadoCell}
                                ${tramiteParcialCell}
                                ${valorTramiteParcialCell}
                                ${entregaInfoCells}
                                ${entregaParcialCells}
                                ${recepcionInfoCells}
                                ${recepcionParcialCells}
                            </tr>`;
                            })
                            .join("")}
                    </tbody>
                </table>
            </div>
        </div>`;
}

export function renderDetalleSolicitudHtml(s, options = {}) {
    const {
        productosOptions = {},
        showAprobacionParcialAlert = true,
        seleccionarCotizacion = false,
    } = options;
    const tieneTramiteParcial = (s.productos || []).some((p) =>
        Boolean((p.numero_tramite_oc || "").trim())
    );
    const tramiteGeneral = (s.numero_tramite_oc || "").trim();

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}
            ${showAprobacionParcialAlert ? renderAprobacionParcialAlertHtml(s) : ""}
            ${renderSalidasEntregaAlertHtml(s, { contexto: "solicitante" })}
            ${renderTramitandoOcAlertHtml(s, { contexto: "solicitante" })}
            ${renderOrdenOcRegistradaAlertHtml(s, { contexto: "solicitante" })}

            ${renderInformacionGeneralHtml(s, {
                showServiciosCampos: true,
                showFechaRegistro: true,
                showCreadoPor: true,
                showTramiteOc: true,
            })}

            ${renderServiciosDetalleHtml(s)}

            ${
                esSolicitudServicios(s)
                    ? ""
                    : renderProductosTableHtml(s.productos, {
                ...productosOptions,
                modoSalidas: esSolicitudSalidasAlmacen(s),
                titulo: productosOptions.titulo
                    ?? (esSolicitudSalidasAlmacen(s) ? "Detalle de la salida" : "Productos"),
                showEstado:
                    productosOptions.showEstado ??
                    (tieneProductosNoAprobados(s.productos) ||
                        Boolean(s.aprobacion_parcial)),
                resaltarNoAprobados:
                    productosOptions.resaltarNoAprobados ??
                    (tieneProductosNoAprobados(s.productos) ||
                        Boolean(s.aprobacion_parcial)),
                showTramiteOcParcial:
                    productosOptions.showTramiteOcParcial ??
                    (tieneTramiteParcial || Boolean(tramiteGeneral)),
                showValorTramiteOcParcial:
                    productosOptions.showValorTramiteOcParcial ??
                    (tieneTramiteParcial ||
                        Boolean(tramiteGeneral) ||
                        (s.productos || []).some(
                            (p) =>
                                p.valor_tramite_oc !== null && p.valor_tramite_oc !== undefined
                        )),
                showEntregaInfo:
                    productosOptions.showEntregaInfo ??
                    (["tramitada_oc", "entregado_parcial", "entregado"].includes(
                        normalizarEstado(s.estado)
                    ) ||
                        (s.productos || []).some(
                            (p) => Number(p.cantidad_entregada || 0) > 0
                        )),
            })
            }

            ${renderArchivosHtml(s, {
                categoria: "cotizacion",
                titulo: "Cotizaciones",
                seleccionable: seleccionarCotizacion,
            })}

            ${renderObservacionesTrazabilidadHtml(s)}

            ${renderArchivosHtml(s)}
            ${renderAnticipoDetalleHtml(s)}
        </div>`;
}

export function renderPanelGestionHtml(s, lideresOptionsHtml) {
    const cotizaciones = (s.archivos || []).filter((a) => a.categoria === "cotizacion");

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}

            ${renderInformacionGeneralHtml(s, {
                liderTitulo: "Líder aprobador inicial",
                showServiciosCampos: false,
                showGestor: true,
            })}

            ${renderAprobacionParcialAlertHtml(s)}

            ${renderProductosTableHtml(s.productos, {
                titulo: tieneProductosNoAprobados(s.productos)
                    ? "Productos aprobados"
                    : "Productos",
                excluirNoAprobados: true,
                showEstado: false,
            })}

            ${renderObservacionesTrazabilidadHtml(s)}

            ${renderArchivosHtml(s)}

            ${renderAgregarComentarioHtml({
                showIntro: false,
                showHint: false,
                showSaveButton: false,
                title: "Observación del gestor",
                label: "Comentario",
            })}

            <div class="sg-detail-panel sg-gestion-form-panel">
                <h3 class="sg-detail-panel-title">Gestión de cotización</h3>

                ${renderCotizacionesUploadHtml(cotizaciones.length)}

                ${
                    cotizaciones.length
                        ? renderArchivosHtml(s, {
                              categoria: "cotizacion",
                              titulo: "Cotizaciones ya registradas",
                          })
                        : ""
                }

                <div class="field" id="gestion-justificacion-wrap" hidden>
                    <label for="gestion-justificacion">
                        Justificación
                        <span class="required">*</span>
                    </label>
                    <textarea
                        id="gestion-justificacion"
                        rows="3"
                        placeholder="Indica por qué se adjuntan menos de 3 cotizaciones..."
                    >${escapeHtml(s.justificacion_cotizaciones || "")}</textarea>
                </div>

                <div class="field">
                    <label for="gestion-lider-aprobacion">
                        Líder Colbeef — segunda aprobación
                        <span class="required">*</span>
                    </label>
                    <select id="gestion-lider-aprobacion" required>
                        <option value="">Selecciona un líder</option>
                        ${lideresOptionsHtml}
                    </select>
                </div>
            </div>
        </div>`;
}

export function renderPanelSalidasEntregaHtml(s) {
    const estado = normalizarEstado(s.estado);
    const esEntregaParcial = estado === "entregado_parcial";
    const esRecepcionInsumos = estado === "recepcion_insumos";
    const mostrarEntregaInfo =
        esEntregaParcial ||
        esRecepcionInsumos ||
        (s.productos || []).some((p) => Number(p.cantidad_entregada || 0) > 0);

    const panelEntregaParcial = solicitudTieneDisponibleEntrega(s)
        ? `
            <div class="sg-detail-panel sg-gestion-form-panel sg-entrega-parcial-panel" id="panel-entrega-parcial-wrap" hidden>
                <h3 class="sg-detail-panel-title">Registrar entrega parcial al solicitante</h3>
                <p class="muted sg-detail-panel-hint">
                    Selecciona los ítems a entregar e indica la cantidad de esta entrega.
                    La solicitud permanece abierta mientras queden insumos pendientes.
                </p>
                ${renderProductosTableHtml(s.productos, {
                    titulo: "Ítems disponibles para entrega",
                    modoSalidas: true,
                    excluirNoAprobados: true,
                    showEntregaInfo: true,
                    entregaParcialEditable: true,
                    panelId: "sg-entrega-parcial-table",
                })}
            </div>`
        : "";

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}

            <div class="sg-detail-panel">
                <h3 class="sg-detail-panel-title">Información general</h3>
                <dl class="sg-detail-grid">
                    <div class="sg-detail-field">
                        <dt>Título</dt>
                        <dd>${escapeHtml(s.titulo)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Estado actual</dt>
                        <dd>${badgeEstado(s.estado, s)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Centro de costo</dt>
                        <dd>${escapeHtml(s.centro_costo_area)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Líder aprobador inicial</dt>
                        <dd>${escapeHtml(s.lider_area_label || "—")}</dd>
                    </div>
                    ${
                        s.gestor_username
                            ? `<div class="sg-detail-field">
                        <dt>Gestor asignado</dt>
                        <dd>${escapeHtml(s.gestor_username)}</dd>
                    </div>`
                            : ""
                    }
                </dl>
            </div>

            ${renderAprobacionParcialAlertHtml(s)}
            ${renderSalidasEntregaAlertHtml(s, { contexto: "gestor" })}

            <div class="sg-detail-panel sg-gestion-form-panel">
                <h3 class="sg-detail-panel-title">Gestión de entrega de almacén</h3>
                <p class="muted sg-detail-panel-hint">
                    Los productos solicitados ya se encuentran en almacén. Registra la entrega
                    al solicitante; puede ser total o parcial mientras queden ítems pendientes.
                </p>
            </div>

            ${renderProductosTableHtml(s.productos, {
                modoSalidas: true,
                titulo: "Detalle de la salida",
                excluirNoAprobados: true,
                showEntregaInfo: mostrarEntregaInfo,
                showEstado: false,
            })}

            ${panelEntregaParcial}

            ${renderObservacionesTrazabilidadHtml(s)}

            ${renderArchivosHtml(s)}

            ${renderAgregarComentarioHtml({
                showIntro: false,
                showHint: false,
                showSaveButton: false,
                title: "Observación del gestor",
                label: "Comentario",
            })}
        </div>`;
}

export function renderPanelTramiteOcHtml(s) {
    if (esSolicitudSalidasAlmacen(s)) {
        return renderPanelSalidasEntregaHtml(s);
    }
    const presupuestado =
        s.presupuestado === null || s.presupuestado === undefined
            ? "—"
            : s.presupuestado
              ? "Sí"
              : "No";
    const estado = normalizarEstado(s.estado);
    const esEntregaParcial = estado === "entregado_parcial";
    const esTramitandoOc = estado === "tramitando_oc";
    const esItemsEnCamino = estado === "items_en_camino";
    const esRecepcionInsumos = estado === "recepcion_insumos";
    const mostrarEntregaInfo =
        esEntregaParcial ||
        esRecepcionInsumos ||
        (s.productos || []).some((p) => Number(p.cantidad_entregada || 0) > 0);
    const mostrarRecepcionInfo =
        esItemsEnCamino ||
        esRecepcionInsumos ||
        (s.productos || []).some((p) => Number(p.cantidad_recibida || 0) > 0);

    const panelOcEditable = esTramitandoOc && !esEntregaParcial
        ? `
            <div class="sg-detail-panel sg-gestion-form-panel">
                <h3 class="sg-detail-panel-title">Trámite Orden de Compra</h3>
                <p class="muted sg-detail-panel-hint">
                    Registra el número y valor del trámite OC para toda la solicitud o, si aplica,
                    un registro distinto por cada ítem aprobado.
                </p>
                <div class="row-2">
                    <div class="field">
                        <label for="gestion-tramite-oc-general">
                            Trámite Orden de Compra (solicitud completa)
                        </label>
                        <input
                            type="text"
                            id="gestion-tramite-oc-general"
                            class="input-table"
                            value="${escapeHtml(s.numero_tramite_oc || "")}"
                            placeholder="Número de trámite OC general"
                            autocomplete="off"
                        />
                    </div>
                    <div class="field">
                        <label for="gestion-tramite-oc-valor-general">
                            Valor trámite OC (solicitud completa)
                        </label>
                        <input
                            type="number"
                            id="gestion-tramite-oc-valor-general"
                            class="input-table"
                            value="${
                                s.valor_tramite_oc !== null && s.valor_tramite_oc !== undefined
                                    ? escapeHtml(String(s.valor_tramite_oc))
                                    : ""
                            }"
                            min="0"
                            step="0.01"
                            placeholder="Valor en pesos"
                            autocomplete="off"
                        />
                    </div>
                </div>
            </div>

            ${renderProductosTableHtml(s.productos, {
                titulo: tieneProductosNoAprobados(s.productos)
                    ? "Trámite OC parcial por ítem aprobado"
                    : "Trámite OC parcial por ítem",
                excluirNoAprobados: true,
                showEstado: false,
                tramiteOcParcialEditable: true,
                tramiteValorOcParcialEditable: true,
            })}

            ${renderAnticipoTramiteFormHtml(buildLideresOptionsHtml())}`
        : `
            <div class="sg-detail-panel">
                <h3 class="sg-detail-panel-title">Trámite Orden de Compra</h3>
                <dl class="sg-detail-grid">
                    <div class="sg-detail-field">
                        <dt>Trámite OC general</dt>
                        <dd>${escapeHtml((s.numero_tramite_oc || "").trim() || "—")}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Valor trámite OC general</dt>
                        <dd>${formatValorTramiteOc(s.valor_tramite_oc)}</dd>
                    </div>
                </dl>
            </div>
            ${renderProductosTableHtml(s.productos, {
                titulo: "Trámite OC por ítem",
                excluirNoAprobados: true,
                showEstado: false,
                showTramiteOcParcial: solicitudTieneOcRegistrada(s),
                showValorTramiteOcParcial: solicitudTieneOcRegistrada(s),
            })}`;

    const panelRecepcionParcial =
        solicitudTieneOcRegistrada(s) && solicitudTieneRecepcionPendiente(s)
            ? `
            <div class="sg-detail-panel sg-gestion-form-panel sg-recepcion-parcial-panel" id="panel-recepcion-parcial-wrap" hidden>
                <h3 class="sg-detail-panel-title">Registrar llegada de ítems</h3>
                <p class="muted sg-detail-panel-hint">
                    Selecciona los ítems que llegaron físicamente a Compras e indica la cantidad recibida.
                    El solicitante será notificado cuando pase a <strong>Recepción de Insumos</strong>.
                </p>
                ${renderProductosTableHtml(s.productos, {
                    titulo: "Ítems pendientes de recepción",
                    excluirNoAprobados: true,
                    showRecepcionInfo: true,
                    recepcionParcialEditable: true,
                    panelId: "sg-recepcion-parcial-table",
                })}
            </div>`
            : "";

    const panelEntregaParcial =
        solicitudTieneOcRegistrada(s) && solicitudTieneDisponibleEntrega(s)
            ? `
            <div class="sg-detail-panel sg-gestion-form-panel sg-entrega-parcial-panel" id="panel-entrega-parcial-wrap" hidden>
                <h3 class="sg-detail-panel-title">Registrar entrega parcial al solicitante</h3>
                <p class="muted sg-detail-panel-hint">
                    Selecciona los ítems a entregar e indica la cantidad de esta entrega
                    (solo lo ya recibido físicamente en Compras).
                </p>
                ${renderProductosTableHtml(s.productos, {
                    titulo: "Ítems disponibles para entrega",
                    excluirNoAprobados: true,
                    showEntregaInfo: true,
                    showRecepcionInfo: true,
                    entregaParcialEditable: true,
                    panelId: "sg-entrega-parcial-table",
                })}
            </div>`
            : "";

    return `
        <div class="sg-detail-layout">
            ${renderWorkflowTimelineHtml(s)}

            <div class="sg-detail-panel">
                <h3 class="sg-detail-panel-title">Información general</h3>
                <dl class="sg-detail-grid">
                    <div class="sg-detail-field">
                        <dt>Título</dt>
                        <dd>${escapeHtml(s.titulo)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Estado actual</dt>
                        <dd>${badgeEstado(s.estado, s)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Centro de costo</dt>
                        <dd>${escapeHtml(s.centro_costo_area)}</dd>
                    </div>
                    <div class="sg-detail-field">
                        <dt>Líder aprobador inicial</dt>
                        <dd>${escapeHtml(s.lider_area_label || "—")}</dd>
                    </div>
                    ${
                        s.tipo === "compra"
                            ? `<div class="sg-detail-field">
                        <dt>Presupuestado</dt>
                        <dd>${presupuestado}</dd>
                    </div>`
                            : ""
                    }
                    ${
                        s.gestor_username
                            ? `<div class="sg-detail-field">
                        <dt>Gestor asignado</dt>
                        <dd>${escapeHtml(s.gestor_username)}</dd>
                    </div>`
                            : ""
                    }
                </dl>
            </div>

            ${renderAprobacionParcialAlertHtml(s)}

            ${esTramitandoOc ? renderTramitandoOcAlertHtml(s, { contexto: "gestor" }) : ""}

            ${renderOrdenOcRegistradaAlertHtml(s)}

            ${panelOcEditable}

            ${
                mostrarRecepcionInfo && (esRecepcionInsumos || esItemsEnCamino)
                    ? renderProductosTableHtml(s.productos, {
                          titulo: "Estado de recepción por ítem",
                          excluirNoAprobados: true,
                          showRecepcionInfo: true,
                      })
                    : ""
            }

            ${panelRecepcionParcial}

            ${
                mostrarEntregaInfo && (esEntregaParcial || esRecepcionInsumos)
                    ? renderProductosTableHtml(s.productos, {
                          titulo: "Estado de entrega por ítem",
                          excluirNoAprobados: true,
                          showEntregaInfo: true,
                          showRecepcionInfo: true,
                      })
                    : ""
            }

            ${panelEntregaParcial}

            ${renderAnticipoDetalleHtml(s)}

            ${renderObservacionesTrazabilidadHtml(s)}

            ${renderArchivosHtml(s)}

            ${renderAgregarComentarioHtml({
                showIntro: false,
                showHint: false,
                showSaveButton: false,
                title: "Observación del gestor",
                label: "Comentario",
            })}
        </div>`;
}

export function attachGestionDownloadHandlers(container, onError) {
    if (!container) return;

    container.addEventListener("click", (e) => {
        const toggle = e.target.closest(".sg-obs-collapsible-toggle");
        if (toggle) {
            const panel = toggle.closest(".sg-obs-collapsible");
            const bodyId = toggle.getAttribute("aria-controls");
            const body = bodyId ? document.getElementById(bodyId) : null;
            if (!panel || !body) return;

            const expanded = toggle.getAttribute("aria-expanded") === "true";
            const next = !expanded;
            toggle.setAttribute("aria-expanded", next ? "true" : "false");
            panel.classList.toggle("sg-obs-collapsible--open", next);
            body.hidden = !next;
            return;
        }
    });

    container.addEventListener("click", async (e) => {
        const link = e.target.closest("a[data-download-url]");
        if (!link) return;
        e.preventDefault();

        const path = link.dataset.downloadUrl;
        const filename = link.dataset.filename || "archivo";
        const mimeType = link.dataset.mimeType || "";

        try {
            const response = await fetch(`${API_BASE}${path}?inline=1`, {
                headers: { Authorization: `Bearer ${session.getToken()}` },
            });
            if (!response.ok) {
                throw new Error(`No se pudo abrir el archivo (${response.status}).`);
            }
            const blob = await response.blob();
            const type = mimeType || blob.type || "application/octet-stream";
            const viewBlob = blob.type ? blob : new Blob([blob], { type });
            const url = URL.createObjectURL(viewBlob);
            const popup = window.open(url, "_blank", "noopener,noreferrer");
            if (!popup) {
                URL.revokeObjectURL(url);
                throw new Error(
                    "Permite ventanas emergentes en el navegador para visualizar el archivo."
                );
            }
        } catch (err) {
            onError?.(err.message || "No se pudo abrir el archivo.");
        }
    });
}

export async function hydrateInlineObservacionImages(container, solicitudId) {
    if (!container || !solicitudId) return;
    const token = session.getToken();
    if (!token) return;

    const imgs = container.querySelectorAll("img[data-sg-archivo-id]");
    await Promise.all(
        Array.from(imgs).map(async (img) => {
            const archivoId = img.getAttribute("data-sg-archivo-id");
            if (!archivoId || img.dataset.hydrated === "1") return;
            try {
                const response = await fetch(
                    `${API_BASE}/solicitudes-gestion/${solicitudId}/archivos/${archivoId}`,
                    { headers: { Authorization: `Bearer ${token}` } }
                );
                if (!response.ok) return;
                const blob = await response.blob();
                img.src = URL.createObjectURL(blob);
                img.dataset.hydrated = "1";
            } catch {
                /* ignorar fallo puntual de una imagen */
            }
        })
    );
}
