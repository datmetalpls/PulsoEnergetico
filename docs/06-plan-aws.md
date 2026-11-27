# Plan AWS — capa 2 de la demo: una EC2 en AWS Academy Learner Lab

> Reemplaza el plan anterior (App Runner/RDS/ALB), que no es viable en el laboratorio. Estado: **propuesto, sin ejecutar**. Nada se ha probado contra AWS.
> La capa 2 es **opcional**. La demo principal es la capa 1 (local, sin Internet) y la de respaldo es la capa 3 (video y capturas). Ver `docs/07-riesgos.md`.

## Restricciones del laboratorio
- 50 USD **totales** para toda la cuenta y sesiones de 4 h. *End Lab* detiene las instancias, y la IP pública cambia al volver a arrancar.
- **Reset borra todo: nunca usarlo.**
- Quedan fuera: RDS, ELB/ALB, NAT, IP elástica, App Runner, Fargate, ECR, Secrets Manager, OIDC y HTTPS/ACM.

## Arquitectura
| Pieza | Decisión |
|---|---|
| Cómputo | 1 EC2 **t3.micro** (1 GiB) con **Ubuntu Server 24.04 LTS** (amd64), más 2 GB de swap creados por el script. Se pasa a **t3.small** solo si `free -h` o el log muestran falta de memoria (OOM). |
| Disco | EBS raíz gp3 de **16 GB**: las imágenes, la swap y el volumen de PostgreSQL. |
| Red | VPC por defecto con subred pública e IP pública automática. Sin IP elástica. |
| Grupo de seguridad `pulso-sg` (propio) | Entrada **22/tcp solo desde «Mi IP»** y **8080/tcp desde 0.0.0.0/0**, abierto solo durante la demo porque el jurado entra desde la red de la sala. Salida: todo. |
| App | Es el mismo `docker-compose.yml` del repo (Django + SPA y PostgreSQL 17). En la EC2 se agrega un override, `compose.ec2.yml`, que genera el script y no se sube al repo. |
| BD | PostgreSQL en el mismo compose, en la red interna `database`, sin puerto publicado y con el volumen `postgres_data`. |
| Secretos | Un `.env` preparado en el portátil, copiado por scp, con permisos `chmod 600` y **nunca en git** (`.gitignore` ya lo excluye). |
| Acceso | `http://<IP-pública>:8080`, **sin HTTPS**. Hay que decirlo en voz alta: es una demo con datos simulados. |

## Puerto: bind 127.0.0.1 → 0.0.0.0
`docker-compose.yml` publica `"127.0.0.1:8080:8000"` de forma fija, sin variable, así que en la EC2 solo responde a sí misma. Un override normal **sumaría** el puerto y generaría un conflicto en 8080, por eso se usa `!override`, que exige Compose ≥ 2.24 (el repo ya lo requiere):

```yaml
# compose.ec2.yml (lo escribe scripts/deploy-ec2.sh)
services:
  db:  { restart: unless-stopped }
  web:
    build: !reset null        # no compilar en la EC2
    image: pulso-web:demo     # imagen traída del portátil
    pull_policy: never
    restart: unless-stopped   # vuelve sola tras End Lab / reboot
    ports: !override
      - "0.0.0.0:8080:8000"
```
Se usa con `docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml up -d`. Lo comprobé en local con `docker compose config` (Compose v5.4.0): el override deja `host_ip: 0.0.0.0` y `published: 8080`, quita `build` y añade `restart`.

Además, Django rechaza un Host desconocido (`ALLOWED_HOSTS` por defecto: `localhost,127.0.0.1,testserver,web`). El script escribe en `.env` el valor `ALLOWED_HOSTS=<IP pública>,<DNS público>,localhost,127.0.0.1,web`, que obtiene del servicio de metadatos IMDSv2, y lo vuelve a escribir con `refresh-ip` cuando la IP cambia. Si no hay tiempo, el plan B es `ALLOWED_HOSTS=*`, aceptable solo en esta demo.

## Frontend compilado en el portátil (sin tocar el código)
El `Dockerfile` compila Angular dentro del stage `frontend` con `npm ci && npm run build`, y `.dockerignore` excluye `**/dist`. Por eso subir `frontend/dist` **no** sirve sin cambiar el Dockerfile. La opción elegida es **construir la imagen completa en el portátil para linux/amd64 y transferirla**:

