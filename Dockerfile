# Production Dockerfile for StudentERP (Faculty Face Attendance SaaS)
FROM python:3.12-slim

# Prevent Python from writing .pyc files & buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Install system dependencies for OpenCV, PostgreSQL, and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    build-essential \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependency definition & install Python dependencies
COPY pyproject.toml /app/
RUN uv pip install --system --no-cache \
    django>=5.1 \
    django-tenants>=3.7 \
    opencv-python-headless \
    numpy \
    pillow \
    gunicorn \
    django-redis \
    psycopg2-binary \
    python-decouple \
    argon2-cffi

# Copy application source code
COPY . /app/

# Expose WSGI port
EXPOSE 8000

# Default command: launch Gunicorn WSGI server
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
