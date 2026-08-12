# Sistema Distribuido de Gestión y Vigilancia

## Contexto

La aplicación combina la funcionalidad obligatoria de gestión de tareas con
una ampliación de vigilancia distribuida. El backend, MongoDB y los nodos Edge
corren en la Máquina A; el frontend corre en la Máquina B. Ambas máquinas se
comunican mediante Tailscale y cada una tiene su propio Kubernetes de Docker
Desktop.

La funcionalidad base no cambia: crear, listar, editar y eliminar tareas. Las
cámaras agregan una segunda capa: funcionan como nodos distribuidos que generan
eventos de vigilancia y, cuando un evento requiere atención, el backend puede
crear una tarea automática.

## Arquitectura

```text
Máquina A — Estudiante A
  Backend FastAPI + MongoDB + Edge de cámaras
  Backend publicado como NodePort :30080

                 Tailscale
        IP privada 100.x.x.x

Máquina B — Estudiante B
  Frontend Next.js/Bun
```

```text
Navegador B -> Tailscale -> NodePort backend A
                             |
                             +-> Pods backend -> MongoDB ClusterIP
                             +-> eventos y tareas

Cámara/Edge -> stream MJPEG + heartbeat + eventos -> Backend
```

## Funcionalidad obligatoria

La tarea mínima es:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente"
}
```

Endpoints:

```text
GET    /api/tasks
POST   /api/tasks
GET    /api/tasks/{id}
PATCH  /api/tasks/{id}
DELETE /api/tasks/{id}
```

El frontend de Juanfer consume estos endpoints. No crea otra API ni otra base
de datos. La información real viene de MongoDB en la Máquina A.

## Cámaras como nodos distribuidos

Cada cámara tiene un `camera_id` y puede ser integrada, USB, IP, RTSP, teléfono
o virtual. El Edge captura video, publica un stream, envía heartbeats y puede
enviar detecciones de movimiento, personas u objetos.

El backend conserva el estado de cada cámara:

```text
online | offline | degraded
```

## Evento automático y tarea automática

El flujo correcto es:

```text
1. La cámara captura un frame.
2. Edge detecta movimiento, persona u objeto.
3. Edge envía un evento al backend.
4. Backend guarda el evento en MongoDB.
5. Backend decide si requiere atención.
6. Si requiere atención, crea una tarea automática.
7. Frontend muestra la tarea y el evento relacionado.
8. Usuario revisa y cambia su estado.
```

Ejemplo de evento:

```json
{
  "camera_id": "CAM-001",
  "type": "person",
  "object_name": "person",
  "confidence": 0.91,
  "description": "Persona detectada en laboratorio"
}
```

Ejemplo de tarea automática:

```json
{
  "titulo": "Revisar persona detectada en laboratorio",
  "estado": "Pendiente",
  "source": "camera",
  "camera_id": "CAM-001",
  "event_id": "EVT-123",
  "priority": "high"
}
```

Las tareas manuales usan `source=manual` y las automáticas `source=camera`.
Ambas se administran con el mismo CRUD. El backend debe aplicar cooldown o
deduplicación para no crear una tarea por cada frame.

## Qué verá el usuario

- Tareas manuales.
- Tareas generadas por vigilancia.
- Cámara y evento relacionados.
- Cuadrícula de streams.
- Estado online/offline/degraded.
- Timeline de eventos.
- Estado de salud del backend.

## Tecnologías

- Backend: FastAPI, PyMongo y MongoDB.
- Edge: OpenCV, MJPEG, heartbeats y YOLO opcional.
- Frontend: Next.js, TypeScript y Bun.
- Infraestructura: Docker, Docker Compose, Kubernetes y Tailscale.

## Video

El stream actual es MJPEG y se renderiza con `<img src={stream_url}>`. WebRTC
queda como mejora futura porque requiere señalización y un relay multimedia.

## Mensaje para la exposición

> El proyecto implementa una aplicación distribuida de gestión de tareas. Como
> ampliación, incorpora nodos Edge de vigilancia que generan eventos automáticos.
> Los eventos relevantes se convierten en tareas operativas que el usuario
> revisa desde un frontend desplegado en otra máquina mediante Tailscale.
