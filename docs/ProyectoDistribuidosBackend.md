# Sistema Distribuido de Gestión y Vigilancia — Backend

## Implementado actualmente

El backend es una API FastAPI con MongoDB, configuración por entorno, CORS,
OpenAPI en `/docs` y health check real en `/health`. El health check hace ping a
MongoDB y responde `healthy/connected` o HTTP 503 `degraded/unavailable`.

### Tareas

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
```

Las tareas contienen `id`, `titulo`, `estado`, `created_at` y `updated_at`.

### Cámaras

```text
GET    /api/cameras
POST   /api/cameras
POST   /api/cameras/configure
GET    /api/cameras/{camera_id}
PATCH  /api/cameras/{camera_id}
DELETE /api/cameras/{camera_id}
POST   /api/cameras/{camera_id}/heartbeat
```

Soporta cámaras integradas, USB, IP, RTSP, teléfonos y nodos virtuales.

### Eventos y tiempo real

```text
GET/POST/PATCH/DELETE /api/events
WS /ws/events
GET /api/system/summary
```

Los eventos representan movimiento, personas, objetos y estados de conexión.
El WebSocket notifica eventos y cambios de estado de cámaras.

### Edge y video

El agente Edge captura cámaras integradas y USB en Windows, permite múltiples
procesos, publica MJPEG en `/stream`, expone `/health` y `/discover`, envía
heartbeats, registra movimiento, puede ejecutar YOLO y reporta FPS, detecciones
y errores. Incluye perfiles `fast`, `balanced` y `quality`.

### Docker Compose

Compose contiene MongoDB en `argus_core_net`, API en `argus_core_net` e
`argus_iot_net`, Edge opcional, health checks y volumen persistente.

### Kubernetes

`k8s/mongodb.yaml` contiene Secret, Service ClusterIP, PVC y Deployment de
MongoDB. `k8s/backend.yaml` contiene ConfigMap, Secret, Deployment con 2
réplicas, probes y Service NodePort `30080` usando `argus-api:0.4.0`.

## Falta para completar la ampliación de vigilancia

La asignación base del CRUD ya está cubierta. Para conectar completamente
eventos y tareas falta:

### Campos opcionales en tareas

```text
source: manual | camera
camera_id: string opcional
event_id: string opcional
priority: low | medium | high
```

Esto mantiene compatible el payload original.

### Conversión evento-tarea

Crear una regla interna:

```text
evento importante -> crear tarea automática
evento informativo -> guardar solamente evento
```

Ejemplos: persona en zona restringida, cámara desconectada, objeto no permitido
o movimiento persistente.

### Deduplicación

Agregar cooldown para evitar una tarea por cada frame. Una primera regla puede
permitir una tarea equivalente por cámara cada 60 segundos.

### Reglas configurables

Como mejora, configurar por cámara qué eventos crean tareas y con qué prioridad.

### WebRTC

Todavía no está implementado. El stream actual es MJPEG; WebRTC requiere
señalización, ICE y un productor o relay multimedia.

## Validaciones

- Tests de contrato exitosos.
- Build Docker exitoso.
- Health real contra MongoDB exitoso.
- Smoke test de crear, editar y eliminar tareas exitoso.
- Branch `gustavo-backend`.
- Commit publicado: `d43e4dc`.

## Prioridad

1. Integrar frontend.
2. Conectar Tailscale.
3. Desplegar Kubernetes.
4. Obtener evidencias.
5. Agregar campos de origen.
6. Implementar evento a tarea.
7. Refinar vigilancia.
