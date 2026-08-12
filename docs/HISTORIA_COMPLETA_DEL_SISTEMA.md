# Historia completa del sistema distribuido

## 1. Punto de partida

El proyecto comenzó como una aplicación distribuida de gestión de tareas. La actividad requería separar el frontend y el backend en dos computadoras distintas, utilizar MongoDB, Docker, Kubernetes y una red privada con Tailscale.

La distribución inicial fue:

- Máquina A, Gustavo: backend y MongoDB.
- Máquina B, Juanfer: frontend.
- Comunicación entre máquinas: Tailscale.
- Orquestación: Kubernetes de Docker Desktop.

La funcionalidad mínima solicitada era un CRUD de tareas: crear, listar, editar y eliminar.

## 2. Construcción del backend

Se implementó una API con FastAPI y Python. El backend se organizó por rutas, esquemas y servicios para mantener una estructura clara y ampliable.

La API incorporó:

- configuración centralizada mediante variables de entorno;
- conexión a MongoDB;
- endpoint `/health` con comprobación real de la base de datos;
- CRUD completo de tareas;
- gestión de cámaras;
- gestión de eventos;
- actualización de estados mediante heartbeat;
- comunicación en tiempo real mediante WebSocket.

El endpoint `/health` diferencia entre una API activa y un sistema completamente saludable:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

Si MongoDB no está disponible, la API responde con estado degradado y código HTTP `503`.

## 3. Integración de MongoDB

MongoDB se utilizó como base de datos principal para almacenar:

- tareas manuales;
- tareas automáticas;
- cámaras registradas;
- eventos de vigilancia;
- estados y heartbeats de los dispositivos.

En Kubernetes, MongoDB funciona como un Deployment de una réplica y se expone mediante un Service `ClusterIP`. Esto significa que solo la API puede acceder directamente a la base de datos.

La contraseña se administra mediante un Secret y los parámetros de conexión mediante un ConfigMap.

## 4. Cumplimiento del CRUD de tareas

El backend expone los endpoints obligatorios:

```text
GET    /api/tasks
POST   /api/tasks
PATCH  /api/tasks/{id}
DELETE /api/tasks/{id}
```

Una tarea puede tener los siguientes datos:

```json
{
  "titulo": "Estudiar Kubernetes",
  "estado": "Pendiente",
  "source": "manual",
  "priority": "medium"
}
```

Además de las tareas creadas por los usuarios, el sistema puede generar tareas automáticamente a partir de eventos de vigilancia.

## 5. Evolución hacia vigilancia distribuida

Para ampliar la aplicación, las cámaras se modelaron como dispositivos Edge. Cada cámara tiene un proceso local que:

1. accede a una webcam, USB o celular;
2. captura los frames;
3. publica un stream MJPEG;
4. ejecuta detección visual;
5. envía eventos al backend;
6. reporta su estado mediante heartbeat;
7. intenta reconectarse si la fuente se desconecta.

Las cámaras físicas no se ejecutan dentro de los pods de Kubernetes porque pertenecen al hardware de Windows, USB o teléfonos. Kubernetes administra la API y la base de datos; los procesos Edge permanecen en los equipos que tienen acceso físico a las cámaras.

## 6. Cámaras configuradas

El sistema quedó preparado para cinco cámaras:

| Identificador | Equipo | Fuente | Stream Edge |
|---|---|---|---|
| CAM-001 | Gustavo | Laptop, source `0` | `http://100.77.143.36:8091/stream` |
| CAM-002 | Gustavo | USB, source `1` | `http://100.77.143.36:8092/stream` |
| CAM-003 | Gustavo | Celular IP Webcam | `http://100.77.143.36:9020/stream` |
| CAM-004 | Juanfer | Laptop, source `0` | `http://100.112.215.44:8091/stream` |
| CAM-005 | Juanfer | Celular IP Webcam | `http://100.112.215.44:9010/stream` |

El frontend no necesita conocer manualmente estas direcciones. Las obtiene mediante:

```text
GET /api/cameras
```

## 7. Estados de las cámaras

El sistema diferencia entre estado deseado y estado observado:

- `enabled`: indica si el usuario desea que la cámara esté activa;
- `online`: la fuente está entregando frames;
- `offline`: no hay conexión o la cámara está desactivada;
- `degraded`: el proceso Edge está vivo, pero la fuente tiene problemas.

El frontend puede activar o desactivar una cámara mediante:

```text
POST /api/cameras/{camera_id}/control
```

Body para activar:

```json
{
  "enabled": true
}
```

Body para desactivar:

```json
{
  "enabled": false
}
```

El proceso Edge consulta este estado periódicamente. De esta forma, el frontend controla la cámara sin ejecutar comandos de PowerShell directamente.

## 8. Detección visual y eventos

El agente Edge utiliza OpenCV para captura y movimiento, y YOLO para detección de objetos. El stream puede mostrar cuadros alrededor de los objetos identificados, junto con:

- etiqueta del objeto;
- nivel de confianza;
- identificador de seguimiento;
- coordenadas del bounding box;
- FPS;
- modo de visión.

