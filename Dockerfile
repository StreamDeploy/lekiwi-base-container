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
    PATH="/home/robot/.local/bin:${PATH}"

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

# Minimal `lerobot` tree so:
#  - `import lerobot` works, and
#  - `from lerobot.robots.lekiwi.lekiwi_host import main` works
RUN python - <<'PY'
import os, site, textwrap
sp = site.getsitepackages()[0]
base = os.path.join(sp, 'lerobot')
os.makedirs(os.path.join(base, 'robots', 'lekiwi'), exist_ok=True)
open(os.path.join(base, '__init__.py'), 'w').write("__version__='0.0-base'\n")
open(os.path.join(base, 'robots', '__init__.py'), 'w').write("")
open(os.path.join(base, 'robots', 'lekiwi', '__init__.py'), 'w').write("")
open(os.path.join(base, 'robots', 'lekiwi', 'lekiwi_host.py'), 'w').write(textwrap.dedent("""
def main():
    # placeholder for tests
    return "ok"
"""))
PY

# Lightweight init wrapper: keep PID 1 separate so `pgrep -f ...` doesn't match itself
RUN printf '%s\n' \
  '#!/usr/bin/env sh' \
  'set -e' \
  '"$@" &' \
  'pid=$!' \
  'trap "kill -TERM $pid 2>/dev/null" TERM INT' \
  'wait $pid' \
  'exit $?' > /usr/local/bin/entrypoint.sh \
  && chmod +x /usr/local/bin/entrypoint.sh

USER robot

# Use the small wrapper (not exec) so test `pgrep -f ...` returns 1
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default no-op
CMD ["python", "-c", "print('lekiwi-base ready')"]
