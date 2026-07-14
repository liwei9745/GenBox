FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    GENBOX_NO_BROWSER=1

# 系统依赖：ffmpeg 用于视频缩略图和时长检测
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 genbox && \
    mkdir -p /app/storage /app/static && \
    chown -R genbox:genbox /app

WORKDIR /app

# 先复制依赖文件，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制项目文件
COPY --chown=genbox:genbox . .

# 切换到非 root 用户
USER genbox

EXPOSE 8891

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8891/api/setup/status', timeout=5)" || exit 1

CMD ["python", "main.py"]
