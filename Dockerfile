FROM mysterysd/wzmlx:wzadv
# COPY --from=mysterysd/wzmlx:m-tools /usr/local /usr/local

WORKDIR /usr/src/app

COPY requirements.txt .
RUN uv pip install --python /wzvenv/bin/python --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["bash", "start.sh"]
