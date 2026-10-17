# Build context: repository root. Existing application and analysis share one volume.
FROM node:22-slim AS dashboard
WORKDIR /app/sessions/cs2-backend/mvp/dashboard
COPY sessions/cs2-backend/mvp/dashboard/package*.json ./
RUN npm ci
COPY sessions/cs2-backend/mvp/dashboard/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY sessions/cs2-backend/mvp/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY sessions/ds-analytics/pyproject.toml /tmp/diza-analysis/pyproject.toml
COPY sessions/ds-analytics/diza_analysis /tmp/diza-analysis/diza_analysis
RUN pip install --no-cache-dir /tmp/diza-analysis && rm -rf /tmp/diza-analysis
COPY sessions/cs2-backend/mvp/backend sessions/cs2-backend/mvp/backend
COPY --from=dashboard /app/sessions/cs2-backend/mvp/dashboard/dist sessions/cs2-backend/mvp/dashboard/dist
COPY agents/forms agents/forms
COPY agents/resources agents/resources
ENV DIZA_DB=/data/diza.sqlite3 PYTHONUNBUFFERED=1
RUN mkdir -p /data
WORKDIR /app/sessions/cs2-backend/mvp
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn diza_analysis.live:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
