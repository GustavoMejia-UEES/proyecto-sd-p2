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

Para una cámara IP o teléfono, usa como `-CameraSource` su URL MJPEG/RTSP. Si
el frontend está en otra máquina, cambia `EDGE_STREAM_URL` para usar la IP de
Tailscale en vez de `localhost`.

## Edge dentro de Compose

Para un stream IP o un host Linux con cámara disponible, también existe el
servicio opcional:

```powershell
docker compose --profile edge up -d --build edge
```

En Windows, ese servicio no puede leer directamente la cámara integrada; usa
`scripts/start-edge.ps1`.
