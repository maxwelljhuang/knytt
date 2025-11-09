# Multi-stage build for Python application
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt backend/requirements-ml.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt && \
    pip install --user --no-cache-dir -r requirements-ml.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder to appuser's home
COPY --from=builder /root/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser/.local

# Copy application code
COPY backend/ ./backend/
COPY database/ ./database/
COPY scripts/ ./scripts/
COPY logging.conf .

# Create necessary directories
RUN mkdir -p data/raw data/processed data/temp logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Update PATH for appuser
ENV PATH=/home/appuser/.local/bin:$PATH

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
ENV PORT=8080
EXPOSE 8080

# Health check (disabled for Cloud Run - they have their own)
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
#     CMD python -c "import requests; requests.get('http://localhost:${PORT}/health')" || exit 1

# Run the application (Cloud Run provides PORT environment variable)
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT}

