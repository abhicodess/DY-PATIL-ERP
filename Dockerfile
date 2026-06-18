# STAGE 1: Builder
FROM python:3.12-slim as builder

WORKDIR /build

# Install system dependencies for C-extensions (like psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies and compile .pyc
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --user --no-cache-dir -r requirements.txt && \
    python -m compileall .

# STAGE 2: Runtime
FROM python:3.12-slim as runtime

# Install libpq for psycopg2 at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libglib2.0-0 \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Set up non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m appuser

WORKDIR /app

# Copy only what's needed from builder and source
COPY --from=builder /root/.local /home/appuser/.local
COPY . .

# Ensure appuser owns the app directory
RUN chown -R appuser:appgroup /app /home/appuser

# Configure environment
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Entrypoint will be defined in docker-compose or start script
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
