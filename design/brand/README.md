# Pulso Energético — Identidad oficial vigente

> **Decisión oficial (2026-11-27):** La identidad oficial de **Pulso Energético** es **`sello-latino`** (**Sello Cartel Latino**, ubicado en [`design/brand/sello-latino/vector/`](./sello-latino/vector/)).
> Las propuestas anteriores **`v1`**, **`v2`** y **`v3`** quedan registradas exclusivamente como **exploraciones archivadas** de referencia histórica y no deben utilizarse como marca activa de la aplicación.

## Identidad oficial (`sello-latino`)

- **Vectores oficiales:** [`sello-latino/vector/`](./sello-latino/vector/) (`sello-completo*.svg`, `sello-simple*.svg`, `sello-mini*.svg` en variantes petróleo, crema, dorado y negro; [`NOTAS.md`](./sello-latino/vector/NOTAS.md) y lámina de aplicación [`aplicacion-16x9.png`](./sello-latino/vector/aplicacion-16x9.png)).
- **Tokens y tipografía:** [`tokens.css`](./tokens.css) (`--pe-petroleo`, `--pe-crema`, `--pe-dorado`, verdes ODS 7, alerta) y [`fonts/`](./fonts/) (**Fraunces** y **DM Sans**, licencia SIL OFL 1.1).
- **Integración en el frontend (`frontend/`):**
  - Encabezado con `sello-mini.svg` junto a «Pulso Energético» en Fraunces (≤ 2 líneas en 390 px).
  - Login editorial con `sello-completo.svg`, kicker «HACKATÓN ECUADOR × CHILE», titular en Fraunces y bajada «La energía de tu sede, a la vista.».
  - Favicon SVG/PNG desde `sello-mini`, `apple-touch-icon-180.png` desde `sello-simple` sobre petróleo y `og-image-1200x630.png` recompuesta desde `aplicacion-16x9`.
  - Temas Día, Tarde y Noche tematizados con `--pe-*` en cumplimiento WCAG AA (≥ 4,5:1 texto, ≥ 3:1 UI).
  - Panel de Modo presentación y tarjeta de ahorro con `sello-simple` (y `sello-completo` pequeño en la lámina final de Noche).

---

## Exploraciones archivadas (v1, v2 y v3)

La documentación original de `v1` (Concepto 01 / Pulso-rayo), junto con las carpetas `v2/` y `v3/` («Casa que late»), se conserva a continuación únicamente como archivo histórico.

### Archivo histórico — Identidad corporativa v1.0

## Recomendación

**Concepto 01 / Pulso-rayo.** Un pulso angular forma un rayo: energía que se puede seguir. Su bloque compacto se reconoce en 32 px y admite una sola tinta; no sugiere sensores cardíacos, generación solar ni beneficios ambientales medidos. Unir el símbolo al nombre en las primeras apariciones.

- `concepts/concepto-1.svg`: pulso-rayo; recomendado.
- `concepts/concepto-2.svg`: conexión compartida; enchufe con onda, dos localidades y una lectura común.
- `concepts/concepto-3.svg`: luz con límite; sol abierto con línea de umbral y margen disponible.

La inspiración Cuypleto se limita al lenguaje editorial: petróleo, crema, dorado, serif/sans y chips de país. No se copiaron dibujos, fotografías, logotipos ni composiciones originales. Los chips usan banderas simplificadas sin escudo y nombres visibles; no representan asociación oficial con gobiernos ni ONU.

## Archivos listos

`logo-horizontal.svg`, `logo-vertical.svg`, `isotipo.svg` son las versiones de color sobre crema o blanco, con fondo transparente. Cada una tiene variantes `-negativo.svg` (sobre petróleo), `-negro.svg` y `-blanco.svg`; las dos monocromas usan un calado transparente en el símbolo. Son **12 maestros SVG** con texto convertido a trazados, sin fuentes externas ni imágenes raster incrustadas. El nombre accesible y la explicación permanecen en `<title>`/`<desc>`.

