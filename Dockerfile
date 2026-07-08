FROM python:3.11-slim

# 系统依赖：ffmpeg 用于视频缩略图和时长检测
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt requests psutil

# 复制项目文件
COPY . .

EXPOSE 8891

CMD ["python", "main.py"]
