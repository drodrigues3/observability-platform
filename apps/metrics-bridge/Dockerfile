# ---- Builder stage ----
FROM cgr.dev/chainguard/python:latest-dev AS builder

WORKDIR /app

# Chainguard runs as nonroot — pip installs scripts to ~/.local/bin
ENV PATH="/home/nonroot/.local/bin:${PATH}"

RUN pip install --no-cache-dir poetry==1.7.1

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --only main

# ---- Final stage (distroless — 0 CVE) ----
FROM cgr.dev/chainguard/python:latest

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY bridge/ bridge/
COPY main.py .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]
