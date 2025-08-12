FROM python:3.13.6-alpine3.22

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    HOST=0.0.0.0 \
    PORT=8000 \
    GENERATE_EVERY_SECONDS=10800 \
    GENERATE_ON_START=true \
    API_KEYS= \
    TAXII_API_ROOT_PATH=/taxii2/root \
    COLLECTION_ID=indicators \
    COLLECTION_TITLE= \
    TAXII_INDICATORS_ONLY=false \
    SOURCE_SYSTEM=

WORKDIR /app

# tini on Alpine installs to /sbin/tini
RUN apk add --no-cache tini

# Optional but recommended: upgrade pip first
RUN python -m pip install --upgrade pip

COPY requirements.txt /app/

# uvicorn[standard] may need compilers (uvloop, httptools, watchfiles)
# Install build deps, pip install, then remove build deps to keep image slim
RUN apk add --no-cache --virtual .build-deps \
      build-base rust cargo \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && apk del .build-deps

COPY app /app/app
RUN mkdir -p /app/data

EXPOSE 8000

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
