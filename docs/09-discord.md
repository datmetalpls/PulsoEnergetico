# Integración con Discord (webhook): pasos

Pulso Energético publica en un canal de Discord mediante un **webhook**. No usa un bot con token. Si no hay webhook configurado, la app funciona igual y muestra «Simulación local».

## Qué se publica
- **Alerta de umbral:** un solo mensaje por ensayo, al alcanzar el límite. No se duplica al refrescar ni al reenviar lecturas.
- **Reporte manual:** botón «Enviar reporte a Discord» (solo operador; máximo 1 cada 30 s por ensayo).
- Pie de cada mensaje: `Datos simulados · Prototipo hackatón Ecuador × Chile · Origen: <local|EC2>`.

## 1. Crear o regenerar el webhook
1. En Discord: *Configuración del canal → Integraciones → Webhooks → Nuevo webhook* (o *Copiar URL* de uno existente).
2. Tras la hackatón, **regenera** el webhook usado durante el desarrollo: su URL quedó en el historial del chat y en los registros de Orca.

> La URL del webhook es un **secreto**: quien la tenga puede publicar en el canal. Nunca la subas al repositorio (es público), ni a issues, capturas o mensajes.

## 2. Local (portátil)
```sh
# en la raíz del repo; .env está en .gitignore
echo 'DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/…' >> .env
chmod 600 .env
docker compose up -d --force-recreate web   # o up --build -d si cambió el código
```
`PULSO_ORIGIN` queda en `local` por defecto (viene de `.env.example`).

## 3. AWS EC2
1. Añade `DISCORD_WEBHOOK_URL=…` al `.env` que preparas en el portátil para la EC2, junto con las contraseñas nuevas.
2. Cópialo solo por `scp`. En la instancia, deja sus permisos con `chmod 600 .env`.
3. `scripts/deploy-ec2.sh` escribe `PULSO_ORIGIN=EC2` por sí solo, así que no hay que tocarlo.
4. Comprueba la salida a Internet desde la instancia:
   ```sh
   curl -s -o /dev/null -w "%{http_code}\n" https://discord.com/api/v10/gateway   # 200 = OK
   ```
   Si no responde 200, el laboratorio bloquea la salida. En ese caso la app muestra «Simulación local» y el resto funciona igual.

## 4. Verificar
- En la app, la zona de alertas muestra «Discord configurado». Tras la alerta muestra «Enviado a Discord».
- `GET /api/sites/<sitio>/state` → `discord.configured: true`. La URL nunca aparece en el JSON.
- Comprueba que el secreto no quedó versionado:
  ```sh
  git grep -n "discord.com/api/webhooks/[0-9]" -- . ':!*.md'   # no debe mostrar nada
  ```

## 5. Desactivar
Borra la línea `DISCORD_WEBHOOK_URL` del `.env` y recrea el contenedor web. La app vuelve a «Simulación local».

## Notas técnicas
- Código: `backend/energy/discord.py`, con `urllib`, timeout de 5 s y sin reintentos en bucle ante un 429.
- El envío ocurre después de confirmar la transacción y en un hilo aparte: si Discord falla, la demo no se cae.
- La alerta enviada se marca en `Alert.discord_sent_at` (migración `0002_discord`).
- Contrato v0.1.2: campos `state.discord` y `report.discord`, y `POST /api/sessions/{id}/discord/report`. Detalle en `backend/CONTRACT-NOTES.md`.
- Si la demo local y la EC2 están encendidas a la vez, ambas publican en el mismo canal y se distinguen por «Origen».
