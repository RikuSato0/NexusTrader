FROM python:3.11-slim-bullseye

RUN pip install --no-cache-dir --upgrade pip
# 安装 git 和 build-essential
RUN apt-get update && apt-get install -y \
    nano \
    git \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN npm install pm2 -g

WORKDIR /app

RUN git clone https://github.com/Crypto7816/tradebot.git

WORKDIR /app/tradebot

RUN mkdir keys && \
    touch keys/config.cfg && \
    touch keys/server-cert.pem && \
    touch keys/server-key.pem

RUN pip install --no-cache-dir -r requirements.txt
