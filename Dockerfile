FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --no-create-home appuser

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "poetry==2.4.1"

COPY pyproject.toml poetry.lock* ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi --only main

COPY --chown=appuser:appgroup rod_project_portal .

RUN mkdir -p /app/static /app/db \
    && chown appuser:appgroup /app/static /app/db

USER appuser

CMD ["uvicorn", "rod_project_portal.asgi:application", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--no-access-log"]