# =========================
# BUILDER (lourd – jetable)
# =========================
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod

WORKDIR /app

# Dépendances système pour compiler certaines libs Python + OCR + PDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    curl \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copier uniquement le fichier requirements
COPY requirements.txt .

# Créer un environnement Python isolé
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Mettre pip, setuptools et wheel à jour
RUN pip install --upgrade pip setuptools wheel

# Installer toutes les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# =========================
# RUNTIME (image finale)
# =========================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=prod
ENV PATH="/opt/venv/bin:$PATH"

# Définitions nécessaires pour Tesseract
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/

WORKDIR /app

# Dépendances système minimales pour le runtime (OCR + PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 \
    libffi8 \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-fra \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Récupérer le venv optimisé du builder
COPY --from=builder /opt/venv /opt/venv

# Copier le code de l’application
COPY app/ ./app

# Exposer le port FastAPI
EXPOSE 8020

# Lancer Uvicorn
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8020"]