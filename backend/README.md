# Backend de Pulso Energético

Python 3.12, Django 5.2 LTS, PostgreSQL 17 y psycopg 3. Sin hardware, Discord ni llamadas externas durante la demo.

## Arranque

Desde la raíz del repositorio:

```sh
cp .env.example .env
docker compose up --build -d
```

Abrir http://localhost:8080. Compose requiere versión 2.24 o posterior: usa `.env.example` como base y superpone `.env` cuando existe. Cambiar los valores en `.env` antes de publicar fuera de localhost. PostgreSQL solo está en una red interna, sin puertos publicados; volumen `postgres_data`. El entrypoint ejecuta migrate, seed_demo, collectstatic y gunicorn.

Usuarios: `operador_cuenca`, `operador_puente`, `observador`; contraseñas definidas por las correspondientes variables de `.env.example` / `.env`. La semilla crea las contraseñas solo una vez y conserva las existentes.

El build multistage compila Angular con Node 22 y copia `frontend/dist/pulso/browser` a WhiteNoise. Si faltan dependencias, falla la compilación o falta el index, el build aborta. Recompilar la imagen al completar frontend; no se necesita CORS ni otro servidor.

## Variables

- `DJANGO_SECRET_KEY`: requerida, sin valor implícito.
- `DATABASE_URL`: URL PostgreSQL opcional; tiene prioridad sobre `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
- `POSTGRES_PASSWORD`: requerida cuando no existe DATABASE_URL. Los demás valores por defecto son `pulso`, `pulso`, `db`, `5432`.
- `DEMO_CUENCA_PASSWORD`, `DEMO_PUENTE_PASSWORD`, `DEMO_OBSERVER_PASSWORD`: requeridas por seed_demo.
- `DEBUG`: `true`/`false`, por defecto false.
- `ALLOWED_HOSTS`: lista separada por comas; por defecto localhost,127.0.0.1,testserver,web.
- `SPA_ROOT`: ruta del build Angular, definida por la imagen.

## Comandos

```sh
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py load_backup_demo
docker compose exec web python manage.py test
docker compose exec web python manage.py makemigrations --check --dry-run
docker compose up -d
docker compose logs web
```

`load_backup_demo` crea dos ensayos cerrados de Cuenca de forma idempotente e imprime sus URL de reporte. Banco: 18 s encendido, 10 s apagado, 18 s encendido, luego apagado; 0,020 Wh, 36 s efectivos y una alerta. Sede: 6 h, sala apagada al terminar reunión de 3 h; ambas cargas apagadas al cierre. Las sesiones activas se conservan.

Pruebas usan el runner de Django y una base `test_pulso` en PostgreSQL; el usuario de pruebas debe poder crear bases. Ninguna prueba usa SQLite. Contratos se leen desde `/app/contracts` dentro del contenedor o `../contracts` en ejecución local.

## API

`GET /api/auth/csrf` fija `csrftoken`. Enviar `POST /api/auth/login` con `{username,password}`, cookie y header `X-CSRFToken`. Django rota CSRF al iniciar sesión: usar la nueva cookie en los siguientes POST/PATCH. Lecturas protegidas requieren una sesión autenticada; las escrituras requieren operador del sitio. `GET /api/auth/me` incluye `operable_sites`.

Las rutas y cuerpos están en `docs/02-contrato.md`. Crear otro ensayo cierra el anterior; `/api/sessions/{uuid}/report` conserva los valores de cierre. No existe endpoint de envío: `discord_preview.sent` siempre false. Las excepciones resueltas están en [CONTRACT-NOTES.md](CONTRACT-NOTES.md).

No usar `docker compose down -v` si se desea conservar el ensayo: elimina el volumen de PostgreSQL.