```sh
docker buildx build --platform linux/amd64 -t pulso-web:demo --load .
docker pull --platform linux/amd64 postgres:17-alpine
docker save pulso-web:demo postgres:17-alpine | gzip > pulso-images.tar.gz
scp -i labsuser.pem pulso-images.tar.gz ubuntu@<IP>:~
# en la EC2, el script hace: gunzip -c pulso-images.tar.gz | docker load
```
- Incluir `postgres:17-alpine` en el archivo evita depender de Docker Hub desde la EC2.
- En un Mac con Apple Silicon, el build amd64 corre emulado y tarda varios minutos más. Conviene hacerlo **antes** de iniciar la sesión del laboratorio.
- Antes de copiar, conviene revisar que la SPA no sea la página de reemplazo: `docker run --rm --entrypoint grep pulso-web:demo -c "pendiente de compilación" /app/frontend/dist/pulso/browser/index.html` debe imprimir `0`.
- La EC2 nunca ejecuta `npm` ni `--build`, así que 1 GiB de RAM alcanza para Django (2 workers de gunicorn) y PostgreSQL.

## Semilla
`backend/entrypoint.sh` ejecuta `migrate`, `seed_demo`, `collectstatic` y luego gunicorn en **cada** arranque. `seed_demo` es idempotente: no reemplaza ensayos, controles ni contraseñas existentes. Crea `cuenca` y `puente-alto`, con los sitios `cuenca-sede`, `cuenca-banco`, `puente-alto-sede` y `puente-alto-banco`, y los usuarios `operador_cuenca`, `operador_puente` y `observador`. Las contraseñas se fijan **solo la primera vez**: hay que definir las definitivas en `.env` **antes** del primer `up`. Lo mismo vale para `POSTGRES_PASSWORD`, que se fija al crear el volumen.

## Control de costo
- Antes y después de cada sesión, anotar el valor «**Used $X of $50**» del panel del laboratorio en `docs/05-resultados.md` o en el chat del equipo.
- Estimación (us-east-1, orden de magnitud, **por verificar**): t3.micro ≈ 0,01 USD/h (≈ 0,05 USD por sesión de 4 h) y EBS de 16 GB ≈ 0,05 USD/día aunque la instancia esté detenida. Un día de hackatón cuesta menos de 1 USD.
- Al cerrar se sigue `scripts/shutdown-ec2.md`, con Terminate cuando ya no haga falta y nunca Reset.

## Por verificar en la consola del laboratorio
- [ ] Región asignada (se supone **us-east-1**) y si se puede cambiar.
- [ ] Tipos de instancia permitidos (se suponen t3.micro y t3.small) y el límite de instancias simultáneas.
- [ ] AMI disponible: Ubuntu Server 24.04 LTS amd64 (si no está, 22.04 LTS; el script sirve para ambas).
- [ ] Key pair **vockey** y descarga de `labsuser.pem` desde *AWS Details*.
- [ ] Perfil **LabInstanceProfile/LabRole**: no se necesita, porque la instancia no llama a APIs de AWS. No asignarlo, salvo que el laboratorio lo exija.
- [ ] Que el grupo de seguridad propio permita abrir 8080/tcp y que la VPC por defecto asigne IP pública.
- [ ] Qué ocurre con las instancias al terminar los 4 h y al iniciar otra sesión (¿quedan detenidas o se reinician?) y si cambia el DNS público.
- [ ] Que IMDSv2 responda en la instancia (lo usa `refresh-ip`).
- [ ] Que la red de la sala permita la salida al puerto 8080. Si no, publicar en 80 con `PUBLIC_PORT=80` y abrir 80/tcp en el grupo de seguridad.
- [ ] El costo real en el panel «Used $X of $50».

## Prerrequisito del repo
La EC2 clona `https://github.com/datmetalpls/PulsoEnergetico`. Al momento de escribir esto, `docker-compose.yml`, `.env.example`, `Dockerfile` y `backend/` **no están en el commit** de `main`. Antes de desplegar, el integrador debe hacer push, o bien hay que copiar `docker-compose.yml` y `.env.example` por scp (ver `scripts/deploy-ec2.md` §3). Con la opción elegida la EC2 no necesita el código fuente, solo esos dos archivos y la imagen.

## Pasos
Ver `scripts/deploy-ec2.md` (despliegue) y `scripts/shutdown-ec2.md` (apagado).
