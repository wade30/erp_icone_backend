
FROM python:3.12-slim-bookworm

# ==================================================
# 1. CONFIGURATION PYTHON
# ==================================================

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# ==================================================
# 2. INSTALLATION DES DEPENDANCES SYSTEME
# ==================================================

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libffi-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    shared-mime-info \
    fonts-dejavu-core \
    fontconfig \
    curl \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# ==================================================
# 3. INSTALLATION DES DEPENDANCES PYTHON
# ==================================================

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install "gunicorn>=23.0,<24.0"

# ==================================================
# 4. COPIE DU CODE DJANGO
# ==================================================

COPY . .

# ==================================================
# 5. CREATION DES DOSSIERS DE STOCKAGE
# ==================================================

RUN mkdir -p /app/staticfiles /app/media

# ==================================================
# 6. EXPOSITION DU PORT DJANGO
# ==================================================

EXPOSE 8000

# ==================================================
# 7. LANCEMENT DE DJANGO AVEC GUNICORN
# ==================================================

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]