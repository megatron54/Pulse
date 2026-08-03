FROM python:3.12-slim

WORKDIR /app

# Dependencias de sistema para psycopg2 (compilación mínima)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PULSE_ENV=production
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Verifica/crea el schema antes de arrancar (idempotente - ver
# scripts/ensure_schema.py para el hallazgo real que motivó esto: un
# Postgres nuevo levantado por docker-compose queda vacío, y nada más
# ejecutaba create_all() fuera de los tests/CI). `exec` es crítico: sin
# él, `sh` queda como PID 1 y NO reenvía SIGTERM a uvicorn (docker stop/
# compose down no harían un apagado gradual, solo SIGKILL tras el
# timeout) - con `exec`, uvicorn reemplaza a `sh` como PID 1 y maneja
# SIGTERM de forma nativa (code-review, hallazgo HIGH).
CMD ["sh", "-c", "python -m scripts.ensure_schema && exec uvicorn api.main:app --host 0.0.0.0 --port 8000"]
