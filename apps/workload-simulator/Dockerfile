# ---- Builder stage ----
# latest-dev has pip, shell, and build tools for installing dependencies
FROM cgr.dev/chainguard/python:latest-dev AS builder

WORKDIR /app

# Chainguard runs as nonroot — pip installs scripts to ~/.local/bin
ENV PATH="/home/nonroot/.local/bin:${PATH}"

# Install poetry — pinned version for reproducibility
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files first (layer cache optimization)
COPY pyproject.toml poetry.lock* ./

# Install dependencies into a virtual env inside the project
RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --only main

# ---- Final stage (distroless — 0 CVE) ----
# No shell, no package manager, no root user — minimal attack surface
FROM cgr.dev/chainguard/python:latest

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv .venv

# Copy application source only
COPY simulator/ simulator/
COPY main.py .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

ENTRYPOINT ["python", "main.py"]
