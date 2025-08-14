# Stage 1: build frontend
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: backend
FROM python:3.11-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY back/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY back/ ./back/

# Копируем готовый фронт напрямую из первого этапа
COPY --from=frontend /app/frontend/dist/ /app/back/frontend/

EXPOSE 8000
WORKDIR /app/back
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
