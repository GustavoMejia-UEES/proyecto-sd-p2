# ARGUS — Pendientes, conectividad y evidencias

## Estado actual

El backend y MongoDB ya están preparados. El cierre de la asignación requiere
conectar dos máquinas independientes:

```text
Máquina A / Gustavo
  Tailscale + Docker Desktop Kubernetes
  MongoDB
  ARGUS Core API : NodePort 30080
  Edge de cámaras

Máquina B / Juanfer
  Tailscale + Docker Desktop Kubernetes
  ARGUS Frontend
```

Flujo final:

```text
Navegador B
   |
   | HTTP API y WebSocket por Tailscale
   v
IP Tailscale A:30080
   |
   v
Service NodePort -> Pods argus-api -> Service mongodb -> MongoDB

Edge cámara -> stream MJPEG y heartbeats -> ARGUS API
```

## Pendientes de Gustavo

- Instalar o verificar Tailscale en la Máquina A.
- Confirmar que Docker Desktop tiene Kubernetes habilitado.
- Construir `argus-api:0.4.0`.
- Aplicar MongoDB y backend en Kubernetes.
- Obtener la IP Tailscale de la Máquina A.
- Probar el NodePort desde la propia máquina y desde la Máquina B.
- Ejecutar la cámara Edge y registrar su `stream_url` con una IP alcanzable.
- Guardar las capturas de evidencia.

## Pendientes de Juanfer

- Crear el frontend con Next.js y Bun.
- Implementar el CRUD de tareas.
- Configurar `API_URL` con la IP Tailscale de la Máquina A.
- Crear Dockerfile y manifiestos Kubernetes del frontend.
- Consumir `/health`, `/api/tasks`, `/api/cameras`, `/api/events` y `/ws/events`.
- Mostrar una cámara usando `<img src={stream_url}>` para MJPEG.
- Ejecutar las pruebas desde la Máquina B y guardar evidencia.

## Tailscale paso a paso

En ambas máquinas:

1. Instalar Tailscale.
2. Iniciar sesión con cuentas autorizadas dentro de la misma tailnet.
3. Confirmar que ambas máquinas aparecen como conectadas.

En PowerShell:

```powershell
tailscale status
tailscale ip -4
```

En la Máquina A, guardar el resultado de `tailscale ip -4`. Supongamos que
devuelve `100.80.20.10`; esa será `TAILSCALE_IP_A`.

En la Máquina B:

```powershell
Test-NetConnection 100.80.20.10 -Port 30080
Invoke-RestMethod "http://100.80.20.10:30080/health"
Invoke-RestMethod "http://100.80.20.10:30080/api/tasks"
```

Si falla el puerto, revisar que el backend esté Ready, que el Service sea
NodePort `30080` y que Tailscale/Firewall permita el tráfico entre las dos
máquinas.

## Evidencia 1 — Tailscale

Capturar en ambas máquinas:

```powershell
tailscale status
tailscale ip -4
```

La captura debe mostrar ambas máquinas conectadas en la misma tailnet.

## Evidencia 2 — Docker Compose local

En la Máquina A:

```powershell
docker compose up -d --build mongodb api
docker compose ps
docker image ls argus-api
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/tasks
```

La captura debe mostrar MongoDB y API en estado `healthy` y los puertos
publicados.

## Evidencia 3 — Cámara Edge

Con la webcam conectada:

```powershell
.\scripts\discover-cameras.ps1
.\scripts\start-edge.ps1 -CameraId CAM-001 -CameraName "Laptop" -CameraSource 0 -Port 8091 -Vision -VisionMode cctv
```

Capturar:

```powershell
Invoke-RestMethod http://localhost:8091/health
Invoke-RestMethod http://localhost:8000/api/cameras | ConvertTo-Json -Depth 8
```

También abrir el stream en el navegador: `http://localhost:8091/stream`.

Para una cámara USB adicional, usar otro índice y puerto, por ejemplo `1` y
`8092`. Cada cámara necesita su propio `camera_id` y proceso Edge.

## Evidencia 4 — Kubernetes de Máquina A

```powershell
docker build -t argus-api:0.4.0 ./backend
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
kubectl rollout status deployment/mongodb
kubectl rollout status deployment/argus-api
kubectl get pods -o wide
kubectl get services
```

La evidencia debe mostrar MongoDB con 1 pod listo, `argus-api` con 2 pods
listos, `mongodb` como `ClusterIP` y `argus-api` como `NodePort` con `30080`.

## Evidencia 5 — conexión cruzada

Desde la Máquina B:

```powershell
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/health"
$body = @{ titulo = "Prueba desde Máquina B"; estado = "Pendiente" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://TAILSCALE_IP_A:30080/api/tasks" -ContentType "application/json" -Body $body
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/api/tasks"
```

La captura debe probar que la petición se originó desde B y que los datos
provienen del backend/MongoDB de A.

## Evidencia 6 — frontend en Máquina B

Capturar `docker build`, `kubectl apply`, `kubectl get pods`, `kubectl get
services`, el navegador mostrando la SPA, tareas creadas desde la SPA, el panel
de salud conectado y una cámara renderizada desde `stream_url`.

## Evidencia 7 — escalado

En la Máquina A:

```powershell
kubectl scale deployment argus-api --replicas=4
kubectl get pods -l app=argus-api
kubectl describe deployment argus-api
```

La captura debe mostrar cuatro pods del backend y el Deployment actualizado.

## Problemas frecuentes

Desde B es incorrecto usar `http://localhost:30080`; debe usarse
`http://TAILSCALE_IP_A:30080`. `0.0.0.0` sirve para escuchar en todas las
interfaces, pero no es una dirección navegable.

El backend actual entrega MJPEG, no WebRTC. Usar `<img>` para las cámaras. No
usar `<video src=".../stream">` esperando que convierta MJPEG en WebRTC.

## Conexión de un celular

El celular puede entrar a la misma tailnet instalando Tailscale y autenticándose
con una cuenta autorizada. Hay tres usos diferentes:

1. **Celular como visor:** abre el frontend usando la URL publicada por la
   Máquina B o consulta la API mediante la IP Tailscale.
2. **Celular como cámara IP:** utiliza una app que publique MJPEG, RTSP o HTTP;
   el agente Edge debe poder alcanzar esa URL y luego registrarla en
   `/api/cameras/configure`.
3. **Celular como cámara WebRTC del navegador:** requiere una futura capa de
   señalización y permisos de navegador. No es parte del backend actual.

Para pruebas, el camino más estable es usar el celular como cámara IP con
Tailscale y hacer que un Edge autorizado consuma su URL. El frontend seguirá
recibiendo el `stream_url` normalizado por ARGUS.
