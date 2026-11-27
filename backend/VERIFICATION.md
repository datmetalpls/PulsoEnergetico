# Entrega backend — 2026-11-27

P1 terminada y verificada. Código solo en backend y archivos de infraestructura asignados; sin commits. Se conservan las funciones P2/P3 ya escritas antes del ajuste de alcance; no se depuró CI ni se agregó trabajo posterior en ellas.

## Ejecución y resultados

1. `docker info --format '{{.ServerVersion}}'`: Docker Desktop **29.7.2** disponible.
2. Python local **3.12.14**; instalación efectiva desde PyPI de todas las versiones fijadas en `backend/requirements.txt`, incluido Django **5.2.19** y psycopg **3.2.13**. Migración `energy/0001_initial.py` generada con Django y aplicada en PostgreSQL.
3. `docker compose up --build -d`: correcto. Compilación real de Angular con `npm ci && npm run build`, Node 22; no se usó index de reemplazo. Django ejecutó migrate, seed_demo y collectstatic, y gunicorn arrancó con dos workers.
4. `docker compose exec web python manage.py test --verbosity 1` sobre la imagen final:

```text
Found 13 test(s).
System check identified no issues (0 silenced).
Ran 13 tests in 5.847s
OK
Destroying test database for alias 'default'...
```

Las pruebas usan PostgreSQL 17 y comprueban explícitamente `connection.vendor == 'postgresql'`. Cubren aceptación, ambas sedes independientes, lecturas duplicadas/fuera de orden, gaps incluso para cortes cortos, catch-up limitado e idempotente, refresco y dos clientes, CSRF real, permisos, validación y transacciones, unicidad de alerta, reporte cerrado, comparación, forma JSON, límite de series y respaldo idempotente.

5. `docker compose run --rm --entrypoint python -v "$PWD/backend:/app/backend" web manage.py makemigrations --check --dry-run`: **No changes detected**. `docker compose config --quiet`: correcto.
6. Verificación mediante subprocess de **curl real**, con cookie de sesión, cookie CSRF y header actualizado tras login; los datos de acceso se leyeron del archivo de entorno sin imprimirlos:

```text
curl /api/localities: HTTP 200; 2 localities, 4 sites
curl /api/sites/cuenca-banco/state: HTTP 200
curl /: HTTP 200; actual Angular app-root, no placeholder
curl Angular JS/deep route: HTTP 200; missing API: HTTP 404
P1 banco: 2 W; 18 s=0.010 Wh; 10 s apagado=0.010 Wh; 46 s=0.020 Wh; una alerta
P1 sede Cuenca: sala=0 W, conserva 2.6666666666666665 Wh; salon aumenta a 10.666666666666666 Wh
```

La sala consumió durante 120 s y después quedó apagada otros 120 s; el salón permaneció encendido durante los 240 s. El banco completó exactamente 36 s efectivos dentro de 46 s de ensayo.

7. Semilla ejecutada dos veces sobre la base real mediante `call_command('seed_demo')`, con assert de conteos antes/después:

```text
Demo ready: 2 localities, 4 sites, 3 users.
Demo ready: 2 localities, 4 sites, 3 users.
SEED IDEMPOTENTE: [2, 4, 6, 6, 9, 3] == [2, 4, 6, 6, 9, 3]
```

Orden de los conteos: Locality, Site, Zone, Session, ZoneState, User. Los ensayos adicionales son el historial creado por las comprobaciones, no duplicaciones de la semilla.

8. Segundo arranque, preservando el volumen:

```sh
docker compose down
docker compose up -d --no-build --pull never
```

Ambos comandos terminaron correctamente. Arranque exclusivamente desde imágenes locales, sin reconstrucciones, pulls ni instalación de dependencias. No se deshabilitó físicamente la conexión de Internet del Mac.

Se preparó un ensayo **pausado** en `puente-alto-banco`, 2 W durante 18 s, y se apagó la carga antes del down. GET state después del up confirmó igualdad de la sesión, zonas y alertas completas:

```text
UUID: 76c4f346-9580-4ba3-b1a1-8690205c087f
PERSISTENCIA OK puente-alto-banco: mismo UUID, energy_wh=0.01, elapsed_s=18
```

La primera comparación en Cuenca fue invalidada porque otro agente creó y operó nuevos ensayos entre prepare y verify; la auditoría permitió identificar esa interferencia. La repetición aislada en Puente Alto fue correcta.

## Sitios reales

- `cuenca-banco`
- `cuenca-sede`
- `puente-alto-banco`
- `puente-alto-sede`

Zonas: `carga-5v` en bancos; `salon-principal` y `sala-reuniones` en sedes.

## Endpoints implementados

Todas las rutas son sin barra final, bajo el mismo origen:

| Método | Ruta |
|---|---|
| GET | `/api/auth/csrf` |
| POST | `/api/auth/login` |
| POST | `/api/auth/logout` |
| GET | `/api/auth/me` |
| GET | `/api/localities` |
| GET | `/api/sites/{site}/state` |
| PATCH | `/api/sites/{site}` |
| POST | `/api/sites/{site}/sessions` |
| POST | `/api/sessions/{uuid}/play` |
| POST | `/api/sessions/{uuid}/pause` |
| POST | `/api/sessions/{uuid}/next-band` |
| POST | `/api/sessions/{uuid}/advance` |
| POST | `/api/sessions/{uuid}/speed` |
| POST | `/api/sessions/{uuid}/zones/{zone}` |
| POST | `/api/sessions/{uuid}/connection` |
| POST | `/api/sessions/{uuid}/readings` |
| POST | `/api/sessions/{uuid}/alerts/{id}/ack` |
| GET | `/api/sessions/{uuid}/report` |
| GET | `/api/sites/{site}/comparison` |

`GET /api/localities` es una lista directa compatible con `LocalityWithSites[]` del frontend. Los demás JSON respetan las claves de los fixtures. CSRF obligatorio en todas las escrituras, incluido login. Lecturas protegidas requieren sesión autenticada; observador no puede escribir y cada operador solo opera sus sitios.

## Decisiones, límites y pendientes

- Decisiones del contrato: [CONTRACT-NOTES.md](CONTRACT-NOTES.md). Destacan el origen temporal de importación, cierre al crear otra sesión, `on_seconds` del reporte como máximo por zona y excepción de respuesta duplicada. No se modificó el contrato congelado.
- Arranque y variables: [README.md](README.md). Compose superpone `.env` sobre `.env.example`; los valores de demo solo están en `.env.example`. Cambiar contraseña de un usuario ya creado requiere hacerlo explícitamente; seed_demo no la reemplaza.
- El Dockerfile intenta compilar Angular durante el build; si falta o falla, usa index de reemplazo con advertencia. Para una SPA completa el primer build necesita dependencias disponibles. El segundo arranque con imágenes locales no necesita compilar Angular. Para EC2 se puede transportar la imagen compilada en el portátil; no se implementó otra ruta de empaquetado.
- Npm reportó **43 vulnerabilidades** del árbol de frontend: 2 bajas, 25 moderadas, 14 altas y 2 críticas; también cuatro avisos de selectores CSS omitidos. No se modificó frontend ni se intentó resolverlos: su responsable debe evaluar cuáles afectan al artefacto distribuido.
- CI está creado y sin ejecutar en GitHub, conforme al ajuste de alcance. Sin pruebas con hardware ni servicios externos. El reporte solo produce una vista previa local, nunca envía a Discord.
- Memoria persistente fue leída al inicio; su actualización queda al coordinador porque el vault está fuera de las rutas de escritura asignadas a este worker.
