# Auditoría QA — Pulso Energético (OpenCode / DeepSeek)

**Fecha:** 2026-11-27 · **Commit auditado:** `de02502` (`main`) · **Demo:** http://localhost:8080
**Entorno:** macOS, Docker Compose, Django 5.2 + PostgreSQL 17, Angular 19, gunicorn (2 workers).
**Alcance:** API REST, suite Django, aceptación automática, build Angular y pruebas exploratorias con `curl`.
**Sesiones usadas:** solo `cuenca-banco` y `cuenca-sede` con `operador_cuenca`; `observador` para permisos. No se tocaron `puente-alto-*` ni se ejecutó `docker compose down -v`.

## Resumen (5 líneas)

1. Ejecuté la suite Django (**13/13 OK**), la aceptación API (**19/19 PASS**), el build Angular (**OK**) y ~150 comprobaciones `curl` de casos borde sobre las sesiones de Cuenca.
2. **No hay hallazgos críticos ni altos**: el recorrido P1 (2 W → 0,0100 Wh a 18 s → 0,0200 Wh a 36 s, alerta única, gap, 409, permisos y CSRF) se comporta según el contrato.
3. Hay **4 hallazgos medios**: el lote máximo de 5000 lecturas se rechaza por el límite de 1 MB con error HTML, el slider dispara un POST por paso, el reporte de una sesión cerrada puede mostrar potencia distinta de 0 y, solo si se publica en EC2, un `.env` con contraseñas de ejemplo deja credenciales conocidas.
4. Hay **5 hallazgos bajos**: `on=true` con 0 A/0 % deja la UI contradictoria, `advance 3600` bloquea el polling ~6 s, faltan `X-Frame-Options`/`Cache-Control`, las acciones de la UI no muestran errores 409/403 y la cookie no lleva `Secure` fuera de HTTP local.
5. El resto son **7 notas** (next-band de noche, texto del reporte, `on_seconds`, npm audit, `/admin`, content-type y warnings de build); ninguna bloquea la demo local.

## Conteo por severidad

| Crítica | Alta | Media | Baja | Nota |
|---:|---:|---:|---:|---:|
| 0 | 0 | 4 | 5 | 7 |

## Hallazgos

