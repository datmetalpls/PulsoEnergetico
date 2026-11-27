# Tablero — Pulso Energético

Leyenda de estado: ☐ pendiente · ◐ en curso · ☑ hecho y verificado · ⚠ propuesto o no ejecutado

## Propiedad de archivos
| Ruta | Responsable |
|---|---|
| `docs/`, `contracts/`, `README.md`, `scripts/demo-check.sh` | Claude |
| `backend/**`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.github/workflows/**`, `.dockerignore` | Codex |
| `frontend/**`, `design/**` (wireframes y prototipo) | Antigravity |

Nadie edita fuera de su ruta. Los cambios al contrato se piden a Claude.

## Tareas
| # | Tarea | Resp. | Depende de | Criterio de aceptación | Estado |
|---|---|---|---|---|---|
| A1 | Ficha, contrato, ejemplos JSON, wireframe principal | Claude | — | `docs/00..03`, `contracts/*.json` | ☑ |
| B1 | Wireframes de escritorio y móvil, más recorrido navegable de día, tarde y noche con 6 estados | Antigravity | A1 | `design/` y la ruta `/?mock=1` recorren los estados inicial, apagada, encendida, umbral, sin conexión y reporte | ☐ |
| B2 | Interfaz Angular + Bootstrap alimentada con los ejemplos del contrato | Antigravity | A1 | `npm run build` genera `frontend/dist/pulso/browser`; la vista funciona con fixtures | ☐ |
| C1 | Modelos, migraciones, semilla idempotente y usuarios | Codex | A1 | `migrate` + `seed_demo` dos veces sin duplicar | ☐ |
| C2 | Motor de energía, simulador, alertas, duplicados y gaps | Codex | C1 | pruebas de §8 en verde | ☐ |
| C3 | API, permisos, CSRF y reporte con comparación | Codex | C2 | respuestas iguales en forma a `contracts/*.json` | ☐ |
| C4 | Docker Compose con mismo origen, CI y `.env.example` | Codex | C3, B2 | `docker compose up --build` deja la demo en http://localhost:8080 | ☐ |
| C5 | Conexión de la interfaz con la API real | Antigravity | C3 | refresco y segunda pestaña muestran el mismo ensayo | ☐ |
| D1 | Integración, prueba de aceptación, ensayo de 90 s y respaldo local | Claude | C4, C5 | `docs/05-resultados.md` con lo observado | ☐ |
| D2 | Plan para AWS (solo documento) | Claude | — | `docs/06-plan-aws.md` | ☐ |
