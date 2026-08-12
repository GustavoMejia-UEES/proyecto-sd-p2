param(
    [string]$CameraId = "CAM-001",
    [string]$CameraName = "Camera Laptop Gustavo",
    [string]$CameraType = "integrated",
    [string]$CameraSource = "0",
    [int]$Port = 8081,
    [string]$EdgeHost = "localhost",
    [string]$CoreApiUrl = "http://localhost:8000",
    [string]$IotSegment = "iot-cameras",
    [int]$CaptureWidth = 1280,
    [int]$CaptureHeight = 720,
    [int]$CaptureFps = 30,
    [int]$JpegQuality = 82,
    [int]$DetectionInterval = 3,
    [int]$DetectionInputSize = 640,
    [string]$DetectionDevice = "",
    [string]$DetectionModel = "yolo11n.pt",
    [double]$DetectionConfidence = 0.45,
    [ValidateSet("motion", "cctv", "activity", "expression")]
    [string]$VisionMode = "motion",
    [ValidateSet("fast", "balanced", "quality")]
    [string]$VisionProfile = "balanced",
    [switch]$Vision
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
$requirementsFile = if ($Vision) {
    Join-Path $edgePath "requirements-vision.txt"
} else {
    Join-Path $edgePath "requirements.txt"
}
& $pythonPath -m pip install -r $requirementsFile

$env:CORE_API_URL = $CoreApiUrl
$env:CAMERA_ID = $CameraId
$env:CAMERA_NAME = $CameraName
$env:CAMERA_TYPE = $CameraType
$env:CAMERA_SOURCE = $CameraSource
$env:EDGE_STREAM_URL = "http://$EdgeHost`:$Port/stream"
$env:IOT_SEGMENT = $IotSegment
$env:CAPTURE_WIDTH = $CaptureWidth
$env:CAPTURE_HEIGHT = $CaptureHeight
$env:CAPTURE_FPS = $CaptureFps
$env:JPEG_QUALITY = $JpegQuality
$env:DETECTION_INTERVAL = $DetectionInterval
$env:DETECTION_INPUT_SIZE = $DetectionInputSize
$env:DETECTION_DEVICE = $DetectionDevice
$env:DETECTION_MODEL = $DetectionModel
$env:DETECTION_CONFIDENCE = $DetectionConfidence.ToString(
    [System.Globalization.CultureInfo]::InvariantCulture
)

if ($Vision) {
    switch ($VisionProfile) {
        "fast" {
            if (-not $PSBoundParameters.ContainsKey("DetectionModel")) {
                $env:DETECTION_MODEL = "yolo11n.pt"
            }
            if (-not $PSBoundParameters.ContainsKey("DetectionInputSize")) {
                $env:DETECTION_INPUT_SIZE = "416"
            }
            if (-not $PSBoundParameters.ContainsKey("DetectionInterval")) {
                $env:DETECTION_INTERVAL = "4"
            }
        }
        "quality" {
            if (-not $PSBoundParameters.ContainsKey("DetectionModel")) {
                $env:DETECTION_MODEL = "yolo11s.pt"
            }
            if (-not $PSBoundParameters.ContainsKey("DetectionInputSize")) {
                $env:DETECTION_INPUT_SIZE = "640"
            }
            if (-not $PSBoundParameters.ContainsKey("DetectionInterval")) {
                $env:DETECTION_INTERVAL = "3"
            }
        }
    }
}
$env:VISION_MODE = $VisionMode
$env:DETECTION_ENABLED = if ($Vision) { "true" } else { "false" }
if ($Vision -and $VisionMode -eq "motion") {
    $env:VISION_MODE = "cctv"
}

Write-Host "Iniciando $CameraId en $env:EDGE_STREAM_URL usando source $CameraSource"
Push-Location $edgePath
try {
    & $pythonPath -m uvicorn camera_agent:app --host 0.0.0.0 --port $Port
}
finally {
    Pop-Location
}