| ID | Severidad | Archivo:línea | Hallazgo | Evidencia | Recomendación | Esfuerzo (min) |
|---|---|---|---|---|---|---|
| QA-01 | **Media** | `backend/pulso/settings.py:39`, `backend/energy/views.py:190` | El lote máximo que permite el contrato (5000 lecturas) se rechaza por `DATA_UPLOAD_MAX_MEMORY_SIZE = 1 MB`; además el error es HTML, no JSON. | Generé 5000 filas con `reading_id` de 200 caracteres (máximo permitido): **1.575.034 bytes** → `HTTP 400` con `<title>Bad Request (400)</title>`. Un body de 1,1 MB a `/advance` también devuelve 400 HTML. `views.py:190` acepta `1..5000`. | Subir el límite a 5 MB (o bajar el máximo documentado) y capturar `RequestDataTooBig` para devolver `400 {"error":"validation","fields":{"body":...}}`. Añadir prueba con 5000 filas. | 15 |
| QA-02 | **Media** | `frontend/src/app/app.component.html:265,289`, `frontend/src/app/app.component.ts:80-92`, `frontend/src/app/services/pulso-store.service.ts:480,507` | Los sliders envían un POST por cada evento `input`, sin debounce: arrastrar de 0 a 0,40 A genera ~40 peticiones, 40 lecturas y 40 transacciones. | 40 POST secuenciales 0,01..0,40: **1,96 s**; estado final 0,40 A / 2,00 W. 20 POST concurrentes ×3 conservaron 0,20 A (no se reprodujo inversión de orden, pero no hay protección). | Debounce de 150–250 ms en `(input)` o usar `(change)` para el valor final; actualizar el estado de forma optimista. Probar el arrastre en navegador. | 20 |
| QA-03 | **Media** | `backend/energy/serializers.py:70-71`, `backend/energy/services.py:13-18` | El reporte de una sesión cerrada muestra `power_w` distinto de 0 si una zona quedó encendida al cerrar. | Encender 0,40 A, `advance 5`, crear sesión nueva y `GET report` de la anterior → `values.power_w: 2.0` y texto «Potencia actual: 2 vatios». El ejemplo `contracts/report.example.json:11` muestra 0 W para una sesión cerrada. | En `report_json`, usar 0 si `session.status == 'closed'` (o apagar las zonas al cerrar); añadir prueba de cierre con carga encendida. | 5 |
| QA-04 | **Media** (Por confirmar; solo EC2) | `.env.example:9-13`, `docker-compose.yml:20-23`, `scripts/deploy-ec2.sh:173` | Si se despliega en EC2 un `.env` que conserva las contraseñas de `.env.example`, la demo pública queda con credenciales conocidas; el script solo valida `DJANGO_SECRET_KEY`. | `.env.example` publica `Cuenca-demo-2026`, `Puente-demo-2026`, `Observador-demo-2026` y `Demo-2026`; compose carga `.env.example` como fallback; `deploy-ec2.sh:173` solo busca `replace-before-deployment` en `DJANGO_SECRET_KEY`. `docs/05` §4 y `docs/06` ya advierten, pero no se enforce. | Añadir a `configure_env` una comprobación que falle si las contraseñas demo siguen iguales, o exigir un marcador `DEMO_PASSWORDS_CHANGED=1`; documentarlo en `docs/06`. | 10 |
| QA-05 | **Baja** | `backend/energy/views.py:287-300`, `backend/energy/serializers.py:39-45`, `frontend/src/app/app.component.html:228,247` | `current_a=0` o `intensity_pct=0` con `on=true` deja la zona «encendida» con 0 W; la UI muestra «ENCENDIDA (Apagar)» y «Carga deshabilitada/Apagada» a la vez. | `POST zones {"on":true,"current_a":0}` → 200, `on:true`, `power_w:0`, `indicator.label:"Carga deshabilitada"`; `intensity_pct:0` → 200, `on:true`, `power_w:0`, «Apagada». El botón usa `zone.on` (`app.component.html:247`). | Al recibir 0 A/0 %, poner `on=false` en backend, o que la UI derive el botón de `power_w>0`/`indicator.led`. Probar ambos controles en navegador. | 10 |
| QA-06 | **Baja** | `backend/energy/views.py:162` (y `:85`), `backend/energy/services.py:73-91,47` | `GET state` toma `select_for_update` y se serializa detrás de `advance`; `advance 3600` en el banco tarda ~6,5 s y bloquea el polling ~6,2 s. | `advance 3600` banco: **6,52 s**; `GET state` concurrente: **6,22 s** (0,04 s en reposo); 20 `GET state` tras 4200 lecturas: **27,8 ms**. `advance` emite 3601 lecturas y guarda la sesión en cada una. | No bloquear `GET state` (o limitar el lock a `catch_up`) y batchear las escrituras de `advance`; documentar que no se use `advance` durante la demo. | 30-60 |
| QA-07 | **Baja** | `backend/pulso/settings.py:12-15` | Faltan `X-Frame-Options` y `Cache-Control: no-store` en la API (y no hay CSP). | Cabeceras observadas: `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`; **ausentes** `X-Frame-Options`, `Cache-Control` y `Content-Security-Policy`. No está `XFrameOptionsMiddleware`. | Añadir `django.middleware.clickjacking.XFrameOptionsMiddleware` (`X_FRAME_OPTIONS='DENY'`), `@never_cache`/`Cache-Control: no-store` en `state` y evaluar una CSP. | 10 |
| QA-08 | **Baja** | `frontend/src/app/services/pulso-store.service.ts:357-536` | Las acciones de la UI no manejan errores: un 409 `session_closed` o 403 no muestra mensaje y el botón parece no hacer nada. | `play/pause/next-band/speed/zones/connection/ack` se suscriben con `subscribe((next) => this.state.set(next))` sin `catchError`; el backend devuelve `409 {"error":"session_closed"}` (casos E2-E4). Ocurre en dos pestañas si una inicia un ensayo nuevo. | Añadir `catchError` que setee `errorMessage` y refresque el estado en 409; probar dos pestañas. | 15 |
| QA-09 | **Baja** (solo HTTPS/EC2) | `backend/pulso/settings.py:36-38` | La cookie de sesión no lleva `Secure` (correcto en HTTP local; riesgoso si se publica por HTTPS sin configurarlo). | `Set-Cookie: sessionid=...; HttpOnly; SameSite=Lax` (sin `Secure`); `SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` no están definidos. | Definir `SESSION_COOKIE_SECURE=True` y `CSRF_COOKIE_SECURE=True` cuando se sirva por HTTPS (EC2/proxy). | 5 |
| QA-10 | **Nota** (Por confirmar) | `backend/energy/services.py:112-116` | `next-band` desde la franja noche salta a las 08:00 del día siguiente (13 h), no a una franja «siguiente» del mismo día; el contrato no define el wrap. | `next-band` con reloj `19:00:00` → `08:00:00`, `band: day`, `elapsed_s` y `energy_wh` sin cambios. | Confirmar con el contrato si es lo esperado; documentarlo o definir el comportamiento. | 5 |
| QA-11 | **Nota** (Por confirmar) | `backend/energy/serializers.py:73-86`, `contracts/report.example.json:15,19` | El texto de `report.text` y `discord_preview.content` no coincide literalmente con el ejemplo congelado; las pruebas solo comparan claves. | Ejemplo: «Energía acumulada: 0,0200 vatios hora, igual al umbral...»; implementación: «Energía acumulada: 0,0011 vatios hora. Umbral: 0,0010 vatios hora...». `tests.py:214-215` solo compara `keys()`. | Alinear el ejemplo o el texto; añadir prueba de snapshot si el texto es normativo. | 10 |
| QA-12 | **Nota** (Por confirmar) | `backend/energy/serializers.py:71` | `report.values.on_seconds` usa el máximo entre zonas, no la suma; en la sede con dos zonas el «consumo efectivo» es el de la zona más larga. | `on_seconds = max(session.zone_states.values_list('on_seconds', flat=True))`; el contrato define `on_seconds` por zona. | Aclarar el contrato; si se quiere consumo total, sumar o reportar por zona. | 5 |
| QA-13 | **Nota** | `frontend/package-lock.json` (npm audit) | 7 vulnerabilidades en producción (4 high, 3 moderate) y 43 en total (2 critical en dev); el fix exige Angular 22 (salto mayor). | `npm audit --omit=dev`: `{moderate:3, high:4, total:7}`; `npm audit`: `{critical:2, high:14, moderate:25, total:43}`. No se encontró `innerHTML` ni `bypassSecurityTrust`. | No actualizar antes de la demo; documentar y planificar el salto mayor después. Ejecutar `npm audit` en CI. | 0 ahora |
| QA-14 | **Nota** | `backend/pulso/urls.py:6`, `backend/pulso/settings.py` | `/admin/` está expuesto (302 a login) y no hay límite de intentos de login. | `GET /admin/` → 302 a `/admin/login/`; login con contraseña incorrecta → 403 sin throttling; no hay superusuario semilla. | Restringir `/admin/` por IP o quitarlo en EC2; añadir rate limit si se publica. | 5 |
| QA-15 | **Nota** | `backend/energy/views.py:53-59` | El API acepta JSON con `Content-Type: text/plain` (200); no es explotable por CSRF, pero no valida el tipo. | `POST /advance` con `Content-Type: text/plain` y body JSON → 200. | Exigir `application/json` en escrituras si se quiere endurecer; baja prioridad. | 5 |
| QA-16 | **Nota** | `frontend/src/styles.css` / build | `npm run build` emite 4 warnings de selectores Bootstrap (`.form-floating>~label`, `.btn-group>+.btn`, etc.); el build termina OK. | Salida: `4 rules skipped due to selector errors`; `Application bundle generation complete`; 493,44 kB inicial / 94,90 kB transferencia. | Ignorar o actualizar Bootstrap; no bloquea la demo. | 0 |

