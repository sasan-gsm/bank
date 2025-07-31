# Multi-stage build for Document Service
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
    libffi-dev \
    libssl-dev \
    libmagic1 \
    libmagic-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /build

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/appuser/.local/bin:$PATH

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libmagic1 \
    libjpeg62-turbo \
    libpng16-16 \
    libtiff5 \
    libwebp6 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directories
RUN mkdir -p /app /app/data /app/logs /app/uploads /app/thumbnails \
    && chown -R appuser:appuser /app

# Copy Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Create __init__.py files for proper module imports
RUN touch /app/__init__.py && \
    touch /app/app/api/__init__.py && \
    touch /app/app/core/__init__.py && \
    touch /app/app/db/__init__.py && \
    touch /app/app/services/__init__.py

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003", "--reload"]

# Stage 4: Testing stage
FROM development as testing

# Copy test files
COPY --chown=appuser:appuser tests/ ./tests/

# Run tests
CMD ["python", "-m", "pytest", "tests/", "-v"]

# Labels for metadata
LABEL maintainer="Bank Document Team" \
      version="1.0.0" \
      description="Document management microservice for banking application" \
      service="document-service"