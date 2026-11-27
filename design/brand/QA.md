# QA de identidad — Pulso Energético

Fecha: 27-11-2026. Recomendación: **concepto 01 / Pulso-rayo**.

## Resultados observados

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| XML SVG | **18/18 PASS**, `xmllint --noout` | 12 maestros, 3 conceptos, favicon, apple-touch y OG |
| Texto vectorial | **18/18 sin elementos `<text>`**; trazados FontTools | `build_brand.py` + SVG maestros |
| Autonomía SVG | Sin fuentes externas, raster incrustado ni URLs de red | Aserciones y revisión de los SVG |
| Contraste de tokens | **52 pares AA para texto normal**, ≥4,5:1 | `contrast-report.json`, `tokens.json` |
| Control del cálculo | Negro/blanco = 21:1; dorado/crema <3:1, descartado para texto | Aserciones en `build_brand.py` |
| Fuentes | Fraunces y DM Sans, TTF y WOFF2, licencias SIL OFL 1.1 incluidas | `fonts/` |
| PNG | 32×32, 180×180, 1200×630, 720×160 y 1440×320, todos RGBA | Pillow `Image.size`, exportación Chrome 158 headless |
| Transparencia | Horizontal 1x/2x transparentes; apple-touch y OG opacos | Inspección de canales alfa y fondos |
| Manual headless | Captura completa, fuentes e imágenes presentes | `preview-manual.png` |
| Manual PDF | **1 página A4**, 594,96×841,92 pt, PDF etiquetado | `manual.pdf`, `pdfinfo`, `preview-manual-pdf.png` |
| Manual en navegador | 1120 px y 390 px sin desborde horizontal; todas las imágenes cargadas | Evaluación DOM en Orca |
| Fuentes en navegador | Ambas WOFF2 cargadas desde `file://`, estado `loaded` | `document.fonts` y registro de red Orca |
| Red y consola | 9 recursos locales, respuestas 200; 0 entradas de consola | Orca `network` / `console` |
| Revisión visual | Logo a 1x, favicon a tamaño real, variantes, conceptos, OG, manual y PDF revisados | `preview-kit.png`, `preview-manual.png`, `preview-manual-pdf.png` |
| Ortografía | «Pulso Energético» y «Hackatón» conservan tildes; Cuenca/Puente Alto correctos | SVG metadata, trazados, manual e integración |
| Alcance | Escrituras solo en `design/brand/`; sin commits ni cambios a la aplicación | Estado de trabajo y rutas de entrega |

Ratios principales calculados, redondeados a dos decimales: crema/petróleo **12,33:1**, petróleo/dorado **8,44:1**, blanco/verde **6,51:1**, blanco/alerta **6,57:1**, crema/noche **14,06:1**. Los logotipos no dependen de exenciones de contraste para sus palabras en estas combinaciones.

El primer PDF de prueba salió en dos páginas por una regla CSS sin cierre; se corrigió, regeneró y revisó el PDF final de una página. Los archivos entregados corresponden a la versión corregida.

## Reproducción

```sh
python3 design/brand/build_brand.py
python3 design/brand/render_exports.py
python3 -c 'from pathlib import Path; import subprocess; [subprocess.run(["xmllint", "--noout", str(p)], check=True) for p in Path("design/brand").rglob("*.svg")]'
pdfinfo design/brand/manual.pdf
```

`build_brand.py` usa FontTools; `render_exports.py` usa Pillow y el Chrome de macOS indicado dentro del script. El render no requiere conexión a Internet. Los WOFF2 se entregan ya preparados; no se necesita Brotli para ejecutar los scripts. Se eliminaron la dependencia temporal de conversión y el perfil temporal de Chrome.

## Límites y pendientes

- Este QA verifica el kit. No se aplicó la integración ni se ejecutó build de frontend, backend o pruebas del producto; el contraste final de controles, hover, gráficos y los tres temas debe volver a verificarse al integrar.
- El manual contiene ejemplos editoriales estáticos; su botón de muestra no opera el prototipo. La lámina 16:9 corresponde a la composición de escritorio e impresión; en la vista estrecha del manual se deja crecer para conservar la lectura.
- No se hizo búsqueda de registro de marca ni revisión física de impresión. No se prometen ahorros ni reducciones de emisiones demostrados.
- Claude debe registrar el cierre en el vault Obsidian, porque la restricción de escritura de este encargo excluye esa carpeta; hay texto de cierre en `README.md`.

## Modern Web Guidance

- **`css-layout`**: Usé Grid para las secciones en dos columnas y Flexbox con ajuste de línea para chips y encabezados. Respeté «Use `flex-wrap: wrap` whenever overflow is a possibility» y «Do NOT use `overflow: hidden` to mask layout issues»; la vista de 390 px no oculta el contenido para simular que cabe.
