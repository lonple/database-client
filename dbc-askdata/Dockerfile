FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBC_ASKDATA_SECRETS_DIR=/app/secrets \
    DBC_ASKDATA_NACOS_REGISTER=true

COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY prompts ./prompts

RUN pip install --no-cache-dir -e .

EXPOSE 8009

CMD ["uvicorn", "dbc_askdata.main:app", "--host", "0.0.0.0", "--port", "8009"]
