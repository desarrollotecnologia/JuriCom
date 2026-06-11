# Juridica · Colbeef

Sistema unificado para los roles de **Jurídica**, **Compras** y **Administración** de Colbeef. Construido siguiendo **Clean Architecture** para que la base sea mantenible y escalable.

> Primer hito: autenticación con roles + módulo "Solicitud Radicar" del área de Compras.

---

## Stack tecnológico

| Capa       | Tecnología                                               |
| ---------- | -------------------------------------------------------- |
| Backend    | Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic v2         |
| Base datos | MySQL 8 (`Juridica`)                                     |
| Seguridad  | bcrypt + JWT (python-jose)                               |
| Frontend   | HTML5 + CSS3 + JavaScript (ES Modules) — sin frameworks  |
| Estilo     | Clean Architecture, separación domain / application / infrastructure / presentation |

---

## Estructura del proyecto

```
Juridica/
├── backend/
│   ├── app/
│   │   ├── domain/            # Entidades + reglas de negocio puras
│   │   ├── application/       # Casos de uso + interfaces (puertos)
│   │   ├── infrastructure/    # MySQL, JWT, almacenamiento, config
│   │   └── presentation/      # FastAPI: endpoints, schemas, DI
│   ├── tests/                 # Pruebas (pytest)
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py
├── frontend/
│   ├── public/                # HTMLs servidos como estáticos
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── admin/usuarios.html
│   │   └── compras/
│   └── src/
│       ├── styles/theme.css
│       └── js/
│           ├── api/client.js
│           ├── auth/session.js
│           ├── components/
│           └── utils/
├── database/schema.sql        # Respaldo del esquema (la app lo crea sola)
├── uploads/contratos/         # Archivos subidos por compras
└── README.md
```

### ¿Por qué Clean Architecture?

- **Domain**: la regla "Colbeef es la compañía por defecto" o "se requieren 5 archivos obligatorios" vive en una sola clase, sin saber nada de MySQL ni HTTP.
- **Application**: los casos de uso (`RadicarSolicitud`, `CreateUser`, `LoginUser`) sólo dependen de interfaces. Son testeables sin levantar BD.
- **Infrastructure**: si mañana se migra de MySQL a Postgres, o de disco local a S3, sólo se cambia una clase concreta.
- **Presentation**: FastAPI es sólo una "capa de transporte". Cambiarlo por gRPC o un CLI no requiere tocar la lógica.

---

## Instalación

### 1. Pre-requisitos

- Python 3.10 o superior
- Acceso a MySQL en `192.168.20.205:3306`
- (Opcional) Node.js no es necesario: el frontend es estático y se sirve desde FastAPI.

### 2. Configurar entorno

```bash
cd backend
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Variables de entorno

El archivo `backend/.env` ya viene configurado con los datos provistos:

```env
DB_HOST=192.168.20.205
DB_PORT=3306
DB_USER=usuario_juridica
DB_PASSWORD=clave_juridica_123
DB_NAME=Juridica

ADMIN_USERNAME=gerencia2026*
ADMIN_PASSWORD=gerencia2026*
```

> **Importante**: para producción cambia `SECRET_KEY` por un valor aleatorio.
> Genéralo así:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

### 4. Inicializar la base de datos

No se necesita hacer nada manual: al arrancar la app por primera vez, FastAPI:

1. Crea las tablas (`users`, `contratos`, `archivos_contrato`) si no existen.
2. Inserta el usuario administrador inicial:
   - **Usuario**: `gerencia2026*`
   - **Contraseña**: `gerencia2026*`

> Si prefieres ejecutar el SQL manualmente, está en `database/schema.sql`.

### 5. Levantar el servidor

Desde la carpeta `backend/` con el venv activo:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visita:

- **Aplicación web**: <http://localhost:8000/app/login.html>
- **API Swagger (auto-generada)**: <http://localhost:8000/docs>
- **API ReDoc**: <http://localhost:8000/redoc>

---

## Roles y permisos

| Acción                                | Admin | Jurídica | Compras |
| ------------------------------------- | :---: | :------: | :-----: |
| Iniciar sesión                        | ✅    | ✅       | ✅      |
| Cambiar su propia contraseña          | ✅    | ✅       | ✅      |
| Crear usuarios                        | ✅    | ❌       | ❌      |
| Editar / activar / desactivar usuarios| ✅    | ❌       | ❌      |
| Reasignar contraseña de otros usuarios| ✅    | ❌       | ❌      |
| Asignar rol Admin a otros usuarios    | ✅    | ❌       | ❌      |
| Eliminar usuarios                     | ✅    | ❌       | ❌      |
| Radicar solicitud de contrato         | ✅    | ❌       | ✅      |
| Ver TODOS los contratos               | ✅    | ✅       | ❌      |
| Ver SUS contratos                     | ✅    | ✅       | ✅      |

### Nota sobre "ver contraseñas"

Las contraseñas se almacenan con **bcrypt** (hash irreversible). Esto significa que **nadie** puede ver una contraseña en texto plano — ni el administrador, ni el desarrollador, ni un atacante con acceso a la BD. Esta es la práctica estándar de la industria (Google, Microsoft, bancos).

En lugar de "ver" contraseñas, el admin puede **reasignar** una nueva contraseña a cualquier usuario y comunicarla por canal seguro. El módulo de gestión de usuarios incluye esta funcionalidad.

---

## Módulo: Solicitud Radicar (Compras)

Permite a un usuario de Compras radicar un contrato con los siguientes datos:

### Datos del contrato

- **Compañía**: Colbeef (fijo por defecto)
- **Proveedor / Contratista** (texto, obligatorio)
- **NIT del proveedor** (texto, obligatorio)
- **Descripción del servicio** (texto, obligatorio)
- **Principales obligaciones de Colbeef** (texto, obligatorio)
- **Principales obligaciones del proveedor** (texto, obligatorio)
- **Valor del contrato** (numérico, obligatorio)
- **Moneda**: COP (pesos colombianos) / USD / EUR
- **Plazo**: cantidad + unidad (días / meses / años)
- **Renovación automática**: Sí / No
- **Condiciones de recibido satisfactorio** (texto, obligatorio)
- **Requiere póliza**: Sí / No

### Archivos adjuntos (todos los obligatorios deben enviarse)

| Archivo                                       | ¿Obligatorio? |
| --------------------------------------------- | :-----------: |
| Cámara de comercio del proveedor              | ✅            |
| Cotización de oferta                          | ✅            |
| Cédula del representante legal del proveedor  | ✅            |
| Screenshot de aprobación de Gerencia          | ✅            |
| Screenshot de aprobación del Líder de proceso | ✅            |
| Archivo opcional adicional                    | ❌            |

Los archivos se guardan en `uploads/contratos/YYYY/MM/<uuid>.<ext>`.

---

## Próximos pasos (roadmap)

- [ ] Notificaciones a Jurídica cuando un contrato esté próximo a vencer.
- [ ] Renovación automática programada de contratos con `renovacion_automatica = true`.
- [ ] Módulo de pólizas (cuando `requiere_poliza = true`).
- [ ] Edición / aprobación / rechazo de contratos por parte de Jurídica.
- [ ] Auditoría: historial de cambios sobre cada contrato.

---

## Pruebas

```bash
cd backend
pytest -q
```

---

## Soporte

Para dudas técnicas o reportes de bugs, contacta al equipo de desarrollo interno de Colbeef.
