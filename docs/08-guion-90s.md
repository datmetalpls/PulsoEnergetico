# Guion de 90 s — Pulso Energético

Solo usa funciones de **Prioridad 1** (`docs/01-tablero.md`). Los datos son **simulados** y los beneficios climáticos son **hipótesis**. Los tiempos se miden con cronómetro en el ensayo; los valores de Wh son aproximados y dependen del momento de cada clic.

## Preparación (antes de subir al escenario)
1. Demo **C1 local** levantada y probada. C2 (EC2) solo si `verify` dio OK hace menos de 30 min. Video **C3** abierto en otra ventana, pausado en 0:00.
2. Navegador a 1280×720 o más, zoom al 100–125 %, sesión iniciada como `operador_cuenca`, **Cuenca → Centro Comunitario Río Tomebamba (ficticio)**.
3. Ejecutar `BASE_URL=http://localhost:8080 ./scripts/deploy-ec2.sh reset-demo` y refrescar la página. Debe verse un ensayo en pausa, las dos zonas apagadas, 0 W y un umbral de 150 Wh (presupuesto de 0,15 kWh) a ×60, que es la velocidad base de la sede.
4. Comprobar que se ven el banner «Datos simulados», las 3 cifras (Potencia actual · Energía acumulada · Restante al umbral) y los dos gráficos.

Ritmo esperado a ×60: con salón y sala encendidos (240 W) se suman unos 4 Wh por segundo real, y con el salón solo (160 W), unos 2,7 Wh/s.

## Guion
| Tiempo | Qué se dice (frase exacta) | Acción en pantalla |
|---|---|---|
| **0–10 s** · Problema | «Quien cuida una sede comunitaria descubre que gastó de más cuando llega la boleta. No sabe qué está encendido, cuánto lleva ni cuánto le queda.» | Pantalla de Cuenca en reposo. Al llegar a los 8 s, pulsar **▶ Reproducir**. |
| **10–20 s** | «Abrimos el centro comunitario de Cuenca. Enciendo el salón principal… y la sala de reuniones.» | **10 s:** encender *Salón principal*. **15 s:** encender *Sala de reuniones*. La potencia actual sube a 160 W y luego a 240 W. |
| **20–32 s** | «Tres respuestas a la vista: qué está encendido, cuánto llevo en Wh y cuánto me falta para el presupuesto del día.» | Señalar con el cursor las 3 cifras y el gráfico de W. |
| **32–45 s** | «Terminó la reunión y la sala quedó vacía. La apago.» … «La potencia baja a 160 W y lo ya consumido se conserva: apagar no borra el acumulado.» | **32 s:** apagar *Sala de reuniones*. Señalar que el gráfico de W baja, que la sala muestra 0 W y conserva sus Wh (≈ 20–25 Wh) y que el total sigue subiendo más lento. |
| **45–70 s** | «Mire la línea del umbral en el gráfico de energía. El salón sigue encendido… y al llegar al presupuesto aparece **una sola** alerta, visible, sin repetirse.» | Señalar la línea de umbral. Hacia los **55–60 s** aparece la banda «Presupuesto alcanzado». Dejarla 5 s en pantalla. |
| **70–80 s** · Recuperación | «Si se corta el navegador o alguien recarga la página…» *(F5)* «…el estado vuelve igual, porque lo calcula y guarda el servidor.» | Pulsar **F5**. Se ven el mismo acumulado (sigue avanzando), la misma alerta y la sala apagada. |
| **80–90 s** · Cierre | «Pulso Energético apunta al ODS 7, energía asequible y eficiente. Nuestra hipótesis, por validar en un piloto, es que apagar a tiempo las salas vacías reduce kWh y emisiones. Siguiente etapa: hardware real y aviso por Discord. Gracias.» | Dejar la pantalla con la alerta visible y el banner «Datos simulados». |

## Plan B (sin explicar el fallo, siempre hacia adelante)
| Falla | Qué hacer | Frase puente |
|---|---|---|
| La C2 (EC2) no carga o da error 400 | Cambiar a la pestaña **C1** (localhost), ya abierta y preparada. | «Lo mostramos en local, que es donde correrá sin Internet.» |
| La UI se cuelga o un clic no responde | Pulsar F5 una vez. Si no se recupera en 3 s, pasar a **C3** desde el mismo tramo. | «Les muestro el mismo recorrido grabado.» |
| La alerta no aparece antes de los 68 s | Seguir con el refresco. Si al 80 s tampoco hay alerta, mostrar la captura de la alerta (C3). | «Con el presupuesto del día, la alerta salta así.» |
| No hay red ni proyector compatible | Video C3 en MP4 desde el pendrive. | — |
| Se olvidó ▶ Reproducir | Pulsarlo en cuanto se note. El recorrido se corre unos segundos: abreviar el tramo de 20–32 s. | — |

## Reiniciar el ensayo (menos de 10 s)
```sh
BASE_URL=http://localhost:8080 ./scripts/deploy-ec2.sh reset-demo   # C1
ssh -i labsuser.pem ubuntu@<IP> './deploy-ec2.sh reset-demo'        # C2
```
Después: **F5** → ▶ Reproducir. El comando cierra el ensayo anterior, abre uno nuevo en pausa con las zonas apagadas y fija el umbral en 150 Wh. Para volver al presupuesto de la semilla: `BUDGET_KWH=0.6`. ⚠ `reset-demo` todavía no se ha ejecutado: probarlo en el primer ensayo.

## Fuera del guion (no mostrar hoy)
Puente Alto, la comparación de jornada (P2), el reporte de voz, Discord, Wokwi, el hardware, el botón ×300, «Siguiente franja» y el análisis ODS 13 (P3). Solo se nombran como «siguiente etapa» en el cierre.
