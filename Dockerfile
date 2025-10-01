# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 换源加速 - 使用阿里云镜像
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖和时区数据
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 设置时区为上海（北京时间 UTC+8）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制依赖文件
COPY requirements.txt .

# 使用清华源安装 Python 依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data

# 暴露端口
EXPOSE 38506

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=38506", "--server.address=0.0.0.0", "--server.headless=true"]
