# ARGUS Edge Camera

El agente Edge corre en la máquina donde está conectada la webcam o donde se
recibe el stream del teléfono. No debe ejecutarse como réplica del API: cada
cámara física necesita su propio proceso.

## Ejecución local

Desde `backend/edge`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:CORE_API_URL="http://localhost:8000"
$env:CAMERA_ID="CAM-001"
$env:CAMERA_NAME="USB Camera Gustavo"
$env:CAMERA_SOURCE="0"
$env:EDGE_STREAM_URL="http://TAILSCALE_IP_DE_ESTA_MAQUINA:8081/stream"
uvicorn camera_agent:app --host 0.0.0.0 --port 8081
```

Para un teléfono o una cámara IP, cambia `CAMERA_SOURCE` por su URL MJPEG/RTSP.
El frontend puede usar directamente `stream_url` recibido en
`GET /api/cameras`, siempre que esa URL sea accesible por Tailscale.

El agente registra la cámara, envía un heartbeat cada cinco segundos y reporta
eventos `motion` con OpenCV. Si el API está caído, el stream local puede seguir
activo y el agente reintentará los heartbeats.
