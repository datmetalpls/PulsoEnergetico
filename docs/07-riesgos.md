# Registro de riesgos — Pulso Energético (entrega en 1 día)

**Tres capas de demo.** Las mitigaciones remiten a ellas:
- **C1 · Local sin Internet:** `docker compose up -d` en el portátil, con la imagen ya construida. Es la demo **principal**.
- **C2 · EC2:** `docs/06-plan-aws.md`. Es opcional y sirve para mostrar que corre en la nube.
- **C3 · Video y capturas:** el recorrido de 90 s grabado más las capturas clave, guardados **fuera del laboratorio** (en el portátil, el drive del equipo y un pendrive).

Estado: ☐ abierto · ◐ mitigación en curso · ☑ mitigado y verificado.

| # | Riesgo | Mitigación | Responsable | Estado |
|---|---|---|---|---|
| 1 | **Alcance excesivo** (no se cierra P1) | Solo P1 entra a la demo y P2 se aborda después de cerrar P1. P3 queda en «Siguiente etapa» (`docs/01-tablero.md`). El guion usa solo P1. | Claude (integrador) | ◐ |
| 2 | **Fallo en vivo** (bug, la UI se cuelga, falla un clic) | Ensayar el guion 2 veces. `reset-demo` deja la demo lista en menos de 10 s. Si falla C1 o C2, se pasa al video **C3** sin explicar el fallo (plan B en `docs/08`). | Claude + presentador | ☐ |
| 3 | **La IP cambia al reiniciar** (End Lab o Stop/Start) | Usar `./deploy-ec2.sh refresh-ip`, que reescribe ALLOWED_HOSTS. La URL de C2 se actualiza al final y nunca se imprime en material fijo. Siempre se puede caer a C1. | Claude-docs (script) / Claude (ejecuta) | ◐ |
| 4 | **Expira la sesión de 4 h del laboratorio** justo en la presentación | Iniciar la sesión del laboratorio **menos de 1 h antes** de presentar y anotar la hora de expiración. Si quedan menos de 30 min, se presenta en **C1**. Los datos se conservan en EBS. | Claude | ☐ |
| 5 | **RAM insuficiente** (t3.micro, 1 GiB) | No se compila en la EC2: la imagen viene del portátil. Swap de 2 GB y 2 workers de gunicorn. Si hay OOM, cambiar a t3.small (Stop → Change type → Start → `refresh-ip`). | Claude-docs | ◐ |
| 6 | **Servicio no disponible en el laboratorio** (tipo de instancia, AMI, puerto) | El plan usa solo EC2, EBS y un grupo de seguridad. Las alternativas son 22.04 si falta la AMI 24.04, t3.small si falta t3.micro, y el puerto 80 si se bloquea 8080. Si EC2 no está disponible, se omite C2 y se presenta C1 + C3. Lista «por verificar» en `docs/06`. | Claude-docs | ◐ |
| 7 | **Pérdida de la máquina** (se pierde o falla el portátil) | El repo ya está en GitHub, con push frecuente del integrador. C3 queda en el drive del equipo. `pulso-images.tar.gz` y `.env.ec2` se guardan en un pendrive, cifrados o fuera de git. Hay una segunda persona capaz de levantar C1 (README del backend). | Claude + equipo | ☐ |
| 8 | **El contrato cambia a mitad de camino** | El contrato v0.1 está **congelado**: solo el integrador lo cambia y avisa a los dos agentes. Las excepciones van a `backend/CONTRACT-NOTES.md`. El guion depende solo de `state`, zonas y alerta. | Claude (integrador) | ☑ (congelado) |
| 9 | **Lecturas y alertas duplicadas** (dos pestañas, refresco, reintentos) | `reading_id` determinista: un duplicado devuelve `200 duplicate` sin integrar. Una sola alerta por sesión (`alert_fired`). El avance ocurre en el servidor con `select_for_update`. Prueba P1.2 y refresco en el guion (70–80 s). | Codex | ◐ (pruebas sin auditar) |
| 10 | **Cae el Internet de la sala** | **C1** funciona sin red; falta verificar el segundo arranque sin red (P1.5 / R1). El video C3 está guardado **en local**, no solo en el drive. | Claude | ☐ |
| 11 | **Presentar en otro equipo** (sin Docker, otra resolución, proyector) | Llevar el video C3 en MP4 en el pendrive, y C2 desde cualquier navegador si el laboratorio está activo. Probar el zoom del navegador a 1280×720. No depender de audio ni de permisos de notificación. | Presentador | ☐ |
| 12 | **Avisos de vulnerabilidades de npm** (Codex informó 43 en el build del frontend) | Son dependencias de **build**. La imagen final no incluye `node_modules`, solo la SPA estática. No ejecutar `npm audit fix --force` hoy porque puede romper Angular. Se registran como deuda para la siguiente etapa y se revisan las de severidad crítica en runtime, si las hay. | Antigravity (revisa) / Claude (decide) | ☐ |
| 13 | **Secretos filtrados** (`.env` en git o en capturas) | `.gitignore` excluye `.env`, que se copia solo por scp con `chmod 600`. No mostrar la terminal con `.env` en el video. Las contraseñas de la demo no son las de `.env.example`. | Todos | ◐ |
| 14 | **Costo del laboratorio** (50 USD totales) | Anotar «Used $X of $50» antes y después de cada sesión. Usar una sola t3.micro, sin IP elástica, ALB ni NAT. Terminar la instancia al final (`scripts/shutdown-ec2.md`). Nunca Reset. | Claude | ☐ |
| 15 | **Contraseñas o `POSTGRES_PASSWORD` cambiadas después del primer arranque** (error 403 en el login o la BD no conecta) | Definir los valores definitivos antes del primer `up`, porque `seed_demo` no sobrescribe contraseñas y PostgreSQL fija la suya al crear el volumen. | Claude-docs | ◐ |
