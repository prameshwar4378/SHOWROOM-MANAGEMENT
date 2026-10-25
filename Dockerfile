# ====================================================================
# Production Dockerfile for Tractor Showroom Management System
# Multi-stage lightweight Python 3.12/3.13 image
# ====================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies required for Weasyprint/xhtml2pdf, Pillow, and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# Copy project files
COPY . /app/

# Create logs, staticfiles, and media directories with appropriate permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media

# Collect static files during build
RUN python manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Default command: Run production Gunicorn server
CMD ["gunicorn", "--workers", "3", "--threads", "2", "--bind", "0.0.0.0:8000", "--timeout", "120", "SHOWROOM_MANAGEMENT.wsgi:application"]