Cada detección relevante genera un evento almacenado en MongoDB:

```json
{
  "camera_id": "CAM-001",
  "type": "object_detected",
  "object_name": "person",
  "confidence": 0.86,
  "metadata": {
    "track_id": 4,
    "bbox": [120, 80, 500, 700]
  }
}
```

Los eventos también pueden representar movimiento, conexión, desconexión o degradación de una cámara.

## 9. Generación automática de tareas

Cuando una cámara detecta un objeto, el backend puede crear una tarea automática. Los eventos repetidos no generan infinitas tareas iguales: se agrupan mediante una clave de alerta formada por cámara, tipo de evento y objeto.

Ejemplo:

```text
CAM-001:object_detected:person
```

La tarea conserva información como:

- número de ocurrencias;
- último evento recibido;
- última fecha de detección;
- cámara de origen;
- prioridad;
- estado de revisión.

Esto convierte una detección visual en una actividad gestionable desde el frontend.

## 10. Docker y entorno local

Docker Compose se utilizó para desarrollar y validar localmente:

- MongoDB;
- API FastAPI;
- health check;
- conexión con la base;
- pruebas iniciales de cámaras y tareas.

El backend tiene un Dockerfile basado en Python y expone el puerto interno `8000`.

Durante la demostración final, Compose se detiene para evitar confundirlo con Kubernetes. La ejecución oficial queda en Kubernetes.

## 11. Kubernetes en la Máquina A

La máquina de Gustavo utiliza Kubernetes de Docker Desktop. Se desplegaron:

- MongoDB con una réplica;
- API con dos réplicas iniciales;
- Service interno para MongoDB;
- Service `NodePort` para la API;
- ConfigMap para configuración;
- Secret para credenciales.

El backend se publica mediante:

```text
NodePort: 30080
```

Por tanto, la API se consume desde otra máquina con:

```text
http://100.77.143.36:30080
```

## 12. Tailscale y comunicación entre máquinas

Tailscale creó una red privada entre las computadoras y teléfonos. Las direcciones utilizadas fueron:

- Gustavo: `100.77.143.36`;
- celular Gustavo: `100.106.180.86`;
- Juanfer: `100.112.215.44`;
- celular Juanfer: `100.96.186.21`.

Gracias a Tailscale, Juanfer puede acceder al NodePort de Gustavo sin utilizar `localhost` ni depender de que ambas computadoras estén en la misma red Wi-Fi.

La prueba principal es:

```powershell
Test-NetConnection 100.77.143.36 -Port 30080
```

Y luego:

```powershell
Invoke-RestMethod "http://100.77.143.36:30080/health"
```

## 13. Escalamiento del backend

La actividad solicita demostrar el escalamiento del backend. Se ejecutó:

```powershell
kubectl scale deployment argus-api --replicas=4
```

El estado final esperado es:

```text
argus-api   4/4   Running
mongodb     1/1   Running
```

Las cuatro réplicas representan instancias de la API, no cámaras. Las cámaras continúan siendo procesos Edge independientes y todas utilizan la API y MongoDB centralizados.

## 14. Papel del frontend

El frontend de Juanfer consume la API mediante:

```env
NEXT_PUBLIC_API_URL=http://100.77.143.36:30080
```

Debe mostrar:

- listado de cámaras;
- estados online, offline y degraded;
- streams recibidos desde `stream_url`;
- eventos recientes;
- tareas automáticas;
- creación, edición y eliminación de tareas;
- controles para activar y desactivar cámaras.

Para mostrar un stream MJPEG, puede utilizar:

```jsx
<img src={camera.stream_url} alt={camera.name} />
```

El frontend funciona como panel de supervisión. No accede directamente a MongoDB ni controla hardware de forma directa.

## 15. Resultado final

El resultado es un sistema distribuido de gestión y vigilancia:

```text
Webcams, USB y celulares
            ↓
Procesos Edge en las computadoras físicas
            ↓
Tailscale
            ↓
API FastAPI en Kubernetes
            ↓
MongoDB en Kubernetes
            ↓
Frontend de Juanfer
```

La aplicación cumple el objetivo académico original porque permite crear, listar, editar y eliminar tareas desde un frontend separado. Además, amplía el alcance mediante cámaras distribuidas, streams, detección de objetos, eventos automáticos, tareas de vigilancia y escalamiento del backend.

## 16. Evidencias finales

Las evidencias principales son:

1. `tailscale status` mostrando las máquinas conectadas;
2. `kubectl get nodes` mostrando nodos en estado `Ready`;
3. `kubectl get pods` mostrando MongoDB y las réplicas de la API;
4. `kubectl get services` mostrando `ClusterIP` y `NodePort`;
5. `/health` devolviendo `healthy` y `connected`;
6. `kubectl describe deployment argus-api`;
7. escalamiento a cuatro réplicas;
8. petición remota de Juanfer mediante Tailscale;
9. frontend mostrando tareas provenientes del backend;
10. stream de una cámara remota funcionando.

