# Wireframe principal v0 (Claude) — base para Antigravity

## Escritorio / proyector (≥ 992 px)
```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ PULSO ENERGÉTICO   [Cuenca ▾] › [Banco de pruebas 5 V ▾]      ☀ DÍA  08:00:18     │
│ Origen: ● Simulador local   ○ Lecturas Wokwi   · Pico simulada / Zero W prevista │
│ ▌DATOS SIMULADOS▐                         Ensayo 18 s · [▶ Reproducir][⏸][⏭ Franja]│
├───────────────────────────┬──────────────────────────────────────────────────────┤
│ ZONAS / CARGA             │  POTENCIA ACTUAL   ENERGÍA ACUMULADA   RESTANTE       │
│ ┌───────────────────────┐ │   2,00 W            0,0100 Wh          0,0100 Wh      │
│ │ ● LED verde  💡        │ │                     ▓▓▓▓▓▓▓░░░░ 50 %   ≈ 18 s al     │
│ │ Carga habilitada      │ │                                         límite        │
│ │ [ ENCENDIDA ⏻ ]       │ ├──────────────────────────────────────────────────────┤
│ │ Perilla 0,40 A ──●──  │ │  Potencia (W) vs tiempo del ensayo (s)               │
│ │ 5,00 V · 2,00 W       │ │  2 ┤▔▔▔▔▔▔▔▔▔▔▔▔                                       │
│ │ 0,0100 Wh · 18 s on   │ │  0 ┼──────────────────────────────▶ s                 │
│ └───────────────────────┘ ├──────────────────────────────────────────────────────┤
│ ALERTAS                   │  Energía acumulada (Wh) · línea de umbral              │
│ (sin alertas)             │ .020 ┤- - - - - - - - - - - - - - - umbral 0,020 Wh   │
│ 🔊 Sonido: [Activar]       │ .010 ┤      ╱▔▔▔(plano = apagado)                     │
│ [🗣 Escuchar reporte]      │    0 ┼──╱───────────────────────────▶ s              │
│ Discord · Simulación local│                                                       │
└───────────────────────────┴──────────────────────────────────────────────────────┘
```
En el recinto (venue), la columna izquierda muestra dos tarjetas de zona: Salón principal (on/off) y Sala de reuniones (on/off + intensidad %, «control simulado»). Las cifras se muestran en kWh y W, y las series se dibujan por zona y en total. Debajo de los gráficos van la tarjeta de comparación y la ficha contextual MWh/día (estimación ilustrativa).

## Móvil (< 576 px): estado, control y alerta antes que los gráficos
```
┌─────────────────────────┐
│ PULSO · Cuenca › Banco  │
│ ☀ Día 08:00:18 · SIMUL. │
│ [▶][⏸][⏭]               │
├─────────────────────────┤
│ ⚠ ALERTA (si existe)    │  ← banda fija, roja, texto + icono
├─────────────────────────┤
│ ● Carga habilitada      │
│ [ ENCENDIDA ⏻ ]  0,40 A │
├─────────────────────────┤
│ 2,00 W │0,0100│0,0100 Wh│
│ potencia│acum. │restante │
├─────────────────────────┤
│ gráfico W               │
│ gráfico Wh + umbral     │
│ [🗣 Escuchar reporte]    │
└─────────────────────────┘
```

## Estados obligatorios
| Estado | Señal visual (sin depender del audio) |
|---|---|
| Inicial | «Ensayo sin iniciar», cifras en 0 y botón «Iniciar ensayo» |
| Carga apagada | LED gris, «Carga deshabilitada», restante muestra «Consumo detenido», curva Wh horizontal |
| Carga encendida | LED verde con pulso suave, «Carga habilitada» |
| Umbral alcanzado | Banda roja persistente «⚠ Límite alcanzado: 0,0200 Wh», borde rojo en la cifra de energía, título de pestaña con «⚠» y beep único de 0,8 s si el sonido está activado |
| Conexión interrumpida | Banda ámbar «Conexión interrumpida · sin datos de X s», con el tramo sombreado en los gráficos sin consumo atribuido |
| Reporte disponible | Tarjeta con texto del reporte, botón «Escuchar» y vista previa de Discord «Simulación local» |

Temas por franja: Día (claro), Tarde (cálido) y Noche (oscuro). Todos cumplen un contraste AA mínimo de 4,5:1 y se controlan por teclado (Tab, Enter, Espacio y flechas en la perilla).
