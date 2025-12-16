FROM mysterysd/wzmlx:v3

WORKDIR /usr/src/app

RUN chmod 777 /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    ca-certificates \
    && wget https://mega.nz/linux/repo/xUbuntu_25.04/amd64/megacmd-xUbuntu_25.04_amd64.deb && sudo apt install "$PWD/megacmd-xUbuntu_25.04_amd64.deb" \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


RUN uv venv --system-site-packages

COPY requirements.txt .
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]

