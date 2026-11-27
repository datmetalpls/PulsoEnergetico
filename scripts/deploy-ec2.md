# Despliegue en EC2 (Learner Lab), paso a paso

Contexto y decisiones: `docs/06-plan-aws.md`. Estado: **sin ejecutar contra AWS**. `deploy-ec2.sh` pasó `bash -n` y shellcheck, y su subcomando `verify` se probó contra el stack local (OK en `/api/localities` y `/api/sites/cuenca-sede/state`).
Todo lo que se marca ⚠ está **por verificar en la consola del laboratorio**.

## 0. Antes de iniciar el laboratorio (en el portátil, sin gastar sesión)
```sh
cd "<repo>"
# §1 .env de producción (no se sube a git)
cp .env.example .env.ec2
python3 -c "import secrets;print(secrets.token_urlsafe(50))"   # → DJANGO_SECRET_KEY
python3 -c "import secrets;print(secrets.token_urlsafe(24))"   # → POSTGRES_PASSWORD
# editar .env.ec2 y cambiar DJANGO_SECRET_KEY, POSTGRES_PASSWORD y las 3 DEMO_*_PASSWORD
# (ALLOWED_HOSTS lo completa el script)

# §2 imagen precompilada para amd64 (Apple Silicon: tarda varios minutos más, por la emulación)
docker buildx build --platform linux/amd64 -t pulso-web:demo --load .
docker run --rm --entrypoint grep pulso-web:demo -c "pendiente de compilación" /app/frontend/dist/pulso/browser/index.html  # debe decir 0
docker pull --platform linux/amd64 postgres:17-alpine
docker save pulso-web:demo postgres:17-alpine | gzip > pulso-images.tar.gz
```
Las contraseñas del jurado y del equipo **se fijan solo en el primer arranque**, porque `seed_demo` no las sobrescribe.

## 1. Consola del laboratorio
1. *Start Lab* → anotar «**Used $X of $50**». En *AWS Details* → *Download PEM* → `labsuser.pem` → `chmod 400 labsuser.pem`. ⚠ El nombre del key pair debería ser `vockey`.
2. EC2 → *Launch instance*: nombre `pulso-demo`, AMI **Ubuntu Server 24.04 LTS (x86_64)** ⚠, tipo **t3.micro** ⚠, key pair **vockey**, disco **16 GB gp3**, VPC por defecto con *Auto-assign public IP: Enable* ⚠.
3. Grupo de seguridad nuevo `pulso-sg`: SSH 22/tcp con origen **My IP**, y Custom TCP 8080 con origen 0.0.0.0/0 (o 80, si la red de la sala bloquea 8080 ⚠).
4. No usar IP elástica ni balanceador, y no asignar LabRole (no hace falta).
5. Anotar la **IP pública** (cambia en cada arranque).

## 2. Copiar archivos y desplegar
```sh
IP=<ip-publica>
scp -i labsuser.pem pulso-images.tar.gz scripts/deploy-ec2.sh ubuntu@$IP:~
ssh -i labsuser.pem ubuntu@$IP 'mkdir -p ~/PulsoEnergetico'          # solo si aún no existe
scp -i labsuser.pem .env.ec2 ubuntu@$IP:~/PulsoEnergetico/.env
ssh -i labsuser.pem ubuntu@$IP 'chmod +x deploy-ec2.sh && ./deploy-ec2.sh'
```
`./deploy-ec2.sh` (subcomando `all`) es idempotente y se puede repetir. Hace lo siguiente:
1. Crea 2 GB de swap en `/swapfile` si no hay swap (`SWAP_GB=1` la reduce a 1 GB).
2. Instala Docker Engine y el plugin compose desde el repo oficial de Docker, si faltan, y comprueba que Compose sea ≥ 2.24.
3. Clona el repo en `~/PulsoEnergetico` o hace `git pull --ff-only`. Si el directorio ya existe porque se copió `.env`, clona en un directorio temporal y copia los archivos sin pisar `.env`. Si ya hay un `docker-compose.yml` copiado por scp (§3), lo usa tal cual.
4. Escribe `compose.ec2.yml`: bind `0.0.0.0:8080`, `image: pulso-web:demo`, sin build, `restart: unless-stopped`.
5. Ejecuta `docker load` del archivo `.tar.gz`, solo si cambió (compara el sha256), y comprueba que la imagen sea amd64.
6. Exige `.env` con una `DJANGO_SECRET_KEY` distinta de la de ejemplo y escribe `ALLOWED_HOSTS` con la IP y el DNS públicos (IMDSv2).
7. Ejecuta `docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml up -d` **sin `--build`** y espera la respuesta de `/api/auth/me` y la línea `Demo ready` en el log (`seed_demo` lo ejecuta el entrypoint).
8. Ejecuta `verify`: inicia sesión como `observador` con CSRF y luego hace `GET /api/localities` y `GET /api/sites/cuenca-sede/state`.

