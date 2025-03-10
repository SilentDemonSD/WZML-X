FROM mysterysd/wzmlx:hkwzv3

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY --from=mysterysd/pymegadk:v8.1.1 /usr/local/lib/python3.13/dist-packages/mega /usr/local/lib/python3.13/dist-packages/mega
COPY --from=mysterysd/pymegadk:v8.1.1 /usr/local/lib/ /usr/local/lib/
RUN ldconfig

RUN uv venv --system-site-packages

COPY requirements.txt .
RUN uv pip install --upgrade pip setuptools
RUN uv pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
