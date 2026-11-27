# Plan posterior para AWS (propuesto, sin implementar)

En esta etapa **solo existe la demo local**. Este documento propone un piloto pequeño y de bajo costo para ejecutarlo después de la hackatón.

## Destino
| Pieza | Opción propuesta | Alternativa |
|---|---|---|
| Aplicación (imagen Docker actual, Django + SPA en un solo origen) | **AWS App Runner** o ECS Fargate (1 tarea, 0,25 vCPU / 0,5 GB) detrás de un ALB con HTTPS (ACM) | Lightsail Containers (precio fijo) |
| Imágenes | Amazon ECR | — |
| Base de datos | **Amazon RDS for PostgreSQL 17**, `db.t4g.micro`, 20 GB gp3, subred privada sin acceso público | Lightsail Managed DB |
| Secretos | **AWS Secrets Manager** (DJANGO_SECRET_KEY, credenciales de BD y, más adelante, webhook de Discord) inyectados como variables de entorno; nunca en la imagen, el repositorio ni el frontend | SSM Parameter Store (SecureString) |
| Registros | CloudWatch Logs con retención de 14 días y sin datos personales ni secretos | — |
| Mantenimiento | Acceso autenticado mediante **SSM Session Manager** o ECS Exec, sin SSH abierto. El acceso queda auditado en CloudTrail, además del `AuditEvent` propio | — |

## Código ≠ datos
- **Código:** GitHub Actions (el CI actual), luego un build de la imagen, un push a ECR (OIDC de GitHub → rol IAM, sin claves largas) y un deploy. Las migraciones corren como paso previo controlado.
- **Datos:** no viajan con el código. Para llevar datos de la demo local se usa `pg_dump -Fc` local, se sube el archivo cifrado a S3 privado y se ejecuta `pg_restore` hacia RDS desde una tarea de mantenimiento. Lo normal es empezar el piloto con `seed_demo` y sin datos locales.

## Respaldo y restauración
- Snapshots automáticos de RDS (7 días) y un snapshot manual antes de cada migración.
- Un `pg_dump` semanal a S3 con versionado y ciclo de vida de 30 días.
- **Ensayo de restauración** (obligatorio antes del piloto): restaurar el snapshot en una instancia nueva, apuntar una tarea de staging y comprobar que GET state devuelve el acumulado. Hay que medir y anotar el RTO.

## Costo estimado (us-east-1, orden de magnitud, a verificar con AWS Pricing Calculator)
App Runner o Fargate mínimo: ~10–25 USD/mes. RDS t4g.micro con 20 GB: ~15–20 USD/mes. ALB, si se usa: ~18 USD/mes. ECR, Secrets Manager, logs y S3: < 5 USD/mes. **Total aproximado: 30–70 USD/mes.** Hay que configurar AWS Budgets con una alerta a 20 USD.

## Apagado de recursos
Todos los recursos llevan la etiqueta `project=pulso-energetico` y se crean con IaC (CDK o Terraform) para poder ejecutar `destroy`. Al terminar el piloto:
1. Snapshot final de RDS.
2. Eliminar el servicio, el ALB y la instancia RDS.
3. Vaciar ECR y S3 según la retención acordada.
4. Revisar en Cost Explorer y Tag Editor que no queden recursos con la etiqueta.

## Pendiente de definir por el equipo
Región (São Paulo `sa-east-1`, por latencia hacia Chile y Ecuador, frente a `us-east-1`, por costo), política oficial del evento si existe, y responsable de la cuenta AWS.
