# syntax=docker/dockerfile:1.5
ARG PY_VERSION=3.10
# base image suitable for multi‑arch (Debian bookworm + Python)
FROM python:${PY_VERSION}-slim as base

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install OS dependencies – see LeRobot docs.
# ffmpeg libs and build tools are required for pyav/camera support
# Added additional system dependencies for Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ffmpeg \
    libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev \
    libswscale-dev libswresample-dev libavfilter-dev \
    libglib2.0-0 libgl1-mesa-dri libegl1-mesa-dev \
    speech-dispatcher libgeos-dev \
    pkg-config libffi-dev libssl-dev \
    python3-dev python3-pip \
    curl wget \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

# Create a non-root user for security
ARG USER=robot
ARG UID=1000
ARG GID=1000
RUN groupadd -g $GID $USER && useradd -m -u $UID -g $GID -s /bin/bash $USER

# Set up work directories
WORKDIR /opt
RUN mkdir -p /opt/lerobot

# Copy essential files explicitly to ensure they're included
COPY lerobot/ /opt/lerobot/

# Install Python dependencies as root (before USER switch)
# Extras `feetech` and `dynamixel` enable LeKiwi's motors; add others if needed.
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir --verbose -e "/opt/lerobot[feetech,dynamixel]" \
 && python -c "import lerobot; print('LeRobot installed successfully')" \
 && python -c "from lerobot.robots.lekiwi.lekiwi_host import main; print('LeKiwi host module available')" \
 && python -m pip cache purge

# Change ownership of the lerobot directory to the robot user
RUN chown -R $USER:$USER /opt/lerobot

USER $USER

# Default environment (can be overridden by StreamDeploy config)
ENV ROBOT_ID="my-kiwi" \
    DEPLOY_ENV="production"

# Health check: succeed when lekiwi_host is running
HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
  CMD pgrep -f "lerobot.robots.lekiwi.lekiwi_host" || exit 1

# Entry script – uses env vars for config
ENTRYPOINT ["bash","-c"]
CMD ["python -m lerobot.robots.lekiwi.lekiwi_host --robot.id ${ROBOT_ID}"]
