FROM node:24-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.10-slim-bookworm AS runtime
ARG ESSENTIA_MODEL_ARCHIVE_URL=https://oc-file.gozdzik.online/api/public/dl/_OlwyHdn/
ARG ESSENTIA_MODEL_ARCHIVE_SHA256=25878d4d36533b2ef6ac888f4479baa2477eac48bae0bdbea79a1bad79c41916
ARG VERSION=0.0.0
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    ESSENTIA_VERSION=$VERSION \
    ESSENTIA_MUSIC_ROOT=/music \
    ESSENTIA_DATA_DIR=/data \
    ESSENTIA_MODEL_DIR=/app/models \
    ESSENTIA_MODEL_MANIFEST=/app/models.json \
    ESSENTIA_IMAGE_VARIANT=cpu \
    ESSENTIA_FRONTEND_DIR=/app/frontend
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libfftw3-double3 libsamplerate0 libtag1v5 libyaml-0-2 libchromaprint1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --home-dir /app --create-home app
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.11.7
COPY requirements/analysis.lock /app/requirements.lock
RUN uv pip install --system --require-hashes -r /app/requirements.lock
COPY backend/essentia_studio/analysis/models.json /app/models.json
COPY scripts/download_models.py /app/download_models.py
RUN python /app/download_models.py --manifest /app/models.json --output /app/models \
    --archive-url "$ESSENTIA_MODEL_ARCHIVE_URL" \
    --archive-sha256 "$ESSENTIA_MODEL_ARCHIVE_SHA256"
COPY backend/essentia_studio /app/essentia_studio
COPY --from=frontend /src/frontend/dist /app/frontend
COPY docker/entrypoint.py /app/entrypoint.py
COPY scripts/cpu_smoke.py /app/scripts/cpu_smoke.py
COPY scripts/worker_recovery_smoke.py /app/scripts/worker_recovery_smoke.py
RUN mkdir -p /music /data \
    && chown -R root:root /app \
    && chmod -R a+rX,a-w /app \
    && chown app:app /music /data
USER app
EXPOSE 8000
VOLUME ["/music", "/data"]
LABEL org.opencontainers.image.source="https://github.com/Skrockle/Essentia-Studio" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.licenses="MIT"
ENTRYPOINT ["python", "/app/entrypoint.py"]
CMD ["python", "-m", "uvicorn", "essentia_studio.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
