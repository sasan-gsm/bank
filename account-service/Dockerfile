# Multi-stage Dockerfile for Account Service
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Create necessary directories
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create __init__.py files for proper module imports
RUN touch /app/__init__.py && \
    touch /app/api/__init__.py && \
    touch /app/api/routes/__init__.py && \
    touch /app/core/__init__.py && \
    touch /app/domain/__init__.py && \
    touch /app/db/__init__.py && \
    touch /app/services/__init__.py && \
    touch /app/scripts/__init__.py

# Set proper permissions
RUN chmod +x /app/scripts/init_db.py

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

# Stage 3: Development stage (optional)
FROM runtime as development

# Switch back to root to install dev dependencies
USER root

# Install development tools
RUN apt-get update && apt-get install -y \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install \
    pytest-asyncio \
    pytest-cov \
    httpx \
    pytest-mock

# Switch back to appuser
USER appuser

# Development command with auto-reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]

# Stage 4: Testing stage
FROM development as testing

# Copy test files
COPY --chown=appuser:appuser tests/ ./tests/

# Run tests
CMD ["python", "-m", "pytest", "tests/", "-v", "--cov=.", "--cov-report=html", "--cov-report=term"]

# Stage 5: Production stage (default)
FROM runtime as production

# Production-specific optimizations
ENV ENVIRONMENT=production

# Remove unnecessary files for production
RUN rm -rf /app/tests /app/scripts/test_* /app/.git* /app/README.md

# Production command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]