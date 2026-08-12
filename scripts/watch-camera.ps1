param(
    [string]$CameraId = "CAM-003",
    [string]$CoreApiUrl = "http://localhost:8000",
    [string]$EdgeUrl = "http://localhost:8093",
    [int]$IntervalSeconds = 3
)

$ErrorActionPreference = "Stop"
$CoreApiUrl = $CoreApiUrl.TrimEnd("/")
$EdgeUrl = $EdgeUrl.TrimEnd("/")

Write-Host "Monitoreando $CameraId" -ForegroundColor Cyan
Write-Host "API: $CoreApiUrl | Edge: $EdgeUrl" -ForegroundColor DarkCyan
Write-Host "Presiona Ctrl+C para salir." -ForegroundColor Yellow

while ($true) {
    try {
        $health = Invoke-RestMethod "$EdgeUrl/health" -TimeoutSec 5
        $camera = Invoke-RestMethod "$CoreApiUrl/api/cameras/$CameraId" -TimeoutSec 5
        $eventResponse = Invoke-RestMethod "$CoreApiUrl/api/events?camera_id=$CameraId&limit=5" -TimeoutSec 5
        $events = if ($null -ne $eventResponse.value) {
            @($eventResponse.value)
        } else {
            @($eventResponse)
        }
        $taskResponse = Invoke-RestMethod "$CoreApiUrl/api/tasks" -TimeoutSec 5
        $allTasks = if ($null -ne $taskResponse.value) {
            @($taskResponse.value)
        } else {
            @($taskResponse)
        }
        $tasks = @($allTasks |
            Where-Object { $_.camera_id -eq $CameraId } |
            Select-Object -First 5)

        Clear-Host
        Write-Host ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $CameraId) -ForegroundColor Cyan
        Write-Host ("Estado Edge: {0} | API camera: {1} | FPS: {2}" -f $health.status, $camera.status, $health.fps)
        Write-Host ("Detecciones: {0} | Etiquetas: {1} | Latencia: {2} ms" -f $health.detections, ($health.labels -join ", "), $health.detection_latency_ms)
        if ($health.detection_details) {
            $health.detection_details | Select-Object label,confidence,track_id,bbox |
                Format-Table -AutoSize | Out-Host
        }
        Write-Host ("Ultimo evento enviado: {0} | ID: {1}" -f $health.last_event_at, $health.last_event_id)
        if ($health.last_event_error) {
            Write-Host ("Error enviando evento: {0}" -f $health.last_event_error) -ForegroundColor Red
        }

        Write-Host "`nUltimos eventos:" -ForegroundColor Magenta
        if ($events.Count -eq 0) {
            Write-Host "  Sin eventos para esta cámara."
        } else {
            $events | Select-Object id,type,object_name,confidence,status,timestamp |
                Format-Table -AutoSize | Out-Host
        }

        Write-Host "Tareas asociadas:" -ForegroundColor Green
        if ($tasks.Count -eq 0) {
            Write-Host "  Sin tareas automáticas para esta cámara."
        } else {
            $tasks | Select-Object id,titulo,estado,priority,event_id,created_at |
                Format-Table -AutoSize | Out-Host
        }
    } catch {
        Clear-Host
        Write-Host ("[{0}] No se pudo consultar la cámara/API: {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $_.Exception.Message) -ForegroundColor Red
    }

    Start-Sleep -Seconds $IntervalSeconds
}
