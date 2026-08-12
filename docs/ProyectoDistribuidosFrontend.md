# Sistema Distribuido de Gestión y Vigilancia — Frontend

## Responsabilidad de Juanfer

Juanfer construye únicamente el frontend. No crea otra API ni otra base de
datos. Consume el backend de la Máquina A.

## Stack recomendado

- Next.js con App Router.
- TypeScript.
- Bun.
- Tailwind CSS.
- Fetch o TanStack Query.
- WebSocket nativo.

```powershell
bunx create-next-app@latest frontend --typescript --eslint --app
cd frontend
bun install
bun dev -H 0.0.0.0
```

## Configuración

Local:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Entre máquinas:

```env
NEXT_PUBLIC_API_URL=http://TAILSCALE_IP_A:30080
```

Desde la Máquina B nunca se usa `localhost` para llegar al backend de A.

## Funcionalidad obligatoria

Consumir:

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{id}
PATCH  /api/tasks/{id}
DELETE /api/tasks/{id}
```

La interfaz debe crear, listar, editar y eliminar tareas; mostrar loading y
errores; y comprobar persistencia recargando la página.

Payload mínimo:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente"
}
```

## Vista de vigilancia

Consumir además:

```text
GET /api/cameras
GET /api/events
GET /api/system/summary
WS  /ws/events
```

Mostrar cuadrícula de cámaras, nombre, ubicación, estado, FPS, modo de visión,
detecciones, timeline y tareas relacionadas.

## Streams

El backend entrega MJPEG. Renderizar así:

```tsx
<img src={camera.stream_url} alt={camera.name} />
```

Si el frontend está en otra máquina, el `stream_url` debe usar una IP
alcanzable por Tailscale y no `localhost`. No usar `<video>` esperando que
MJPEG se convierta automáticamente en WebRTC.

## Tareas automáticas

La interfaz debe distinguir:

```text
manual  -> creada por el usuario
camera  -> creada por el backend debido a un evento
```

Una tarea de cámara puede mostrar su prioridad, cámara, evento relacionado y un
botón para abrir el stream. El frontend muestra el resultado; no inventa el
evento. El flujo es:

```text
Edge detecta -> Backend guarda evento -> Backend crea tarea -> Frontend muestra
```

## WebSocket

```ts
const wsUrl = apiUrl.replace(/^http/, "ws") + "/ws/events";
const socket = new WebSocket(wsUrl);
```

Manejar `event_created`, `event_updated`, `event_deleted` y `camera_status`.
Reconectar con backoff y conservar polling de respaldo.

## Docker y Kubernetes

El frontend debe tener Dockerfile propio:

```powershell
docker build -t sistema-frontend:0.1.0 .
docker run --rm -p 3000:3000 sistema-frontend:0.1.0
```

En Kubernetes de B debe entregar Deployment de 1 réplica, ConfigMap para la
URL del backend y Service del frontend. No debe desplegar MongoDB ni conectarse
directamente a MongoDB.

## Criterio de terminado

- SPA funcionando en B.
- Tareas obtenidas desde backend A.
- CRUD completo.
- Persistencia después de recargar.
- `/health` visible.
- API configurada con Tailscale.
- Al menos una cámara visible.
- Al menos un evento o tarea automática cuando Edge esté activo.
