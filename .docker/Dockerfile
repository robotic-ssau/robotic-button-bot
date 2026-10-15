FROM python:3.11-slim
ENV WORKDIR=/app \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1
WORKDIR $WORKDIR

RUN apt-get update && \
    apt-get install -y --no-install-recommends tzdata && \
    rm -rf /var/lib/apt/lists/*

COPY poetry.lock pyproject.toml ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --without dev --no-interaction --no-ansi && \
    rm -rf ~/.cache

COPY /src $WORKDIR/src
COPY /data $WORKDIR/data