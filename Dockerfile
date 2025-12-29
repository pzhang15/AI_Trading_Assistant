# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:/root/.cargo/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app
COPY pyproject.toml README.md ./

# Copy source (required before editable install)
COPY src ./src

# Install runtime dependencies (editable install)
RUN uv pip install --system --no-cache -e .

EXPOSE 8000

# Default command runs the API
CMD ["uvicorn", "trade_guardian.api.main:app", "--host", "0.0.0.0", "--port", "8000"]