## Resultados de las pruebas ejecutadas

### 1. Suite Django

```text
$ docker compose exec -T web python manage.py test
Found 13 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...
Ran 13 tests in 23.377s
OK
Destroying test database for alias 'default'...
```

**Resultado:** 13/13 OK. `docs/05-resultados.md:9` registra 5,7 s; esta corrida tardó 23,4 s (probablemente por carga concurrente de otros procesos). El resultado funcional es el mismo.

### 2. Aceptación contra la API real

```text
$ python3 -I scripts/acceptance.py .env.example contracts/telemetry.example.json
PASS login operador_cuenca 200
PASS 5 V × 0,40 A = 2 W 2.0
PASS 18 s ≈ 0,010 Wh 0.01
PASS 10 s apagado conserva acumulado 0.01
PASS 36 s efectivos ≈ 0,020 Wh 0.02
PASS una sola alerta 1
PASS seguir consumiendo no repite alerta 1
PASS siguiente franja conserva Wh y elapsed_s ('day', 'afternoon')
PASS refresco / segunda pestaña ven el mismo ensayo 0.02277777777777778
PASS observador no puede operar (403) 403
PASS operador Cuenca no opera Puente Alto (403) 403
PASS reenviar lote no duplica Wh (0.0016666666666666666, 0.001667)
PASS Cuenca: sala apagada → 0 W 0.0
PASS Cuenca: sala conserva su acumulado 40.0
PASS Cuenca: potencia total baja y salón sigue (240.0, 160.0)
PASS Puente Alto conserva su propio estado 26.666666666666668
PASS Inversa: Puente Alto sala 0 W, conserva Wh, salón sigue 13.333333333333334
PASS Inversa: Cuenca no cambia 199.99999999999997
PASS comparación: diferencia = 80 W × (dur − fin reunión)/3600 240.0

19/19 PASS
```

