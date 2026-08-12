# Integración final: frontend, cámaras, Docker y Kubernetes

## Flujo definitivo

```text
Fuente física o teléfono -> Edge -> Backend FastAPI + MongoDB -> Frontend
```

El Edge captura o consume el video, publica el stream procesado, envía
heartbeats y genera eventos. El backend persiste cámaras, eventos y tareas. El
frontend consulta el backend y muestra el sistema.

## Descubrimiento automático de cámaras

Al iniciar, el frontend debe llamar:

```text
GET ${API_URL}/api/cameras
```

Cada registro contiene `id`, `name`, `status`, `fps`, `vision_mode` y
`stream_url`. La cuadrícula se construye con esos datos:

```tsx
{cameras.map((camera) => (
  <img key={camera.id} src={camera.stream_url} alt={camera.name} />
))}
```

El frontend debe refrescar estados y tareas al recibir por WebSocket:

```text
camera_status
event_created
task_created
task_updated
```

No debe codificar manualmente `CAM-001`, `CAM-002` o `CAM-003`.

## Quién inicia cada cámara

El backend no ejecuta PowerShell remotamente. El Edge debe correr en el equipo
que puede acceder físicamente a la cámara.

### Laptop o USB en Windows

```powershell
.\scripts\start-edge.ps1 `
  -CameraId CAM-001 `
  -CameraName "Camara laptop" `
  -CameraType integrated `
  -CameraSource 0 `
  -Port 8091 `
  -EdgeHost IP_TAILSCALE_EDGE `
  -CoreApiUrl http://localhost:8000 `
  -Vision `
  -VisionMode cctv `
  -VisionProfile fast
```

### Teléfono IP

```powershell
.\scripts\start-edge.ps1 `
  -CameraId CAM-003 `
  -CameraName "Telefono IP" `
  -CameraType phone `
  -CameraSource "http://IP_TAILSCALE_TELEFONO:9881/video" `
  -Port 8093 `
  -EdgeHost IP_TAILSCALE_EDGE `
  -CoreApiUrl http://localhost:8000 `
  -Vision `
  -VisionMode cctv `
  -VisionProfile fast
```

## Cámaras y Kubernetes

Las cámaras son nodos Edge lógicos, no necesariamente Pods.

```text
Webcam Windows -> Edge fuera del contenedor
Teléfono/IP     -> Edge fuera o dentro de contenedor
Cámara Linux    -> Edge en contenedor si existe acceso al dispositivo
```

Cada nodo se representa en el backend por `camera_id`, heartbeat, segmento IoT
y `stream_url`. Para cámaras IP se puede desplegar un Edge por cámara. Para la
webcam de Windows no conviene forzar el dispositivo dentro de Kubernetes.

## Prueba local con Docker Compose

```powershell
Copy-Item .env.example .env
docker compose up -d --build mongodb api
docker compose ps
Invoke-RestMethod http://localhost:8000/health
```

Después iniciar Edge y comprobar:

```powershell
Invoke-RestMethod http://localhost:8091/health
Invoke-RestMethod http://localhost:8000/api/cameras | ConvertTo-Json -Depth 8
Invoke-RestMethod "http://localhost:8000/api/events?camera_id=CAM-001"
```

## Prueba del frontend

Juanfer debe configurar:

```env
NEXT_PUBLIC_API_URL=http://IP_TAILSCALE_BACKEND:30080
```

Debe probar:

```text
GET/POST/PATCH/DELETE /api/tasks
GET /api/cameras
GET /api/events
WS /ws/events
```

Las tareas de vigilancia deben mostrar `source`, `camera_id`, `event_id`,
`priority`, `occurrences` y `last_seen_at`.

## Prueba en Kubernetes

En la Máquina A:

```powershell
docker build -t argus-api:0.4.0 ./backend
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
kubectl rollout status deployment/mongodb
kubectl rollout status deployment/argus-api
kubectl get pods -o wide
kubectl get services
```

Desde B:

```powershell
Invoke-RestMethod http://IP_TAILSCALE_BACKEND:30080/health
Invoke-RestMethod http://IP_TAILSCALE_BACKEND:30080/api/cameras
```

En B se despliega el frontend con Deployment de 1 réplica, ConfigMap para
`API_URL` y su propio Service.

## Evidencias finales

1. `tailscale status` en ambas máquinas.
2. `docker compose ps` y `/health` en A.
3. Edge online, stream y FPS.
4. `kubectl get pods` y `kubectl get services` en A y B.
5. Petición cruzada desde B al NodePort de A.
6. CRUD ejecutado desde el navegador.
7. Cámara descubierta automáticamente en el frontend.
8. Evento automático y tarea asociada.
9. `kubectl describe deployment argus-api`.
10. Escalado a 4 réplicas.

## Mejora futura

Para iniciar cámaras desde una interfaz se necesitaría un supervisor Edge local
con endpoints como `GET /edge/discover`, `POST /edge/cameras/start` y
`POST /edge/cameras/stop`. El frontend solicitaría la operación, pero el
supervisor ejecutaría el proceso local de forma segura.
