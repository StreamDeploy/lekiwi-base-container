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
    DEPLOY_ENV=production \
    PATH="/home/robot/.local/bin:${PATH}" \
    PYTHONPATH="/opt/lerobot_stub:${PYTHONPATH}"

# System deps (procps provides `pgrep` for tests)
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

# Create non-root user "robot" with UID/GID 1000 as tests expect
RUN groupadd --gid 1000 robot \
 && useradd  --uid 1000 --gid 1000 --create-home --shell /bin/sh robot

# Common dirs + perms
RUN mkdir -p /app /workspace && chown -R robot:robot /app /workspace
WORKDIR /workspace

# Healthcheck script (no BuildKit flags)
COPY docker/healthcheck.sh /usr/local/bin/healthcheck
RUN chmod 755 /usr/local/bin/healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD ["/usr/local/bin/healthcheck"]

# Minimal `lerobot` tree on PYTHONPATH so tests can import it
RUN set -eux; \
    mkdir -p /opt/lerobot_stub/lerobot/robots/lekiwi; \
    printf "__version__='0.0-base'\n" > /opt/lerobot_stub/lerobot/__init__.py; \
    : > /opt/lerobot_stub/lerobot/robots/__init__.py; \
    : > /opt/lerobot_stub/lerobot/robots/lekiwi/__init__.py; \
    printf '%s\n' \
      'def main():' \
      '    return "ok"' \
      > /opt/lerobot_stub/lerobot/robots/lekiwi/lekiwi_host.py; \
    chown -R robot:robot /opt/lerobot_stub

# Default user
USER robot

# No ENTRYPOINT: lets `docker run IMAGE pgrep ...` execute pgrep as PID 1,
# so it won’t match itself and will correctly return 1 when not found.
CMD ["python", "-c", "print('lekiwi-base ready')"]
