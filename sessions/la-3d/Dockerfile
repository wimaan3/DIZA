# Optional combined deployment. Build context must be the repository root.
FROM node:22-slim AS ui
WORKDIR /app/sessions/cs2-backend/mvp/dashboard
COPY sessions/cs2-backend/mvp/dashboard/package*.json ./
RUN npm ci
COPY sessions/cs2-backend/mvp/dashboard/ ./
COPY sessions/elder-care/branding/ /app/sessions/elder-care/branding/
COPY sessions/elder-care/web/branding/ /app/sessions/elder-care/web/branding/
RUN npm run build
WORKDIR /app/sessions/la-3d
COPY sessions/la-3d/package*.json ./
RUN npm ci
COPY sessions/la-3d/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY sessions/cs2-backend/mvp/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY sessions/cs2-backend/mvp/backend sessions/cs2-backend/mvp/backend
COPY --from=ui /app/sessions/cs2-backend/mvp/dashboard/dist sessions/cs2-backend/mvp/dashboard/dist
COPY --from=ui /app/sessions/la-3d/dist sessions/la-3d/dist
COPY sessions/la-3d/server.py sessions/la-3d/server.py
COPY agents/forms agents/forms
COPY agents/resources agents/resources
COPY agents/retell.ids.json agents/retell.ids.json
ENV DIZA_DB=/data/diza.sqlite3 PYTHONUNBUFFERED=1
RUN mkdir -p /data
WORKDIR /app/sessions/la-3d
EXPOSE 8000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
