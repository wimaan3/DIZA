# DIZA backend + dashboard, one container. Build context = repo root (branch cs1/demo-deploy).
# 1) build the React dashboard
FROM node:22-slim AS dashboard
WORKDIR /app/sessions/cs2-backend/mvp/dashboard
COPY sessions/cs2-backend/mvp/dashboard/package*.json ./
RUN npm ci
COPY sessions/cs2-backend/mvp/dashboard/ ./
RUN npm run build

# 2) FastAPI backend serving the API, the Retell endpoints and the built dashboard
FROM python:3.12-slim
WORKDIR /app
COPY sessions/cs2-backend/mvp/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY sessions/cs2-backend/mvp/backend sessions/cs2-backend/mvp/backend
COPY --from=dashboard /app/sessions/cs2-backend/mvp/dashboard/dist sessions/cs2-backend/mvp/dashboard/dist
# Form schemas + verified resources the backend reads (same layout as the repo, so defaults work)
COPY agents/forms agents/forms
COPY agents/resources agents/resources
COPY agents/retell.ids.json agents/retell.ids.json
# SQLite on a mounted volume (/data) so a restart doesn't wipe reports
ENV DIZA_DB=/data/diza.sqlite3 PYTHONUNBUFFERED=1
RUN mkdir -p /data
WORKDIR /app/sessions/cs2-backend/mvp
EXPOSE 8000
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
