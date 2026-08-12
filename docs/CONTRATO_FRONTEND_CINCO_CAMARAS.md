# Contrato de integración del frontend

## Sistema Distribuido de Gestión de Tareas y Vigilancia

Este documento define exactamente qué debe consumir y mostrar el frontend de
Juanfer. La funcionalidad obligatoria sigue siendo el CRUD de tareas. Las
cámaras y eventos representan la ampliación distribuida de vigilancia.

## 1. URL del backend

### Desarrollo local

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Prueba entre máquinas

```env
NEXT_PUBLIC_API_URL=http://100.77.143.36:30080
```

La IP `100.77.143.36` corresponde a la Máquina A de Gustavo. Desde la Máquina
B nunca se debe usar `localhost` para llegar al backend.

## 2. Inventario lógico de cámaras

El frontend debe reservar cinco espacios, pero no asumir que todas están
conectadas. La disponibilidad real llega desde `/api/cameras`.

| ID | Nombre | Tipo | Host Edge | Puerto público | Fuente |
|---|---|---|---|---:|---|
| `CAM-001` | Cámara laptop Gustavo | integrada | `100.77.143.36` | `8091` | `0` |
| `CAM-002` | Cámara USB Gustavo | USB | `100.77.143.36` | `8092` | `1` confirmado cuando esté disponible |
| `CAM-003` | Teléfono Gustavo | phone/IP Webcam | `100.77.143.36` | `9020` | URL HTTP del celular |
| `CAM-004` | Cámara laptop Juanfer | integrada | `100.112.215.44` | `8093` | `0` en la PC de Juanfer |
| `CAM-005` | Teléfono Juanfer | phone/IP Webcam | `100.112.215.44` | `9010` | URL HTTP del celular |

Los puertos `8091`, `8092`, `8093`, `9010` y `9020` son puertos del Edge que
publica el stream procesado. El puerto interno de IP Webcam puede ser distinto.

## 3. Estados de cámara

Cada tarjeta debe representar uno de estos estados:

```text
online    -> Edge envía heartbeat y FPS mayor que cero
offline   -> no hay heartbeat reciente
degraded  -> Edge responde, pero no recibe frames o tiene error de fuente
disabled  -> cámara marcada como no disponible para la operación
unknown   -> todavía no existe registro en el backend
```

La tarjeta nunca debe desaparecer porque una cámara esté desconectada. Debe
permanecer como espacio reservado mostrando el motivo:

```text
CAM-004
Sin conexión
Esperando heartbeat de Juanfer
```

## 4. Descubrimiento de cámaras

Al cargar el dashboard:

```http
GET /api/cameras
```

Ejemplo de respuesta:

```json
[
  {
    "id": "CAM-001",
    "name": "Camara integrada Gustavo",
    "type": "integrated",
    "stream_url": "http://100.77.143.36:8091/stream",
    "source": "0",
    "vision_mode": "cctv",
    "status": "online",
    "fps": 29.7,
    "last_heartbeat": "2026-08-12T18:30:00+00:00"
  }
]
```

El frontend debe mapear por `id`, no por posición del arreglo. Si falta una
cámara, crea una tarjeta vacía para el ID esperado.

## 5. Renderizado del stream

El Edge actual entrega MJPEG. Usar:

```tsx
<img src={camera.stream_url} alt={camera.name} />
```

No usar `<video>` para estos streams. WebRTC no forma parte del contrato actual.

Si `stream_url` contiene `localhost` y el frontend corre en otra máquina,
mostrar error de configuración: el backend debe registrar la IP Tailscale del
host Edge.

## 6. CRUD obligatorio de tareas

```http
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
```

Crear tarea manual:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente"
}
```

Estados válidos:

```text
Pendiente
En progreso
Completada
```

La pantalla debe permitir crear, editar, completar, eliminar y filtrar tareas.

## 7. Tareas automáticas de vigilancia

Cuando una cámara detecta algo:

```text
Edge detecta objeto
    -> POST /api/events
    -> backend guarda evento
    -> backend crea o actualiza alerta
    -> frontend recibe task_created/task_updated
