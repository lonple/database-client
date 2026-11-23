# dbc-askdata 运行时镜像（Python / FastAPI；无 bootJar）
# 基础镜像：python:3.12-slim
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DBC_ASKDATA_SECRETS_DIR=/app/secrets \
    DBC_ASKDATA_MIGRATIONS_DIR=/app/migrations \
    DBC_ASKDATA_EVAL_CASES_DIR=/app/eval-cases \
    DBC_ASKDATA_NACOS_REGISTER=true

RUN mkdir -p /app/secrets /app/logs /app/eval-cases

COPY pyproject.toml README.md ./
COPY src ./src
COPY migrations ./migrations
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

EXPOSE 8009

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8009/health', timeout=4)"

ENTRYPOINT ["/app/entrypoint.sh"]
