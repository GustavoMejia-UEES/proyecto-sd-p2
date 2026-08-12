# Operación de las cinco cámaras

La API en Kubernetes mantiene el registro y el estado de las cámaras. En cada computadora se ejecuta un supervisor local que mantiene vivos los procesos Edge. Cada Edge tiene acceso a sus fuentes físicas, publica un stream y envía heartbeats a la API.

## Gustavo

Desde la raíz del proyecto y con Kubernetes activo:

```powershell
.\scripts\start-camera-fleet.ps1 -Owner gustavo -Kubernetes
```

Inicia `CAM-001` (laptop, source `0`, puerto `8091`), `CAM-002` (USB, source `1`, puerto `8092`) y `CAM-003` (celular, puerto `9020`).

## Juanfer

En su copia del proyecto:

```powershell
.\scripts\start-camera-fleet.ps1 -Owner juanfer -Kubernetes
```

Inicia `CAM-004` (laptop, source `0`, puerto `8091`) y `CAM-005` (celular, puerto `9010`). Los puertos pueden repetirse porque cada equipo tiene una IP Tailscale diferente.

## Inicio automático

Cada equipo puede registrar el inicio automático de sus propios Edge:

```powershell
.\scripts\install-camera-autostart.ps1 -Owner gustavo -Kubernetes
```

Juanfer cambia `gustavo` por `juanfer`. El supervisor inicia los procesos al iniciar sesión y Windows los reinicia si se cierran. El agente Edge reintenta la fuente si se desconecta.

## Activar y desactivar desde el frontend

Para activar una cámara:

```http
POST /api/cameras/CAM-001/control
Content-Type: application/json

{"enabled": true}
```

Para desactivarla:

```http
POST /api/cameras/CAM-001/control
Content-Type: application/json

{"enabled": false}
```

El Edge permanece ejecutándose, pero con `enabled=false` libera la cámara, deja de producir frames y reporta `offline`. Al volver a `true`, intenta abrir la fuente nuevamente y cambia a `online` cuando obtiene frames.

## Límites y Kubernetes

Las réplicas de `argus-api` no representan cámaras. Las cámaras son procesos Edge distribuidos en los equipos físicos. Kubernetes escala la API, mientras MongoDB centraliza cámaras, eventos y tareas. Se pueden agregar más cámaras usando un ID, fuente, host Tailscale y puerto únicos; el límite práctico depende de CPU, memoria, red e inferencia.
