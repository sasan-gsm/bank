
FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ================================
# Dependencies stage
# ================================
FROM base as deps

COPY requirements.txt .
RUN pip install --user -r requirements.txt

# ================================
# Production stage
# ================================
FROM base as production

# Copy installed packages from deps stage
COPY --from=deps /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create directory for SQLite database
RUN mkdir -p /app/data

# Copy application code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ================================
# Worker stage
# ================================
FROM production as worker
CMD ["celery", "-A", "app.core.celery_app", "worker", "--loglevel=info"]

# ================================
# Scheduler stage
# ================================
FROM production as scheduler
CMD ["celery", "-A", "app.core.celery_app", "beat", "--loglevel=info"]
