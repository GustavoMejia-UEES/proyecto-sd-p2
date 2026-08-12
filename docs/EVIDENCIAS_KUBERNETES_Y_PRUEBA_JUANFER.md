# Evidencias finales: Kubernetes, Tailscale y frontend

Este documento es la guía exacta para tomar las capturas de la exposición. La demostración final usa únicamente Kubernetes. Docker Compose queda como herramienta de desarrollo y recuperación local; no debe estar levantado al mismo tiempo que Kubernetes.

## 0. Regla de operación

En la máquina de Gustavo:

```powershell
docker compose down
```

No usar `docker compose down -v`: eso eliminaría el volumen local de MongoDB.

Después de apagar Compose, la API oficial es:

```text
http://100.77.143.36:30080
```

La API local de Compose `http://localhost:8000` ya no debe usarse en la demostración.

## 1. Captura: Tailscale

Ejecutar en ambas máquinas:

```powershell
tailscale status
tailscale ip -4
```

Capturar la pantalla donde se vean conectados:

- `desktop-tglbjb4` — Gustavo — `100.77.143.36`
- `juanferp` — Juanfer — `100.112.215.44`

## 2. Captura: nodo Kubernetes de Gustavo

```powershell
kubectl config current-context
kubectl get nodes
```

Resultado esperado:

```text
docker-desktop   Ready
```

Tomar una captura.

## 3. Captura: pods y servicios

```powershell
kubectl get pods -o wide
kubectl get services
```

La captura final debe mostrar:

```text
argus-api   4/4   Running
mongodb     1/1   Running
argus-api   NodePort   8000:30080/TCP
mongodb     ClusterIP  27017/TCP
```

## 4. Captura: salud real de la API

```powershell
Invoke-RestMethod "http://localhost:30080/health"
```

Resultado esperado:

```text
status    database
------    --------
healthy   connected
```

## 5. Captura: escalamiento a cuatro réplicas

```powershell
kubectl scale deployment argus-api --replicas=4
kubectl rollout status deployment/argus-api
kubectl get deployment argus-api
kubectl get pods -l app=argus-api
```

Tomar una captura cuando aparezca:

```text
4/4   4   4
```

No capturar mientras aparezca `ContainerCreating` o `0/1`.

## 6. Captura: descripción del Deployment

```powershell
kubectl describe deployment argus-api
```

La captura debe incluir:

- `Replicas: 4 desired | 4 updated | 4 total | 4 available`
- imagen `argus-api:0.4.0`
- puerto `8000/TCP`
- ConfigMap `argus-api-config`
- Secret `argus-api-secret`

## 7. Captura: prueba cruzada desde Juanfer

Juanfer ejecuta desde su PowerShell:

```powershell
Test-NetConnection 100.77.143.36 -Port 30080
Invoke-RestMethod "http://100.77.143.36:30080/health"
Invoke-RestMethod "http://100.77.143.36:30080/api/cameras"
Invoke-RestMethod "http://100.77.143.36:30080/api/tasks"
```

Debe enviar una captura donde aparezca:

```text
TcpTestSucceeded : True
status           : healthy
database         : connected
```

Esto prueba `Juanfer → Tailscale → NodePort → API Kubernetes → MongoDB`.

## 8. Captura: stream remoto

Desde el navegador de Juanfer abrir:

```text
http://100.77.143.36:8091/stream
```

La captura debe mostrar el video de `CAM-001` y la URL completa.

El frontend debe recibir el stream desde `stream_url` en `/api/cameras`; no debe usar `localhost`.

## 9. Prueba del frontend de Juanfer

Su variable de entorno debe ser:

```env
NEXT_PUBLIC_API_URL=http://100.77.143.36:30080
```

En el navegador debe demostrar:

1. listado de cámaras;
2. stream de `CAM-001`;
3. listado de tareas automáticas;
4. creación de una tarea manual;
5. edición de esa tarea;
6. eliminación de esa tarea.

Tomar una captura del panel mostrando tareas y cámaras.

## 10. Cámaras y arranque sin comandos largos

Los perfiles están centralizados. Para iniciar una cámara se usa solamente:

```powershell
.\scripts\start-camera.ps1 -CameraId CAM-001 -Kubernetes
.\scripts\start-camera.ps1 -CameraId CAM-002 -Kubernetes
.\scripts\start-camera.ps1 -CameraId CAM-003 -Kubernetes
```

El proceso Edge ya intenta reconectar la fuente si falla y envía heartbeat cada cinco segundos. La API marca la cámara `offline` cuando deja de recibir heartbeat.

Importante: la webcam USB/integrada no debe ejecutarse dentro del pod Linux de Kubernetes porque Docker Desktop no expone automáticamente el hardware de Windows. El API sí vive en Kubernetes; el proceso Edge vive en el equipo físico que tiene la cámara.

## 11. Orden narrativo para la exposición

1. Mostrar Tailscale y las dos computadoras conectadas.
2. Mostrar el nodo `docker-desktop` en estado `Ready`.
3. Mostrar MongoDB y las cuatro réplicas de la API.
4. Mostrar el `NodePort` `30080`.
5. Mostrar `/health` como `healthy/connected`.
6. Mostrar la prueba de Juanfer por la IP Tailscale.
7. Mostrar el stream remoto.
8. Mostrar el frontend con tareas CRUD y eventos de cámara.
9. Mostrar `kubectl describe deployment` para cerrar la evidencia técnica.