### 3. Build Angular

```text
$ cd frontend && npm run build
✔ Building...
Initial chunk files   | Names         |  Raw size | Estimated transfer size
styles-VJIZJT2I.css   | styles        | 235.49 kB |                23.58 kB
main-EX24GPL5.js      | main          | 223.37 kB |                59.98 kB
polyfills-5CFQRCPP.js | polyfills     |  34.59 kB |                11.33 kB
                      | Initial total | 493.44 kB |                94.90 kB
Application bundle generation complete. [4.213 seconds]

WARNING: 4 rules skipped due to selector errors:
  .form-floating>~label -> Did not expect successive traversals.
  .btn-group>+.btn -> Did not expect successive traversals.
  .btn-group>+.btn -> Did not expect successive traversals.
  .btn-group-vertical>+.btn -> Did not expect successive traversals.

Output location: /Users/dmp/Hackathon/Proyecto a ejecutar/frontend/dist/pulso
```

**Resultado:** build OK; solo warnings de selectores de Bootstrap (QA-16).

### 4. Pruebas exploratorias `curl` (entrada / esperado / obtenido / PASS-FAIL)

Todas las escrituras usaron CSRF y `Referer`; las lecturas usaron la cookie de sesión. Las sesiones se crearon/cerraron solo en `cuenca-banco` y `cuenca-sede`.

