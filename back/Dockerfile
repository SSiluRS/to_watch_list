FROM python:3.11-slim

WORKDIR /app

# Системные зависимости для mysqlclient/connector при необходимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential default-libmysqlclient-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY app ./app
COPY frontend ./frontend

# Переменные окружения считываем через docker-compose
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
