param(
    [string]$CameraId = "CAM-001",
    [string]$CameraName = "Camera Laptop Gustavo",
    [string]$CameraType = "integrated",
    [string]$CameraSource = "0",
    [int]$Port = 8081,
    [string]$CoreApiUrl = "http://localhost:8000",
    [string]$IotSegment = "iot-cameras"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$edgePath = Join-Path $root "backend\edge"
$venvPath = Join-Path $edgePath ".venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $pythonPath)) {
    Write-Host "Creando entorno virtual del agente Edge..."
    python -m venv $venvPath
}

Write-Host "Instalando/verificando dependencias del agente Edge..."
& $pythonPath -m pip install -r (Join-Path $edgePath "requirements.txt")

$env:CORE_API_URL = $CoreApiUrl
$env:CAMERA_ID = $CameraId
$env:CAMERA_NAME = $CameraName
$env:CAMERA_TYPE = $CameraType
$env:CAMERA_SOURCE = $CameraSource
$env:EDGE_STREAM_URL = "http://localhost:$Port/stream"
$env:IOT_SEGMENT = $IotSegment

Write-Host "Iniciando $CameraId en $env:EDGE_STREAM_URL usando source $CameraSource"
Push-Location $edgePath
try {
    & $pythonPath -m uvicorn camera_agent:app --host 0.0.0.0 --port $Port
}
finally {
    Pop-Location
}
