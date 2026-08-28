# Despliegue de JURICOM_BEEF en el servidor

Guía para dejar el sistema corriendo en el servidor (Windows). El backend
(FastAPI) sirve también el frontend, así que **no necesitas nginx ni otro
servidor web** para la red local.

---

## 1. Requisitos del servidor

- **Windows** con acceso de red al servidor MySQL (`192.168.20.205:3306`).
- **Python 3.11 o superior** instalado y agregado al PATH.
  - Verificar: `python --version`
- **MySQL** con:
  - Base de datos `Juridica` creada (charset `utf8mb4`).
  - Usuario con permisos sobre esa BD (el de `backend\.env`).
  - Las tablas y migraciones se crean **solas** al primer arranque; no hay que
    correr `.sql` a mano.

---

## 2. Copiar el proyecto

Copia toda la carpeta del proyecto al servidor, por ejemplo a `C:\JuriCom\`.
Debe incluir, como mínimo:

```
C:\JuriCom\
├── backend\
├── frontend\
├── uploads\          (si migras archivos ya cargados, copia esta carpeta)
└── juricom.bat
```

> Si migras desde otro equipo, **copia también la carpeta `uploads\`** para no
> perder los archivos ya subidos (contratos, cotizaciones, pólizas, etc.).

---

## 3. Crear el entorno virtual e instalar dependencias

El `juricom.bat` exige que exista `backend\.venv`. En una terminal:

```bat
cd C:\JuriCom\backend
python -m venv .venv
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt
```

---

## 4. Configurar `backend\.env`

Si no existe, cópialo desde el ejemplo y edítalo:

```bat
copy backend\.env.example backend\.env
```

Valores a revisar/ajustar **antes de arrancar**:

| Variable | Qué poner |
|---|---|
| `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | Credenciales reales de MySQL. |
| `DB_ACTIVATE_ROLE` | Solo si el DBA dio permisos vía rol; si no, déjalo vacío. |
| `SECRET_KEY` | Token largo y aleatorio (ver abajo cómo generarlo). |
| `APP_ENV` | `production`. |
| `APP_PUBLIC_URL` | `http://IP_DEL_SERVIDOR:8000` (IP real de red, **no** localhost). Se usa en los enlaces de los correos. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Credenciales del admin inicial (se crea automáticamente). |
| `SMTP_*` | Servidor de correo y `SMTP_PASSWORD`. |
| `EMAIL_OVERRIDE_TO` | **Debe quedar vacío** en producción. Si tiene un correo, TODOS los envíos se redirigen ahí (modo prueba). |
| `JURIDICA_EMAILS` | Correos del equipo de Jurídica (separados por coma). |

Generar una `SECRET_KEY` nueva:

```bat
.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> **Quién aprueba las solicitudes:** el líder inmediato NO sale del `.env`. Se
> elige en cada solicitud desde la lista oficial de líderes Colbeef
> (`frontend\src\js\catalogos\lideres-colbeef.js` y su gemelo en
> `backend\app\application\services\lideres_colbeef.py`). `LIDER_INMEDIATO_EMAIL`
> y `GERENCIA_EMAIL` son valores heredados que hoy no se usan en el flujo.

---

## 5. Firewall

Abrir el puerto **8000/TCP** de entrada para que otros PCs accedan:

```powershell
New-NetFirewallRule -DisplayName "JuriCom 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## 6. Arrancar

Doble clic en **`juricom.bat`** (o ejecútalo desde la terminal). El script:

1. Verifica que exista `backend\.venv`.
2. Mata cualquier instancia previa en el puerto 8000.
3. Detecta la IP de red y muestra los enlaces de acceso.
4. Levanta el servidor con `uvicorn` en `0.0.0.0:8000`.

Acceso:

- App: `http://IP_DEL_SERVIDOR:8000/app/login.html`
- API docs: `http://IP_DEL_SERVIDOR:8000/docs`
- Health check: `http://IP_DEL_SERVIDOR:8000/health`

> La ventana del `.bat` debe quedar abierta: si la cierras, se detiene el
> servidor. Para detenerlo manualmente: `Ctrl+C`.

---

## 7. (Opcional) Arranque automático

- **Sencillo:** crea un acceso directo a `juricom.bat` en la carpeta de inicio
  (`shell:startup`) para que arranque al iniciar sesión.
- **Task Scheduler:** crea una tarea "al iniciar el equipo" que ejecute
  `C:\JuriCom\juricom.bat`.
- **Servicio 24/7 (recomendado producción):** envuelve el arranque con
  [NSSM](https://nssm.cc/):

  ```bat
  nssm install JuriCom "C:\JuriCom\backend\.venv\Scripts\uvicorn.exe" "main:app --host 0.0.0.0 --port 8000"
  nssm set JuriCom AppDirectory "C:\JuriCom\backend"
  nssm start JuriCom
  ```

---

## 8. Verificación post-arranque

1. Abre `http://IP_DEL_SERVIDOR:8000/health` → debe responder `{"status":"ok"}`.
2. Entra a la app y haz login con `ADMIN_USERNAME` / `ADMIN_PASSWORD`.
3. En los logs del arranque debe aparecer `Aplicación lista en 0.0.0.0:8000`.
   Si hubo un fallo de BD, saldrá un error de conexión: revisa credenciales /
   conectividad a MySQL y reinicia.

---

## 9. Actualizaciones futuras

1. `Ctrl+C` para detener (o `nssm stop JuriCom`).
2. Actualiza los archivos del proyecto.
3. Si cambió `requirements.txt`:
   `.venv\Scripts\pip install -r requirements.txt`
4. Vuelve a arrancar con `juricom.bat` (o `nssm start JuriCom`). Las migraciones
   de BD se aplican solas.
