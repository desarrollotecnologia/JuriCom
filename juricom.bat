@echo off
title Juridica - Colbeef
cd /d "%~dp0backend"

if not exist ".venv\Scripts\uvicorn.exe" (
    echo [ERROR] No se encontro el entorno virtual en backend\.venv
    echo Ejecuta primero: python -m venv .venv  y  pip install -r requirements.txt
    pause
    exit /b 1
)

echo Cerrando instancias previas en el puerto 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn.*main:app' -or ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'JuriCom\\backend') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
timeout /t 3 /nobreak >nul

set "LAN_IP="
for /f "usebackq delims=" %%i in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.PrefixOrigin -ne 'WellKnown' } | Select-Object -First 1 -ExpandProperty IPAddress)"`) do set "LAN_IP=%%i"

echo.
echo  Juridica - servidor en red local
echo  --------------------------------
if defined LAN_IP (
    echo  Abrir aqui:  http://%LAN_IP%:8000/app/login.html
    echo  Otros PCs:   http://%LAN_IP%:8000/app/login.html
    echo  API docs:    http://%LAN_IP%:8000/docs
) else (
    echo  Abrir aqui:  http://192.168.20.177:8000/app/login.html
    echo  API docs:    http://192.168.20.177:8000/docs
)
echo.
echo  IMPORTANTE: No abras localhost:8000 si otros PCs deben entrar.
echo  En backend\.env debe estar APP_PUBLIC_URL con tu IP de red.
echo.
echo  Detener: Ctrl+C
echo.

".venv\Scripts\uvicorn.exe" main:app --host 0.0.0.0 --port 8000

pause