- `favicon.svg`, `favicon-32.png` (32×32).
- `apple-touch-icon.svg`, `apple-touch-icon-180.png` (180×180, fondo crema opaco).
- `og-image-1200x630.svg` y `.png` (1200×630, kicker «HACKATÓN ECUADOR × CHILE · ODS 7»).
- `logo-horizontal-1x.png` (720×160) y `logo-horizontal-2x.png` (1440×320), RGBA transparente.
- `manual.html`, `manual.pdf`: mini manual de una página A4. Abrir HTML en navegador e imprimir con colores de fondo habilitados y escala 100 %; CSS ya define el tamaño y márgenes.
- `preview-manual.png`, `preview-kit.png`, `preview-kit.html`: evidencias visuales.
- `tokens.css`, `tokens.json`, `contrast-report.json`: paleta y pares permitidos con ratios WCAG AA calculados.
- `INTEGRACION.md`: destinos exactos y propuesta para Antigravity, sin aplicar cambios.

Los SVG tienen área de seguridad incorporada (24 u alrededor del símbolo de 112 u); respetar el viewBox. El favicon es la excepción sin margen adicional. Mínimos: horizontal 220 px/58 mm; vertical 144 px/38 mm; isotipo 32 px/8,5 mm. No animar el logo como alarma: reservar las alertas al contenido operativo.

## Fuentes y licencia

**Fraunces**, titulares y wordmark: `fonts/Fraunces.woff2`, fuente variable original `fonts/Fraunces.ttf`; licencia `fonts/Fraunces-OFL.txt` (SIL OFL 1.1). Peso recomendado 600–700; logo trazado a 650, tamaño óptico 24.

**DM Sans**, interfaz: `fonts/DMSans.woff2`, fuente variable original `fonts/DMSans.ttf`; licencia `fonts/DMSans-OFL.txt` (SIL OFL 1.1). Pesos 400, 500, 600 y 700. Usar cifras tabulares y unidades legibles.

Ambas se descargaron del repositorio oficial de Google Fonts y se empaquetaron localmente; los WOFF2 son conversiones completas, sin renombrado ni cambios de diseño. Conservar los avisos OFL al distribuir. No usar Georgia/Arial del sistema como archivos redistribuibles: solo son referencias históricas o fallback.

Fuentes primarias: [Fraunces y OFL](https://github.com/google/fonts/tree/main/ofl/fraunces), [DM Sans y OFL](https://github.com/google/fonts/tree/main/ofl/dmsans). Archivos TTF originales tomados de esas carpetas; WOFF2 generado con FontTools/Brotli. No hay cargas de red en el manual.

## Verificación reproducible

```sh
python3 design/brand/build_brand.py
python3 design/brand/render_exports.py
```

El primer script requiere FontTools y valida XML, ausencia de `<text>` en SVG y 52 pares AA (≥4,5:1), más controles de negro/blanco y dorado/crema. `render_exports.py` usa Pillow y el Google Chrome instalado en macOS para exportar todos los PNG, captura del manual, PDF y hoja de revisión; no instala dependencias ni toca la app. Las fuentes WOFF2 ya están entregadas: no es necesario reconvertirlas.

`QA.md` reúne los resultados observados y los límites de la revisión. El color oficial de ODS 7 es amarillo; el verde de este kit corresponde al estado operativo propio de la app. Los beneficios climáticos siguen siendo hipótesis por validar.

## Cierre para memoria compartida

Se revisaron `Cerebro/Memoria-de-trabajo.md` y el resumen semanal 2026-W48. La restricción de este encargo permite escribir exclusivamente en `design/brand/`; por ello Claude debe registrar el cierre en Obsidian y enlazar este kit: concepto 01 recomendado, fuentes OFL locales, 52 pares AA, SVG trazados y QA visual. Pendiente: integración por Antigravity y aprobación final del equipo, sin commits de este trabajador.
