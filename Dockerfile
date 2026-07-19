# ==============================================================================
# STAGE 1: BUILD (Dependency installation and compilation tools)
# ==============================================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies required to build C extensions (like pgvector/asyncpg requirements)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtualenv and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ==============================================================================
# STAGE 2: RUNTIME (Clean and secure production runtime image)
# ==============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install only the runtime PostgreSQL client library (without heavy compilation tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from Stage 1
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# SRE/SECURITY BEST PRACTICES: Create a non-root user to run the application
RUN useradd -m -u 10001 agent_user && \
    chown -R agent_user:agent_user /app
ENV HF_HOME=/app/.cache
COPY . .
USER agent_user

# Expose port matching K8s and Terraform configs
EXPOSE 8000

# Initialize Uvicorn server targeting the app instance inside main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]