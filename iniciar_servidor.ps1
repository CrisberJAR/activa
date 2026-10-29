# Arranca el backend de ACTIVA para que la app del celular pueda conectarse
# (misma red Wi-Fi o internet compartido desde el celular).
#
# Uso (desde la carpeta activa):
#   powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1
#   powershell -ExecutionPolicy Bypass -File .\iniciar_servidor.ps1 -Recargar   (desarrollo: se reinicia solo al cambiar el código)
#
# La primera vez en una laptop, ejecutarlo "como administrador" para crear la regla del firewall.

param([switch]$Recargar)

$ErrorActionPreference = "Stop"
$puerto = 8000
$backend = Join-Path $PSScriptRoot "backend"

if (-not (Test-Path (Join-Path $backend ".venv"))) {
    Write-Host "Falta el entorno virtual. Ejecuta primero los pasos de docs\guia_otra_laptop.md" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $backend ".env"))) {
    Write-Host "Falta backend\.env (copialo desde tu laptop por USB, nunca por GitHub)" -ForegroundColor Red
    exit 1
}

# Regla del firewall para el puerto 8000 en todas las redes (las redes compartidas desde el celular suelen ser "publicas")
$regla = "ACTIVA backend $puerto"
if (-not (Get-NetFirewallRule -DisplayName $regla -ErrorAction SilentlyContinue)) {
    $esAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($esAdmin) {
        New-NetFirewallRule -DisplayName $regla -Direction Inbound -Protocol TCP -LocalPort $puerto -Action Allow -Profile Any | Out-Null
        Write-Host "Regla del firewall creada para el puerto $puerto" -ForegroundColor Green
    } else {
        Write-Host "AVISO: no existe la regla del firewall. Si el celular no conecta, cierra esto y ejecuta el script" -ForegroundColor Yellow
        Write-Host "       una vez 'como administrador' (clic derecho en PowerShell > Ejecutar como administrador)." -ForegroundColor Yellow
    }
}

$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and $_.PrefixOrigin -ne 'WellKnown' } |
    Sort-Object InterfaceMetric

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host " Escribe en la app (Ajustes > Direccion del servidor):" -ForegroundColor Cyan
foreach ($ip in $ips) {
    Write-Host ("   http://{0}:{1}    ({2})" -f $ip.IPAddress, $puerto, $ip.InterfaceAlias) -ForegroundColor White
}
Write-Host " Usa la de la red Wi-Fi o la del celular que comparte internet." -ForegroundColor Cyan
Write-Host " Web del asesor en esta laptop: http://localhost:$puerto/login" -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $backend
$opciones = @("--host", "0.0.0.0", "--port", $puerto)
if ($Recargar) {
    # Solo vigila la carpeta app (no .venv); los YAML de config se leen en cada uso
    $opciones += @("--reload", "--reload-dir", "app")
    Write-Host "Modo desarrollo: el servidor se reinicia solo al guardar cambios en backend\app" -ForegroundColor Yellow
}
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app @opciones
