param(
    [switch]$Kubernetes,
    [ValidateSet("gustavo", "juanfer")]
    [string]$Owner = "gustavo"
)

$ErrorActionPreference = "Stop"
$taskName = "SistemaDistribuido-CamarasEdge"
$fleetScript = Join-Path $PSScriptRoot "start-camera-fleet.ps1"
$arguments = @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $fleetScript,
    "-Owner", $Owner
)
if ($Kubernetes) { $arguments += "-Kubernetes" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument ($arguments -join " ")
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Write-Host "Autoinicio instalado: $taskName"
Write-Host "Las camaras Edge iniciaran al iniciar sesion en Windows."
