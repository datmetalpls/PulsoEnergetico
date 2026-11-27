# Resultados: prueba de aceptación y estado de la entrega (2026-11-27)

Entorno: macOS, Docker 29.7.2, Compose 5.4.0, PostgreSQL 17 y Django 5.2.19 en Docker Compose, con la demo en http://localhost:8080.
Ejecutado por **Claude (integrador)**, salvo donde se indica «informado por Codex».

## 1. Pruebas automáticas
| Prueba | Comando | Resultado |
|---|---|---|
| Suite de Django sobre PostgreSQL 17 (13 pruebas: aceptación, sedes independientes, duplicados, fuera de orden, gaps, refresco y dos clientes, CSRF, permisos, alerta única, reporte, comparación y semilla) | `docker compose exec -T web python manage.py test` | **OK, 13 pruebas en 5,7 s** (Claude, después del `up --build` con el frontend final) |
| Aceptación contra la API real | `python3 -I scripts/acceptance.py .env.example contracts/telemetry.example.json` | **19/19 PASS** ([salida](evidencia/acceptance-api.txt)) |

Detalle de la aceptación por API (banco Cuenca, tolerancia de una muestra = 0,000556 Wh):
- 5 V × 0,40 A = **2,00 W** ✔
- 18 s → **0,0100 Wh** ✔
- 10 s apagado → sigue en **0,0100 Wh** y 0 W ✔
- 18 s más (36 s efectivos) → **0,0200 Wh** y **1 alerta** ✔. Al seguir consumiendo no aparece otra ✔
- «Siguiente franja» (Día → Tarde) conserva Wh y `elapsed_s` ✔
- Un segundo cliente (observador) ve la misma sesión y el mismo acumulado ✔. El observador recibe 403 al operar y el operador de Cuenca recibe 403 en Puente Alto ✔
- Reenviar el lote `telemetry.example.json` no duplica Wh: 0,001667 Wh, igual al valor esperado ✔
- **Criterio del recinto:** al apagar la sala de Cuenca, su potencia pasa a 0 W, conserva 40,0 Wh, la potencia total baja de 240 W a 160 W y el salón sigue encendido. Puente Alto no cambia ✔
- **Prueba inversa:** al apagar la sala de Puente Alto, su potencia pasa a 0 W, conserva 13,3 Wh, el salón sigue encendido y Cuenca no cambia ✔
- Comparación «Sala encendida» vs «Sala apagada al terminar la reunión»: diferencia de 240 Wh, que equivale a 80 W × 3 h ✔ (P2)

## 2. Prueba en navegador (Playwright y Chromium, 1440×900, API real, sin `?mock=1`)
Recorrido: iniciar sesión como `operador_cuenca`, abrir el Banco de pruebas 5 V, «Iniciar ensayo», «Encender» y «Reproducir» en tiempo real (×1).
| Momento | Potencia | Energía | Alerta visible | Otros |
|---|---|---|---|---|
| Inicio | 2,00 W | 0,0000 Wh | no | «DATOS SIMULADOS» visible |
| 41 s | 2,00 W | 0,0228 Wh | **sí**: banda «⚠ Límite alcanzado: 0,0200 Wh», borde rojo y título «⚠ Pulso Energético» | la curva de Wh cruza la línea de umbral |
| Apagar | 0,00 W | 0,0233 Wh | sí | «Consumo detenido» |
| **Refrescar** | 0,00 W | **0,0233 Wh** | sí | el estado se recupera desde el backend ✔ |

Captura: [navegador-banco-umbral.png](evidencia/navegador-banco-umbral.png). La alerta aparece a los 36 s de consumo efectivo. La captura muestra 0,0228 Wh porque la carga siguió encendida hasta el segundo 41, ya que el operador decide cuándo apagarla.
Antigravity informa que hizo su propia verificación en vivo del recorrido de la sede Cuenca (240 W → 160 W), con 0 errores de consola. Sus capturas están en `design/screenshots/live-*.png`.

## 3. Arranque
| Prueba | Resultado |
|---|---|
| `docker compose up --build -d` | ✔ en 39 s, con caché (Claude). Angular se compila dentro de la imagen y Django sirve la SPA y la API en el mismo origen |
| PostgreSQL no publicado | ✔ `docker compose ps` muestra `5432/tcp` sin puerto del host. La web queda en `127.0.0.1:8080` |
| Segundo arranque sin reconstruir ni descargar | ✔ informado por Codex: `docker compose down` y luego `up -d --no-build --pull never` conservan el UUID, 0,010 Wh y 18 s en `puente-alto-banco` |
| `seed_demo` idempotente | ✔ informado por Codex: dos ejecuciones dejan los mismos conteos `[2, 4, 6, 6, 9, 3]` |

