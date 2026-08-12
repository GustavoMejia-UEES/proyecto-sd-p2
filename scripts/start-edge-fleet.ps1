param(
    [string]$ManifestPath = ".\scripts\cameras.local.json",
    [string]$CoreApiUrl = "http://localhost:8000"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$startScript = Join-Path $PSScriptRoot "start-edge.ps1"
$resolvedManifest = Join-Path (Get-Location) $ManifestPath

function Quote-ProcessArgument([string]$Value) {
    return '"' + $Value.Replace('"', '\\"') + '"'
}

if (-not (Test-Path -LiteralPath $resolvedManifest)) {
    throw "No existe el manifiesto: $resolvedManifest. Copia scripts/cameras.example.json como scripts/cameras.local.json."
}

$cameras = Get-Content -LiteralPath $resolvedManifest -Raw | ConvertFrom-Json
$seenIds = @{}
$seenPorts = @{}
$started = @()

foreach ($camera in $cameras) {
    if (-not $camera.enabled) {
        continue
    }

    $cameraId = [string]$camera.camera_id
    $port = [int]$camera.port
    if ($seenIds.ContainsKey($cameraId)) {
        throw "camera_id duplicado en el manifiesto: $cameraId"
    }
    if ($seenPorts.ContainsKey($port)) {
        throw "Puerto duplicado en el manifiesto: $port"
    }
    $seenIds[$cameraId] = $true
    $seenPorts[$port] = $true

    $visionMode = if ($camera.vision_mode) { [string]$camera.vision_mode } else { "motion" }
    $visionProfile = if ($camera.vision_profile) { [string]$camera.vision_profile } else { "balanced" }
    $iotSegment = if ($camera.iot_segment) { [string]$camera.iot_segment } else { "iot-cameras" }
    $edgeHost = if ($camera.edge_host) { [string]$camera.edge_host } else { "localhost" }
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", (Quote-ProcessArgument $startScript),
        "-CameraId", (Quote-ProcessArgument $cameraId),
        "-CameraName", (Quote-ProcessArgument ([string]$camera.name)),
        "-CameraType", (Quote-ProcessArgument ([string]$camera.type)),
        "-CameraSource", (Quote-ProcessArgument ([string]$camera.source)),
        "-Port", (Quote-ProcessArgument ([string]$port)),
        "-EdgeHost", (Quote-ProcessArgument $edgeHost),
        "-CoreApiUrl", (Quote-ProcessArgument $CoreApiUrl),
        "-IotSegment", (Quote-ProcessArgument $iotSegment),
        "-VisionMode", (Quote-ProcessArgument $visionMode),
        "-VisionProfile", (Quote-ProcessArgument $visionProfile)
    )
    if ($visionMode -ne "motion") {
        $arguments += "-Vision"
    }

    $process = Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList $arguments `
        -WorkingDirectory $root `
        -PassThru
    $started += [PSCustomObject]@{
        CameraId = $cameraId
        Port = $port
        ProcessId = $process.Id
        Stream = "http://localhost:$port/stream"
        PublicStream = "http://$edgeHost`:$port/stream"
    }
}

if ($started.Count -eq 0) {
    Write-Host "No hay cámaras enabled=true en el manifiesto."
} else {
    $started | Format-Table -AutoSize
    Write-Host "Cada proceso Edge se registra automáticamente en $CoreApiUrl/api/cameras"
}
