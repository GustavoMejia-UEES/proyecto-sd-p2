# Frontend — Argus

Frontend Next.js/TypeScript para la Máquina B. Consume exclusivamente la API
del backend de la Máquina A; no contiene MongoDB ni una API alternativa.

## Desarrollo local

```powershell
Copy-Item .env.example .env.local
bun install
bun dev -H 0.0.0.0
```

Para la prueba entre máquinas, `API_URL` debe ser `http://TAILSCALE_IP_A:30080`.

## Docker

```powershell
docker build -t sistema-frontend:0.1.0 .
docker run --rm -p 3000:3000 -e API_URL=http://TAILSCALE_IP_A:30080 sistema-frontend:0.1.0
```

## Kubernetes en la Máquina B

Edita `k8s/frontend.yaml` y reemplaza `100.x.x.x` por la IP Tailscale de A.
Luego:

```powershell
kubectl apply -f k8s/frontend.yaml
kubectl rollout status deployment/argus-frontend
kubectl get pods,services
```

El frontend queda publicado en el NodePort `30030`. La configuración se lee en
tiempo de ejecución desde `/api/config`, por lo que el ConfigMap sí aplica al
contenedor ya construido.
