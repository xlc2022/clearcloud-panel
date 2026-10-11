# Clear Cloud Farm panel: built frontend served by the FastAPI backend.

FROM node:22.20-bookworm-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PANEL_DATA_DIR=/data \
    PANEL_PORT=8080
WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/clearcloud_panel ./clearcloud_panel
RUN pip install --no-cache-dir . \
    && useradd --system --uid 10001 --home /app panel \
    && mkdir -p /data && chown panel /data
COPY --from=frontend /src/dist /app/static
ENV PANEL_STATIC_DIR=/app/static
USER panel
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PANEL_PORT\"]}/healthz', timeout=4)"
CMD ["sh", "-c", "exec uvicorn clearcloud_panel.main:app --host 0.0.0.0 --port ${PANEL_PORT} --proxy-headers --forwarded-allow-ips='*'"]
