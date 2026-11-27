FROM node:22-alpine AS frontend
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build && test -f dist/pulso/browser/index.html

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SPA_ROOT=/app/frontend/dist/pulso/browser
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY contracts/ /app/contracts/
COPY --from=frontend /build/frontend/dist/pulso/browser/ /app/frontend/dist/pulso/browser/
RUN chmod +x entrypoint.sh && useradd --create-home pulso && chown -R pulso:pulso /app
USER pulso
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
