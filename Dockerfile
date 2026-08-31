FROM python:3.12-slim

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

# Dependency layer first (cache-friendly)
COPY ./pyproject.toml ./README.md ./uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

# Application code
COPY ./app ./app
COPY ./house ./house
COPY ./config ./config
COPY ./fixtures ./fixtures
COPY ./infra ./infra
RUN uv sync --frozen --no-dev

ARG AGENT_VERSION=0.0.0
ENV AGENT_VERSION=${AGENT_VERSION}
# The image venv is complete — `uv run` must NOT re-sync (it would pull dev
# deps back in and hit PyPI at container start, breaking offline judge mode).
ENV UV_NO_SYNC=1

EXPOSE 8080

CMD uv run uvicorn app.server:api --host 0.0.0.0 --port ${PORT:-8080}
