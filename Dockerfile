# Use Python 3.11 slim image for better security and smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=backend.settings_docker
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    libopenblas-dev \
    pkg-config \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-docker.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /app/media /app/staticfiles /app/temp_uploads /app/logs

# Make entrypoint script executable
RUN chmod +x /app/docker-entrypoint.sh

# Collect static files (only if Django is properly configured)
RUN python manage.py collectstatic --noinput || echo "Static files collection skipped - Django not fully configured"

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]

