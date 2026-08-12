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

## Ajuste de FPS y latencia

La captura y la inferencia YOLO trabajan en hilos separados. El capturador
prioriza el frame mÃ¡s reciente, mientras el detector descarta frames viejos
si se queda atrÃ¡s. Esto evita que una inferencia lenta congele el stream.

Para una laptop normal, empieza con esta configuraciÃ³n:

```powershell
.\scripts\start-edge.ps1 `
  -CameraId CAM-001 `
  -CameraName "Camera Laptop Gustavo" `
  -CameraSource 0 `
  -Port 8091 `
  -Vision `
  -VisionMode cctv `
  -CaptureWidth 1280 `
  -CaptureHeight 720 `
  -DetectionInterval 3 `
  -DetectionInputSize 640
```

Si el FPS baja, sube `-DetectionInterval` a `5` o baja `-DetectionInputSize`
a `416`. Si necesitas mÃ¡s detalle y tienes GPU, mantÃ©n `640` y usa
`-DetectionDevice 0`. El endpoint `/health` permite comparar `fps` contra
`detection_latency_ms` despuÃ©s de cada ajuste.

## Edge dentro de Compose

Para una cámara IP, un stream de teléfono o un host Linux con `/dev/video0`,
puedes usar el servicio Edge del Compose:

```powershell
docker compose --profile edge up -d --build edge
```

En Windows, `CAMERA_SOURCE=0` dentro del contenedor no representa la webcam de
la laptop. Para la webcam integrada usa el modo local anterior.

## Varias cÃ¡maras y dispositivos

Cada dispositivo fÃ­sico o stream IP se ejecuta como un proceso Edge separado.
Lo que los conecta es el mismo `CORE_API_URL`; lo que los diferencia es
`CAMERA_ID`, `CAMERA_SOURCE` y un puerto de stream Ãºnico.

Para lanzar varias cÃ¡maras en Windows:

```powershell
Copy-Item .\scripts\cameras.example.json .\scripts\cameras.local.json
# Edita cameras.local.json y activa las cÃ¡maras deseadas.
.\scripts\start-edge-fleet.ps1
```

La webcam integrada puede usar `source: "0"`; un telÃ©fono o cÃ¡mara IP debe
usar una URL MJPEG/RTSP y un `port` distinto, por ejemplo `8092`. Para que el
frontend acceda desde otra mÃ¡quina, reemplaza `localhost` por la IP LAN del
host Edge en la configuraciÃ³n de la cÃ¡mara.
