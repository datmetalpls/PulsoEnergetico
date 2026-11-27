FROM node:22-alpine AS frontend
WORKDIR /build
COPY . .
RUN mkdir -p /spa; \
    if [ -f frontend/package-lock.json ]; then \
      cd frontend && if npm ci && npm run build && [ -f dist/pulso/browser/index.html ]; then \
        cp -R dist/pulso/browser/. /spa/; \
      else echo 'WARNING: Angular build failed; using placeholder' >&2; fi; \
    else echo 'WARNING: Angular missing; using placeholder' >&2; fi; \
    if [ ! -f /spa/index.html ]; then \
      echo '<!doctype html><html lang="es"><meta charset="utf-8"><title>Pulso Energético</title><h1>Pulso Energético</h1><p>Backend listo. Interfaz Angular pendiente de compilación.</p></html>' > /spa/index.html; \
    fi

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SPA_ROOT=/app/frontend/dist/pulso/browser
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY contracts/ /app/contracts/
COPY --from=frontend /spa/ /app/frontend/dist/pulso/browser/
RUN chmod +x entrypoint.sh && useradd --create-home pulso && chown -R pulso:pulso /app
USER pulso
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
