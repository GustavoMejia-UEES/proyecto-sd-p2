# Sistema Distribuido de Gestión y Vigilancia — Despliegue y evidencias

## Orden de ejecución

```text
1. Tailscale en ambas máquinas
2. Docker Compose local en A
3. Cámara Edge en A
4. Kubernetes backend/MongoDB en A
5. Prueba cruzada por Tailscale
6. Kubernetes frontend en B
7. Prueba desde navegador
8. Escalado y evidencias finales
```

## 1. Tailscale

En A y B instalar Tailscale, iniciar sesión en la misma tailnet y ejecutar:

```powershell
tailscale status
tailscale ip -4
```

Guardar la IP de A como `TAILSCALE_IP_A`. No usar `0.0.0.0` ni `localhost` para
comunicación entre máquinas.

Desde B:

```powershell
ping TAILSCALE_IP_A
```

## 2. Docker Compose local en A

Desde la raíz:

```powershell
Copy-Item .env.example .env
docker compose up -d --build mongodb api
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/tasks
```

Capturar `docker compose ps`, `/health` y `/docs`.

## 3. Cámara Edge en A

```powershell
.\scripts\discover-cameras.ps1
.\scripts\start-edge.ps1 `
  -CameraId CAM-001 `
  -CameraName "Laptop" `
  -CameraSource 0 `
  -Port 8091 `
  -Vision `
  -VisionMode cctv
```

Probar:

```powershell
Invoke-RestMethod http://localhost:8091/health
Invoke-RestMethod http://localhost:8000/api/cameras | ConvertTo-Json -Depth 8
```

Abrir `http://localhost:8091/stream`. Para USB adicional usar otro índice,
`camera_id` y puerto, por ejemplo `1`, `CAM-002` y `8092`.

## 4. Kubernetes en A

```powershell
kubectl config current-context
kubectl get nodes
docker build -t argus-api:0.4.0 ./backend
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
kubectl rollout status deployment/mongodb
kubectl rollout status deployment/argus-api
kubectl get pods -o wide
kubectl get services
kubectl describe deployment argus-api
```

Debe verse MongoDB con 1 pod, backend con 2 pods, MongoDB como `ClusterIP` y
backend como `NodePort` `30080`.

## 5. Prueba cruzada

Desde A:

```powershell
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/health"
```

Desde B:

```powershell
Test-NetConnection TAILSCALE_IP_A -Port 30080
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/health"
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/api/tasks"
```

Crear tarea desde B:

```powershell
$body = @{ titulo = "Prueba desde Máquina B"; estado = "Pendiente" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "http://TAILSCALE_IP_A:30080/api/tasks" `
  -ContentType "application/json" `
  -Body $body
```

Capturar la terminal de B y consultar luego la misma tarea para demostrar que
persistió en MongoDB de A.

## 6. Frontend en B

Configurar:

```env
NEXT_PUBLIC_API_URL=http://TAILSCALE_IP_A:30080
```

Probar primero Docker y después Kubernetes. Capturar:

```powershell
docker build -t sistema-frontend:0.1.0 .
kubectl get pods
kubectl get services
```

En el navegador demostrar listar, crear, editar y eliminar tareas provenientes
del backend de A.

## 7. Evidencia de eventos automáticos

Con Edge activo:

1. Generar movimiento frente a la cámara.
2. Consultar `/api/events`.
3. Confirmar que el backend recibió el evento.
4. Si la conversión evento-tarea está implementada, confirmar una tarea con
   `source=camera`.
5. Mostrarla en el frontend junto con cámara y evento relacionados.

Esta es la ampliación de vigilancia; el CRUD manual es la evidencia obligatoria.

## 8. Escalado

En A:

```powershell
kubectl scale deployment argus-api --replicas=4
kubectl get pods -l app=argus-api
kubectl describe deployment argus-api
```

Capturar los cuatro pods y el Deployment actualizado.

## 9. Checklist final

- [ ] Tailscale conecta A y B.
- [ ] Compose levanta API y MongoDB.
- [ ] `/health` confirma conexión real.
- [ ] Edge muestra cámara y FPS.
- [ ] Kubernetes A tiene MongoDB listo.
- [ ] Kubernetes A tiene 2 réplicas backend.
- [ ] NodePort `30080` responde por Tailscale.
- [ ] B crea una tarea remotamente.
- [ ] Frontend corre en Kubernetes B.
- [ ] CRUD funciona desde navegador.
- [ ] Backend escala a 4 réplicas.
- [ ] Se demuestra al menos un evento de vigilancia.
