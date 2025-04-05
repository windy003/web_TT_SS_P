FROM python:3.9-slim

WORKDIR /app


# 安装必要的依赖
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    apt-transport-https \
    ca-certificates \
    curl \
    unzip \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 安装Chrome浏览器
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建指定UID的用户（使用1000作为示例，这是很多Linux系统默认用户的UID）
RUN useradd -u 1000 -m myuser && \
    chown -R myuser:myuser /app && \
    chmod -R 755 /app


USER myuser

