# -----------------------------------------------------------------------------
# Étape 1 : Builder (contient les compilateurs et outils lourds)
# -----------------------------------------------------------------------------
FROM python:3.10-slim AS builder

# Installation des outils de compilation nécessaires
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Création d'un environnement virtuel pour isoler les paquets
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

# Installer PyTorch CPU (compatible Python 3.10)
RUN pip install --no-cache-dir torch \
    --index-url https://download.pytorch.org/whl/cpu

# 2. Installer les autres dépendances
# On retire torch du requirements.txt temporairement ou on laisse pip gérer s'il est déjà satisfait
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Étape 2 : Image Finale (Runtime léger)
# -----------------------------------------------------------------------------
FROM python:3.10-slim

WORKDIR /app

# Installation des lib système minimales requises pour l'exécution (ex: OpenMP pour PyTorch)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copier l'environnement virtuel depuis l'étape builder
COPY --from=builder /opt/venv /opt/venv

# Activer l'environnement virtuel par défaut
ENV PATH="/opt/venv/bin:$PATH"

# Copier le code de l'application
#COPY . /app

EXPOSE 8030

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8030", "--workers", "2"]