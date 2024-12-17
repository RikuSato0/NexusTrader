#!/bin/bash

# 创建密钥目录（如果不存在）
KEYS_DIR=".keys"
mkdir -p "$KEYS_DIR"

# 如果密钥文件不存在，生成一个新的密钥
KEY_FILE="$KEYS_DIR/master.key"
if [ ! -f "$KEY_FILE" ]; then
    openssl rand -hex 32 > "$KEY_FILE"
    chmod 600 "$KEY_FILE"
    echo "✅ Generated new master key at $KEY_FILE"
fi

# 生成随机密码并保存为二进制密钥文件
read -sp "Please input Redis password: " REDIS_PASSWORD
echo

# 验证密码强度
if [ ${#REDIS_PASSWORD} -lt 8 ]; then
    echo "❌ Password must be at least 8 characters"
    exit 1
fi

# 使用主密钥文件加密 Redis 密码
echo "$REDIS_PASSWORD" | openssl enc -aes-256-cbc -salt -pbkdf2 -pass file:"$KEY_FILE" -out "$KEYS_DIR/redis.key"

echo "✅ Redis key has been securely saved to $KEYS_DIR/redis.key"

# 解密 Redis 密码并导出为环境变量
if [ -f "$KEYS_DIR/redis.key" ]; then
    export REDIS_PASSWORD=$(openssl enc -d -aes-256-cbc -salt -pbkdf2 -pass file:"$KEY_FILE" -in "$KEYS_DIR/redis.key")
else
    echo "❌ Redis key file not found. Please run the setup first."
    exit 1
fi

# 启动 Docker Compose
docker-compose up -d redis

echo "✅ Redis container started successfully"
