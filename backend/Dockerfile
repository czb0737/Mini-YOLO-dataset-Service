# backend/Dockerfile
FROM python:3.11-slim

# ========== 使用 trixie 源（Debian 13）==========
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security/ trixie-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list


# 安装系统依赖（关键！）
RUN apt-get update
RUN apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# # 安装 ossutil
# RUN curl -o ossutil64.zip https://gosspublic.alicdn.com/ossutil/1.7.16/ossutil64.zip && \
#     unzip ossutil64.zip && \
#     mv ossutil64 /usr/local/bin/ossutil && \
#     chmod 755 /usr/local/bin/ossutil

WORKDIR /app

# 配置 pip 使用国内镜像源（清华源）
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 或使用阿里云源（也可）
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
# RUN pip config set install.trusted-host mirrors.aliyun.com

# 复制依赖
COPY backend/requirements.txt ./backend-requirements.txt
COPY fc_worker/requirements.txt ./fc-worker-requirements.txt

# 安装依赖（现在会走国内镜像）
RUN pip install --no-cache-dir -r backend-requirements.txt -r fc-worker-requirements.txt

# 复制代码
COPY backend/ ./backend/
COPY fc_worker/ ./fc_worker/

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]