FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PROJECT_DIR=/app \
    PYTHON_BIN=/usr/local/bin/python \
    STATIC_ROOT=/app/staticfiles \
    MEDIA_ROOT=/app/media

WORKDIR /app

# LibreOffice is used by crm_communications.document_delivery for PDF conversion.
# bash/coreutils are needed by the existing worker loops (including timeout).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash coreutils libreoffice-writer fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 app

COPY requrements.txt .
RUN pip install --requirement requrements.txt

COPY --chown=app:app . .
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R app:app /app/staticfiles /app/media

USER app

EXPOSE 8000

CMD ["uvicorn", "core.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--lifespan", "off", "--no-proxy-headers"]
