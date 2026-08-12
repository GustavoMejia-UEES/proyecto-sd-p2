# ARGUS — Handoff para Juanfer

## Objetivo

Construir el frontend de la aplicación distribuida de tareas y del panel ARGUS.
El frontend corre en la Máquina B y consume el backend que corre en la Máquina
A. Las máquinas se comunican mediante Tailscale.

La primera entrega evaluable es la aplicación CRUD de tareas. El panel de
cámaras es la integración avanzada de ARGUS.

## Stack recomendado

- Next.js con App Router.
- Bun como package manager y runtime de desarrollo.
- TypeScript.
- Tailwind CSS o una librería de componentes.
- `fetch` o TanStack Query para consumir la API.
- WebSocket nativo para eventos en tiempo real.

Comandos iniciales:

```powershell
bunx create-next-app@latest argus-frontend --typescript --eslint --app
cd argus-frontend
bun install
bun dev -H 0.0.0.0
```

## Configuración del backend

En desarrollo local:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Cuando el frontend esté en la Máquina B:

```env
NEXT_PUBLIC_API_URL=http://TAILSCALE_IP_A:30080
```

`TAILSCALE_IP_A` es la IP Tailscale de la Máquina A. Nunca debe usarse
`localhost` desde la Máquina B, porque allí apunta a la propia Máquina B.

## API de tareas

Base URL: `${NEXT_PUBLIC_API_URL}`.

| Acción | Método | Endpoint | Body |
| --- | --- | --- | --- |
| Listar | GET | `/api/tasks` | — |
| Crear | POST | `/api/tasks` | `{ "titulo": "...", "estado": "Pendiente" }` |
| Consultar | GET | `/api/tasks/{id}` | — |
| Editar | PATCH | `/api/tasks/{id}` | `{ "titulo": "...", "estado": "Completada" }` |
| Eliminar | DELETE | `/api/tasks/{id}` | — |
| Salud | GET | `/health` | — |

Estados admitidos:

```text
Pendiente
En progreso
Completada
```

Respuesta de ejemplo:

```json
{
  "id": "TASK-ABC12345",
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente",
  "created_at": "2026-08-12T14:00:00+00:00",
  "updated_at": "2026-08-12T14:00:00+00:00"
}
```

## Panel de cámaras

El backend expone:

```text
GET    /api/cameras
GET    /api/cameras/{id}
POST   /api/cameras/configure
PATCH  /api/cameras/{id}
DELETE /api/cameras/{id}
GET    /api/events
GET    /api/system/summary
WS     /ws/events
```

Cada cámara devuelve un `stream_url`. Para el agente Edge actual, el stream es
MJPEG y se renderiza así:

```tsx
<img src={camera.stream_url} alt={camera.name} />
```

Si la cámara corre en la Máquina A o en otro dispositivo, `stream_url` debe
usar una IP alcanzable por Tailscale; no debe contener `localhost`.

## MJPEG, WebRTC y decisión práctica

Para esta entrega se recomienda usar MJPEG para mostrar las cámaras del backend:

- Ya está implementado en el agente Edge.
- Funciona directamente en navegador con `<img>`.
- Es sencillo de probar y no requiere señalización.
- El backend ya devuelve la URL correcta por cámara.

WebRTC puede agregarse como segunda etapa. Es ideal para baja latencia, pero
requiere señalización, gestión de sesiones ICE/STUN/TURN y un productor WebRTC.
El backend actual todavía no es un servidor WebRTC. No se debe prometer que un
`stream_url` MJPEG se puede poner directamente dentro de un `<video>` WebRTC.

Uso recomendado:

1. MJPEG para los streams entregados por ARGUS en la demostración.
2. `getUserMedia()` solamente para una vista previa de la cámara del navegador,
   si se necesita.
3. WebRTC como mejora posterior cuando exista un servicio de señalización y un
   relay/media server definido.

## Eventos en tiempo real

Conectar:

```ts
const wsUrl = apiUrl.replace(/^http/, "ws") + "/ws/events";
const socket = new WebSocket(wsUrl);
```

Eventos que el frontend debe tolerar:

```text
event_created
event_updated
event_deleted
camera_status
```

El dashboard debe refrescar la tarjeta de cámara, el timeline y los contadores
cuando lleguen estos eventos. Si el WebSocket se desconecta, el frontend debe
reconectar con backoff y continuar funcionando con polling.

## Estructura visual mínima

- Dashboard con total de tareas, pendientes y completadas.
- Tabla o tarjetas de tareas con crear, editar y eliminar.
- Indicador visible de `API online` o `API unavailable` usando `/health`.
- Vista de cámaras en cuadrícula.
- Estado de cámara: `online`, `offline` o `degraded`.
- FPS, modo de visión y cantidad de detecciones.
- Timeline de eventos.
- Selector de cámara y modo de visualización.

## Docker y Kubernetes del frontend

El frontend debe incluir su propio `Dockerfile` y publicarse en Docker Hub, o
construirse localmente dentro del Docker Desktop de la Máquina B.

La variable principal de producción será:

```text
NEXT_PUBLIC_API_URL=http://TAILSCALE_IP_A:30080
```

Su Kubernetes debe tener:

- Deployment del frontend con 1 réplica.
- ConfigMap para `API_URL` o configuración equivalente.
- Service para abrir el frontend desde el navegador.
- Ninguna conexión directa a MongoDB.

## Criterio de terminado

- La SPA abre desde la Máquina B.
- El navegador crea una tarea y aparece persistida al recargar.
- Editar y eliminar funcionan.
- `/health` muestra el estado real del backend.
- La URL de API usa la IP Tailscale de la Máquina A.
- El panel consume `/api/cameras` y muestra al menos un stream.
- El frontend se recupera si el WebSocket se desconecta.