| Caso | Entrada | Esperado | Obtenido | Resultado |
|---|---|---|---|---|
| current_a = 0 con carga on | `{"on":true,"current_a":0}` | 200, 0 W | 200, 0 W, `on:true` | **PASS** (ver QA-05) |
| current_a = 0,80 (máx) | `{"current_a":0.80}` | 200, 4,00 W | 200, 4,0 W | **PASS** |
| current_a = 0,81 | `{"current_a":0.81}` | 400 `fields.current_a` | 400 `current_a:"Valor inválido"` | **PASS** |
| current_a = -1 | `{"current_a":-1}` | 400 | 400 | **PASS** |
| current_a = 0,405 (paso) | `{"current_a":0.405}` | 400 | 400 | **PASS** |
| current_a string/null | `"0.4"`, `null` | 400 | 400 | **PASS** |
| intensity_pct = 0 | `{"on":true,"intensity_pct":0}` | 200, 0 W | 200, 0 W, `on:true` | **PASS** (ver QA-05) |
| intensity_pct = 100 | `{"intensity_pct":100}` | 200, 80 W | 200, 80 W | **PASS** |
| intensity_pct = 101 / -1 | `101`, `-1` | 400 | 400 | **PASS** |
| current_a en luz / intensity en salón | `current_a` en sala; `intensity` en salón | 400 | 400 | **PASS** |
| advance = 0 | `{"seconds":0}` | 400 | 400 | **PASS** |
| advance = 3600 | `{"seconds":3600}` | 200, +3600 s | 200, +3600 s | **PASS** |
| advance = 3601 | `{"seconds":3601}` | 400 | 400 | **PASS** |
| advance = -1 / 1,5 / true / NaN / Infinity | varios | 400 | 400 | **PASS** |
| advance sin seconds / null | `{}`, `{"seconds":null}` | 400 | 400 | **PASS** |
| JSON malformado | `{"seconds":` | 400 `fields.body` | 400 «JSON inválido» | **PASS** |
| JSON array | `[1,2]` | 400 `fields.body` | 400 «Valor inválido» | **PASS** |
| campo extra | `{"seconds":1,"extra":1}` | 400 `fields.extra` | 400 «Campo no admitido» | **PASS** |
| zona inexistente | `/zones/no-existe` | 404 `not_found` | 404 `not_found` | **PASS** |
| sesión cerrada: advance/zones/play | sesión anterior | 409 `session_closed` | 409 `session_closed` | **PASS** |
| report de sesión cerrada | `GET /report` | 200 | 200 | **PASS** |
| doble play | `play` ×2 | 200/200, `playing:true`, energía estable | 200/200, `true`, 0 | **PASS** |
| pausa sin play | `pause` | 200, `playing:false` | 200, `false` | **PASS** |
| next-band en noche | reloj 19:00:00 | 08:00:00, `day`, Wh/elapsed sin cambio | 08:00:00, `day`, sin cambio | **PASS** (ver QA-10) |
| corte y reconexión con gap | off, advance 10, on | gap 10 s, sin energía, reloj +10 | gap 10,0 s, sin energía, +10 | **PASS** |
| alerta en el límite exacto | 2 W, 35 s; +1 s | sin alerta; 1 alerta, 0,0200 Wh | sin alerta; 1 alerta, 0,0200 Wh | **PASS** |
| observador escribiendo | zones/advance/play/sessions/PATCH | 403 | 403 | **PASS** |
| dos advance simultáneos | 1 s + 1 s | 200/200, +2 s | 200/200, +2 s | **PASS** |
| state sin sesión / auth/me / CSRF / Host | sin cookie; Host `evil.example` | 403 / `false` / 403 / 400 | 403 / `false` / 403 / 400 | **PASS** |
| budget 0,05 / 50 / 0,049 / 50,01 | PATCH sede | 200/200/400/400; threshold sincronizado | 200/200/400/400; 50/50000 Wh | **PASS** |
| budget en banco / string / campo extra | PATCH banco | 400 | 400 | **PASS** |
| speed banco 1/60/300 | POST speed | 200/400/400 | 200/400/400 | **PASS** |
| speed sede 60/300/1/2 | POST speed | 200/200/400/400 | 200/200/400/400 | **PASS** |
| comparison: 0 / 86401 / fin>dur / abc | GET comparison | 400 ×4 | 400 ×4 | **PASS** |
| comparison: dur=1, fin=0 | GET comparison | 200, dif 80/3600 | 200, 0,022222 | **PASS** |
| readings: vacío/source/zona/naive/voltaje/corriente/extra/id 201 | POST readings | 400 | 400 | **PASS** |
| readings válido / duplicado / fuera de orden | POST readings | 200 / 200 `duplicate` / 202 | 200 / 200 / 202 | **PASS** |
| reporte cerrado con carga encendida | cerrar con 2 W on | `power_w:0` | `power_w:2.0` | **FAIL** (QA-03) |
| lote de 5000 filas | 1.575.034 bytes | 200 (contrato 1..5000) | 400 HTML | **FAIL** (QA-01) |
| 40 POST del slider | 0,01..0,40 | sin bloqueo; final 0,40 | 1,96 s; final 0,40 | **PASS** (ver QA-02) |
| advance 3600 en banco | 3601 lecturas | 200 sin bloquear polling | 6,52 s; poll 6,22 s | **PASS** (ver QA-06) |
| cabeceras defensivas | GET state | `X-Frame-Options`, `Cache-Control` | ausentes | **FAIL** (QA-07) |
| cookie de login | `Set-Cookie` | `HttpOnly`, `SameSite`; `Secure` si HTTPS | `HttpOnly`, `SameSite`; sin `Secure` | **PASS** local (QA-09) |
| npm audit producción | `npm audit --omit=dev` | sin críticos | 4 high, 3 moderate | **PASS** (QA-13) |
| build | `npm run build` | OK | OK + 4 warnings | **PASS** (QA-16) |

**Nota sobre los FAIL del script crudo:** el primer script imprimió 138 PASS / 15 FAIL y el segundo 77 PASS / 1 FAIL. Tras revisarlos uno a uno, esos FAIL eran mayoritariamente del arnés, no del producto:

