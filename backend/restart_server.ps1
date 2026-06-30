$listeners = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $listeners) {
    Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'uvicorn.*main:app' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2
Set-Location $PSScriptRoot
if (Test-Path '.venv\Scripts\uvicorn.exe') {
    Start-Process -FilePath '.venv\Scripts\uvicorn.exe' -ArgumentList 'main:app','--host','0.0.0.0','--port','8000','--reload' -WorkingDirectory $PSScriptRoot
} else {
    Start-Process -FilePath 'C:\laragon\bin\python\python-3.13\python.exe' -ArgumentList '-m','uvicorn','main:app','--host','0.0.0.0','--port','8000','--reload' -WorkingDirectory $PSScriptRoot
}
Start-Sleep -Seconds 5
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
    Select-Object OwningProcess
