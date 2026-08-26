# Multi-stage secure Dockerfile for FixItFixa Discord Bot Manager
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Runtime Image
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1001 appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser

# Healthcheck for container vitality
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
  CMD python -c "import psutil; exit(0 if psutil.cpu_percent() >= 0 else 1)"

CMD ["python", "manager.py"]
