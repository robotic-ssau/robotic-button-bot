FROM python:3.11-slim
ENV WORKDIR=/app
WORKDIR $WORKDIR

COPY poetry.lock pyproject.toml ./

RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-root --without dev --no-interaction --no-ansi && \
    rm -rf ~/.cache


ENV WORKDIR=/app \
    PYTHONPATH=/app

WORKDIR $WORKDIR

COPY /src $WORKDIR/src
