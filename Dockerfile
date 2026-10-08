# ============================================================
# Production Dockerfile — Memory-Optimized for Render (512MB RAM)
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

# CRITICAL FOR 512MB RENDER INSTANCES:
# 1. Install CPU-only PyTorch FIRST from the official PyTorch CPU wheel index.
#    This prevents pip from pulling 4GB+ of NVIDIA CUDA libraries (cublas, cudnn, cusolver, triton),
#    saving ~3.5GB disk and ~350MB idle runtime RAM.
# 2. Then install the rest of requirements.txt.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# -------------------------
# Stage 2: Runtime
# -------------------------
FROM python:3.11-slim AS runner

WORKDIR /app

# Runtime dependency for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages and executables from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Memory & Runtime Optimization Environment
# - USE_GEMINI_EMBEDDINGS=true: use Gemini API embeddings (eliminates PyTorch -> fits 512MB RAM)
# - Limit thread pools to 1 to avoid thread arena heap allocations in low-RAM containers
# - Use standard malloc instead of pymalloc to return memory directly to OS
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    TORCH_NUM_THREADS=1 \
    PYTHONMALLOC=malloc \
    RERANKER_ENABLED=false \
    USE_GEMINI_EMBEDDINGS=true \
    EMBEDDING_VECTOR_SIZE=768 \
    PORT=10000

# Copy application source code, static frontend assets, and configurations
COPY app/ /app/app/
COPY data/ /app/data/
COPY docker/ /app/docker/
COPY scripts/ /app/scripts/
COPY static/ /app/static/
COPY .env.example /app/.env.example

# Create unprivileged application user
RUN useradd -m -u 1001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 10000

# Health check — start-period is extended to allow startup document indexing
# (embedding all PDFs in data/raw/ into Qdrant in-memory takes ~30-60s on cold start)
HEALTHCHECK --interval=60s \
    --timeout=10s \
    --start-period=120s \
    --retries=3 \
    CMD curl -f http://localhost:${PORT:-10000}/api/v1/health || exit 1

# Start Uvicorn with single worker and concurrency limits to prevent memory spikes
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1 --limit-concurrency 50 --timeout-keep-alive 5"]
