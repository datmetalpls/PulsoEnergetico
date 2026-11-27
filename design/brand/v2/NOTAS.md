# Pulso Energético · Marca v2

Propuesta para el pedido «pónganle más cariño al logo». La v1 (Pulso-rayo de Codex) era correcta pero genérica: un rayo dentro de un cuadrado redondeado, igual que miles de apps y sin nada que la ate a Ecuador ni a Chile. La v2 conserva la paleta (petróleo, crema y dorado) y la tipografía (Fraunces, OFL), pero el isotipo es propio y el rotulado está ajustado a mano.

Esta carpeta no modifica la v1. Todo se regenera con `python3 build_v2.py`, que necesita fontTools, Pillow y Google Chrome.

## Tres direcciones

| | Archivo | Lógica en una línea |
|---|---|---|
| **A (recomendada)** | `direccion-a.svg` | Un solo trazo es umbral, cumbre andina y rayo; el sol asoma entre Ecuador y Chile. |
| B | `direccion-b.svg` | El ecuador late entre dos cielos: el sol de la Mitad del Mundo arriba y la Cruz del Sur abajo. |
| C | `direccion-c.svg` | La casa comunitaria lleva el latido adentro: la energía se cuida entre vecinos. |

**Por qué A.** Es la única que cuenta las tres cosas del proyecto en un solo gesto: el pulso (la medición), el rayo (la energía) y la cordillera que une a los dos países. Además conserva la «línea de umbral» del producto como horizonte. B es la más bonita como sello, pero a 16 px el sol con rayos y las estrellas se vuelven ruido. C se entiende al instante, aunque una casa con latido es un ícono muy visto. Las exploraciones de Antigravity (`exploracion-agy/`) llegaron a las mismas tres familias. Las usé como contraste y no como fuente de vectores.

## Decisiones de diseño (dirección A)

- **Un solo trazo continuo.** Recorre el umbral, sube por la ladera hasta la cumbre Ecuador (33, 16), quiebra en un escalón que dibuja el rayo, cae por debajo del umbral (el latido, 57, 75), sube a la cumbre Chile (68, 32) y vuelve al umbral. Se lee como electrocardiograma, cordillera y rayo, sin ningún contenedor.
- **Sol ecuatorial con espacio negativo.** El disco dorado (centro 54, 20; r 17) queda oculto tras la cordillera mediante una máscara. Entre el sol y el trazo hay 3 u de aire, así que el sol «asoma» entre las dos cumbres. La máscara recorta el fondo real, de modo que el aire se ve igual sobre crema, sobre petróleo o sobre una foto.
- **Retícula.** Lienzo de 96 u, módulo de 8 u y retícula mayor de 24 u. El umbral está en y = 60 y es también la línea base del texto en el logo horizontal: las letras «se paran» sobre el horizonte. Ver `construccion.svg/png`.
- **Remates y uniones.** Todos son redondeados. Las esquinas son curvas cuadráticas con radios de 6 u en el umbral, 3,4 u en las cumbres y 2,4 u en el escalón del rayo, que es más cerrado para que se note el quiebre. No hay esquinas de polígono.
- **Compensación óptica.** El trazo mide 7,5 u en tamaños medianos y grandes. A 32 px o menos se usa `favicon.svg`: trazo de 12 u, quiebres más abiertos, sol un poco mayor y disco petróleo de fondo, porque las pestañas pueden ser claras u oscuras.
- **Rotulado.** Fraunces variable con opsz 144, wght 640, SOFT 100 y WONK 0. Los remates suaves aportan el «cariño» y la versión display aporta el contraste. Ajustes a mano:
  - Kerning: P‑u −40, r‑g −30, é‑t −18, E‑n −14, t‑i −12 y r‑e −10, con otros pares finos, más un interletrado óptico de −6 (en unidades de 2000 upm).
  - **La tilde es un rayo.** El agudo de la «é» está dibujado como un pequeño rayo relleno, inclinado como un acento agudo. Es el único detalle de color dentro de la palabra: ámbar `#B87708` sobre crema (3,3:1, apto para gráficos) y dorado `#FFC04C` sobre petróleo.
  - Todo el texto está convertido a trazados. Ningún SVG contiene `<text>`.
