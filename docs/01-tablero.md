# Tablero — Pulso Energético (ajuste de alcance, 2026-11-27: entrega en 1 día)

Leyenda: ☑ ejecutado y verificado (con comando y salida en `docs/05-resultados.md`) · ◐ en curso · ☐ pendiente · ⚠ propuesto o no ejecutado · ✂ recortado (siguiente etapa)
**Contrato v0.1 CONGELADO** (`docs/02-contrato.md`, `contracts/*.json`). Solo Claude puede cambiarlo y debe avisar a los dos agentes.
Regla: no se abre un nivel hasta cerrar el anterior con su prueba.

## Propiedad de archivos
| Ruta | Responsable |
|---|---|
| `docs/01-tablero.md`, `docs/02-contrato.md`, `docs/05-resultados.md`, `contracts/`, `README.md` | Claude (integrador) |
| `docs/06-plan-aws.md`, `docs/07-riesgos.md`, `docs/08-guion-90s.md`, `scripts/deploy-ec2.*`, `scripts/shutdown-ec2.md` | Claude-docs (worker) |
| `backend/**`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `.dockerignore`, `.gitignore` | Codex |
| `frontend/**`, `design/**` | Antigravity |

## Prioridad 1: recorrido mínimo de extremo a extremo (sin esto no hay demo)
| # | Tarea | Resp. | Criterio de aceptación (prueba) | Estado |
|---|---|---|---|---|
| A1 | Ficha, contrato, ejemplos JSON y wireframe | Claude | `docs/00..03`, `contracts/` en el commit f434541 | ☑ |
| P1.1 | Sede Cuenca con salón principal y sala de reuniones; on/off por zona; W y Wh calculados en el backend | Codex | prueba Django: apagar la sala deja 0 W, conserva sus Wh y el salón sigue consumiendo | ◐ (Codex informa 13 pruebas OK, sin auditar) |
| P1.2 | Umbral con alerta única y visible; prueba del banco (2 W → ≈0,010 Wh a 18 s → 0,020 Wh a 36 s, apagado que conserva el acumulado) | Codex | prueba de aceptación automática y ejecución reproducida por Claude | ◐ |
| P1.3 | UI: control por zona, 3 cifras, gráfico W y gráfico Wh con línea de umbral, banda de alerta y «Datos simulados» | Antigravity | build local y verificación en el navegador por Claude | ◐ |
| P1.4 | Recuperar el estado al refrescar (GET state desde el backend) | Codex + Antigravity | refrescar el navegador muestra el mismo acumulado | ☐ |
| P1.5 | `docker compose up --build` desde cero; segundo arranque SIN Internet; `seed_demo` idempotente | Codex → Claude verifica | comando y salida registrados | ◐ (Codex: build + curl 200; arranque sin red pendiente) |
| P1.6 | Prueba de aceptación registrada en `docs/05-resultados.md` (automática / navegador / pendiente) | Claude | documento con evidencia | ☐ |

## Prioridad 2: solo después de cerrar P1
| # | Tarea | Resp. | Criterio | Estado |
|---|---|---|---|---|
| P2.1 | Puente Alto con estado independiente | Codex + Antigravity | misma prueba con las localidades intercambiadas | ☐ (el código existe, sin verificar) |
| P2.2 | Comparación «Sala encendida» vs «Sala apagada al terminar la reunión» | Codex + Antigravity | diferencia = 80 W × (duración − fin de reunión) / 3600 | ☐ |

## Respaldo y entrega
| # | Tarea | Resp. | Criterio | Estado |
|---|---|---|---|---|
| R1 | Demo local sin Internet (capa 1) | Claude | arranque sin red verificado | ☐ |
| R2 | Plan y script de EC2 única, más apagado (capa 2) | Claude-docs → Claude ejecuta si hay tiempo | `scripts/deploy-ec2.*` y `docs/06` | ◐ |
| R3 | Video y capturas guardados fuera del laboratorio (capa 3) | Claude + equipo | archivo en el portátil y en el drive del equipo | ☐ |
| R4 | Registro de riesgos | Claude-docs | `docs/07-riesgos.md` | ◐ |
| R5 | Guion de 90 s y ensayo | Claude-docs (guion) + Claude (ensayo) | `docs/08-guion-90s.md` y tiempo medido | ◐ |

## ✂ Recortado: siguiente etapa (no se implementa ni se presenta hoy)
Reporte de voz, vista previa de Discord, importación de Wokwi, hardware físico (Pico/Zero W), roles complejos, avance acelerado (×60/×300), análisis ODS 13, CI de GitHub Actions y despliegue gestionado en AWS. El código ya escrito de estas funciones se conserva, pero queda **fuera del recorrido de la demo** y sin verificar; donde se vea en la interfaz, se oculta o se etiqueta «Siguiente etapa».
