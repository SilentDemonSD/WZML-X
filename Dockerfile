FROM python:3.12-slim

ENV UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    aria2 cpulimit curl default-jre-headless ffmpeg git libmagic1 p7zip-full \
    procps qbittorrent-nox rclone sabnzbdplus unrar-free util-linux \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv

WORKDIR /usr/src/app

COPY requirements.txt .
RUN uv pip install --system --no-cache -r requirements.txt

COPY . .

ENTRYPOINT ["bash", "start.sh"]
