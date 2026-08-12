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
    # Primero identifica los procesos que realmente poseen los puertos Edge.
    # Esto evita depender del texto de CommandLine, que cambia entre Python y PowerShell.
    $ports = @(8091, 8092, 8093, 9010, 9020)
    $connections = Get-NetTCPConnection -LocalPort $ports -State Listen -ErrorAction SilentlyContinue
    $processIds = @($connections | Select-Object -ExpandProperty OwningProcess -Unique)

    # Los lanzadores pueden dejar un proceso padre de PowerShell; se incluye solo
    # si su línea de comando pertenece a esta flota Edge.
    $allProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
    $parentIds = @($allProcesses |
        Where-Object { $processIds -contains $_.ProcessId } |
        Select-Object -ExpandProperty ParentProcessId -Unique)
    $parentProcesses = $allProcesses | Where-Object {
        $parentIds -contains $_.ProcessId -and
        $_.CommandLine -and
        ($_.CommandLine -match "camera_agent|start-edge|start-camera")
    }
    $processIds += @($parentProcesses | Select-Object -ExpandProperty ProcessId)

    foreach ($processId in ($processIds | Where-Object { $_ -and $_ -ne $PID } | Select-Object -Unique)) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Host "Proceso Edge detenido: $processId"
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
