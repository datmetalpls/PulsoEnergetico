# Sello cartel latino · Pulso Energético (vector)

Versión vectorial **paralela** al logo principal. Parte de la exploración 3 de Antigravity («Sello Cartel Latino Artesanal», `../../v2/exploracion-agy/exploracion-3.png`). No reemplaza al isotipo de producto (v3 «casa + cordillera»): es el **emblema del evento**.

## Archivos

| Nivel | Uso | SVG (petróleo · crema · dorado · negro) | PNG color |
|---|---|---|---|
| Completo | hero, portada, video, OG, sticker grande (≥ 512 px) | `sello-completo.svg`, `-crema`, `-dorado`, `-negro` | 2048 · 512 · 128 |
| Simple | avatar, badge, tarjeta (128–256 px) | `sello-simple*.svg` | 2048 · 512 · 128 |
| Mini | favicon de evento, sticker diminuto (32–64 px) | `sello-mini*.svg` | 2048 · 512 · 128 (+ 64 · 32) |

- `png/`: además de los PNG en color (sobre petróleo y sobre crema) hay previsualizaciones de 512 px de los monocromos.
- `lamina-sello.png`: comparación de los niveles con el original de agy, las variantes y el mini a tamaño real.
- `aplicacion-16x9.png`: aplicación 1920×1080 al estilo Cuypleto.
- Fuentes reproducibles: `build_sello.py` (genera los 12 SVG), `render.sh` (Chrome headless), `lamina-sello.html` y `aplicacion-16x9.html`.

Regenerar: `python3 build_sello.py` y luego `./render.sh <svg|html> <png> <ancho> [alto]`.

## Construcción

**Lienzo y retícula.** viewBox 1000 × 1000, centro (500, 500). Todo se mide en radios desde el centro y ángulos desde la vertical:

| Radio | Elemento (nivel completo) |
|---|---|
| 477 | filete exterior crema (6) |
| 410–466 | banda verde con el texto (centro de la banda en 438) |
| 404 | filete interior crema (5) |
| ≤ 401 | campo (noche `#08272E`) |
| 232–328 | chakanas en los ejes, centradas en r = 280 |
| 342 · 352–392 | punto terracota y flor dorada de tres pétalos en cada eje |
| 212–390 | flora en las diagonales |
| 183–199 | corona de 72 rayos finos (cada 5°) |
| 165 / 172 | disco verde y filete dorado |
| 96/120–150 | 40 rayos de sol alternados dentro del disco |

**Simetría.** La flora se dibuja **una sola vez**: media guía con sus hojas y volutas en un sector de 45°. Se refleja sobre la diagonal y se rota 0°, 90°, 180° y 270°, lo que da simetría diédrica D4: 8 copias exactas sin trazo a mano alzada. Las chakanas y las flores usan la misma rotación D4 sobre los ejes. El rayo-pulso es la única figura que no tiene simetría especular: tiene simetría puntual (180°). El ECG gira con el rayo, así que la deflexión de la izquierda va hacia abajo y la de la derecha hacia arriba.

**Chakana.** Es una cruz andina de 3 escalones (2 en el mini) con módulo `u`: el brazo mide 2u y la cruz entera 8u. El filete interior se obtiene por desplazamiento ortogonal exacto, porque en una figura escalonada basta restar el mismo valor a |x| e |y|. El ojo central es un calado con un punto.

**Rayo-pulso.** El rayo es un polígono de 6 vértices con una faceta crema en el filo izquierdo. La línea ECG se extiende en horizontal hasta casi las chakanas este y oeste y remata en puntas afiladas. Un calado (petróleo/noche) separa el rayo y el pulso del fondo; en los extremos usa `miterlimit` 2,2 para no comerse las chakanas.

**Texto.** «PULSO ENERGÉTICO» va en el arco superior, en sentido horario. «ECUADOR × CHILE · ODS 7» va en el arco inferior y se lee de izquierda a derecha, con las letras derechas. Entre ambos arcos, a las 3 y a las 9, hay rombos dorados con dos puntos. La tipografía es Fraunces (OFL, `../../fonts`) con wght 640 (780 en el nivel simple), opsz 48 y SOFT 50. Los glifos se convierten a trazados con fontTools: cada uno se coloca por longitud de arco y el interletrado se calcula para llenar el ángulo asignado (104°/128° en el completo y 122°/150° en el simple). Las tildes (É) y el signo × usan los glifos reales de la fuente. Los SVG no contienen ningún `<text>`.

**Niveles.**
- *Simple*: conserva el texto (más grueso), 4 hojas grandes con 8 hojas laterales, volutas y destellos; quita las guías, la faceta y los rayos finos (16 rayos gruesos y una corona de 36).
- *Mini*: solo la banda (sin texto), 4 chakanas de 2 escalones y el rayo-pulso engrosado (ECG de 30), sin disco.

**Paleta** (`../../tokens.css`): petróleo `#06323B`, noche `#08272E`, crema `#FFF1D9`, dorado `#FFC04C`, verde `#176B46`, verde claro `#83D9AA`. Acento terracota opcional `#D9643A`, que no está en los tokens; sobre crema reemplaza al dorado en las flores para mantener el contraste.

**Monocromos.** Se construyen con `<mask>`: cada rol queda como tinta o como calado, así que el fondo es transparente de verdad.
- `-dorado`: dorado sobre un cuadrado petróleo.
- `-negro`: negro sin fondo, sirve para serigrafía, sellos de goma o fotocopia.

## Dónde usarlo frente al logo principal

- **Logo principal (v3, casa + cordillera)**: app, navbar, favicon de producto, documentos técnicos y cualquier pieza que diga «qué es el producto».
- **Sello**: identidad del **evento y la narrativa**, es decir, portada del pitch, primera y última diapositiva, video, OG/redes, sticker, poleras y certificados. Va como pieza protagonista, nunca junto al logo principal en el mismo tamaño. Si conviven, el logo principal va pequeño como firma.
- No usar el sello completo por debajo de 256 px (pasar a simple) ni el simple por debajo de 128 px (pasar a mini). El texto del anillo deja de leerse por debajo de ~160 px.
- Fondo preferente: petróleo. Sobre fotos, usar el monocromo dorado o negro, o el de color recortado al círculo (r = 481, `clip-path: circle(48.1%)`).

## Verificación hecha

- `xmllint --noout` en los 12 SVG: OK.
- `grep "<text"` no encuentra ninguno.
- Render con Chrome headless de todos los PNG y revisión visual de cada nivel, de las variantes, de la lámina y de la aplicación.

**Pendiente**: kerning fino (los arcos usan interletrado amplio sin GPOS) y una revisión con la vista del equipo. Antigravity no pudo generar sus variantes raster (cuota HTTP 429, ver `../raster/README.md`), así que la comparación usa solo la exploración 3.
