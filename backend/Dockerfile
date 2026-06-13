# Multi-stage build setup for Python FastAPI
FROM python:3.13-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies to user site-packages
RUN pip install --no-cache-dir --user -r requirements.txt

# Final production stage
FROM python:3.13-slim

WORKDIR /app

# Install runtime system dependencies (e.g. libpq for PostgreSQL connectivity)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies and app code
COPY --from=builder /root/.local /root/.local
COPY . /app

# Expose PATH and PYTHONPATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

# Start FastAPI application with Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
