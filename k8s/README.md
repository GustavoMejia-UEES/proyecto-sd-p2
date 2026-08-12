# Despliegue de la asignaciÃ³n distribuida

Este backend corresponde a la MÃ¡quina A: API FastAPI + MongoDB. La MÃ¡quina B
solo debe ejecutar el frontend y consumir el NodePort del backend mediante la
IP de Tailscale de la MÃ¡quina A.

## MÃ¡quina A — Gustavo / backend

Habilita Kubernetes en Docker Desktop y verifica que el contexto sea el local:

```powershell
kubectl config current-context
kubectl get nodes
```

Construye la imagen en el mismo Docker Desktop que usa Kubernetes y despliega:

```powershell
docker build -t argus-api:0.4.0 ./backend
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/backend.yaml
kubectl rollout status deployment/mongodb
kubectl rollout status deployment/argus-api
kubectl get pods -o wide
kubectl get services
```

La API queda publicada en el NodePort `30080`. ObtÃ©n la IP Tailscale de esta
mÃ¡quina con `tailscale ip -4`; esa IP reemplaza `TAILSCALE_IP_A` en las pruebas.

```powershell
Invoke-RestMethod "http://localhost:30080/health"
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/health"
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/api/tasks"
kubectl scale deployment argus-api --replicas=4
kubectl get pods -l app=argus-api
kubectl describe deployment argus-api
```

La primera respuesta de health debe ser `healthy/connected`; si MongoDB aÃºn no
estÃ¡ listo, debe responder HTTP 503 `degraded/unavailable`.

## Tailscale — ambas mÃ¡quinas

Cada integrante instala Tailscale, inicia sesiÃ³n en la misma tailnet y confirma:

```powershell
tailscale status
tailscale ip -4
Test-NetConnection TAILSCALE_IP_A -Port 30080
```

No se usa `localhost` desde la MÃ¡quina B: allÃ­ `localhost` apunta a la propia
MÃ¡quina B. El frontend debe usar:

```text
http://TAILSCALE_IP_A:30080
```

Para la evidencia, Juanfer debe ejecutar desde su mÃ¡quina:

```powershell
Invoke-RestMethod "http://TAILSCALE_IP_A:30080/api/tasks"
```

## MÃ¡quina B — Juanfer / frontend

El frontend debe recibir `API_URL` mediante ConfigMap o variable de build:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
data:
  API_URL: "http://TAILSCALE_IP_A:30080"
```

Su SPA debe consumir:

```text
GET    ${API_URL}/api/tasks
POST   ${API_URL}/api/tasks
PATCH  ${API_URL}/api/tasks/{id}
DELETE ${API_URL}/api/tasks/{id}
GET    ${API_URL}/health
```

El frontend se despliega en el Kubernetes de la MÃ¡quina B. Su Service puede ser
`NodePort` para abrirlo en el navegador; no debe incluir MongoDB ni intentar
conectarse a `localhost:27017`.

## Checklist de entrega

- [ ] `kubectl get pods` muestra MongoDB listo y 2 rÃ©plicas de `argus-api`.
- [ ] `kubectl get services` muestra `mongodb` como ClusterIP y `argus-api` como NodePort `30080`.
- [ ] `tailscale status` muestra ambas mÃ¡quinas en la misma tailnet.
- [ ] La MÃ¡quina B obtiene tareas desde `http://TAILSCALE_IP_A:30080`.
- [ ] Crear, editar y eliminar una tarea funciona desde el navegador.
- [ ] `kubectl scale deployment argus-api --replicas=4` funciona y se evidencia.
- [ ] `kubectl describe deployment argus-api` se incluye como evidencia.
