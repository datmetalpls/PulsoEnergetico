# Ficha — Pulso Energético (hackatón Chile–Ecuador)

**Usuario.** La persona encargada de un recinto comunitario, como una sede vecinal o un centro comunitario, que abre, opera y cierra el local sin formación técnica en energía.

**Problema.** Esa persona no sabe qué carga está encendida, cuánta energía se ha consumido en la jornada ni cuánto falta para llegar al presupuesto. Hoy descubre el exceso cuando llega la boleta.

**Decisión que habilita.** Le permite decidir en el momento, por ejemplo: «Si apago la sala de reuniones, que ya quedó vacía, ¿cuánto me ahorro y cuánto margen me queda?». El producto responde tres preguntas:
1. ¿Qué está encendido? Cada zona muestra luz, icono y texto.
2. ¿Cuánto llevo? Energía acumulada en Wh o kWh, junto a la potencia actual en W.
3. ¿Cuánto me falta? Energía restante y tiempo estimado hasta el límite con la potencia actual. Si se apaga todo, la pantalla muestra «Consumo detenido».

**Métrica de éxito (demo).** Un jurado sin contexto responde las tres preguntas en menos de 10 s mirando la pantalla. La prueba de aceptación (2 W → 0,010 Wh a 18 s → 0,020 Wh a 36 s de consumo, una sola alerta) se cumple con una tolerancia de una muestra.
**Métrica de éxito (piloto, por validar).** Reducción del consumo de iluminación evitable, como salas vacías encendidas, medida en kWh por jornada. Es una **hipótesis**.

**ODS.** El ODS 7 (energía asequible y eficiente) es el principal. El ODS 13 orienta la exploración de decisiones según las condiciones ambientales. Los beneficios climáticos se presentan como **hipótesis por validar**, no como resultados.

**Alcance v0.1 (demo local).** Dos localidades: Cuenca (Ecuador) y Puente Alto (Chile). Cada una tiene un banco de pruebas de 5 V y una sede ficticia con dos zonas de iluminación. Los datos son **simulados** y están etiquetados en pantalla. La demo usa un simulador local, la importación de lecturas al estilo Wokwi, un aviso del navegador que imita el buzzer, un reporte de voz y una vista previa de Discord con la etiqueta «Simulación local». Quedan fuera el hardware real, el envío a Discord y AWS.
