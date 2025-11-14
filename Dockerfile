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

# Copy and install Python dependencies globally
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r requirements/prod.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder (global installation)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy project files
COPY --chown=appuser:appuser . /app/

# Make scripts executable (as root before switching users)
RUN chmod +x /app/scripts/*.sh || true

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Collect static files (before switching to appuser, Django is now globally available)
RUN python manage.py collectstatic --noinput || true

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ || exit 1

EXPOSE 8000

# Set entrypoint to run migrations and create superuser automatically
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Default command (can be overridden)
# Uses PORT environment variable for Render.com compatibility
CMD ["gunicorn", "academy_crm.wsgi:application", "--bind", "0.0.0.0:${PORT:-8000}", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
