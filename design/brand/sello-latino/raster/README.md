# Sello Cartel Latino Artesanal — Variantes raster (`sello-latino/raster`)

## Estado actual: bloqueado por cuota del generador de imágenes (`HTTP 429`)

No se pudieron generar las 3 variantes raster de alta resolución (`2048×2048`+) ni la lámina comparativa `sello-variantes.png` porque la herramienta `generate_image` agotó su cuota de modelo tras las exploraciones previas (`exploracion-1` a `exploracion-5`):

- **Intento 1** (`03:28:03 -03:00` / `06:28:03 UTC`): `ResourceExhausted (HTTP 429) — You have exhausted your capacity on this model. Your quota will reset after 2h32m34s.`
- **Reintento tras espera de 15 s** (`03:30:40 -03:00` / `06:30:40 UTC`): `ResourceExhausted (HTTP 429) — You have exhausted your capacity on this model. Your quota will reset after 2h30m3s.`

Por política de veracidad, no se sustituyeron las ilustraciones artesanales por gráficos sintéticos ni se fabricó `sello-variantes.png`. El reinicio de cuota reportado ocurre aproximadamente a las **06:00 `-03:00` (`09:00 UTC`)**.

---

## Base de referencia inspeccionada

- Imagen base: [`../../v2/exploracion-agy/exploracion-3.png`](../../v2/exploracion-agy/exploracion-3.png) (`1024×1024`)
- Paleta oficial ([`../../tokens.css`](../../tokens.css)):
  - Petróleo: `#06323B`
  - Crema: `#FFF1D9`
  - Dorado ODS 7: `#FFC04C`
  - Verde ODS 7: `#176B46`

### Notas de simetría y trazo observadas en `exploracion-3.png` para el vector/refinamiento
- El núcleo del sello funciona muy bien: disco verde `#176B46` con rayos radiales dorados `#FFC04C` y el rayo-pulso dorado contorneado en crema `#FFF1D9` (con 4 remates/puntas cardinales: arriba, abajo, izquierda, derecha).
- Las grecas escalonadas tipo chakana (N/S/E/O) y los rulos crema con tres gotas doradas en los 4 ejes cardinales anclan la simetría radial de 4 cuadrantes.
- En el original raster hay leve textura granulada y pequeñas asimetrías orgánicas en las hojas verdes de los cuadrantes; al refinar en alta resolución o vectorizar conviene espejar exactamente los 4 cuadrantes de flora y grecas manteniendo el rayo-pulso central asimétrico pero equilibrado en su caja central.

---

## Prompts preparados para ejecutar tras el reinicio de cuota (`2048×2048`+)

### Variante (a) — Fiel a la original pulida
- **Archivo objetivo**: `sello-a-fiel.png`
- **Prompt**:
  > Edit and refine `/Users/dmp/Hackathon/Proyecto a ejecutar/design/brand/v2/exploracion-agy/exploracion-3.png` at high resolution (2048x2048 or higher, 1:1 square). Keep the exact composition: solid deep petrol teal (`#06323B`) background, double circular outer ring in warm cream (`#FFF1D9`) and emerald green (`#176B46`), stepped Andean chakana frets at top/bottom/left/right, mirrored botanical leaf flourishes and cream scrolls in the four quadrants, radial golden burst lines inside the emerald center disc, and the bold golden amber (`#FFC04C`) and cream heartbeat pulse-lightning bolt at the center. Make linework razor-sharp and vector-clean, enforce precise 4-quadrant geometric symmetry on all ornaments and rings, remove background grain/noise, and keep pure flat-print craft clarity. Strictly NO text, NO letters, NO numbers, NO words anywhere.

### Variante (b) — Austera y legible a `128 px`
- **Archivo objetivo**: `sello-b-austero-128.png`
- **Prompt**:
  > Create a cleaner, simplified high-resolution (2048x2048, 1:1 square) edition of `/Users/dmp/Hackathon/Proyecto a ejecutar/design/brand/v2/exploracion-agy/exploracion-3.png` engineered to remain crisp and readable down to 128x128 px. Same `#06323B` petrol teal background, `#FFF1D9` cream, `#FFC04C` golden amber, and `#176B46` ODS 7 emerald green palette. Enlarge the central emerald disc and make the golden-and-cream heartbeat pulse-lightning bolt significantly bolder and thicker with clean, simple silhouette edges. Reduce the outer decorative ring to minimal, chunky geometric elements: bold stepped Andean chakana brackets at N/S/E/W and just a few large simplified leaf/petal accents with wide breathing room (no tiny filigree, no fine grain, no delicate curls). Bold clean double border ring, exact radial symmetry, zero noise. Strictly NO text, NO letters, NO numbers, NO words anywhere.

### Variante (c) — Con anillo exterior libre para tipografía vectorial
- **Archivo objetivo**: `sello-c-anillo-texto.png`
- **Prompt**:
  > Create a high-resolution (2048x2048, 1:1 square) circular seal based on `/Users/dmp/Hackathon/Proyecto a ejecutar/design/brand/v2/exploracion-agy/exploracion-3.png`, leaving a clean, completely blank outer circular ring band so vector typography («ECUADOR × CHILE · ODS 7 · PULSO ENERGÉTICO») can be added later in SVG. Keep the exact `#06323B` petrol teal background and `#FFF1D9` / `#FFC04C` / `#176B46` palette. Structure from outside in: (1) crisp outer cream-and-gold thin border ring; (2) a wide, completely empty solid deep petrol teal (`#06323B`) circular ring band with NO ornaments, NO dots, NO lines, and NO text inside this band; (3) an inner cream circular ring enclosing the compact artisanal seal core—stepped chakana frets, clean mirrored emerald botanical leaves, radial golden rays, and the centered golden-and-cream heartbeat pulse-lightning bolt. Razor-sharp symmetry, clean vector-like edges, zero noise. Strictly NO text, NO letters, NO placeholder glyphs, NO numbers anywhere.