- **Sello (estilo Cuypleto).** Lleva «ECUADOR × CHILE · ODS 7» en el arco superior y «PULSO ENERGÉTICO» en el inferior, en Fraunces 700 versalitas espaciadas, con estrellas de cuatro puntas como separadores, un anillo dorado y un compás de puntos que marca el ritmo. Pensado para la lámina, el video y los adhesivos.
- **Color.** Petróleo `#06323B`, crema `#FFF1D9` y dorado `#FFC04C` vienen de `tokens.css`. Se agrega solo `ámbar #B87708` para los acentos sobre crema.

## Archivos

- Direcciones: `direccion-a.svg/png`, `direccion-b.svg/png`, `direccion-c.svg/png`
- Isotipo: `isotipo.svg` (color sobre crema), `isotipo-negativo.svg` (sobre petróleo), `isotipo-negro.svg`, `isotipo-blanco.svg`
- Logo horizontal: `logo-horizontal{,-negativo,-negro,-blanco}.svg` y `logo-horizontal@2x.png` (1356 × 320, fondo transparente)
- Logo vertical: `logo-vertical{,-negativo,-negro,-blanco}.svg`
- Sello: `sello{,-negativo,-negro,-blanco}.svg` y `sello.png` (960 px)
- Favicon: `favicon.svg` y `favicon-32.png`
- Construcción: `construccion.svg/png`
- Comparación: `comparacion-v1-v2.png` (512, 64, 32 y 16 px, sobre crema y petróleo)
- Hoja de revisión: `preview-kit-v2.png`
- Fuente: `marca.py` (geometría y rotulado) y `build_v2.py` (exportación)

Los archivos de color son transparentes. «Color» está pensado para fondos crema o claros y «negativo» para petróleo o fondos oscuros.

## Verificación hecha

- `xmllint --noout` pasa en los 21 SVG.
- Render con Chrome headless y revisión visual de todos los PNG: kit completo, comparación, construcción, direcciones y favicon ampliado a 16 y 32 px.
- Ortografía revisada: Energético, Dirección, Construcción, petróleo, ECUADOR × CHILE · ODS 7.

## Cómo reemplazar v1 si se aprueba (no aplicado)

1. Hacer una copia de seguridad de la v1: `git mv` de los activos actuales a `design/brand/v1/`, o confiar en el historial de git.
2. Copiar desde `v2/` a `design/brand/` con los mismos nombres que la v1:
   - `isotipo*.svg`, `logo-horizontal*.svg`, `logo-vertical*.svg` y `favicon.svg`: el nombre es idéntico.
   - `favicon-32.png`: idéntico.
   - `logo-horizontal@2x.png` reemplaza a `logo-horizontal-2x.png` de la v1 (renombrarlo o actualizar las referencias).
   - Nuevos, sin equivalente en la v1: `sello*.svg` y `construccion.*`.
3. Regenerar lo que la v1 deriva del isotipo y que la v2 aún no produce: `apple-touch-icon.svg/-180.png`, `og-image-1200x630.*`, `logo-horizontal-1x.png`, `manual.html/pdf` y `preview-kit.*`. Lo más simple es cambiar `icon()` y `lettering()` en `build_brand.py` para que importen `isotipo()` y `word()` de `v2/marca.py`, y luego correr `build_brand.py` y `render_exports.py`.
4. Actualizar las referencias en `README.md`, `INTEGRACION.md` y `preview-kit.html`. Agregar `--pe-ambar: #B87708` a `tokens.css` y `tokens.json`.
5. Volver a pasar el QA de la v1 (`QA.md`): contraste, xmllint y render.
