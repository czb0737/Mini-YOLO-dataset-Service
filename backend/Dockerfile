# backend/Dockerfile
FROM python:3.11-slim

# ========== Use trixie source (Debian 13) ==========
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security/ trixie-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ trixie-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list


# Install system dependencies (critical!)
RUN apt-get update
RUN apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# # Install ossutil
# RUN curl -o ossutil64.zip https://gosspublic.alicdn.com/ossutil/1.7.16/ossutil64.zip && \
#     unzip ossutil64.zip && \
#     mv ossutil64 /usr/local/bin/ossutil && \
#     chmod 755 /usr/local/bin/ossutil

WORKDIR /app

# Configure pip to use domestic mirror source (Tsinghua mirror)
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# Or use Alibaba Cloud source (also works)
# RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
# RUN pip config set install.trusted-host mirrors.aliyun.com

# Copy dependencies
COPY backend/requirements.txt ./backend-requirements.txt
COPY fc_worker/requirements.txt ./fc-worker-requirements.txt

# Install dependencies (will now use domestic mirror)
RUN pip install --no-cache-dir -r backend-requirements.txt -r fc-worker-requirements.txt

# Copy code
COPY backend/ ./backend/
COPY fc_worker/ ./fc_worker/

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]