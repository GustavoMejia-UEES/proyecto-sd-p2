# ARGUS — Backend implementado por Gustavo

## Resumen

El backend actual es una API FastAPI con MongoDB para administrar cámaras,
eventos, tareas y señales de estado. También incluye un agente Edge separado
para capturar cámaras locales, generar el stream y enviar heartbeats al API.

## Componentes entregados

### API Core

Ubicación: `backend/app/`.

- FastAPI centralizado.
- Configuración mediante variables de entorno y `.env`.
- CORS configurable.
- Documentación OpenAPI en `/docs`.
- Health check real en `/health`.
- El health check hace ping a MongoDB.
- HTTP 200 cuando la API y MongoDB están conectados.
- HTTP 503 cuando la API está viva pero MongoDB no está disponible.

### MongoDB

- MongoDB como persistencia principal.
- Colecciones `cameras`, `events` y `tasks`.
- Usuario y contraseña configurables mediante entorno.
- MongoDB queda en la red interna `core_net` en Compose.
- MongoDB usa Service `ClusterIP` en Kubernetes.

### Tareas de la asignación

Implementado en `backend/app/routes/tasks.py`:

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
```

Payload:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente"
}
```

Cada tarea recibe un ID, fecha de creación y fecha de actualización.

### Cámaras

Implementado:

```text
GET    /api/cameras
POST   /api/cameras
POST   /api/cameras/configure
GET    /api/cameras/{camera_id}
PATCH  /api/cameras/{camera_id}
DELETE /api/cameras/{camera_id}
POST   /api/cameras/{camera_id}/heartbeat
```

Una cámara puede ser integrada, USB, IP, RTSP, teléfono o virtual. La
configuración conserva nombre, fuente, ubicación, modo de visión, URL del
stream y segmento lógico IoT.

### Edge y visión

El agente Edge:

- Captura la cámara integrada o USB desde Windows.
- Puede trabajar con varias cámaras mediante procesos independientes.
- Publica MJPEG en `/stream`.
- Expone `/health` y `/discover`.
- Envía heartbeats periódicos al backend.
- Registra eventos de movimiento.
- Puede usar detección YOLO y dibujar cuadros sobre el stream.
- Reporta FPS, detecciones, modo de visión y errores de detección.
- Incluye perfiles de visión `fast`, `balanced` y `quality`.

La webcam de Windows se ejecuta actualmente fuera del contenedor mediante
`scripts/start-edge.ps1`, porque Docker Desktop no expone automáticamente la
cámara integrada de Windows a un contenedor Linux.

### Tiempo real

El API expone:

```text
WS /ws/events
```

Se publican cambios de eventos y estados de cámaras para que el frontend pueda
actualizar el dashboard sin depender únicamente de polling.

## Docker Compose

Compose define:

- `mongodb` en `argus_core_net`.
- `api` conectado a `argus_core_net` e `iot_net`.
- `edge` opcional mediante el profile `edge`.
- Health checks para MongoDB y API.
- Persistencia de MongoDB en un volumen.

Arranque:

```powershell
Copy-Item .env.example .env
docker compose up -d --build mongodb api
docker compose ps
```

## Kubernetes

Manifiestos:

- `k8s/mongodb.yaml`: Secret, Service ClusterIP, PVC y Deployment de MongoDB.
- `k8s/backend.yaml`: ConfigMap, Secret, Deployment de 2 réplicas y Service
  NodePort `30080`.

La imagen usada por Kubernetes es:

```text
argus-api:0.4.0
```

Construcción local para Docker Desktop Kubernetes:

```powershell
docker build -t argus-api:0.4.0 ./backend
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
```

## Verificación realizada

- Tests de contrato de FastAPI: 6 pruebas exitosas.
- Build Docker de `argus-api:0.4.0` exitoso.
- Health real contra MongoDB: `healthy/connected`.
- Smoke test real de crear, editar y eliminar tareas.
- Branch: `gustavo-backend`.
- Commit publicado: `d43e4dc`.

## Nota de alcance

El backend no implementa todavía WebRTC como servidor de medios. Entrega
MJPEG desde Edge, que es suficiente para la demostración actual y para que el
frontend renderice las cámaras. WebRTC requiere una capa adicional de
señalización y media relay.
