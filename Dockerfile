# syntax=docker/dockerfile:1.4
# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building (optimized - single layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip for faster installs
# Suppress root user warning (safe in Docker containers)
RUN pip install --root-user-action=ignore --upgrade pip setuptools wheel

# Copy only requirements first (better layer caching)
COPY requirements/ /app/requirements/

# Install Python dependencies with BuildKit cache mount for faster rebuilds
# Mount pip cache to speed up subsequent builds
# Suppress root user warning (safe in Docker containers)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --root-user-action=ignore --upgrade-strategy only-if-needed -r requirements/prod.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only (optimized - single layer, no recommends)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder (global installation)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set Python environment variables early (better for caching)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user and directories in one layer
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R appuser:appuser /app

# Copy project files (this layer changes most often, so it's last)
COPY --chown=appuser:appuser . /app/

# Make scripts executable and collect static files (as root, before switching users)
# Note: collectstatic moved to runtime in entrypoint for faster builds
# But we can still do it here if you prefer (slower build, faster startup)
RUN chmod +x /app/scripts/*.sh || true

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
# Using shell form to allow environment variable expansion
CMD gunicorn academy_crm.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 4 --timeout 120 --access-logfile - --error-logfile -
