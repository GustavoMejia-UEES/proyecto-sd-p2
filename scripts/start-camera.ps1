param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("CAM-001", "CAM-002", "CAM-003")]
    [string]$CameraId,
    [switch]$Kubernetes
)

$ErrorActionPreference = "Stop"

# Perfiles centralizados: el operador solo necesita indicar el ID de la cámara.
$profiles = @{
    "CAM-001" = @{
        Name = "Camara integrada Gustavo"
        Type = "integrated"
        Source = "0"
        Port = 8091
        Host = "100.77.143.36"
    }
    "CAM-002" = @{
        Name = "Camara USB Gustavo"
        Type = "usb"
        Source = "1"
        Port = 8092
        Host = "100.77.143.36"
    }
    "CAM-003" = @{
        Name = "Celular IP Webcam"
        Type = "phone"
        Source = "http://100.96.186.21:8030/video"
        Port = 8093
        Host = "100.77.143.36"
    }
}

$profile = $profiles[$CameraId]
$apiUrl = if ($Kubernetes) { "http://localhost:30080" } else { "http://localhost:8000" }
$startScript = Join-Path $PSScriptRoot "start-edge.ps1"

Write-Host "Iniciando $CameraId - $($profile.Name)"
Write-Host "API: $apiUrl | Stream: http://$($profile.Host):$($profile.Port)/stream"

& $startScript `
    -CameraId $CameraId `
    -CameraName $profile.Name `
    -CameraType $profile.Type `
    -CameraSource $profile.Source `
    -Port $profile.Port `
    -EdgeHost $profile.Host `
    -CoreApiUrl $apiUrl `
    -Vision `
    -VisionMode cctv `
    -VisionProfile fast
