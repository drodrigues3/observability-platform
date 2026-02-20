# ---- Builder stage ----
FROM python:3.11-slim AS builder

WORKDIR /app

# Install poetry — pinned version for reproducibility
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files first (layer cache optimization)
COPY pyproject.toml poetry.lock* ./

# Install dependencies into a virtual env inside the project
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --only main

# ---- Final stage ----
FROM python:3.11-slim AS final

# Create non-root user (security best practice)
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv .venv

# Copy application source only
COPY simulator/ simulator/
COPY main.py .

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import confluent_kafka; print('ok')" || exit 1

ENTRYPOINT ["python", "main.py"]
