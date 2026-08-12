param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("status", "stop", "start")]
    [string]$Action,
    [ValidateSet("gustavo", "juanfer")]
    [string]$Owner = "gustavo",
    [switch]$Kubernetes
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$fleet = Join-Path $PSScriptRoot "start-camera-fleet.ps1"

function Show-Status {
    Write-Host "=== Kubernetes ===" -ForegroundColor Cyan
    kubectl get nodes 2>$null
    kubectl get pods 2>$null
    kubectl get services 2>$null

    Write-Host "=== Puertos Edge ===" -ForegroundColor Cyan
    Get-NetTCPConnection -LocalPort 8091,8092,8093,9010,9020 -State Listen -ErrorAction SilentlyContinue |
        Select-Object LocalAddress, LocalPort, OwningProcess, State
}

function Stop-Edge {
    $processes = Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -match "camera_agent\.py" -or
                $_.CommandLine -match "start-camera\.ps1" -or
                $_.CommandLine -match "start-camera-fleet\.ps1"
            )
        }

    foreach ($process in $processes) {
        if ($process.ProcessId -ne $PID) {
            Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "Proceso Edge detenido: $($process.ProcessId)"
        }
    }

    Write-Host "Camaras Edge detenidas. No se borraron registros ni configuraciones." -ForegroundColor Green
}

if ($Action -eq "status") {
    Show-Status
    exit 0
}

if ($Action -eq "stop") {
    Stop-Edge
    if ($Kubernetes) {
        kubectl scale deployment argus-api --replicas=0
        kubectl scale deployment mongodb --replicas=0
        Write-Host "Kubernetes detenido temporalmente. Los datos permanecen en el volumen." -ForegroundColor Green
    }
    exit 0
}

if ($Action -eq "start") {
    if ($Kubernetes) {
        kubectl config use-context docker-desktop
        kubectl get nodes
        kubectl scale deployment mongodb --replicas=1
        kubectl scale deployment argus-api --replicas=4
        kubectl rollout status deployment/mongodb --timeout=180s
        kubectl rollout status deployment/argus-api --timeout=180s
        Write-Host "Kubernetes restaurado." -ForegroundColor Green
    }

    $fleetArguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ('"' + $fleet + '"'),
        "-Owner", $Owner
    )
    if ($Kubernetes) { $fleetArguments += "-Kubernetes" }

    Start-Process powershell.exe `
        -ArgumentList $fleetArguments `
        -WorkingDirectory $root `
        -WindowStyle Minimized

    Write-Host "Flota Edge iniciada para $Owner." -ForegroundColor Green
    Write-Host "Usa .\scripts\operar-sistema.ps1 -Action status para verificar." 
}