Prueba desde el portátil: abrir `http://$IP:8080` en el navegador. Si no carga, revisar la regla 8080 del grupo de seguridad.

## 3. Si el repo aún no tiene push de `docker-compose.yml` / `.env.example`
El paso 3 del script se detiene con un mensaje claro. En ese caso:
```sh
ssh -i labsuser.pem ubuntu@$IP 'mkdir -p ~/PulsoEnergetico'
scp -i labsuser.pem docker-compose.yml .env.example ubuntu@$IP:~/PulsoEnergetico/
ssh -i labsuser.pem ubuntu@$IP './deploy-ec2.sh'
```

## 4. Después de End Lab, de la expiración de 4 h o de un reboot: la IP cambió
Los contenedores vuelven solos (`restart: unless-stopped`), pero Django responde **400 Bad Request** a la IP nueva hasta que se actualiza `ALLOWED_HOSTS`:
```sh
IP=<ip-nueva>                                   # verla en la consola EC2
ssh -i labsuser.pem ubuntu@$IP './deploy-ec2.sh refresh-ip'
```
Si la instancia quedó detenida ⚠, primero se ejecuta *Instance state → Start*. El acumulado se conserva en el volumen. También hay que actualizar la URL en el material que vea el jurado.

## 5. Reiniciar el ensayo (menos de 10 s; sirve en local y en EC2)
```sh
# en el portátil, contra la demo local (lee la contraseña de ./.env o ./.env.example)
BASE_URL=http://localhost:8080 ./scripts/deploy-ec2.sh reset-demo
# contra la EC2
ssh -i labsuser.pem ubuntu@$IP './deploy-ec2.sh reset-demo'   # usa http://localhost:8080 dentro de la EC2
```
Crea un ensayo nuevo de `cuenca-sede` (cierra el anterior) y fija el presupuesto en **0,15 kWh**, es decir un umbral de 150 Wh, para que la alerta aparezca dentro del guion de 90 s (`BUDGET_KWH=0.6` devuelve el valor de la semilla). El ensayo queda en pausa: en la UI se pulsa **▶ Reproducir**. ⚠ Este subcomando no se ha ejecutado: se evitó cerrar el ensayo local que estaban usando los otros agentes. Hay que probarlo en el primer ensayo general.

## 6. Diagnóstico rápido
```sh
./deploy-ec2.sh status                 # ps, free -h, log
sudo docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml logs -f web
```
- `Killed` u OOM en el log: subir la swap (`SWAP_GB=2`), y si no alcanza, *Stop* → *Change instance type* → t3.small → *Start* → `refresh-ip`.
- Error 400 en el navegador: falta `refresh-ip` o la URL usa otro nombre de host.
- Error 403 en el login: la contraseña de `.env` no coincide con la sembrada en el primer arranque.
- **Nunca** ejecutar `docker compose down -v` (borra la BD) ni *Reset* del laboratorio.

Apagado: `scripts/shutdown-ec2.md`.
