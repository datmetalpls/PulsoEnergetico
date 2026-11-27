# Propuesta de integración — Pulso Energético

**Estado: propuesta, sin aplicar.** Antigravity integra; Claude coordina. Concepto recomendado: **01 / Pulso-rayo**. Todo este kit vive en `design/brand/`; no se modificó frontend ni backend.

## Archivos que copiaría Antigravity

| Origen en `design/brand/` | Destino exacto |
| --- | --- |
| `logo-horizontal.svg`, `logo-horizontal-negativo.svg`, `isotipo.svg`, `isotipo-negativo.svg` | `frontend/src/assets/brand/` (mismos nombres) |
| `tokens.css` | `frontend/src/assets/brand/tokens.css` |
| `fonts/Fraunces.woff2`, `fonts/DMSans.woff2`, `fonts/Fraunces-OFL.txt`, `fonts/DMSans-OFL.txt` | `frontend/src/assets/brand/fonts/` |
| `favicon.svg`, `favicon-32.png`, `apple-touch-icon-180.png`, `og-image-1200x630.png` | `frontend/public/` (mismos nombres) |

`frontend/angular.json` ya copia `public/` a la raíz y `src/assets/` a `assets/`; no requiere cambios ni dependencias.

## Encabezado: conservar nombre, estado y acciones

En `frontend/src/app/app.component.html`, dentro de `.header-brand-group`, sustituir solo el contenido del `h1.header-title` por un `<picture>` con estas imágenes. Conservar el `h1`, la etiqueta `{{ s.data_label }}`, los selectores, el menú, las acciones y todos sus bindings.

```html
<h1 class="header-title fw-bold mb-0">
  <picture class="pe-brand">
    <source media="(max-width: 575px)"
      [srcset]="themeClass() === 'theme-night'
        ? 'assets/brand/isotipo-negativo.svg' : 'assets/brand/isotipo.svg'">
    <img [src]="themeClass() === 'theme-night'
        ? 'assets/brand/logo-horizontal-negativo.svg' : 'assets/brand/logo-horizontal.svg'"
      alt="Pulso Energético" width="720" height="160">
  </picture>
</h1>
```

El `alt` conserva el nombre accesible aun cuando en móvil solo se vea el isotipo. Mantener la marca completa visible en escritorio y login. En móvil, el nombre de la aplicación seguirá en el título del documento; el isotipo evita comprimir la etiqueta de simulación y el botón principal.

En `frontend/src/styles.css`, agregar al inicio `@import './assets/brand/tokens.css';` (antes de las reglas). Agregar dos `@font-face` locales:

```css
@font-face {
  font-family: 'DM Sans';
  src: url('./assets/brand/fonts/DMSans.woff2') format('woff2');
  font-weight: 100 1000;
  font-display: swap;
}
@font-face {
  font-family: Fraunces;
  src: url('./assets/brand/fonts/Fraunces.woff2') format('woff2');
  font-weight: 100 900;
  font-display: swap;
}
body { font-family: var(--pe-font-ui); }
.pe-brand, .pe-brand img { display: block; }
.pe-brand img { inline-size: 220px; block-size: auto; }
@media (max-width: 575px) {
  .pe-brand img { inline-size: 32px; block-size: 32px; }
}
```

El kit propone Fraunces para títulos editoriales/login/presentación; conservar DM Sans en cifras, controles y encabezados de métricas. Mantener `.tabular-nums`. El símbolo tiene margen integrado: evitar recortar el viewBox para ganar espacio.

## Tokens y temas Día, Tarde y Noche

La integración mínima segura importa los tokens `--pe-*` y usa las imágenes; **mantiene las variables semánticas actuales** (`--bg`, `--surface`, `--text`, `--accent`, `--danger-*`, `--chart-*`) hasta revalidar la pantalla completa. Los nombres `--pe-*` no colisionan con ellas.

Si se aplica la paleta completa, hacerlo explícitamente en los bloques existentes de `frontend/src/styles.css` con esta correspondencia. No convertir todos los temas a crema ni imponer el verde oscuro de Día en Noche.

| Variable actual | `.theme-day` | `.theme-afternoon` | `.theme-night` |
| --- | --- | --- | --- |
| `--bg` | `--pe-crema` | `--pe-tarde` | `--pe-noche` |
| `--surface` | `--pe-blanco` | `--pe-crema` | `--pe-superficie-noche` |
| `--surface-alt` | `--pe-crema` | `--pe-tarde` | `--pe-petroleo` |
| `--text` | `--pe-petroleo` | `--pe-petroleo` | `--pe-crema` |
| `--text-muted` | `--pe-texto-secundario` | `--pe-texto-secundario` | `--pe-crema` |
| `--accent` | `--pe-verde` | `--pe-verde` | `--pe-verde-claro` |
| `--accent-contrast` | `--pe-blanco` | `--pe-blanco` | `--pe-petroleo` |
| `--danger-bg` | `--pe-alerta-fondo` | `--pe-alerta-fondo` | `--pe-alerta-fondo-noche` |
| `--danger-border`, `--danger-text` | `--pe-alerta` | `--pe-alerta` | `--pe-alerta-clara` |
| `--focus-ring` | `--pe-foco` | `--pe-foco` | `--pe-foco-noche` |

Ejemplo de asignación: `--text: var(--pe-petroleo);`. Los pares de esta tabla figuran en `tokens.json` y `contrast-report.json`. Los tokens de marca no sustituyen automáticamente `--border`, rangos ni líneas de gráficos: conservarlos y comprobar ≥3:1 contra el fondo cuando indiquen un control o dato. Dorado `#FFC04C` tiene contraste insuficiente sobre crema; usar `--pe-dorado-texto` en rótulos claros. El rojo de alerta y su texto nunca se sustituyen por dorado. Conservar la línea discontinua de umbral y el mensaje de estado; no depender solo del color.

## Favicon y metadatos

En `frontend/src/index.html`, reemplazar el enlace `favicon.ico` por:

```html
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="apple-touch-icon-180.png" sizes="180x180">
<meta name="theme-color" content="#06323B">
```

Para compartir públicamente, agregar `og:title`, `og:description`, `og:image`, `og:image:width=1200`, `og:image:height=630` y `og:image:alt`. `og:image` necesita la URL absoluta HTTPS del despliegue real, pendiente de Claude; evitar fijar localhost. Descripción sugerida: «Qué está encendido, cuánto consume y cuánto falta para el límite. Prototipo con datos simulados para Cuenca y Puente Alto».

## Verificación de la integración

1. `cd frontend && npm run build` y comprobar que se empaquetan SVG, iconos y WOFF2.
2. Abrir Día/Tarde/Noche en 1440 y 390 px; probar también 320 px, zoom 200 %, login, menú, selector, alerta y presentación. Conservar encabezado de dos filas en 390 px, etiqueta «Datos simulados» siempre visible y áreas táctiles ≥44 px.
3. Probar teclado, foco visible, nombre accesible del `h1` y contraste del hover, botones y gráficos; los ratios de tokens no certifican automáticamente componentes renderizados.
4. Recargar sin red; fuentes e imágenes deben cargar del mismo origen. No añadir Google Fonts por URL.
5. Mantener «Pulso Energético», «Hackatón» y etiquetas de simulación con sus tildes. No afirmar beneficios climáticos demostrados: son «hipótesis por validar».

**Sin integración aplicada, sin build de frontend en este encargo y sin commits.**
