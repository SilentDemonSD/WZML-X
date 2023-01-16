FROM ubuntu:22.04

ENV DEBIAN_FRONTEND="noninteractive"

RUN apt-get -y update && apt-get -y upgrade && \
    apt-get install -y software-properties-common && \
    add-apt-repository restricted && \
    apt-get install -y python3 python3-pip python3-lxml aria2 \
    qbittorrent-nox tzdata p7zip-full p7zip-rar xz-utils curl wget pv jq \
    ffmpeg locales neofetch git make g++ gcc automake unzip \
    autoconf libtool libcurl4-openssl-dev \
    libsodium-dev libssl-dev libcrypto++-dev libc-ares-dev \
    libsqlite3-dev libfreeimage-dev swig libboost-all-dev \
    libpthread-stubs0-dev zlib1g-dev libpq-dev libffi-dev && \
    locale-gen en_US.UTF-8 

# Installing Mega SDK Python Binding
ENV PYTHONWARNINGS=ignore
ENV MEGA_SDK_VERSION="4.10.0"
RUN git clone https://github.com/meganz/sdk.git --depth=1 -b v$MEGA_SDK_VERSION ~/home/sdk \
    && cd ~/home/sdk && rm -rf .git \
    && autoupdate -fIv && ./autogen.sh \
    && ./configure --disable-silent-rules --enable-python --disable-examples \
    && make -j$(nproc) \
    && cd bindings/python/ && python3 setup.py bdist_wheel \
    && cd dist && ls && pip3 install --no-cache-dir megasdk-*.whl 

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

# Installing Bot Requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps
RUN apt-get update && apt-get upgrade -y
RUN apt -qq update --fix-missing && \
    apt -qq install -y mediainfo

COPY . .

CMD ["bash", "start.sh"]
