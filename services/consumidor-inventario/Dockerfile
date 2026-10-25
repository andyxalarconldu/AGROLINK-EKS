# ==========================================================
# Dockerfile MULTIETAPA (punto 2 del examen)
# ==========================================================

# ---------- ETAPA 1: construir (instala dependencias) ----------
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- ETAPA 2: imagen final (solo lo necesario) ----------
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY main.py .

# USUARIO NO ROOT (punto 2): UID numérico
RUN useradd --uid 10001 --no-create-home appuser
USER 10001

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]