- 7 comparaban el **nombre** del campo (`current_a`, `body`, `extra`, `zone`) contra el **mensaje** devuelto («Valor inválido», «Campo no admitido»); el servidor devuelve 400 con el campo correcto.
- 1 comparaba `10` con `10.0` (gap de 10 s).
- 3 usaban una cookie ya autenticada donde se quería probar «sin sesión»; la verificación manual dio 403 en `state`, 403 en `localities` y `auth/me` con `authenticated:false`.
- 2 capturaban `Set-Cookie` en un GET en vez de en el login; la verificación manual del login mostró `HttpOnly` y `SameSite=Lax`.
- 1 esperaba «Consumo detenido» cuando la sesión ya tenía `alert_fired:true`; «Presupuesto alcanzado» es el comportamiento correcto.

Los **FAIL reales** son QA-01, QA-03 y QA-07; QA-02 y QA-06 son observaciones de rendimiento/UX, no fallos funcionales.

## Casos que deberían ser pruebas automáticas

**Backend (`backend/energy/tests.py`, Django `TestCase`)**

1. `current_a`: 0, 0,80, 0,81, -1, 0,405, string y `null`; verificar potencia 0/4,00 W y 400 con `fields.current_a`.
2. `intensity_pct`: 0, 100, 101 y -1; rechazo en zona no regulable; `current_a` rechazado en luz.
3. `advance`: 0, 3600, 3601, -1, 1,5, `true`, `NaN`, `Infinity`, sin campo y `null`; verificar 400 y que no cambie `elapsed_s`.
4. JSON malformado, body array, campo extra en `advance`/`zones`/`sessions`/`PATCH`; respuesta JSON 400 con `fields`.
5. Sesión cerrada: 409 en `play`, `pause`, `advance`, `zones`, `connection`, `ack`, `readings`; 200 en `GET report`.
6. Doble `play`, doble `pause`, `pause` sin `play`; `playing` y energía estables.
7. `next-band` desde `day`, `afternoon` y `night`; sin cambio de Wh/`elapsed_s`; documentar el wrap de noche.
8. Corte/reconexión: 1 s y 10 s; `Gap` con duración correcta, energía sin cambio, reloj sigue; reconexión no atribuye consumo.
9. Alerta en el límite exacto: 35 s sin alerta, 36 s con 1 alerta y `remaining_wh=0`; no repetir al seguir consumiendo; `ack` idempotente; canal `browser` y `wokwi_buzzer`.
10. Observador: 403 en todas las escrituras (`zones`, `advance`, `play`, `sessions`, `PATCH`); 200 en `state`, `report`, `comparison`, `localities`.
11. Presupuesto: 0,05 y 50 aceptados; 0,049 y 50,01 rechazados; `threshold_wh = budget × 1000`; banco rechazado; bajar el presupuesto bajo la energía acumulada dispara una alerta.
12. `speed`: banco solo 1; sede 60/300; 2 y 1 rechazados.
13. Comparación: `duration_s` 0/86401, `meeting_end_s > duration_s`, no numérico; `duration=1, end=0` → 80/3600.
14. `readings`: lote vacío, `source` inválido, zona inexistente, `instant` sin zona, voltaje > nominal, corriente > límite, campo extra, `reading_id` de 201, duplicado total, fuera de orden; y **lote de 5000 filas** que debe aceptarse o devolver JSON 400 (hoy QA-01).
15. Reporte de sesión cerrada con carga encendida → `power_w:0` (hoy QA-03); snapshot de `text`/`discord_preview`; semántica de `on_seconds` en sede con dos zonas.
16. Dos `advance` simultáneos → +2 s; dos `POST sessions` simultáneos → una sola sesión `running`.
17. Seguridad base: `state`/`localities` sin sesión → 403; `auth/me` → `authenticated:false`; POST sin CSRF → 403; `Host` desconocido → 400; cabeceras `X-Frame-Options`, `Cache-Control`, `nosniff`; cookie `HttpOnly`/`SameSite`/`Secure`.
18. `seed_demo` idempotente y conteo de usuarios (3 + `operador_demo` si hay contraseña); `load_backup_demo` idempotente.

**Frontend / e2e (Playwright o Cypress)**

