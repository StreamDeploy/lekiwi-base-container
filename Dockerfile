# syntax=docker/dockerfile:1.5
ARG PY_VERSION=3.10
FROM python:${PY_VERSION}-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/StreamDeploy/lekiwi-base-container" \
      org.opencontainers.image.description="Lean base image for StreamDeploy AI/robotics workloads" \
      org.opencontainers.image.licenses="Apache-2.0"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    ROBOT_ID=my-kiwi \
    PATH="/home/robot/.local/bin:${PATH}"

# Add procps for `pgrep` (health test), and runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        tini \
        ca-certificates curl git \
        ffmpeg \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
        procps \
    && rm -rf /var/lib/apt/lists/*

# Python deps the tests import
RUN pip install --no-cache-dir \
        pyzmq \
        opencv-python-headless

# Create non-root user "robot"
RUN groupadd --system robot && useradd --system --create-home --gid robot robot

# Common dirs + perms
RUN mkdir -p /app /workspace && chown -R robot:robot /app /workspace
WORKDIR /workspace

# Healthcheck script (legacy builder friendly)
COPY docker/healthcheck.sh /usr/local/bin/healthcheck
RUN chmod 755 /usr/local/bin/healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["/usr/local/bin/healthcheck"]

# Proper init
ENTRYPOINT ["/usr/bin/tini", "--"]

# Minimal `lerobot` so `import lerobot` works without heavy deps
RUN set -eux; \
    for d in /usr/local/lib/python*/site-packages /usr/local/lib/python*/dist-packages; do \
      mkdir -p "$d/lerobot"; \
      printf "__version__='0.0-base'\n" > "$d/lerobot/__init__.py"; \
    done

USER robot

CMD ["python", "-c", "print('lekiwi-base ready')"]
