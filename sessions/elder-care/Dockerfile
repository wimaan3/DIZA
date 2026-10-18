FROM node:22-slim AS original-dashboard
WORKDIR /build
COPY sessions/cs2-backend/mvp/dashboard/package*.json ./
RUN npm ci
COPY sessions/cs2-backend/mvp/dashboard/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
COPY sessions/cs2-backend/mvp/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY sessions/cs2-backend/mvp/backend sessions/cs2-backend/mvp/backend
COPY --from=original-dashboard /build/dist sessions/cs2-backend/mvp/dashboard/dist
COPY agents/forms agents/forms
COPY agents/resources agents/resources
COPY agents/retell.ids.json agents/retell.ids.json
COPY sessions/elder-care/app.py sessions/elder-care/app.py
COPY sessions/elder-care/facility.py sessions/elder-care/facility.py
COPY sessions/elder-care/web sessions/elder-care/web
ENV CARE_DB=/data/care.sqlite3 DIZA_DB=/data/diza.sqlite3 PYTHONUNBUFFERED=1
RUN mkdir -p /data
WORKDIR /app/sessions/elder-care
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
