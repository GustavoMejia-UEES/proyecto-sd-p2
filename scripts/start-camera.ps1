param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("CAM-001", "CAM-002", "CAM-003", "CAM-004", "CAM-005")]
    [string]$CameraId,
    [ValidateSet("gustavo", "juanfer")]
    [string]$Owner = "gustavo",
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
        Source = "http://100.106.180.86:9881/video"
        Port = 9020
        Host = "100.77.143.36"
    }
    "CAM-004" = @{
        Name = "Camara integrada Juanfer"
        Type = "integrated"
        Source = "0"
        Port = 8091
        Host = "100.112.215.44"
    }
    "CAM-005" = @{
        Name = "Celular IP Webcam Juanfer"
        Type = "phone"
        Source = "http://100.96.186.21:8030/video"
        Port = 9010
        Host = "100.112.215.44"
    }
}

$profile = $profiles[$CameraId]
$expectedOwner = if ($CameraId -in @("CAM-001", "CAM-002", "CAM-003")) { "gustavo" } else { "juanfer" }
if ($Owner -ne $expectedOwner) {
    throw "$CameraId pertenece al equipo de $expectedOwner. Usa -Owner $expectedOwner."
}
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
