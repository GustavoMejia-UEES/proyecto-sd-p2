# ARGUS — visión del sistema y checklist de frontend

Documento corto para explicar el proyecto, definir el resultado final y entregarle a Juanfer las tareas concretas del frontend.

## 1. ¿Qué es ARGUS?

ARGUS es un sistema distribuido de vigilancia inteligente. Recibe video desde varias cámaras, analiza la imagen cerca de cada cámara, detecta objetos o movimiento y presenta todo en un dashboard web en tiempo real.

La idea principal es:

> El backend procesa y entiende el video. El frontend lo visualiza, organiza los eventos y permite operar el sistema.

El frontend no debe ejecutar YOLO ni leer directamente la webcam. Solo consume el video, los estados y los eventos que entrega ARGUS.

## 2. ¿Cuál es el resultado final?

El usuario final debería ver una consola de vigilancia con:

- Varias tarjetas de cámaras en un grid.
- Video en vivo por cámara.
- Cajas de detección con etiquetas como `person`, `bottle`, `chair`, etc.
- Estado de conexión: `online`, `degraded` u `offline`.
- FPS, modo de visión y cantidad de objetos detectados.
- Timeline de eventos recientes.
- Alertas en tiempo real.
- Filtros por cámara, tipo de evento, ubicación y estado.
- Vista detallada de cada cámara.
- Indicadores de salud del API, MongoDB y WebSocket.

Visualmente, ARGUS debe sentirse como una central de monitoreo: oscura, clara, rápida y orientada a eventos.

## 3. ¿Cómo funciona el sistema?

```mermaid
flowchart LR
    A[Webcam / celular / cámara IP] --> B[ARGUS Edge]
    B -->|MJPEG /stream| F[Frontend ARGUS Web]
    B -->|heartbeat + eventos| C[ARGUS Core API]
    C --> D[(MongoDB)]
    C -->|WebSocket /ws/events| F
    T[Tailscale] -. red privada .-> B
    T -. red privada .-> C
    T -. acceso remoto .-> F
```

### Componentes

| Componente | Qué hace | Dónde vive actualmente |
|---|---|---|
| Cámara | Produce frames de video | Laptop, celular, USB o IP |
| Edge | Captura, detecta, rastrea, dibuja cajas y publica stream | Host donde está la cámara |
| Core API | Registra cámaras, recibe heartbeats, guarda eventos y comunica estados | Contenedor Docker |
| MongoDB | Guarda cámaras y eventos | Contenedor Docker, red interna |
| Frontend | Dashboard, video, alertas y operación | Aplicación web de Juanfer |
| Tailscale | Conecta nodos sin depender de IP pública | Cada host remoto |

## 4. ¿Qué está hecho actualmente?

### Core API

- FastAPI centralizado.
- MongoDB con health check real.
- CRUD de cámaras.
- Endpoint para configurar/provisionar cámaras.
- Heartbeats periódicos desde cada Edge.
- Estados `online`, `degraded` y `offline`.
- FPS por cámara.
- Registro de eventos.
- WebSocket para actualizaciones en tiempo real.
- Compose con redes separadas:
  - `argus_core_net`: API + MongoDB.
  - `argus_iot_net`: API + Edge.

### Edge

- Webcam integrada funcionando con `source 0`.
- Stream MJPEG en `/stream`.
- Detección YOLO opcional.
- Tracking persistente de objetos.
- Bounding boxes con etiqueta, confianza e ID.
- HUD visual con FPS, modo y objetos rastreados.
- Detección de movimiento con OpenCV.
- Heartbeat cada pocos segundos.
- Reconexión si la cámara falla.
- Inferencia separada del ciclo de captura para no congelar el video.
- Parámetros configurables para FPS, resolución, modelo y latencia.

### Multi-cámara

Cada cámara tiene:

- `camera_id` único.
- `source` propio.
- Puerto de stream propio.
- Proceso Edge propio.
- Heartbeat propio.
- Eventos asociados a su ID.

Existe un manifiesto en `scripts/cameras.example.json` y un launcher en `scripts/start-edge-fleet.ps1`.

## 5. Contrato principal para el frontend

### Base URL

Local:

```text
http://localhost:8000
```

Remoto por Tailscale:

```text
http://IP_TAILSCALE_DEL_CORE:8000
```

La Base URL debe estar en una variable de entorno del frontend, por ejemplo:

```text
VITE_ARGUS_API_URL=http://localhost:8000
```

### Endpoints

