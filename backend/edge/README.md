# ARGUS Edge Camera

El agente Edge corre en la máquina donde está conectada la webcam o donde se
recibe el stream del teléfono. No debe ejecutarse como réplica del API: cada
cámara física necesita su propio proceso.

## Ejecución local en Windows

Docker Desktop ejecuta contenedores Linux y normalmente no expone la webcam
integrada de Windows como `/dev/video0`. Por eso MongoDB y el API se levantan
con Compose, pero el agente de la cámara de la laptop se ejecuta directamente
en Windows.

Primero, desde la raíz del proyecto:

```powershell
Copy-Item .env.example .env
docker compose up -d mongodb api
docker compose ps
```

Después, desde `backend/edge`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:CORE_API_URL="http://localhost:8000"
$env:CAMERA_ID="CAM-001"
$env:CAMERA_NAME="Camera Laptop Gustavo"
$env:CAMERA_TYPE="integrated"
$env:CAMERA_SOURCE="0"
$env:EDGE_STREAM_URL="http://localhost:8081/stream"
uvicorn camera_agent:app --host 0.0.0.0 --port 8081
```

Abre `http://localhost:8081/stream` para probar el video y
`http://localhost:8000/api/cameras` para confirmar que la cámara fue registrada.

Para un teléfono o una cámara IP, cambia `CAMERA_SOURCE` por su URL MJPEG/RTSP.
El frontend puede usar directamente `stream_url` recibido en
`GET /api/cameras`, siempre que esa URL sea accesible por la red.

El agente registra la cámara, envía un heartbeat cada cinco segundos y reporta
eventos `motion` con OpenCV. Si el API está caído, el stream local puede seguir
activo y el agente reintentará los heartbeats.

## Modo CCTV con detección y cuadros

Desde la raíz del proyecto, para instalar el detector YOLO opcional y activar tracking:

```powershell
.\scripts\start-edge.ps1 `
  -CameraId CAM-001 `
  -CameraName "Camera Laptop Gustavo" `
  -CameraSource 0 `
  -Port 8091 `
  -Vision `
  -VisionMode cctv
```

El primer arranque descargará las dependencias y el modelo `yolo11n.pt`. El
stream mostrará cajas con etiqueta, confianza e ID de tracking. Los eventos
`object_detected` se enviarán al API con `label`, `confidence`, `track_id` y
`bbox` dentro de `metadata`.

El endpoint `http://localhost:8091/health` expone el estado operativo del
detector: modo efectivo, etiquetas visibles, cantidad de objetos, latencia de
inferencia, Ãºltimo instante de detecciÃ³n y cualquier error del modelo. El
stream tambiÃ©n incluye un HUD de ARGUS con FPS, modo y objetos rastreados.

Al usar `-Vision`, el script selecciona automÃ¡ticamente el modo efectivo
`cctv` aunque no se especifique `-VisionMode cctv`. Para cambiar de perfil,
puedes usar `-VisionMode motion`, `cctv`, `activity` o `expression`.

Si no instalas el extra `-Vision`, el sistema continúa usando únicamente
OpenCV/motion detection.

## Edge dentro de Compose

Para una cámara IP, un stream de teléfono o un host Linux con `/dev/video0`,
puedes usar el servicio Edge del Compose:

```powershell
docker compose --profile edge up -d --build edge
```

En Windows, `CAMERA_SOURCE=0` dentro del contenedor no representa la webcam de
la laptop. Para la webcam integrada usa el modo local anterior.
