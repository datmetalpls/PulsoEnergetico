# Apagado de la EC2 (Learner Lab)

> **NUNCA usar *Reset*** del laboratorio: borra toda la cuenta.
> **NUNCA** ejecutar `docker compose down -v`: borra el volumen de PostgreSQL.

## 1. (Opcional) Respaldo de la BD al portátil
```sh
IP=<ip-publica>
ssh -i labsuser.pem ubuntu@$IP 'cd ~/PulsoEnergetico && \
  sudo docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml exec -T db \
  sh -c "pg_dump -U \$POSTGRES_USER -d \$POSTGRES_DB -Fc" > ~/pulso-$(date +%Y%m%d-%H%M).dump && ls -lh ~/pulso-*.dump'
scp -i labsuser.pem "ubuntu@$IP:~/pulso-*.dump" ./backups/
```
Para restaurar en local (opcional): `docker compose exec -T db sh -c 'pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists' < backups/<archivo>.dump`.
El respaldo contiene usuarios y hashes de contraseñas: no subirlo al repo ni a canales públicos.

## 2. Detener la app
```sh
ssh -i labsuser.pem ubuntu@$IP 'cd ~/PulsoEnergetico && sudo docker compose -p pulso -f docker-compose.yml -f compose.ec2.yml down'
```
(Sin `-v`.)

## 3. Instancia: Stop o Terminate
| Situación | Acción | Costo que sigue corriendo |
|---|---|---|
| Habrá otra sesión o presentación | EC2 → *Instance state* → **Stop** | Solo EBS (≈ 16 GB gp3, unos centavos al día ⚠) |
| Demo terminada | **Terminate** (después del respaldo §1) | Nada, si el volumen se borra con la instancia |

Después de Terminate se revisa lo siguiente:
- [ ] EC2 → **Volumes**: no quedan volúmenes `available`. Si quedan, *Delete volume*.
- [ ] EC2 → **Elastic IPs**: lista vacía (no se debió crear ninguna). Si hay, *Release*.
- [ ] EC2 → **Snapshots** y **AMIs**: vacíos, salvo que se hayan creado a propósito.
- [ ] El grupo de seguridad `pulso-sg` se puede borrar (no tiene costo, pero así queda limpio).

## 4. Cerrar la sesión
1. Anotar «**Used $X of $50**» y registrarlo junto al valor del inicio de la sesión.
2. Pulsar **End Lab**. Detiene las instancias que sigan encendidas, y la IP cambiará en la próxima sesión.
3. **No** pulsar Reset.