| Método | Endpoint | Uso |
|---|---|---|
| `GET` | `/health` | Saber si API y MongoDB están saludables |
| `GET` | `/api/system/summary` | KPIs generales del dashboard |
| `GET` | `/api/cameras` | Listar todas las cámaras |
| `GET` | `/api/cameras/{camera_id}` | Ver una cámara |
| `POST` | `/api/cameras/configure` | Provisionamiento administrativo |
| `PATCH` | `/api/cameras/{camera_id}` | Actualizar configuración |
| `POST` | `/api/cameras/{camera_id}/heartbeat` | Uso interno del Edge |
| `GET` | `/api/events` | Timeline y filtros |
| `PATCH` | `/api/events/{event_id}` | Marcar alerta como atendida/resuelta |
| `WS` | `/ws/events` | Eventos y cambios de estado en tiempo real |

### Cámara

```json
{
  "id": "CAM-001",
  "name": "Camera Laptop Gustavo",
  "type": "integrated",
  "stream_url": "http://localhost:8091/stream",
  "source": "0",
  "vision_mode": "cctv",
  "location": "Laboratorio",
  "status": "online",
  "fps": 10.41,
  "metadata": {
    "network": {
      "iot_segment": "iot-cameras"
    }
  },
  "last_heartbeat": "2026-08-12T04:24:29Z"
}
```

### Evento de detección

```json
{
  "id": "EVT-ABC123",
  "camera_id": "CAM-001",
  "type": "object_detected",
  "object_name": "person",
  "confidence": 0.87,
  "status": "new",
  "description": "person tracked as #4",
  "metadata": {
    "source": "ultralytics",
    "track_id": 4,
    "bbox": [120, 80, 360, 500]
  },
  "timestamp": "2026-08-12T04:24:29Z"
}
```

### Health del Edge

```json
{
  "camera_id": "CAM-001",
  "status": "online",
  "fps": 10.41,
  "vision_mode": "cctv",
  "detection_enabled": true,
  "detector": "yolo11n.pt",
  "detection_error": null,
  "detections": 1,
  "labels": ["person"],
  "detection_latency_ms": 134.58
}
```

## 6. Stream de video

El backend entrega actualmente MJPEG.

En el frontend se debe renderizar así:

```jsx
<img
  src={camera.stream_url}
  alt={`Stream de ${camera.name}`}
  className="camera-stream"
/>
```

No usar `<video>` para este endpoint actual.

### Regla de URLs

- Si el frontend y Edge están en la misma laptop: `localhost` funciona.
- Si el frontend está en otra máquina: `localhost` está mal.
- En una demo remota, usar la IP Tailscale del host Edge:

```text
http://100.x.y.z:8091/stream
```

`0.0.0.0` sirve para que el servidor escuche en todas las interfaces, pero no es una dirección que se deba abrir en el navegador.

## 7. Estados de conexión

| Estado | Significado | UI sugerida |
|---|---|---|
| `online` | Heartbeat reciente y Edge funcionando | Verde, stream activo |
| `degraded` | Edge existe, pero tiene problemas de captura o dependencia | Amarillo, warning |
| `offline` | No hay heartbeat reciente o la cámara se desconectó | Rojo/gris, stream bloqueado |

El frontend debe mostrar el estado del backend aunque el `<img>` todavía tenga una URL. El stream accesible no reemplaza el estado de salud.

## 8. WebSocket en tiempo real

Conectar a:

```text
ws://localhost:8000/ws/events
```

En remoto:

```text
ws://IP_TAILSCALE_DEL_CORE:8000/ws/events
```

Tipos actuales:

| `type` | Acción del frontend |
|---|---|
| `event_created` | Agregar evento al timeline y mostrar alerta |
| `event_updated` | Actualizar status o descripción |
| `event_deleted` | Retirar evento del estado local |
| `camera_status` | Actualizar badge y disponibilidad de la cámara |

### Reglas de implementación

- Abrir un solo WebSocket global, no uno por cámara.
- No duplicar listeners al cambiar de página.
- Reintentar con backoff si se desconecta.
- Mantener la carga inicial REST y luego actualizar por WebSocket.
- No crear una alerta por cada frame; el Edge ya aplica cooldown a los eventos.

## 9. Checklist exacto para Juanfer

### A. Base del proyecto

- [ ] Crear variable `VITE_ARGUS_API_URL`.
- [ ] Crear cliente HTTP centralizado.
- [ ] Crear tipos/interfaces `Camera`, `Event`, `SystemSummary`.
- [ ] Crear manejo global de loading, error y reconexión.
- [ ] Configurar la URL del WebSocket a partir de la Base URL.