```

Una alerta automática tiene campos adicionales:

```json
{
  "id": "TASK-123",
  "titulo": "person tracked as #7",
  "estado": "Pendiente",
  "source": "camera",
  "camera_id": "CAM-001",
  "event_id": "EVT-123",
  "event_type": "object_detected",
  "priority": "high",
  "occurrences": 5,
  "last_event_id": "EVT-456",
  "last_seen_at": "2026-08-12T18:30:00+00:00"
}
```

El frontend debe distinguir visualmente:

```text
source=manual -> tarea normal
source=camera -> alerta de vigilancia
```

## 8. Eventos

```http
GET /api/events?camera_id=CAM-001&limit=50
GET /api/events/{event_id}
```

Un evento contiene:

```json
{
  "id": "EVT-123",
  "camera_id": "CAM-001",
  "type": "object_detected",
  "object_name": "person",
  "confidence": 0.86,
  "description": "person tracked as #7",
  "metadata": {
    "track_id": 7,
    "bbox": [145, 107, 1159, 713]
  },
  "status": "new",
  "timestamp": "2026-08-12T18:30:00+00:00"
}
```

El panel debe mostrar objeto, confianza, cámara, fecha, estado y tarea
relacionada.

## 9. Tiempo real

Conectar:

```text
ws://100.77.143.36:30080/ws/events
```

Eventos esperados:

```text
camera_status
event_created
event_updated
event_deleted
task_created
task_updated
```

Si el WebSocket se desconecta, el frontend debe reconectar y usar polling como
respaldo:

```text
GET /api/cameras cada 10 segundos
GET /api/tasks cada 10 segundos
```

## 10. Conectar y desconectar cámaras

### Actualmente implementado

- El Edge se inicia en el host de la cámara.
- Se registra automáticamente con `POST /api/cameras`.
- Envía heartbeats.
- El backend calcula `online`, `offline` o `degraded`.
- El frontend puede mostrar disponibilidad y ocultar/mostrar el stream.

### Todavía pendiente para activación real desde un botón

El frontend no puede iniciar directamente `start-edge.ps1`. Para eso hace falta
un supervisor instalado en cada PC:

```text
Frontend -> Backend -> Supervisor Edge del host -> proceso Edge
```

Contrato futuro del supervisor:

```http
GET  /edge/health
GET  /edge/discover
POST /edge/cameras/start
POST /edge/cameras/stop
```

Mientras ese supervisor no exista, “desconectar” significa marcar la cámara
como deshabilitada o detener su Edge; “conectar” significa iniciar el Edge y
dejar que se registre automáticamente.

## 11. Réplicas de Kubernetes

Las cuatro réplicas del backend no representan cuatro cámaras.

```text
4 réplicas = 4 copias de la API FastAPI
1 cámara   = 1 proceso Edge
```

El Service NodePort distribuye las peticiones entre las réplicas. Todas usan la
misma MongoDB, por lo que cualquier réplica puede atender:

```text
GET /api/tasks
POST /api/events
GET /api/cameras
```

No se deben levantar cuatro Edges para una sola cámara, porque generarían
eventos duplicados y competirían por el mismo dispositivo.

## 12. Arquitectura para la exposición

```text
Sensores y cámaras
  laptop Gustavo, USB, teléfono Gustavo,
  laptop Juanfer, teléfono Juanfer
          |
          v
Nodos Edge distribuidos
          |
          | Tailscale
          v
Backend FastAPI / NodePort
       |              |
       v              v
   MongoDB       WebSocket/API
                         |
                         v
                  Frontend Juanfer
```

La aplicación cumple el CRUD obligatorio y agrega vigilancia distribuida. Las
cámaras generan eventos; los eventos generan o actualizan tareas; el usuario
revisa esas tareas desde el frontend.

## 13. Checklist de integración

- [ ] Frontend usa `API_URL` por Tailscale.
- [ ] Existen cinco espacios de cámara.
- [ ] Las cámaras ausentes aparecen como `offline` o `unknown`.
- [ ] Las cámaras online muestran stream, FPS y modo.
- [ ] CRUD manual funciona.
- [ ] Tareas automáticas muestran cámara y evento.
- [ ] Eventos aparecen en timeline.
- [ ] WebSocket actualiza sin recargar.
- [ ] Backend responde desde el NodePort `30080`.
- [ ] Backend escala a 4 réplicas sin duplicar cámaras.
