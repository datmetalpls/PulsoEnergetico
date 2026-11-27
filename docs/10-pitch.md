# Pitch de Pulso Energético: guion, apoyo visual y preguntas

Presentación (10 láminas, identidad sello latino, con notas del orador): **https://claude.ai/artifact/HsaM5xnxzqCwTpMVhmXbCu**. Se descarga como PPTX o PDF desde *Share › Export*. Es privada hasta que se comparte desde *Share*.
Fuentes de las láminas: `docs/pitch/deck/`.

> Regla de oro: los datos son **simulados** y los beneficios (ahorro y clima) son **hipótesis por validar**. No digan cifras que no estén aquí.

---

## 1. Pitch de 90 segundos (versión principal)

Láminas: 1 Portada → 2 Problema → 4 Solución → 5 Demo → 6 Ahorro → 10 Cierre.

| Tiempo | Lámina | Qué se dice (texto exacto) | Qué se hace |
|---|---|---|---|
| 0:00–0:08 | 1 · Portada | «Somos [equipo], de Ecuador y Chile. Esto es **Pulso Energético**: la energía de tu sede, a la vista». | Sonrisa y mirar al jurado. |
| 0:08–0:20 | 2 · Problema | «Quien abre y cierra una sede vecinal no sabe qué luz quedó encendida ni cuánto lleva gastado. Lo descubre cuando llega la boleta, y ahí ya no puede hacer nada». | — |
| 0:20–0:30 | 4 · Solución | «Pulso responde tres preguntas en una pantalla: **qué está encendido, cuánto llevo y cuánto me falta** para el límite». | Señalar las tres tarjetas. |
| 0:30–1:05 | 5 · Demo **en vivo** | «Día: abrimos la sede y encendemos el salón y la sala, 240 vatios. Tarde: terminó la reunión, apagamos la sala vacía y baja a 160; su energía queda guardada. Noche: llegamos al presupuesto y aparece **una sola alerta**, que también llega al Discord del equipo». | Navegador → ☰ → Modo presentación → «Siguiente paso» ×3. La alerta llega a los ~35 s. |
| 1:05–1:20 | 6 · Ahorro | «Una decisión pequeña, repetida cada día: apagar la sala vacía ahorra **0,240 kWh por jornada** en nuestra sede de prueba. Es una estimación que queremos validar en una sede real». | Volver a las láminas. |
| 1:20–1:30 | 10 · Cierre | «Pulso Energético: la energía de tu sede, a la vista. Gracias». | Pausa de 1 s. Fin. |

**Truco de tiempo:** pulsen el paso 3 (Noche) **mientras dicen la frase de la Tarde**. Así la alerta aparece justo cuando terminan de hablar.

---

## 2. Versión de 3 minutos (si dan más tiempo)

Láminas 1 a 10 en orden. Cada lámina tiene sus tiempos en las **notas del orador**:
- 1 Portada, 0:00–0:10
- 2 Problema, 0:10–0:25
- 3 Usuario, 0:25–0:40
- 4 Solución, 0:40–0:55
- 5 Demo, 0:55–1:30
- 6 Ahorro, 1:30–1:45
- 7 Cómo funciona, 1:45–2:05
- 8 Por qué confiar, 2:05–2:20
- 9 Lo que viene, 2:20–2:40
- 10 Cierre, 2:40–3:00

---

## 3. Antes de subir al escenario (checklist, 10 min antes)

