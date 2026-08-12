# ARGUS Core API

Backend central de ARGUS: registra cámaras, recibe heartbeats, persiste eventos
en MongoDB y publica actualizaciones en tiempo real para ARGUS Web.

## Desarrollo local

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

La documentación interactiva queda disponible en
`http://localhost:8000/docs`.

Sin MongoDB, la API puede iniciar, pero `GET /health` responde HTTP 503:

```json
{"status":"degraded","database":"unavailable"}
```

## Contrato para ARGUS Web

Base URL local: `http://localhost:8000`.

| Método | Endpoint | Uso |
| --- | --- | --- |
| GET | `/health` | Salud real del API y MongoDB |
| GET | `/api/system/summary` | Totales para las tarjetas del dashboard |
| GET/POST | `/api/cameras` | Listar y registrar cámaras |
| GET/PATCH/DELETE | `/api/cameras/{id}` | CRUD de una cámara |
| POST | `/api/cameras/{id}/heartbeat` | Actualizar online/offline y FPS |
| GET/POST | `/api/events` | Timeline y creación de eventos |
| GET/PATCH/DELETE | `/api/events/{id}` | CRUD de eventos |
| GET/POST | `/api/tasks` | Listar y crear tareas de la asignaciÃ³n |
| GET/PATCH/DELETE | `/api/tasks/{id}` | Consultar, editar y eliminar una tarea |
| WebSocket | `/ws/events` | Eventos `event_created`, `event_updated`, `event_deleted` y `camera_status` |

### Contrato de tareas

La API conserva el contrato solicitado por la asignaciÃ³n:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente"
}
```

Estados admitidos: `Pendiente`, `En progreso` y `Completada`. La respuesta
incluye `id`, `created_at` y `updated_at`. Las tareas de vigilancia también
pueden incluir `source`, `camera_id`, `event_id`, `event_type` y `priority`.

Las alertas de cámara se agrupan por cámara, tipo y objeto. Mientras una alerta
permanece pendiente, nuevos eventos actualizan `occurrences`, `last_event_id`
y `last_seen_at` en la misma tarea. Al marcarla como `Completada`, una nueva
aparición puede generar otra tarea.

Ejemplo de cámara:

```json
{
  "id": "CAM-001",
  "name": "USB Camera Gustavo",
  "type": "usb",
  "stream_url": "http://TAILSCALE_IP:8081/stream",
  "status": "online",
  "fps": 24.0
}
```

El frontend debe renderizar `stream_url` como fuente de un `<img>` para MJPEG.
Para las cámaras que corren en otra máquina, la URL debe usar la IP de
Tailscale, nunca `localhost`.

## Docker

```powershell
docker build -t argus-api:0.4.0 ./backend
docker run --rm -p 8000:8000 --env-file backend/.env argus-api:0.4.0

# Para Docker Hub, sustituye TU_USUARIO por tu usuario real:
docker tag argus-api:0.4.0 TU_USUARIO/argus-api:0.4.0
docker push TU_USUARIO/argus-api:0.4.0
```

## Kubernetes en la máquina A

```powershell
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
kubectl get pods
kubectl get services
kubectl scale deployment argus-api --replicas=4
```

El API queda publicado en `http://TAILSCALE_IP_DE_GUSTAVO:30080`.
