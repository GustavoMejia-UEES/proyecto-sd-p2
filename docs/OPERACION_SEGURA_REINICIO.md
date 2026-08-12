# Operación segura: apagar y restaurar el sistema

Este procedimiento permite apagar temporalmente las cámaras y Kubernetes sin eliminar datos, volúmenes, imágenes ni manifiestos.

## Consultar estado

Desde la raíz del proyecto:

```powershell
.\scripts\operar-sistema.ps1 -Action status
```

## Apagar solamente las cámaras

```powershell
.\scripts\operar-sistema.ps1 -Action stop
```

Esto detiene los procesos Edge de la computadora. No elimina cámaras de MongoDB y no toca Kubernetes.

## Encender solamente las cámaras

Para Gustavo:

```powershell
.\scripts\operar-sistema.ps1 -Action start -Owner gustavo
```

Para Juanfer:

```powershell
.\scripts\operar-sistema.ps1 -Action start -Owner juanfer
```

## Apagar cámaras y Kubernetes

```powershell
.\scripts\operar-sistema.ps1 -Action stop -Kubernetes
```

Esto escala la API a cero réplicas y MongoDB a cero réplicas. No usar `kubectl delete`, `docker system prune` ni `docker compose down -v` para este procedimiento.

## Restaurar todo en Gustavo

```powershell
.\scripts\operar-sistema.ps1 -Action start -Owner gustavo -Kubernetes
```

El script:

1. selecciona el contexto `docker-desktop`;
2. verifica el nodo;
3. enciende MongoDB;
4. enciende la API con cuatro réplicas;
5. espera a que los pods estén listos;
6. inicia las tres cámaras Edge de Gustavo.

## Restaurar todo en Juanfer

En la carpeta de su proyecto:

```powershell
.\scripts\operar-sistema.ps1 -Action start -Owner juanfer -Kubernetes
```

Juanfer debe tener su frontend y Tailscale activos. Sus Edge registrarán `CAM-004` y `CAM-005` contra la API de Gustavo.

## Verificación final

```powershell
.\scripts\operar-sistema.ps1 -Action status
Invoke-RestMethod "http://localhost:30080/health"
Invoke-RestMethod "http://localhost:30080/api/cameras"
```

Resultado esperado:

```text
argus-api   4/4   Running
mongodb     1/1   Running
healthy     connected
```

## Diferencia entre apagar y borrar

Apagar temporalmente usa `scale --replicas=0` y conserva todo. Borrar recursos o volúmenes es otra operación y no forma parte de este script.