### B. Dashboard principal

- [ ] Consumir `/health`.
- [ ] Consumir `/api/system/summary`.
- [ ] Consumir `/api/cameras`.
- [ ] Renderizar tarjetas dinámicas, no tarjetas hardcodeadas.
- [ ] Mostrar total de cámaras.
- [ ] Mostrar cámaras online.
- [ ] Mostrar eventos del día.
- [ ] Mostrar estado del WebSocket.

### C. Tarjeta de cámara

- [ ] Mostrar `name`.
- [ ] Mostrar `location` si existe.
- [ ] Mostrar `status` con color.
- [ ] Renderizar `stream_url` con `<img>`.
- [ ] Mostrar FPS.
- [ ] Mostrar `vision_mode`.
- [ ] Mostrar cantidad de detecciones cuando esté disponible.
- [ ] Mostrar placeholder si la cámara no está online.
- [ ] Mostrar botón para abrir detalle.

### D. Eventos y alertas

- [ ] Consumir `/api/events` al cargar.
- [ ] Ordenar por timestamp descendente.
- [ ] Filtrar por cámara.
- [ ] Filtrar por tipo.
- [ ] Filtrar por status.
- [ ] Mostrar `object_name`.
- [ ] Mostrar confianza como porcentaje.
- [ ] Mostrar track ID cuando exista.
- [ ] Mostrar timestamp legible.
- [ ] Escuchar `event_created` por WebSocket.
- [ ] Permitir cambiar evento a `acknowledged` o `resolved`.

### E. Detalle de cámara

- [ ] Mostrar stream grande.
- [ ] Mostrar estado y último heartbeat.
- [ ] Mostrar FPS.
- [ ] Mostrar modo de visión.
- [ ] Mostrar labels detectados.
- [ ] Mostrar latencia de inferencia si el Edge la expone.
- [ ] Mostrar metadata de red sin exponer credenciales.

### F. Tiempo real y robustez

- [ ] Implementar reconexión de WebSocket.
- [ ] Mostrar banner `Reconnecting`.
- [ ] Actualizar solo la cámara/evento afectado.
- [ ] Evitar recargar toda la página.
- [ ] Evitar memory leaks de listeners.
- [ ] Manejar cámara sin stream.
- [ ] Manejar API caída.
- [ ] Manejar MongoDB no disponible mediante `/health`.

### G. Responsive y presentación

- [ ] Grid de 1 columna en móvil.
- [ ] Grid de 2 columnas en tablet.
- [ ] Grid de 3 o 4 columnas en escritorio.
- [ ] Sidebar o panel para alertas.
- [ ] Modo oscuro estilo central de vigilancia.
- [ ] Skeleton loading.
- [ ] Empty state cuando no haya cámaras.
- [ ] Mensajes de error claros.

## 10. Qué no debe hacer Juanfer

- No instalar YOLO en el frontend.
- No abrir la webcam desde el navegador para reemplazar Edge.
- No consultar MongoDB directamente.
- No hardcodear `CAM-001`.
- No asumir que todas las cámaras tienen el mismo puerto.
- No usar `localhost` para cámaras ubicadas en otra máquina.
- No crear un WebSocket por cámara.
- No mostrar todas las detecciones como alertas nuevas si solo son actualizaciones de tracking.

## 11. Cómo se conectan celulares y más cámaras

### Laptop o webcam USB

Cada webcam corre un Edge con un `source` diferente:

```powershell
# Webcam integrada
.\scripts\start-edge.ps1 -CameraId CAM-001 -CameraSource 0 -Port 8091 -Vision -VisionMode cctv

# Webcam USB secundaria
.\scripts\start-edge.ps1 -CameraId CAM-002 -CameraSource 1 -Port 8092 -Vision -VisionMode cctv
```

### Celular o cámara IP

El dispositivo debe entregar un stream MJPEG/RTSP o estar conectado a un host que pueda leerlo. Ese host ejecuta Edge y se registra con un `camera_id` nuevo.

Ejemplo conceptual:

```json
{
  "camera_id": "CAM-002",
  "name": "Celular laboratorio",
  "type": "phone",
  "source": "rtsp://USUARIO:CONTRASENA@100.x.y.z:554/stream",
  "port": 8092,
  "vision_mode": "cctv"
}
```

### Tailscale

1. Instalar Tailscale en el host de la cámara.
2. Instalar Tailscale en el host del Core API.
3. Instalar Tailscale en el equipo que ejecuta el frontend remoto.
4. Iniciar sesión en el mismo tailnet.
5. Obtener la IP con `tailscale ip -4`.
6. Usar esa IP en `edge_host`, `stream_url` y `core_api_url`.
7. Permitir únicamente los puertos necesarios: API `8000` y streams Edge `8091+`.

