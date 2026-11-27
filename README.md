# Pulso Energético

Prototipo para la hackatón Chile–Ecuador (ODS 7). Muestra al encargado de un recinto comunitario **qué está encendido, cuánta energía lleva consumida y cuánto le falta para su límite**. Todos los datos son **simulados**. Los beneficios climáticos (ODS 13) son hipótesis por validar.

## Arranque rápido
Requiere Docker Desktop.
```sh
docker compose up --build -d      # primera vez: descarga imágenes y compila
docker compose up -d              # siguientes veces (funciona sin Internet)
```
Abrir **http://localhost:8080**. No uses `docker compose down -v`, porque borra los datos.

| Usuario | Contraseña (solo demo local) | Puede |
|---|---|---|
| operador_demo | Demo-2026 | Operar Cuenca y Puente Alto |
| operador_cuenca | Cuenca-demo-2026 | Operar Cuenca |
| operador_puente | Puente-demo-2026 | Operar Puente Alto |
| observador | Observador-demo-2026 | Solo mirar |

Las contraseñas vienen de `.env.example`. Para un servidor real, crea un `.env` con valores nuevos **antes** del primer arranque.

## Qué hace
- Dos localidades (Cuenca y Puente Alto). Cada una tiene un **banco de pruebas de 5 V**, con umbral de 0,020 Wh en tiempo real, y una **sede ficticia** con salón principal y sala de reuniones, con presupuesto en kWh y escala ×60.
- Encendido y apagado por zona, potencia (W), energía acumulada (Wh o kWh) y energía restante al límite.
- Gráficos de potencia y de energía con línea de umbral.
- Una sola alerta visible por ensayo.
- Reloj de día, tarde y noche, y simulación de cortes de conexión.
- El estado se recupera al refrescar la página.
- La energía se calcula en el backend: `Wh = potencia anterior × segundos / 3600`.

## Probar
```sh
docker compose exec -T web python manage.py test                                  # 13 pruebas Django
python3 -I scripts/acceptance.py .env.example contracts/telemetry.example.json   # 19/19 PASS esperado
```

## Estructura
| Ruta | Contenido |
|---|---|
| `backend/` | Django 5.2 + PostgreSQL 17: motor de energía, simulador y API `/api/` |
| `frontend/` | Angular 19 + Bootstrap (servido por Django en el mismo origen) |
| `contracts/` | Ejemplos JSON del contrato entre la interfaz y el backend |
| `docs/` | Ficha (00), tablero (01), contrato (02), wireframe (03), resultados (05), plan AWS (06), riesgos (07) y guion de 90 s (08) |
| `scripts/` | Prueba de aceptación, despliegue en EC2 y apagado |
| `audits/` | Informes de auditoría (seguridad, legibilidad, QA y arquitectura) |

Siguiente etapa (no incluida en la demo): voz, Discord, Wokwi, hardware físico y despliegue en AWS.
