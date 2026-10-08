# Bitácora de versiones — JURICOM (WorkColbeef)

Cada versión corresponde a lo que está en producción (rama `master`).
Los diagramas de cada proceso están en [`docs/flujos/`](flujos/).

---

## JURICOM 1.3 — 08/10/2026

**Aprobaciones**
- En **Aprobar solicitudes**, cada aprobador puede consultar las solicitudes que ya revisó.
- La consulta muestra la decisión tomada, su fecha, el estado actual y el detalle de la solicitud.
- El Administrador puede consultar las decisiones de todos y el nombre de quien decidió.

**Panel de solicitudes (Compras)**
- La columna **Gestor** muestra el nombre registrado de la persona en lugar de su número interno.
  Si el usuario no tiene nombre registrado, se muestra su correo.

**Roles afectados:** Líder aprobador, Administrador, Compras.

---

## JURICOM 1.2 — 07/10/2026

**Panel de solicitudes (Compras)**
- Nueva columna **Gestor**: muestra quién gestiona cada solicitud, o "Sin gestor" si nadie la ha tomado.
- Nuevo filtro por gestor: *Mías y sin gestor* (por defecto para Compras), *Asignadas a mí*,
  *Sin gestor*, *Todos los gestores* y cada gestor por nombre.
- Nuevo estado **En gestión**: al dar clic en *Gestionar*, la solicitud ya no pasa directo a
  Cotización. Compras queda como gestor, la revisa y con el botón **Pasar a cotización** entra a
  Cotización (o a Programar visita si el servicio la requiere).
  Aplica a Compras (SG) y Servicios (SRV) sin comité técnico.
- Menor cuantía: desde *En gestión* Compras decide si la envía directo a Trámite OC, la pasa a
  cotizar o la devuelve a aprobación del líder.
- **Anular solicitud**: el gestor asignado o un Admin puede anularla en En gestión, Programar
  visita o Cotización (antes de la orden de compra), con motivo obligatorio. Queda en *Cancelado*,
  el motivo queda en la trazabilidad y se avisa por correo al supervisor y al líder.
- **Cambiar gestor**: el gestor asignado o un Admin puede reasignar la solicitud a otro usuario
  de Compras en cualquier etapa abierta. Queda en la trazabilidad y se avisa al nuevo gestor.
  El gestor es informativo: todo Compras puede seguir trabajando cualquier solicitud.

**Roles afectados:** Compras, Supervisor, Líder aprobador, Administrador.

---

## JURICOM 1.1 — 07/10/2026

- **Comité técnico:** los usuarios de mantenimiento (solicitantes) pueden ver las SRV en comité
  y sus cotizaciones, en solo lectura.
- **Manuales por rol:** cada usuario recibió por correo el manual de sus roles.
- **Corrección:** el usuario de Gerencia General muestra el nombre correcto
  (TORO GONZALEZ HANS SEBASTIAN).
- **Documentación:** diagramas de flujo de los 4 procesos (Compras, Salidas de Almacén,
  Salida de Consumibles y Servicios con Contrato u OS).

**Roles afectados:** Supervisor (mantenimiento), Proyectos, todos (manuales).

---

## JURICOM 1.0 — hasta 05/10/2026

- Gestión de solicitudes: Compras (SG), Salidas de Almacén (SA), Salida de Consumibles (SC)
  y Servicios (SRV) con comité técnico.
- Compras elige quién da la segunda aprobación: líder de la primera, Gerencia Financiera
  o Gerencia General.
- Contratos y Órdenes de Servicio en Jurídica: radicación, pólizas, firmas, anticipos
  (Contabilidad y Tesorería), otrosíes y cierre.
- Usuarios con varios roles (por ejemplo Supervisor + Jurídica).
- Manual de usuario general y por rol.
