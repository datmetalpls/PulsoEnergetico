# Pulso Energético · Marca v3 «Casa que late» (final)

Esta es la versión elegida por el usuario: **fusión de casa y cordillera**. Toma la casa comunitaria de las exploraciones de Antigravity 05 y 06 y le pone como techo el trazo «cordillera que late» de la v2. Conserva el rotulado (Fraunces ajustado, con la tilde de la «é» dibujada como rayo) y el sello circular.

La v1 (`design/brand/`) y la v2 (`design/brand/v2/`) no se modificaron. Todo se regenera con `python3 build_v3.py`, que necesita fontTools, Pillow y Google Chrome.

## Isotipo

Es **un solo trazo continuo** de 7,5 u sobre un lienzo de 96 u, con uniones y remates redondeados. Recorre, en orden:

- suelo → pared izquierda → alero
- **cumbre Ecuador** (28, 14)
- escalón del rayo (41, 50) → (48, 46)
- **el latido entra en la casa** (52, 64)
- **cumbre Chile** (70, 18)
- alero → pared derecha → suelo

**El sol ya no muerde el trazo.** El disco dorado (centro 49,6 · 18; r 12,21 u) no lleva máscara: está inscrito entre las dos laderas. Su posición la calcula `sunfit()`, de modo que queda a la misma distancia de la ladera Ecuador y de la ladera Chile (r + 3,75 u de medio trazo + 3 u de aire). El aire es uniforme por construcción y la lámina de construcción lo muestra con las dos cotas rojas.

**Casa simple.**
- Paredes rectas y aleros que sobresalen: son los que hacen que se lea «casa» y no «M».
- Una puerta en arco (r 6,5 u) apoyada en el suelo, en verde `#176B46` sobre crema y verde claro `#83D9AA` sobre petróleo.
- Sin plantas, ventanas ni detalles que se pierdan a 16 px.

**Favicon compensado** (`favicon.svg` y `favicon-32.png`):
- sin escalón del rayo y con picos simétricos;
- trazo de 12,5 u, sol de r 10,7 u y puerta más ancha;
- disco petróleo de fondo, que funciona en pestañas claras y oscuras.

Se usa a 32 px o menos. A 32 px se leen la casa, el techo de montañas, el sol y la puerta. A 16 px queda como silueta: disco oscuro, techo de dos picos, punto dorado y puerta verde.

**Rotulado.**
- Fraunces opsz 144, wght 640, SOFT 100, con el kerning manual de la v2 y la tilde-rayo (ámbar `#B87708` sobre crema, dorado sobre petróleo).
- En el logo horizontal, la línea base del texto es el suelo de la casa (y = 88) y la altura de mayúscula llega a y = 50.
- Todo el texto está convertido a trazados: ningún SVG contiene `<text>`.

**Sello.** Lleva «ECUADOR × CHILE · ODS 7» en el arco superior y «PULSO ENERGÉTICO» en el inferior, con estrellas de cuatro puntas, anillo dorado y compás de puntos, y el nuevo isotipo al centro.

## Archivos

| Pieza | Archivos |
|---|---|
| Isotipo | `isotipo{,-negativo,-negro,-blanco}.svg` y `@2x.png` (240 px) |
| Logo horizontal | `logo-horizontal{,-negativo,-negro,-blanco}.svg` y `@2x.png` |
| Logo vertical | `logo-vertical{,-negativo,-negro,-blanco}.svg` y `@2x.png` |
| Sello | `sello{,-negativo,-negro,-blanco}.svg` y `@2x.png` (960 px) |
| Favicon | `favicon.svg` y `favicon-32.png` |
| iOS | `apple-touch-icon.svg` y `apple-touch-icon-180.png` |
| Redes | `og-image-1200x630.svg/png`: «HACKATÓN ECUADOR × CHILE · ODS 7» y «La energía de tu sede, a la vista.» |
| Construcción | `construccion.svg/png` |
| Comparación | `comparacion-v1-v2-v3.png` (512, 64, 32 y 16 px, sobre crema y petróleo) |
| Hoja de revisión | `preview-kit-v3.png` |
| Fuente | `marca.py` (geometría y rotulado) y `build_v3.py` (exportación) |

Los archivos de color tienen fondo transparente. «Color» es para fondos crema o claros y «negativo» para petróleo u oscuros. La og-image conserva de la v1 las líneas «Cuenca · Puente Alto» y «Prototipo con datos simulados».

## Verificación

- `xmllint --noout` pasa en los 20 SVG, y ninguno contiene `<text>`.
- Todos los PNG se renderizaron con Chrome headless y los revisé uno por uno: kit, comparación, construcción, og-image, apple-touch y favicon ampliado a 16 y 32 px.
- Ortografía revisada: Energético, HACKATÓN, petróleo, «La energía de tu sede, a la vista.».

## Advertencia de lectura

En las versiones de una sola tinta (negro y blanco), el sol macizo entre las dos cumbres puede leerse como una cabeza sobre hombros. En color no pasa, porque el dorado separa el sol del trazo. Si molesta, la salida es usar la versión una tinta solo en sellos o grabados, o dibujar el sol como un anillo a partir de 64 px.

## Cómo reemplazar la v1 (no aplicado)

1. Copiar desde `v3/` a `design/brand/`. `isotipo*.svg`, `logo-horizontal*.svg`, `logo-vertical*.svg`, `favicon.svg`, `favicon-32.png`, `apple-touch-icon.svg`, `apple-touch-icon-180.png`, `og-image-1200x630.svg` y `og-image-1200x630.png` se llaman igual en la v1.
2. `logo-horizontal@2x.png` reemplaza a `logo-horizontal-2x.png`: renombrarlo o actualizar las referencias. `logo-horizontal-1x.png` se puede rasterizar desde el SVG.
3. Rehacer `manual.html/pdf` y `preview-kit.*` con el nuevo isotipo, o hacer que `build_brand.py` importe `isotipo()` y `word()` de `v3/marca.py`.
4. Agregar `--pe-ambar: #B87708` a `tokens.css` y `tokens.json`. El verde de la puerta ya existe como `--pe-verde` y `--pe-verde-claro`.
5. Actualizar `README.md`, `INTEGRACION.md` y el `<link rel="icon">` del frontend, y volver a pasar `QA.md`.
