# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir --user -r requirements/prod.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy project files
COPY --chown=appuser:appuser . /app/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh || true

# Switch to non-root user
USER appuser

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ || exit 1

EXPOSE 8000

# Default command (can be overridden)
# Uses PORT environment variable for Render.com compatibility
CMD ["sh", "-c", "gunicorn academy_crm.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 4 --timeout 120 --access-logfile - --error-logfile -"]
