# Decisiones mínimas para v0.1

- Sesión inicial: `running`, pausada, controles apagados y 0 Wh; representa «sin iniciar» sin añadir un tercer estado al contrato.
- Cierre: no existe ruta de cierre en §6. Crear un ensayo cierra el anterior tras ponerlo al día, congela sus valores y conserva su reporte. El respaldo crea sesiones ya cerradas sin tocar las activas.
- Importación: el primer `instant` importado de la sesión define `telemetry_origin` (t=0). No se compara contra la fecha real de creación; así el fixture histórico integra sus tres intervalos. El lote conserva el orden recibido y los valores negativos respecto del origen se clasifican como fuera de orden cuando hay referencia. Se pausa el simulador al importar para no mezclar relojes automáticamente.
- Respuesta de lecturas: lote totalmente duplicado devuelve `200 {"status":"duplicate"}`, excepción explícita a «todas las escrituras devuelven state»; lote con fuera de orden devuelve state y 202. No se añaden contadores al JSON de state.
- `GET /api/localities`: lista `[{slug,name,country,timezone,sites:[{slug,name,kind,fictitious,budget_kwh_day,sample_interval_s}]}]`, compatible con `LocalityWithSites[]` del frontend; el contrato no incluye un fixture para esa ruta.
- `on_seconds` del reporte es el máximo entre zonas (tiempo efectivo de la carga más utilizada), para no sumar segundos simultáneos como si fueran duración de ensayo. El detalle por zona está en state.
- `/advance` acepta segundos enteros y emite una última lectura parcial si el avance no cae sobre el muestreo; así procesa exactamente N segundos. Los ticks normales mantienen el muestreo de 1/60 segundos. Los cambios inmediatos usan sufijo determinista `:change:N` porque el id de una muestra programada en el mismo t no puede reutilizarse para otra potencia.
- Un corte explícito siempre crea Gap al reconectar, incluso si dura menos de tres muestras. El exceso de 120 ticks por petición tampoco atribuye energía y genera Gap al siguiente dato.
- «Siguiente franja» después de noche salta a las 08:00 del día siguiente; solo mueve scenario_offset_s. Velocidad de sede: 60 o 300; banco: 1.
- El presupuesto nuevo se aplica también a la sesión activa; no borra una alerta anterior. Los parámetros eléctricos se validan contra el voltaje y la corriente nominal/máxima de la zona.
- Auditoría: cada escritura API exitosa y comandos de carga registran AuditEvent; nunca se registran contraseñas. Los avances por polling son cambios internos bajo el bloqueo de la sesión.
- Docker permite un index de reemplazo si Angular falta o falla; el stage escribe una advertencia. El job Angular de CI siempre exige una compilación real. Compose lee `.env.example` y superpone `.env` si existe; los valores de demostración están únicamente en `.env.example`.
