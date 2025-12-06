FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    qbittorrent-nox \
    aria2 \
    ffmpeg \
    rclone \
    sabnzbdplus \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for binaries
RUN ln -s /usr/bin/qbittorrent-nox /usr/bin/stormtorrent && \
    ln -s /usr/bin/aria2c /usr/bin/blitzfetcher && \
    ln -s /usr/bin/ffmpeg /usr/bin/mediaforge && \
    ln -s /usr/bin/rclone /usr/bin/ghostdrive && \
    ln -s /usr/bin/sabnzbdplus /usr/bin/newsripper

RUN uv venv --system-site-packages

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
