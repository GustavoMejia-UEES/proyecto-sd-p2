param(
    [switch]$Kubernetes
)

$ErrorActionPreference = "Stop"
$ids = @("CAM-001", "CAM-002", "CAM-003")
$scriptPath = Join-Path $PSScriptRoot "start-camera.ps1"

foreach ($id in $ids) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-CameraId", $id
    )
    if ($Kubernetes) { $arguments += "-Kubernetes" }

    Start-Process powershell.exe `
        -ArgumentList $arguments `
        -WorkingDirectory (Split-Path -Parent $PSScriptRoot) `
        -WindowStyle Minimized
}

Write-Host "Procesos Edge iniciados para: $($ids -join ', ')"
Write-Host "Cada proceso mantiene su stream y reintenta la fuente si se desconecta."
