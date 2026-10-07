# ============================================================
# Production Dockerfile
# Agentic Enterprise Knowledge Copilot
# ============================================================

# -------------------------
# Stage 1: Builder
# -------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Build dependencies required by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .

# Install packages system-wide
# IMPORTANT: Do NOT use --user here.
RUN pip install --no-cache-dir -r requirements.txt


# -------------------------
# Stage 2: Runtime
# -------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Runtime dependency for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages
COPY --from=builder /usr/local/lib/python3.11/site-packages \
    /usr/local/lib/python3.11/site-packages

# Copy installed executables such as uvicorn
COPY --from=builder /usr/local/bin \
    /usr/local/bin

# Python environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Application source
COPY app/ /app/app/
COPY data/ /app/data/
COPY docker/ /app/docker/
COPY scripts/ /app/scripts/
COPY .env.example /app/.env.example

# Create non-root user
RUN useradd -m -u 1001 appuser \
    && chown -R appuser:appuser /app

# Run application as non-root user
USER appuser

# Render supplies the actual PORT
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s \
    --timeout=5s \
    --start-period=30s \
    --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/api/v1/health || exit 1

# Start FastAPI
# One worker initially to reduce memory usage for ML/RAG models
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
