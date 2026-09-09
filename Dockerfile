FROM python:3.12-slim

# Prevent Python from creating .pyc files
# and make stdout/stderr appear immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# Copy application source
COPY agent/ ./agent/
COPY dashboard/ ./dashboard/
COPY mcp_server/ ./mcp_server/
COPY database/ ./database/
COPY scripts/ ./scripts/

# Copy any other root-level Python modules if present
COPY *.py ./

# Backend port
EXPOSE 8000

# Streamlit port
EXPOSE 8501