# 不从空白系统开始，而是使用一个已经安装 Python 3.13 的精简 Linux 镜像
# slim 表示删除了许多非必要系统工具，镜像更小
FROM python:3.13-slim

# Python 不生成 pyc 缓存，并立即输出日志。
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# 设置工作目录
WORKDIR /app

# onnxruntime 执行 OCR 时可能需要 OpenMP 运行库。
# 安装 Linux 系统依赖
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户，降低容器运行权限。
RUN useradd \
    --create-home \
    --uid 10001 \
    appuser

# 先安装锁定依赖。
# 只要锁文件没有变化，Docker 就可以复用这一层缓存。
COPY requirements-linux.lock ./requirements.lock

RUN python -m pip install \
    --require-hashes \
    --requirement requirements.lock

# 复制项目安装所需文件。
COPY pyproject.toml README.md main.py ./
COPY app ./app

# 安装当前项目，但不重新解析依赖。
RUN python -m pip install \
    --no-deps \
    --no-build-isolation \
    .

# 创建向量数据库和模型缓存目录。
RUN mkdir -p /app/.chroma_db /home/appuser/.cache \
    && chown -R appuser:appuser /app /home/appuser

# 后续命令使用普通用户执行。
USER appuser

EXPOSE 8000

# Docker 定期检查 FastAPI 进程是否可以正常响应。
HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=60s \
    --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/live', timeout=3)"]

# 使用 pyproject.toml 注册的 start 命令启动服务。
CMD ["start"]