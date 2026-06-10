FROM python:3.12-slim

ENV POETRY_VERSION=2.2.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --only main

COPY app ./app
COPY scripts ./scripts
COPY docker-entrypoint.sh ./
RUN mkdir -p ./data

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]