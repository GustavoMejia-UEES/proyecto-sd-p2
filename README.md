# ARGUS local con Docker Compose

## Arranque rápido

Desde la raíz del proyecto:

```powershell
Copy-Item .env.example .env
docker compose up -d --build mongodb api
docker compose ps
```

Comprobaciones:

- API: <http://localhost:8000/docs>
- Salud: <http://localhost:8000/health>
- MongoDB: `localhost:27017`

Las credenciales locales están en `.env`, que está ignorado por Git. Para otro
entorno, cambia únicamente ese archivo; no es necesario modificar el código.

Compose separa la red `argus_core_net` —MongoDB y API— de
`argus_iot_net` —API y agentes Edge—. El API funciona como gateway entre ambas;
MongoDB no queda expuesto directamente al segmento IoT.

## Cámara integrada de la laptop en Windows

La webcam no se expone automáticamente dentro de un contenedor Linux de Docker
Desktop. Levanta MongoDB y API con Compose y ejecuta el agente Edge en Windows:

```powershell
.\scripts\start-edge.ps1 `
  -CameraId CAM-001 `
  -CameraName "Camera Laptop Gustavo" `
  -CameraType integrated `
  -CameraSource 0 `
  -Port 8081
```

Prueba el video en <http://localhost:8081/stream>. El agente registra la cámara
automáticamente en el API y manda heartbeats/eventos de movimiento.

También puedes consultar los índices disponibles en la laptop:

```text
http://localhost:8081/discover
```

Y configurar una cámara desde el API:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/cameras/configure `
  -ContentType "application/json" `
  -Body '{
    "camera_id": "CAM-001",
    "name": "Camera Laptop Gustavo",
    "type": "integrated",
    "source": "0",
    "edge_host": "localhost",
    "edge_port": 8081,
    "core_api_url": "http://localhost:8000",
    "iot_segment": "iot-cameras",
    "enabled": true
  }'
```

La respuesta devuelve el registro de cámara, las variables del agente Edge y
el comando listo para arrancarlo. Para la demo remota, usa como `edge_host` la
IP Tailscale del nodo Edge y conserva `iot_segment` como `iot-cameras`.

El campo `iot_segment` es la etiqueta lógica que viajará con la configuración
de cada dispositivo. La segmentación física entre máquinas se completa después
con la IP de Tailscale, firewall y/o ACL de la red; el endpoint no abre puertos
ni ejecuta comandos remotos.

## Varias cámaras

Cada cámara necesita su propio proceso, identificador y puerto:

```powershell
# Laptop integrada
.\scripts\start-edge.ps1 -CameraId CAM-001 -CameraName "Laptop" -CameraSource 0 -Port 8081

# Segunda webcam USB
.\scripts\start-edge.ps1 -CameraId CAM-002 -CameraName "USB externa" -CameraSource 1 -Port 8082
```

Luego el frontend consulta `GET http://localhost:8000/api/cameras` y renderiza
el `stream_url` de cada registro.

Para activar el primer nivel de inteligencia visual en una cámara:

```powershell
.\scripts\start-edge.ps1 -CameraId CAM-001 -CameraName "Laptop" -CameraSource 0 -Port 8091 -Vision -VisionMode cctv
```

El modo `cctv` agrega detección YOLO, tracking y cuadros sobre el MJPEG. Los
modos `activity` y `expression` quedan preparados para las siguientes capas
de pose y análisis temporal.

Para una cámara IP o teléfono, usa como `-CameraSource` su URL MJPEG/RTSP. Si
el frontend está en otra máquina, cambia `EDGE_STREAM_URL` para usar la IP de
Tailscale en vez de `localhost`.

## Prueba con laptop + webcam USB

Primero conecta la webcam USB y ejecuta:

```powershell
.\scripts\discover-cameras.ps1
```

El resultado indica el Ã­ndice de cada cÃ¡mara. Normalmente la integrada es `0`
y la USB es `1`, pero debes confirmar el valor en tu equipo. Luego puedes usar
el manifiesto listo para dos cÃ¡maras:

```powershell
Copy-Item .\scripts\cameras.usb-pair.example.json .\scripts\cameras.local.json
# Cambia source si discover-cameras.ps1 mostrÃ³ otro Ã­ndice.
.\scripts\start-edge-fleet.ps1
```

Streams esperados:

- Laptop: `http://localhost:8091/stream`
- USB: `http://localhost:8092/stream`

Confirma el registro en:

```powershell
Invoke-RestMethod http://localhost:8000/api/cameras | ConvertTo-Json -Depth 8
```

## Edge dentro de Compose

Para un stream IP o un host Linux con cámara disponible, también existe el
servicio opcional:

```powershell
docker compose --profile edge up -d --build edge
```

En Windows, ese servicio no puede leer directamente la cámara integrada; usa
`scripts/start-edge.ps1`.
