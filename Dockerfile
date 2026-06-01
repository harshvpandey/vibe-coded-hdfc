# ============================================================
#  HDFC AI Mailroom Hub — Production Dockerfile
#  Multi-stage build  •  Python 3.10-slim  •  Non-root user
# ============================================================

# --------------- Stage 1: build / install deps ---------------
FROM python:3.10-slim AS builder

WORKDIR /app

# System deps required by some Python packages (e.g. SQLAlchemy C extensions)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --------------- Stage 2: production image -------------------
FROM python:3.10-slim AS production

# Prevent Python from writing .pyc files & enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only the installed packages from the builder stage
COPY --from=builder /install /usr/local

# Create a non-root user for security
RUN groupadd --system appuser && useradd --system --gid appuser appuser

# Copy application source code
COPY . .

# Create required directories and set ownership
RUN mkdir -p /app/logs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Health-check — pings the root or /docs endpoint every 30s
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

# Override the default bind host so the port is reachable from outside the
# container (settings.py defaults to 127.0.0.1 which is loopback-only).
ENV API_HOST=0.0.0.0

# Start the application
CMD ["python", "main.py"]
