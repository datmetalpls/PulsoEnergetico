# Pulso Energético — Frontend (Angular + Bootstrap 5)

Interfaz web de **Pulso Energético** (hackatón Chile–Ecuador, ODS 7; ODS 13 como hipótesis). Diseñada para funcionar **sin conexión a Internet** (sin CDN ni Google Fonts; todos los recursos son locales).

## Requisitos

- Node.js 20+ y npm 10+

## Instalación y compilación

```bash
cd frontend
npm ci
npm run build
```

La salida de producción se genera en `frontend/dist/pulso/browser`.

## Modos de ejecución

### 1. Prototipo navegable sin backend (`?mock=1`)

Levanta el servidor local y abre:

```bash
npm start
```

Visita `http://localhost:4200/?mock=1`. Incluye un selector superior para recorrer las **3 franjas** (`Día`, `Tarde`, `Noche`) y los **6 estados obligatorios** (`Inicial`, `Carga apagada`, `Carga encendida`, `Umbral alcanzado`, `Conexión interrumpida`, `Reporte disponible`), usando los fixtures copiados en `src/assets/mock/` desde `contracts/*.json`.

### 2. Conexión con el backend Django (mismo origen / proxy)

`proxy.conf.json` redirige `/api/*` hacia `http://localhost:8000` durante `ng serve`:

```bash
npm start
```

Visita `http://localhost:4200/` (sin `?mock=1`). La aplicación:

- Solicita `GET /api/auth/csrf` al iniciar y configura `withXsrfConfiguration({ cookieName: 'csrftoken', headerName: 'X-CSRFToken' })`.
- Consulta `GET /api/sites/{site}/state` cada `1 s` mientras la pestaña está visible (`document.visibilityState === 'visible'`).
- Oculta los controles de operación cuando el usuario tiene rol `observer` o no opera el recinto activo.
- En el login muestra el botón **«Entrar como operador demo»** únicamente cuando `window.location.hostname` es `localhost` o `127.0.0.1` (rellena `operador_demo` con la contraseña demo local de `.env.example`); en el despliegue EC2 (u otro dominio público) este botón **no aparece**.
- El encabezado mantiene solo la marca, localidad › recinto, `DATOS SIMULADOS`, reloj/franja/escala, el botón principal del paso siguiente y el menú hamburguesa (`☰`) con foco atrapado y cierre con `Esc`.
- Emite un único beep WebAudio de `0,8 s` al detectar por primera vez una alerta de umbral si el sonido fue habilitado (registrado en `sessionStorage` por `alert.id`).
- Incluye el **Modo presentación** guiado en las sedes (`kind === 'venue'`) con presupuesto de demostración `0,10 kWh`, transiciones Día → Tarde → Noche y tarjeta de ahorro estimada vía `GET /api/sites/{site}/comparison`.
