param(
    [switch]$Kubernetes,
    [ValidateSet("gustavo", "juanfer")]
    [string]$Owner = "gustavo"
)

$ErrorActionPreference = "Stop"
$ids = if ($Owner -eq "gustavo") {
    @("CAM-001", "CAM-002", "CAM-003")
} else {
    @("CAM-004", "CAM-005")
}
$scriptPath = Join-Path $PSScriptRoot "start-camera.ps1"

foreach ($id in $ids) {
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $scriptPath,
        "-CameraId", $id,
        "-Owner", $Owner
    )
    if ($Kubernetes) { $arguments += "-Kubernetes" }

    Start-Process powershell.exe `
        -ArgumentList $arguments `
        -WorkingDirectory (Split-Path -Parent $PSScriptRoot) `
        -WindowStyle Minimized
}

Write-Host "Procesos Edge iniciados para: $($ids -join ', ')"
Write-Host "Cada proceso mantiene su stream y reintenta la fuente si se desconecta."