La etiqueta `iot_segment: iot-cameras` ayuda a identificar el grupo, pero la seguridad real se completa con Tailscale grants, firewall y permisos de red.

## 12. ¿Qué significa que una cámara viva “virtualmente” en un pod?

La cámara física no vive dentro del pod. Lo que vive en el pod es el agente Edge que representa y procesa esa cámara.

```text
CAM-001 = identidad lógica en MongoDB
Edge CAM-001 = proceso/pod que captura y analiza
stream_url = dirección del video
heartbeat = prueba de que el Edge sigue vivo
events = hechos detectados por ese Edge
```

En local:

```text
1 proceso Edge por cámara
```

En Kubernetes:

```text
1 Pod/Deployment Edge por cámara o por stream
```

El Core API sigue viendo lo mismo: cámaras, estados, FPS, eventos y URLs. Por eso Juanfer no debe acoplar el frontend a Docker o Kubernetes; debe consumir el contrato de la API.

## 13. Resultado esperado de la primera versión del frontend

La demo debe poder contar esta historia:

1. El usuario abre ARGUS.
2. El dashboard muestra que la API y MongoDB están saludables.
3. Aparecen varias cámaras con sus estados.
4. Cada tarjeta reproduce su stream.
5. El Edge detecta una persona y dibuja una caja.
6. El Core API recibe `object_detected`.
7. El frontend muestra una alerta en el timeline sin refrescar la página.
8. Si se apaga una cámara, cambia a `offline`.
9. Si vuelve a conectarse, cambia a `online`.
10. El usuario puede filtrar y revisar qué pasó por cámara.

## 14. Lo que queda para después

Estas capacidades están planeadas, pero no deben bloquear la primera integración:

- Zonas de interés.
- Snapshots asociados a eventos.
- Retención de video.
- WebRTC para menor latencia.
- Redis/pub-sub para varias réplicas del Core API.
- Autenticación y roles.
- Fine-tuning con objetos propios del proyecto.
- Pose y análisis de actividad.
- Detección de emociones con cautela y validación independiente.
- Kubernetes para despliegue distribuido.

Para el estado real del backend y la propuesta de runtime observable, consultar
[`ARGUS_BACKEND_STATUS_RUNTIME.md`](./ARGUS_BACKEND_STATUS_RUNTIME.md).

## 15. Texto resumido para una diapositiva

### ARGUS: sistema distribuido de vigilancia inteligente

- **Edge:** captura y analiza el video cerca de cada cámara.
- **Core API:** centraliza cámaras, estados, heartbeats y eventos.
- **MongoDB:** conserva la información histórica del sistema.
- **Tailscale:** conecta laptops, celulares, cámaras y frontend en una red privada.
- **Frontend:** muestra streams, detecciones, alertas y estados en tiempo real.

### Flujo

```text
Cámara → Edge + YOLO → Core API + MongoDB → WebSocket → Dashboard Web
```

### Resultado

Una central de monitoreo capaz de crecer de una webcam local a múltiples cámaras distribuidas sin cambiar el contrato principal del frontend.

## 16. Mensaje listo para Juanfer

> Juanfer, el frontend de ARGUS debe ser un dashboard de monitoreo en tiempo real. Consume el Core API para listar cámaras, consultar salud, ver eventos y escuchar cambios por WebSocket. Cada cámara trae su propio `stream_url` MJPEG, que se renderiza con `<img>`. El backend/Edge ya se encarga de YOLO, tracking, cajas, FPS, heartbeats y eventos. Tu foco es construir el grid de cámaras, estados, timeline, filtros, detalle de cámara, reconexión y una experiencia visual tipo central CCTV. No hardcodees cámaras y no uses `localhost` para dispositivos remotos: las URLs remotas usarán la IP Tailscale del host Edge.

## Referencias técnicas

- Ultralytics Tracking: <https://docs.ultralytics.com/modes/track>
- Ultralytics Training: <https://docs.ultralytics.com/modes/train>
- OpenCV VideoCapture: <https://docs.opencv.org/4.9.0/d4/d15/group__videoio__flags__base.html>
- Tailscale Windows: <https://tailscale.com/docs/install/windows>
- Tailscale Grants: <https://tailscale.com/docs/features/access-control/grants>
- Tailscale Serve: <https://tailscale.com/docs/reference/tailscale-cli/serve>
