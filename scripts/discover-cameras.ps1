param(
    [int]$MaxIndex = 5,
    [int]$Warmup = 3
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $root "backend\edge\.venv\Scripts\python.exe"
$scriptPath = Join-Path $root "backend\edge\discover_cameras.py"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No existe el entorno Edge. Ejecuta primero .\scripts\start-edge.ps1 para instalarlo."
}

& $pythonPath $scriptPath --max-index $MaxIndex --warmup $Warmup
