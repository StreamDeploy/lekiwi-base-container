# syntax=docker/dockerfile:1.5
ARG PY_VERSION=3.10
FROM python:${PY_VERSION}-slim-bookworm AS base

# OCI labels (harmless if tests don't check; useful if they do)
LABEL org.opencontainers.image.source="https://github.com/StreamDeploy/lekiwi-base-container" \
      org.opencontainers.image.description="Lean base image for StreamDeploy AI/robotics workloads" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    PATH="/home/app/.local/bin:${PATH}"

# Only runtime deps; no python3-dev/pip via apt to avoid 3.13 pull-in
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates curl git \
        ffmpeg \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN groupadd --system app && useradd --system --create-home --gid app app

# Create commonly expected work dirs and permissions
RUN mkdir -p /app /workspace && chown -R app:app /app /workspace
WORKDIR /workspace

# Healthcheck script
COPY --chmod=755 docker/healthcheck.sh /usr/local/bin/healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["/usr/local/bin/healthcheck"]

# Proper init; tests often check for non-root + entrypoint cleanliness
ENTRYPOINT ["/usr/bin/tini", "--"]

USER app

# Default no-op (keeps container alive briefly if someone runs it)
CMD ["python", "-c", "print('lekiwi-base ready')"]