## 3b. Corrección Puente Alto (2026-11-27)
Problema: al entrar como `operador_cuenca` y cambiar a Puente Alto, los controles desaparecían sin aviso, porque ese usuario no tiene permiso sobre Puente Alto. Correcciones:
- Aviso visible «👁 Solo lectura… Entra como operador_puente u operador_demo».
- Nuevo usuario `operador_demo` / `Demo-2026`, que opera Cuenca y Puente Alto.

Verificado en el navegador (aviso visible y controles en ambas localidades con `operador_demo`), Django 13 OK y aceptación de la API 19/19. Con `operador_puente`, el banco de Puente Alto da 2 W y suma Wh; la sede marca 240 W.

## 4. Pendiente o no ejecutado (⚠)
- ⚠ **Arranque con la red físicamente desconectada:** no se apagó el Wi-Fi. `--no-build --pull never` demuestra que no hay descargas, pero conviene repetirlo con el Wi-Fi apagado antes de presentar. Nunca usar `docker compose down -v`, porque borra los datos.
- ⚠ **AWS EC2:** el plan y el script existen (`docs/06`, `scripts/deploy-ec2.*`), pero **no se ejecutaron** en el Learner Lab.
- ⚠ **Video y capturas de respaldo (capa 3):** pendientes de grabar y guardar fuera del laboratorio.
- ⚠ **Ensayo cronometrado de 90 s:** el guion está en `docs/08`; falta el ensayo con persona.
- ⚠ **CI de GitHub Actions:** el archivo `.github/workflows/ci.yml` existe, pero no se ha ejecutado en GitHub (recortado).
- ⚠ **Wokwi y hardware:** sin comprobar (siguiente etapa). No se encontró `Pulso_Wokwi.zip`.
- ⚠ **npm:** quedan 7 avisos de vulnerabilidad en dependencias de producción, ninguno crítico, y 36 en dependencias de desarrollo. No se actualizaron versiones mayores hoy.
- ⚠ **Contraseñas de demo:** están en `.env.example`, que es público. Sirven solo para localhost. En la EC2 hay que usar un `.env` propio con valores nuevos.

## 5. Cómo repetir la demo
```sh
docker compose up --build -d     # primera vez (descarga imágenes y compila)
docker compose up -d             # siguientes veces, también sin Internet
python3 -I scripts/acceptance.py .env.example contracts/telemetry.example.json   # 19/19 PASS esperado
```
Luego abrir http://localhost:8080 y entrar como `operador_cuenca` (contraseña en `.env.example`). Para el respaldo con datos precargados: `docker compose exec web python manage.py load_backup_demo`.

Limitaciones: los datos son simulados y están etiquetados en pantalla. La sede usa una escala de tiempo fija de ×60. Los beneficios de ahorro y climáticos (ODS 13) son hipótesis por validar.

## 6. Auditoría y correcciones (2026-11-27, noche)
Equipo: Codex (seguridad), Antigravity (legibilidad), OpenCode + DeepSeek v4.1 Flash (QA) y Claude (arquitectura). Informes en `audits/`. Además, mejoras de Antigravity Gemini 4 Hydrogen (interfaz) y Neon (backend y operación) en ramas propias, integradas tras revisión.

| Auditoría | Crít. | Alta | Media | Baja | Nota |
|---|---|---|---|---|---|
| Seguridad | 0 | 2 | 4 | 3 | 1 |
| Legibilidad | 0 | 1 | 5 | 5 | 1 |
| Arquitectura | 0 | 2 | 4 | 4 | 3 |
| QA | 0 | 0 | 4 | 5 | 7 |

Corregido e integrado: SEG-01/A2/QA-04 (credenciales de EC2 obligatorias y privadas), SEG-03 (límite de intentos de login), SEG-04 (500 → 400 en JSON), SEG-06 (sqlparse 0.6.1), A1 (el build falla si Angular falla; .dockerignore; usuario no root), M1 (catch-up en lote, sin gaps ficticios), M2 (`setpoint_current_a`), QA-01/02/03/08, LEG-01 (README) y LEG-02 (textos). También accesibilidad AA, `aria-live` y orden en móvil.
Verificación final del integrador (commit fe55400): Django **OK** (21 pruebas en la imagen y 2 de despliegue en el host), aceptación por API **19/19**, navegador con `operador_demo` (2 W → 0,0100 Wh a 18 s; 10 s apagado sin cambio; alerta visible a 36 s; refrescar mantiene la banda «UMBRAL ALCANZADO»; Puente Alto operable), 390 px sin desborde y 0 errores de consola. Capturas: [1440](evidencia/navegador-final-1440.png), [390](evidencia/navegador-final-390.png).
Para después: refactor de componentes (LEG-02/03), cabeceras X-Frame-Options/CSP y no-store, registro de logins fallidos, actualización de Angular por los avisos de npm, HTTPS y carga del historial (SEG-09).
