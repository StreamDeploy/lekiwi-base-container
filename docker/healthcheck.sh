# docker/healthcheck.sh
#!/usr/bin/env sh
set -eu
command -v python >/dev/null 2>&1 || { echo "python missing"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg missing"; exit 1; }
python -c "import ssl" >/dev/null 2>&1 || { echo "python ssl failed"; exit 1; }
echo "OK"