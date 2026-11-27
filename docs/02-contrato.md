# Contrato interfaz ↔ backend — Pulso Energético v0.1

Responsable: Claude (líder técnico). Cambios al contrato solo mediante Claude; el backend (Codex) y la interfaz (Antigravity) consumen **los mismos ejemplos**:

- `contracts/state.example.json` — respuesta de `GET /api/sites/{site}/state` (vista principal).
- `contracts/telemetry.example.json` — lote de lecturas (ingesta / importación Wokwi / fixtures de prueba).
- `contracts/report.example.json` — respuesta de `GET /api/sessions/{id}/report`.

## 1. Nombres y unidades (obligatorios en JSON y en pantalla)

| Campo | Unidad | Significado |
|---|---|---|
| `voltage_v` | V | Tensión de la lectura |
| `current_a` | A | Corriente de la lectura |
| `power_w` | W | **Potencia instantánea** = `voltage_v × current_a`, calculada en backend |
| `energy_wh` | Wh | **Energía acumulada** desde el inicio de la sesión (o de la zona) |
| `threshold_wh` | Wh | Umbral / presupuesto de la sesión |
| `remaining_wh` | Wh | `max(threshold_wh − energy_wh, 0)` |
| `time_to_threshold_s` | s | `remaining_wh × 3600 / total_power_w`; `null` si potencia = 0 («Consumo detenido») |
| `elapsed_s` | s | **Tiempo del ensayo** (reloj de energía): segundos simulados procesados. Único reloj que entra en Wh |
| `on_seconds` | s | Segundos de consumo efectivo de una zona (potencia > 0) |
| `scenario_clock` | HH:MM | **Hora del escenario** (reloj virtual mostrado). Independiente de `elapsed_s` |
| `budget_kwh_day` | kWh/jornada | Presupuesto del recinto; `threshold_wh = budget_kwh_day × 1000` |

Regla: la interfaz nunca recalcula Wh; solo formatea. Formato en pantalla: `2,00 W`, `0,0100 Wh` (banco, 4 decimales), `0,245 kWh` (recinto, 3 decimales), coma decimal `es-CL`. Siempre unidad junto al valor.

## 2. Jerarquía del dominio

`Locality` (Cuenca, Ecuador · `America/Guayaquil` / Puente Alto, Chile · `America/Santiago`)
→ `Site` (dos por localidad):
  - `kind: "bench"` — **Banco de pruebas 5 V** (Pico simulada en Wokwi; Zero W prevista para montaje físico). 1 zona `carga-5v`, umbral fijo 0,020 Wh, muestreo 1 s, velocidad ×1.
  - `kind: "venue"` — **Sede comunitaria ficticia** (Cuenca: «Centro Comunitario Río Tomebamba (ficticio)», 120 V; Puente Alto: «Sede Vecinal Los Andes (ficticia)», 220 V). Zonas `salon-principal` (160 W nominal, on/off) y `sala-reuniones` (80 W nominal, **regulable 0–100 %**, «control simulado»). Presupuesto configurable en kWh/jornada (semilla 0,60), muestreo 60 s, velocidad seleccionable ×60 / ×300 (s simulados por segundo real).
→ `Zone` (carga) → `Reading`.

Cada `Site` tiene su operador, zona horaria (la de su localidad), historial de sesiones y **una sesión activa propia**. Cambiar de sede en la UI nunca pausa ni modifica la otra.

## 3. Modelo mínimo (Django)

