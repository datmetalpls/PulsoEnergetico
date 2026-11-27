# Auditoría de seguridad — Pulso Energético

Revisión del commit `de02502`, 2026-11-27, código y demo local en `http://localhost:8080`.
Resultado: **0 Críticas, 2 Altas, 4 Medias, 3 Bajas y 1 Nota**; las Altas afectan la eventual publicación en EC2.
Los 22 intentos con curl de escritura sin permiso fueron rechazados; CSRF y asociación de alertas a sesión funcionan.
Se reprodujeron tres entradas que devuelven 500; no se demostró SQL injection, XSS ni acceso de escritura entre localidades.
Solo se escribe este informe: sin commits, reinicios, borrado de datos ni cambios persistentes de los ensayos; pruebas internas revertidas.

## Hallazgos, por severidad

Las severidades expresan el riesgo de esta aplicación y su contexto, no copian automáticamente las del escáner. El esfuerzo es una estimación en minutos de implementación y comprobación básica.

| ID | Severidad | Archivo:línea | Hallazgo | Evidencia (comando y salida o código) | Recomendación concreta | Esfuerzo (min) |
|---|---|---|---|---|---|---:|
| SEG-01 | Alta | `scripts/deploy-ec2.md:13`; `.env.example:13`; `scripts/deploy-ec2.sh:143`; `backend/energy/management/commands/seed_demo.py:21` | El procedimiento EC2 puede conservar un **operador global con contraseña pública**, incluso siguiendo la indicación de cambiar las tres contraseñas documentadas. Compose hereda valores ausentes desde `.env.example`; el script solo rechaza el marcador de SECRET_KEY. Además, editar el entorno después de sembrar no cambia las contraseñas de usuarios ya existentes. No afecta solo a un observador: `operador_demo` opera ambas localidades. | `nl -ba scripts/deploy-ec2.md`: línea 13 dice cambiar «las 3 DEMO_*_PASSWORD»; hay cuatro en `.env.example:9–13`. Compose `env_file` combina ejemplo + `.env`. `seed_demo.py:21–24,29–32`: `set_password` solo bajo `if created`; líneas 46–48 asignan todas las sedes al operador demo. Curl con valores del ejemplo autenticó observador y Cuenca: `200` (E1). | Antes de abrir EC2, exigir valores privados de **las cuatro** contraseñas y SECRET_KEY; rechazar valores de ejemplo. Si la BD ya existe, rotar con `changepassword` o `set_password` explícito, sin borrar el volumen; alternativamente desactivar `operador_demo`. Corregir la instrucción de tres a cuatro. | 20 |
| SEG-02 | Alta | `scripts/deploy-ec2.sh:99`; `scripts/deploy-ec2.sh:207`; `docs/06-plan-aws.md:17`; `backend/pulso/settings.py:35` | El plan EC2 publica autenticación y sesión por **HTTP abierto a Internet**. Las credenciales y cookies pueden ser interceptadas en el trayecto; las cookies no llevan Secure. Es un riesgo condicionado al despliegue público, no una exposición remota actual del bind local. | Script genera `0.0.0.0:8080:8000` y URL `http://...`; el plan pide SG `8080/tcp` desde `0.0.0.0/0`. `manage.py check --deploy`: `security.W008`, `W012`, `W016`; runtime: ambas `*_COOKIE_SECURE=False`. Cookie real de sesión: `HttpOnly; SameSite=Lax`, sin Secure (E2). | Para esta entrega, mantener localhost y acceso mediante túnel SSH si hace falta acceso remoto. Si el jurado debe entrar públicamente, poner HTTPS delante, configurar correctamente el proxy y habilitar cookies Secure; después de comprobar HTTPS, redirección y HSTS. No basta habilitar Secure mientras se conserva HTTP. | 15 (túnel) / 60 (HTTPS) |
| SEG-03 | Media | `backend/energy/views.py:109`; `backend/pulso/settings.py:11`; `backend/entrypoint.sh:6` | Login sin limitación de intentos ni demora progresiva. Con dos workers y hashing de contraseñas, los intentos continuos pueden consumir capacidad y facilitar fuerza bruta en una publicación pública. No se midió saturación. | Ocho POST consecutivos a `/api/auth/login`, usuario inexistente y contraseña incorrecta: `403` los ocho, `Retry-After=None`; revisión del único camino de autenticación y middleware sin rate limiter. E3. | Antes de publicar, limitar intentos por IP y usuario en el proxy o mecanismo mantenido de Django; devolver 429 y comprobar recuperación tras la ventana. Para demo local, conservar la restricción de red es la mitigación inmediata. | 30 |
| SEG-04 | Media | `backend/energy/views.py:26`; `backend/energy/views.py:62`; `backend/energy/views.py:198`; `backend/energy/views.py:222` | Tres entradas fuera de dominio eluden la validación y producen **500**: entero gigantesco, NUL en `reading_id` y fechas que exceden el rango del contador de sesión. Requieren operador autorizado; no se demostró corrupción persistente, gracias a las transacciones. | En sesión propia dentro de transacción revertida: `/advance {seconds:10**400}` → `500`, `OverflowError: int too large to convert to float`; `/readings` con `reading_id="security\u0000nul"` → `500`, `DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`; dos lecturas, año 2026 y 9999 → `500`, `DataError: integer out of range`. Script E4. | Comprobar el rango numérico antes de `math.isfinite`, rechazar NUL en IDs y limitar el delta temporal al rango admitido por los contadores antes de guardar. Responder 400 JSON y añadir estos tres casos a la prueba de validación; no ocultar todos los errores de BD con un catch genérico. | 30 |
| SEG-05 | Media | `frontend/package.json:13`; `frontend/package-lock.json:1` | Dependencias npm con avisos conocidos. La explotación concreta en esta SPA está **Por confirmar**; no equivale a afirmar XSS activo. Los críticos detectados pertenecen al árbol de desarrollo, que no se copia al runtime Python final. | `npm audit --json`: **43** paquetes afectados (2 bajos, 25 moderados, 14 altos, 2 críticos: `piscina`, `tar`). `npm audit --omit=dev --json`: **7** (3 moderados, 4 altos, **0 críticos**), todos Angular. [Aviso primario de Angular](https://github.com/angular/angular/security/advisories/GHSA-jj27-h5hq-8x99): i18n y atributos de eventos. No se encontró `innerHTML` ni `bypassSecurityTrust` en `frontend/src`. E5. | Registrar los avisos y revisar qué rutas aplican antes de una publicación; actualizar Angular de forma coordinada a una versión corregida, con build y recorrido P1. Evitar `npm audit fix --force` a un día de la demo; mantener el build con paquetes de confianza y no publicar `ng serve`. | 90 |
| SEG-06 | Media | `backend/requirements.txt:3` | `sqlparse==0.5.3` tiene avisos de seguridad. Su explotación desde esta API está **Por confirmar**: no recibe SQL del usuario ni usa SQL crudo en el código revisado. El resultado del escáner contiene duplicados, no diez fallos independientes. | `uvx --cache-dir /private/tmp/pulso-security-uv-cache pip-audit -r backend/requirements.txt --no-deps --disable-pip --format json`: **10 registros en sqlparse, 6 IDs únicos**; resto de requisitos sin avisos en esa consulta. [Aviso primario GHSA-27jp-wm6q-gp25](https://github.com/andialbrecht/sqlparse/security/advisories/GHSA-27jp-wm6q-gp25): afecta `<=0.5.3`, corregido en `0.5.4`; los otros cinco indican `0.6.0`. E5. | Actualizar el pin a una versión que corrija los seis avisos (el escáner indica `0.6.0`), reconstruir y ejecutar las pruebas Django y la aceptación API. No se necesita rediseñar el acceso a datos. | 20 |
| SEG-07 | Baja | `backend/pulso/settings.py:11` | Falta protección explícita contra embebido en iframe/clickjacking. No se probó explotación en navegador; SameSite y el origen del atacante condicionan el impacto. | `manage.py check --deploy`: `security.W002`. `curl -sS -D - http://localhost:8080/`: sin `X-Frame-Options` ni CSP `frame-ancestors` en la respuesta comprobada (E2). Middleware no incluye `XFrameOptionsMiddleware`. | Añadir middleware de Django con `X_FRAME_OPTIONS='DENY'` si no se requiere embebido. Comprobar la cabecera en `/` y API. | 5 |
| SEG-08 | Baja | `backend/energy/views.py:114`; `backend/energy/views.py:78`; `backend/energy/services.py:9`; `backend/entrypoint.sh:6` | AuditEvent registra operaciones exitosas, pero no intentos fallidos de login ni denegaciones de autorización. Faltan datos útiles para investigar abuso; el access log muestra estado/ruta, no un evento estructurado con actor y motivo. | E3: ocho logins inválidos, delta de `AuditEvent.objects.count()` = **0**. `views.py:114–117` lanza error antes de `audit`; `require_operator` tampoco audita. `audit()` escribe dentro de la transacción del endpoint, que se revierte si se lanza una excepción. | Registrar fallos en logging de seguridad fuera de la transacción que se revierte, con usuario solicitado, resultado y origen bajo una política de retención; nunca incluir contraseña ni cookies. Mantener AuditEvent para cambios exitosos. | 20 |
| SEG-09 | Baja | `backend/energy/serializers.py:24`; `backend/energy/views.py:190` | La respuesta limita la serie visible a 600 puntos, pero reconstruye el total leyendo **todo el historial** en cada polling. Un operador puede importar hasta 5000 filas por petición; un observador puede disparar el recorrido mediante GET autenticado. El riesgo de lentitud con historiales largos está **Por confirmar**, sin prueba de carga para no interrumpir la demo. | Cita: `for r in session.readings.exclude(flag='out_of_order').order_by('t_s', 'id').iterator():` y luego `list(total_points.values())[-600:]`. `import_readings`: 1–5000 filas y consultas por fila (`views.py:201,214,223`). E6. | Para el día de entrega, iniciar ensayos cortos y no cargar lotes grandes durante la presentación. Después, calcular el total con una ventana acotada y sus valores iniciales correctos; medir antes/después sin perder el acumulado previo. | 5 (operación) / 60 (código) |
| SEG-10 | Nota | `git log` (metadatos de autor) | El historial público incluye un correo personal del autor. Es dato personal visible, no una credencial ni una vulnerabilidad de autenticación. No se reproduce el correo aquí. | `git log --all --format='%h %an <%ae>'`: los 9 commits alcanzables muestran el mismo correo personal. `git log --all -G 'AKIA[0-9A-Z]{16}\|ASIA[0-9A-Z]{16}\|BEGIN.*PRIVATE KEY\|sk-[A-Za-z0-9]{20}\|ghp_[A-Za-z0-9]{20}' --format='%h %s' -- .`: sin coincidencias. | Confirmar que se desea publicar ese correo; para futuros commits, usar el correo noreply de GitHub si se prefiere privacidad. No reescribir el historial a un día de entregar sin coordinarlo. | 5 |

## Evidencia y alcance de las pruebas

### E1 — Curl real, autenticación, CSRF y autorización

Se ejecutó un cliente Python que invoca **curl como subprocess**, con jar temporal separado por usuario. Lee contraseñas de `.env.example` sin imprimirlas, hace GET `/api/auth/csrf`, POST login, vuelve a leer el token rotado y envía `X-CSRFToken`. Al terminar hace logout; los eventos legítimos de esos accesos quedan en AuditEvent. No se envió ninguna operación de control autorizada contra los ensayos existentes.

Resultado observado, con `observador` y `operador_cuenca`, destino Puente Alto:

| Método y destino | observador | operador_cuenca |
|---|---:|---:|
| POST `/api/sites/puente-alto-banco/sessions` | 403 | 403 |
| PATCH `/api/sites/puente-alto-sede` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/play` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/pause` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/next-band` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/advance` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/speed` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/connection` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/zones/carga-5v` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/readings` | 403 | 403 |
| POST `/api/sessions/{uuid-puente}/alerts/99999999/ack` | 403 | 403 |

Todos devuelven `{"error":"forbidden"}`. Esto cubre las 11 rutas de escritura de dominio; login/logout se comprueban aparte. Los UUID se obtuvieron por el GET state autorizado como lectura; los reportes de otra localidad dan 200, tal como permite el contrato de observador global. UUID inexistente y UUID mal formado devuelven 404. En la prueba transaccional, operador autorizado sobre su sesión + ID real de alerta perteneciente a Puente Alto da 404: `Alert.objects.get(session=session,id=alert_id)` evita el IDOR.

Login sin token CSRF: 403 JSON para ambos usuarios. Logout con token correcto pero `Origin: https://evil.invalid`: 403. GET de `/api/localities` sin usuario: 403. CSRF_FAILURE_VIEW está configurada como `energy.views.csrf_failure`, devuelve JSON genérico y no expone la razón interna. No hay `csrf_exempt` en el backend revisado.

Forma del curl utilizado (variables/cookies temporales; no pegar secretos en informes):

```sh
curl -sS -b "$JAR" -c "$JAR" -w '\n%{http_code}' \
  -H 'Content-Type: application/json' -H "X-CSRFToken: $CSRF" \
  -X POST --data-binary '{"seconds":1}' \
  "http://localhost:8080/api/sessions/$SESSION_PUENTE/advance"
# 403 {"error":"forbidden"} para los dos usuarios probados.
```

### E2 — Configuración efectiva, cookies y Docker

```text
docker compose ps
db  Up (healthy)  5432/tcp
web Up            127.0.0.1:8080->8000/tcp

docker compose exec -T web python manage.py check --deploy
security.W002 / W004 / W008 / W009 / W012 / W016
System check identified 6 issues (0 silenced).
```

W004 corresponde a HSTS ausente y W009 a la clave de ejemplo corta; ambas son esperables en localhost, pero la clave debe cambiar al publicar. El script EC2 sí rechaza el marcador `replace-before-deployment`; esto ayuda, aunque no valida todas las demás credenciales. SECRET_KEY obligatoria por entorno (`settings.py:6`); no hay fallback secreto silencioso. El backend usa sesiones en BD, por lo que conocer esa clave **no demuestra por sí solo** poder fabricar una sesión autenticada.

Configuración leída desde Django vivo: `DEBUG=False`; `ALLOWED_HOSTS=['localhost','127.0.0.1','testserver','web']`; `SESSION_COOKIE_SECURE=False`, `CSRF_COOKIE_SECURE=False`. Host `evil.invalid` → 400. No hay `*` en la configuración efectiva. La sugerencia documental de usar `ALLOWED_HOSTS=*` como plan B (`docs/06-plan-aws.md:40`) conviene retirar; no se observó aplicada.

```text
curl -sS -D - http://localhost:8080/api/auth/csrf
200; X-Content-Type-Options: nosniff
Referrer-Policy: same-origin
Cross-Origin-Opener-Policy: same-origin
Set-Cookie: csrftoken=[omitido]; Path=/; SameSite=Lax
```

La respuesta de `/` también se comprobó sin cabecera de protección de iframe. En cliente Django con controles CSRF activados: login 200; cookie `sessionid=[omitido]; HttpOnly; Max-Age=1209600; Path=/; SameSite=Lax`, sin Secure; token CSRF cambia tras login. `csrftoken` legible por JavaScript es necesario para el patrón Angular y no constituye un hallazgo.

Dockerfile final: `USER pulso` (línea 23), no root. Compose: Postgres sin `ports`, red `database.internal: true`; web une esa red y la predeterminada. `.dockerignore` excluye `.env`, `.git`, node_modules y dist; no se encontró una clave privada versionada. No se inspeccionaron capas históricas de imágenes ni el daemon de Docker.

### E3/E4 — Validación y errores reproducidos con rollback

Las pruebas se ejecutaron con `docker compose exec -T web python -c '<código Django>'`, usando `Client(raise_request_exception=False)` dentro de `transaction.atomic()`. Se creó una sesión temporal con `new_session`, que cierra la anterior dentro de la misma transacción; **al terminar se hizo `transaction.set_rollback(True)`**, de modo que vuelve íntegra la sesión previa. No ejecutar `new_session` fuera de esta protección al repetir el ensayo. Los contadores de secuencias de PostgreSQL pueden avanzar aunque se reviertan las filas; esto no afecta la integridad.

Resultados correctos: `seconds=True`, `1.5`, `0`, `3601`; `connected=1`; corriente `0.81`, `0.401`, NaN o string; velocidad 300 en banco → 400. Zona ajena/inexistente → 404. Lecturas con lote vacío, 5001 filas o fila no objeto → 400; ID de 201 caracteres, zona de otro sitio, instante inválido/sin zona, voltaje 6 V en banco y corriente >0.80 A → 400. Cuerpo >1 MiB → 400 de Django, sin traceback. Un JSON con 1100 niveles no provocó 500 en el runtime comprobado. Lote de exactamente 5000 filas no se ejecutó por su coste.

Núcleo reproducible de los tres fallos (cada petición tiene además su savepoint en el decorador de endpoint):

```python
import os, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pulso.settings')
import django
django.setup()
from django.test import Client
from django.db import transaction
from django.contrib.auth import get_user_model
from energy.models import Site
from energy.services import new_session

with transaction.atomic():
    c = Client(raise_request_exception=False)
    c.force_login(get_user_model().objects.get(username='operador_cuenca'))
    site = Site.objects.select_for_update().get(slug='cuenca-banco')
    session = new_session(site)
    base = f'/api/sessions/{session.id}'
    row = dict(reading_id='security-probe', zone='carga-5v',
               instant='2026-11-27T00:00:00Z', voltage_v=5, current_a=0.4)
    cases = [
        ('advance', {'seconds': 10**400}),
        ('readings', {'source': 'device', 'readings': [dict(row, reading_id='security\x00nul')]}),
        ('readings', {'source': 'device', 'readings': [row, dict(row,
            reading_id='security-future', instant='9999-01-01T00:00:00Z')]}),
    ]
    for action, body in cases:
        response = c.post(base + '/' + action, json.dumps(body), content_type='application/json')
        assert response.status_code == 500, (action, response.status_code)
        print(action, response.status_code)
    transaction.set_rollback(True)
# advance 500; readings 500; readings 500
```

Repitiendo con `Client()` para capturar excepciones: `OverflowError: int too large to convert to float`; `DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes`; `DataError: integer out of range`. Los 500 externos son genéricos y no muestran traceback con DEBUG desactivado.

En la misma protección transaccional: ocho POST a login con usuario inexistente y password incorrecto → ocho 403, sin `Retry-After`; diferencia del conteo AuditEvent antes/después = 0. No es una prueba de fuerza bruta ni de carga; la ausencia de limitador se confirma con el código de autenticación y middleware revisado.

### E5 — Dependencias

Se consultaron los servicios en línea después de que el sandbox inicial impidiera DNS. No se ejecutó `audit fix`, instalación en el proyecto ni actualización de lockfiles. `uvx` usó caché temporal fuera del repo.

```text
cd frontend && npm audit --json
info=0 low=2 moderate=25 high=14 critical=2 total=43
critical packages: piscina, tar (desarrollo)

cd frontend && npm audit --omit=dev --json
info=0 low=0 moderate=3 high=4 critical=0 total=7
high: @angular/common, @angular/compiler, @angular/core, @angular/router
moderate: @angular/forms, @angular/platform-browser, @angular/platform-browser-dynamic

uvx --cache-dir /private/tmp/pulso-security-uv-cache pip-audit \
  -r backend/requirements.txt --no-deps --disable-pip --format json
Found 10 known vulnerabilities in 1 package: sqlparse 0.5.3
```

IDs únicos Python: `PYSEC-2026-3697`, `PYSEC-2026-3696`, `PYSEC-2026-3698`, `PYSEC-2026-3699`, `PYSEC-2026-3923`, `GHSA-27jp-wm6q-gp25`. Los primeros cuatro aparecen duplicados en la respuesta del servicio. La consulta cubre las líneas fijadas en `requirements.txt`, no todos los paquetes del sistema operativo ni una resolución adicional de transitivas. Varios avisos npm exigen SSR, hidratación o traducciones manipuladas; no se presume que esas condiciones existan en esta SPA estática.

### E6 — Revisión estática y secretos

Se revisaron contrato, tablero y resultados previos; views, servicios, modelos, serializadores, settings/URLs, semilla, entrypoint, Docker/Compose, cliente Angular y scripts EC2. Las consultas de dominio usan el ORM y filtros por sesión/sitio; búsqueda de `raw`, `execute`, `extra`, `eval`, `csrf_exempt`, `innerHTML` y `bypassSecurity` no encontró un punto de inyección en los caminos revisados. No se afirma ausencia absoluta de vulnerabilidades.

`git log --all --oneline` y los nombres de archivos de todos los commits alcanzables: 9 commits; sin `.env` privado, PEM o key versionados. Se buscaron patrones AWS, OpenAI, GitHub y claves privadas en diffs de todo ese historial, sin coincidencias. `.env.example` contiene contraseñas de demostración y clave de desarrollo intencionadas, evaluadas en SEG-01; no se clasificaron como filtración de credenciales de producción. No se encontró información de usuarios reales en los fixtures textuales; sedes y mediciones están marcadas como ficticias/simuladas. Las imágenes no se sometieron a OCR ni análisis de metadatos.

## Lo que está bien

- Autorización centralizada de escritura por sitio en todos los endpoints probados; las alertas se consultan además dentro de la sesión. Lectura global coincide con el contrato.
- CSRF real en login y mutaciones, comprobación de Origin y respuesta de error JSON; cookie de sesión HttpOnly/Lax y rotación CSRF tras login. Sin CORS abierto ni exenciones encontradas.
- DEBUG apagado, ALLOWED_HOSTS acotado y error 500 genérico. Rango, tipo, paso de corriente, tamaño de lote y duplicados tienen controles explícitos; transaction.atomic evita escrituras parciales en los casos comprobados.
- Runtime web sin root, bind local y PostgreSQL en red interna sin puerto del host; `.env` fuera de Git y del contexto de build.
- Operaciones exitosas tienen AuditEvent sin contraseñas en payload. No se necesita un rediseño para conservar una demo local razonablemente protegida.

## No verificado

- AWS no fue desplegado: no se inspeccionaron SG reales, IAM, logs remotos, HTTPS ni contraseñas de una EC2 existente. Las Altas describen el procedimiento versionado, no un incidente en AWS.
- Sin carga sostenida, explotación XSS en navegador, fuzzing exhaustivo, análisis de imágenes/metadatos, objetos Git no alcanzables, ramas remotas no traídas ni escaneo de capas históricas de Docker.
- No se reejecutó toda la suite Django ni la aceptación que reinicia ensayos; se usaron comprobaciones dirigidas y transacciones revertidas. Los límites de importe válidos máximos y crecimiento prolongado quedan pendientes.
- No se actualizó la memoria de Obsidian: la instrucción específica de esta tarea permite escribir **solo este informe**; el coordinador puede incorporar el resultado a la memoria compartida.
- Riesgo residual prioritario: conservar localhost para presentar; antes de exponer EC2, resolver credenciales de las cuatro cuentas y transporte HTTPS/túnel. Las dependencias y los 500 documentados siguen sin corregir, por alcance de auditoría.