19. Arrastrar el slider de 0 a 0,40 A: medir peticiones (con debounce deben ser ≤3–5, no 40) y confirmar valor final 0,40 A.
20. Dos pestañas: una inicia un ensayo nuevo; la otra debe mostrar un mensaje claro o refrescar al recibir 409, no quedarse muda.
21. `current_a=0` e `intensity_pct=0`: la etiqueta del botón y el indicador deben ser coherentes (no «ENCENDIDA» + «Carga deshabilitada»).
22. `play` 3 s reales → `elapsed_s` y `energy_wh` avanzan; `pause` detiene el reloj; refrescar conserva el acumulado.
23. Alerta visible (banda, borde, título) y sonido opcional; el botón de sonido no rompe la consola.
24. `npm run build` sin errores y `npm audit --omit=dev` sin críticos; umbral de warnings en CI.

## Lo que está bien

- **P1 completo y reproducible:** 2,00 W = 5 V × 0,40 A; 18 s → 0,0100 Wh; 36 s → 0,0200 Wh; alerta única y sin repetición; apagado conserva Wh; refresco y segunda pestaña ven lo mismo.
- **Regla de energía correcta:** gap sin consumo inventado, reloj sigue durante el corte, `next-band` no integra energía y no cambia `elapsed_s`, duplicados no suman, fuera de orden no integra.
- **Validación robusta:** límites y paso de `current_a`, `intensity_pct`, `advance`, `speed`, `budget`, `threshold_wh`; rechazo de `true`, `NaN`, `Infinity`, strings, `null`, campos extra y JSON malformado; 404/409/403 coherentes.
- **Concurrencia:** dos `advance` simultáneos suman +2 s sin perder actualización; dos clientes ven la misma sesión; no se observaron 500 ni tracebacks en los logs de gunicorn.
- **Seguridad base:** `DEBUG=false`, gunicorn, usuario no root, PostgreSQL no publicado, web en `127.0.0.1`, `ALLOWED_HOSTS` rechaza Host desconocido, CSRF en escrituras, cookie `HttpOnly`/`SameSite=Lax`, sin SQL crudo ni `eval` en el código propio, Angular sin `innerHTML`/`bypassSecurityTrust`.
- **Formato y contrato:** `Intl.NumberFormat('es-CL')` con coma decimal; unidades siempre presentes; claves de `state`/`report` coinciden con los ejemplos; `series` limitada a 600 puntos; `seed_demo` y `load_backup_demo` idempotentes (probado por la suite).
- **Errores JSON:** 400 con `fields`, 403 `forbidden`, 404 `not_found`, 409 `session_closed`; el caso de body demasiado grande es la excepción (QA-01).

## No verificado

- **Navegador real (Playwright/Chromium):** no repetí la verificación visual ni el audio; solo build + API. `docs/05` tiene evidencia previa, pero no la revalidé en esta corrida.
- **Wokwi, hardware físico, AWS/EC2, arranque sin Wi-Fi, video/capturas y ensayo de 90 s:** fuera del alcance o no ejecutados; `docs/05` los marca pendientes.
- **Comportamiento real del slider y de los 409 en el navegador:** medí las peticiones con `curl`, no los eventos DOM ni el manejo de errores de Angular en vivo.
- **`catch_up` con más de 120 ticks / pestaña oculta:** no lo forcé; la suite cubre el tope con 130 s simulados.
- **`load_backup_demo` ejecutado a mano:** la suite lo cubre (idempotencia y sesión cerrada), pero no lo corrí como comando independiente.
- **Lote de 5000 filas aceptado:** solo comprobé que el payload máximo representativo (1,575 MB) se rechaza por tamaño; no probé un lote de 5000 filas que quepa en 1 MB.
- **`next-band` afternoon → night:** la aceptación cubre day → afternoon y yo probé night → day; no probé afternoon → night.
- **`ack` en sesión cerrada:** el código devuelve 409 por `locked_session`, pero no lo ejecuté.
- **Reporte de sede con dos zonas y `on_seconds`:** lo revisé por código, no con una sesión de sede con tiempos distintos.
- **Explotabilidad real de los avisos npm:** no busqué una cadena de explotación; solo confirmé que no hay `innerHTML`/`bypassSecurityTrust`.
- **Build desde cero y segundo arranque sin red:** `docs/05` dice verificado; no lo repetí. No ejecuté `docker compose down -v` (prohibido).