- `Locality(slug, name, country, timezone)`
- `Site(slug, locality, name, kind, fictitious, budget_kwh_day, sample_interval_s, default_speed, operators[M2M User])`
- `Zone(slug, site, name, kind: "dc_load"|"light", dimmable, nominal_voltage_v, nominal_power_w, max_current_a)`
- `Session(id uuid, site, status: running|closed, started_at, threshold_wh, elapsed_s, scenario_start "08:00", scenario_offset_s, playing, speed, last_tick_wall, connected, energy_wh, alert_fired)`
- `ZoneState(session, zone, on, current_a, intensity_pct, power_w, energy_wh, on_seconds, last_t_s)`
- `Reading(reading_id unique str, session, zone, t_s, instant, voltage_v, current_a, power_w, interval_wh, flag: ok|duplicate|out_of_order|gap_after, source: simulator|wokwi_import|device)`
- `Gap(session, zone, from_t_s, to_t_s, reason)` — intervalo sin datos, 0 Wh atribuidos.
- `Alert(session, kind: "threshold", unique(session, kind), t_s, energy_wh, threshold_wh, acknowledged_at, channel: "browser"|"wokwi_buzzer")`
- `AuditEvent(user, session, action, payload, at)` — toda escritura queda registrada.

## 4. Regla de energía (compartida, una sola función pura en backend)

```
para cada lectura aceptada de una zona, en orden de t_s:
  si es la primera de la zona en la sesión → referencia temporal, interval_wh = 0
  dt = t_s − last_t_s
  si dt > 3 × sample_interval_s → Gap(last_t_s, t_s), interval_wh = 0 (no se inventa consumo)
  si no → interval_wh = prev_power_w × dt / 3600
  energy_wh(zona) += interval_wh ; energy_wh(sesión) = Σ zonas
  on_seconds += dt si prev_power_w > 0 (y sin gap)
umbral alcanzado ⇔ energy_wh ≥ threshold_wh − 1e-9  → crear Alert una sola vez por sesión
```

- **Duplicado** (mismo `reading_id`): no se vuelve a integrar; respuesta `200 {"status":"duplicate"}`; no repite alerta.
- **Fuera de orden** (`t_s` < `last_t_s` de la zona): se guarda con `flag:"out_of_order"`, no se integra; `202`.
- **Mismo `t_s`, distinto id** (p. ej. cambio de estado en el instante de una muestra): se acepta, dt = 0, actualiza la potencia de referencia.
- **Desconexión**: `POST /connection {connected:false}` detiene la generación de lecturas, mientras el reloj sigue corriendo. Al reconectar, la siguiente lectura crea un `Gap`. La UI muestra «Conexión interrumpida · sin datos de X s», sin atribuir consumo a ese tramo.
- Al encender o apagar una zona o al cambiar corriente o intensidad, el simulador emite de inmediato una lectura en el `t_s` actual con el nuevo valor. Apagar no borra el acumulado; volver a encender dentro de la misma sesión conserva `alert_fired`.

## 5. Simulador determinista y relojes

- Se avanza en «ticks»: cada tick procesa `speed` segundos simulados y emite una lectura por zona cada `sample_interval_s`, con id determinista `"{session}:{zone}:{t_s}"`.
- `play`/`pause` se guardan en el servidor (`playing`, `last_tick_wall`). En cada petición, el backend se pone al día y procesa `floor(Δ reloj real)` ticks completos (máx. 120 por petición; un exceso queda como `Gap`). Así, dos pestañas o un refresco ven y producen el mismo ensayo sin duplicar el avance (bloqueo `select_for_update`).
- `POST /advance {seconds}` (solo operador; usado por pruebas y por el modo respaldo) procesa exactamente N segundos simulados.
- `scenario_clock = scenario_start + scenario_offset_s`. Cada tick suma los mismos segundos simulados al offset. **«Siguiente franja»** salta el offset al inicio de la próxima franja **sin integrar energía** (los Wh no cambian).
- Franjas: `day` 08:00–14:00 · `afternoon` 14:00–19:00 · `night` 19:00–23:00.
- Perilla del banco: `current_a` 0,00–0,80 A, paso 0,01. La mitad corresponde a 0,40 A, es decir 2,00 W a 5 V. Para una luz regulable, `power_w = nominal_power_w × intensity_pct/100` y `current_a = power_w / voltage_v`.

## 6. Endpoints (mismo origen, prefijo `/api/`, JSON, CSRF en escrituras)