- [ ] `docker compose up -d` y luego http://localhost:8080 responde. **Con el Wi-Fi apagado**, si la sala no tiene red.
- [ ] Pestaña 1: presentación en modo *Present*. Pestaña 2: la app con **operador demo**, en Cuenca › Centro Comunitario.
- [ ] Ensayo limpio: ☰ → Iniciar ensayo, y dejar el modo presentación listo en el paso 1 sin pulsarlo.
- [ ] Presupuesto restaurado a 0,60 kWh desde el ensayo anterior.
- [ ] Zoom del navegador en 100–110 % y modo oscuro del sistema irrelevante, porque la app tiene sus temas.
- [ ] Notificaciones del sistema silenciadas. Discord abierto en el teléfono para mostrar el mensaje, si conviene.
- [ ] **Video de respaldo** (`docs/video/Pulso_Energetico_demo_respaldo_1080p.mp4`, 89 s, sin audio) en el escritorio, en un pendrive y en el drive del equipo.
- [ ] Cronómetro visible para quien presenta.

## 4. Plan B (si algo falla en vivo)

| Falla | Qué hacer | Qué decir |
|---|---|---|
| La app no carga | Mostrar la lámina 5 (captura) o el video de respaldo | «Les muestro la grabación del mismo recorrido». |
| La alerta tarda | Seguir hablando de la lámina 6. Llega a los ~35 s | — |
| Sin Internet | La app funciona igual; Discord queda en «Simulación local» | «Sin red, el aviso queda en la pantalla». |
| AWS caído | Usar la demo local | No mencionarlo, salvo que pregunten. |

## 5. Preguntas probables del jurado (respuestas cortas)

1. **¿Los datos son reales?** No: hoy son simulados y la pantalla lo dice. El siguiente paso es una Raspberry Pi Pico en Wokwi y luego una Zero W midiendo una zona real.
2. **¿Cómo calculan la energía?** En el servidor, con una sola regla: potencia anterior × segundos ÷ 3600. Las lecturas repetidas no suman dos veces y un corte de conexión no inventa consumo.
3. **¿Por qué no apagan automáticamente?** Porque la decisión es de la persona. Puede haber una actividad que siga. Pulso avisa; no corta.
4. **¿Cuánto ahorra de verdad?** En la sede simulada, 0,240 kWh por jornada por apagar la sala vacía. El ahorro real es la hipótesis que validaría el piloto.
5. **¿Y el clima (ODS 13)?** Es una hipótesis: menos energía desperdiciada puede significar menos emisiones, según la matriz eléctrica de cada país. No lo afirmamos sin medir.
6. **¿Es seguro?** Hay permisos de operador y observador, protección CSRF, límite de intentos de inicio de sesión y cuatro auditorías sin fallos críticos. Los secretos van en `.env`, nunca en el repositorio.
7. **¿Escala?** Corre en Docker: un portátil, una EC2 pequeña o el servidor de un municipio. Cada sede guarda su propio estado.
8. **¿Por qué Ecuador y Chile?** Somos un equipo de ambos países, y cada localidad tiene su propia tensión (120 V y 220 V), su zona horaria y su presupuesto.

## 6. Apoyo visual

- **Video de respaldo (89 s, 1080p, sin audio):** `docs/video/Pulso_Energetico_demo_respaldo_1080p.mp4`. Recorre portada → ingreso → Día, Tarde y Noche → alerta → reporte a Discord → ahorro → refresco → mensajes en el canal de Discord → cierre. Se puede narrar encima con el guion de la sección 1.

- **Presentación:** el enlace de arriba (10 láminas, 16:9, sello latino, Fraunces y DM Sans).
- **Portada para video o redes:** `design/brand/sello-latino/vector/aplicacion-16x9.png`.
- **Imagen para compartir:** `frontend/public/og-image-1200x630.png`.
- **Capturas:** `docs/readme/` (presentación, login, sede, móvil).
- **Informe para el equipo:** `docs/informe/Pulso-Energetico-Informe-Equipo.pdf`.

## 7. Por completar antes de presentar

- [ ] Nombres, país y rol de cada integrante (láminas 1 y 10).
- [ ] Duración del piloto en la lámina 9: «[__ semanas]».
- [ ] Si tienen un dato real de una sede o municipio para la lámina 2, con su fuente. Si no, se deja sin cifra.
