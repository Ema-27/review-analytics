# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

# Dipendenze di sistema minime (build di psycopg/torch e healthcheck curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# torch CPU-only: evita di scaricare ~3 GB di librerie CUDA inutili (il sistema
# gira su CPU). Installata prima cosi' pip non prende la variante GPU da PyPI.
RUN pip install --no-cache-dir torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# I modelli Hugging Face vengono scaricati al primo utilizzo e messi in
# cache qui: la directory viene montata come volume Docker nominato
# (vedi docker-compose.yml) cosi' i riavvii successivi del container non
# richiedono un nuovo download.
ENV AI_MODELS_CACHE_DIR=/app/model_cache \
    HF_HOME=/app/model_cache \
    PYTHONUNBUFFERED=1
RUN mkdir -p /app/model_cache

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