| Método | Ruta | Rol | Cuerpo / notas |
|---|---|---|---|
| GET | `/api/auth/csrf` | público | fija cookie `csrftoken` |
| POST | `/api/auth/login` · `/api/auth/logout` | público | `{username,password}` (sesión Django) |
| GET | `/api/auth/me` | público | `{authenticated, username, role:"observer"|"operator", operable_sites:[slug]}` |
| GET | `/api/localities` | observador | localidades con sus sitios |
| GET | `/api/sites/{site}/state` | observador | **ver `state.example.json`**; incluye series |
| PATCH | `/api/sites/{site}` | operador del sitio | `{budget_kwh_day}` 0,05–50 (solo venue) |
| POST | `/api/sites/{site}/sessions` | operador | inicia un nuevo ensayo (cierra el anterior); `{threshold_wh?}` solo en el banco, entre 0,001 y 10 |
| POST | `/api/sessions/{id}/play` · `/pause` · `/next-band` | operador | — |
| POST | `/api/sessions/{id}/advance` | operador | `{seconds: 1..3600}` |
| POST | `/api/sessions/{id}/speed` | operador | `{speed: 1|60|300}` (banco solo 1) |
| POST | `/api/sessions/{id}/zones/{zone}` | operador | `{on?:bool, current_a?:0..max, intensity_pct?:0..100}` |
| POST | `/api/sessions/{id}/connection` | operador | `{connected: bool}` (simula corte) |
| POST | `/api/sessions/{id}/readings` | operador | lote `telemetry.example.json` (fuente `wokwi_import`/`device`) |
| POST | `/api/sessions/{id}/alerts/{alert}/ack` | operador | — |
| GET | `/api/sessions/{id}/report` | observador | ver `report.example.json` |
| GET | `/api/sites/{site}/comparison` | observador | solo venue (§7) |

Errores: `400 {"error":"validation","fields":{...}}`, `403 {"error":"forbidden"}`, `409 {"error":"session_closed"}`. Las escrituras responden con el `state` completo actualizado, igual que GET state.

Polling: la UI pide `GET state` cada 1 s mientras la pestaña está visible. `series` trae como máximo los últimos 600 puntos por zona.

## 7. Comparación (venue)

`GET /api/sites/{site}/comparison?duration_s=21600&meeting_end_s=10800` ejecuta en memoria, con la misma función de energía, dos recorridos de igual duración:
- A «Sala encendida»: salón y sala encendidos durante todo el intervalo.
- B «Sala apagada al terminar la reunión»: la sala se apaga en `meeting_end_s`.

Respuesta: `{duration_s, runs:[{key,label,energy_wh,zones:[{zone,energy_wh,on_seconds}]}], difference_wh, salon_on_seconds, note:"Datos de demostración"}`.

## 8. Fuentes de datos y hardware (etiquetas UI)

`source` ∈ `simulator` («Simulador local»), `wokwi_import` («Lecturas importadas de Wokwi»), `device` («Dispositivo físico»). La UI muestra solo `state.sources_available`; en v0.1 es `["simulator", "wokwi_import"]`. `hardware`: `{simulated_board:"Raspberry Pi Pico (Wokwi)", planned_board:"Raspberry Pi Zero W (montaje físico previsto)"}`.
Aviso sonoro: `alert.channel = "browser"` («Aviso del navegador: imita el buzzer, 0,8 s, una vez») o `"wokwi_buzzer"` («Buzzer físico en Wokwi»), según el modo.

## 9. Seguridad

Usuarios semilla con contraseñas tomadas del entorno (`.env`, nunca del repositorio): `operador_cuenca` (sitios de Cuenca), `operador_puente` (sitios de Puente Alto) y `observador` (solo lectura). **Cambio 2026-11-27 (aprobado por Claude):** se añadió `operador_demo` (`DEMO_OPERATOR_PASSWORD`), que opera las dos localidades para poder presentar sin cambiar de usuario. Cuando el usuario no puede operar un recinto, la interfaz muestra un aviso de «Solo lectura». La UI oculta los controles sin permiso, aunque la autorización real la decide Django. Angular usa `withXsrfConfiguration({cookieName:'csrftoken', headerName:'X-CSRFToken'})`.
