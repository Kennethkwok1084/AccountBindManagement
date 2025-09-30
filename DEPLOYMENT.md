# 校园网账号管理系统 - 部署指南

## 方案一：Docker 部署（推荐）

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+

### 快速部署

```bash
# 1. 克隆代码
git clone <repository-url>
cd Account_manager

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 停止服务
docker-compose down
```

### 访问地址
- http://localhost:8506

### 数据持久化
- 数据库：`./data/account_manager.db`
- 导出文件：`./exports/`

---

## 方案二：Linux 服务器部署

### 1. 安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python311 python311-pip
```

### 2. 部署应用

```bash
# 创建应用目录
sudo mkdir -p /opt/account_manager
cd /opt/account_manager

# 复制代码
sudo cp -r /path/to/Account_manager/* .

# 创建虚拟环境
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt

# 设置权限
sudo chown -R www-data:www-data /opt/account_manager
```

### 3. 配置 systemd 服务

```bash
# 复制服务文件
sudo cp deploy/account-manager.service /etc/systemd/system/

# 重载配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start account-manager

# 开机自启
sudo systemctl enable account-manager

# 查看状态
sudo systemctl status account-manager
```

### 4. 配置 Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name account.example.com;

    location / {
        proxy_pass http://localhost:8506;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

---

## 方案三：Windows 服务器部署

### 1. 安装 Python

下载并安装 [Python 3.11+](https://www.python.org/downloads/)

### 2. 安装依赖

```cmd
cd D:\Account_manager
pip install -r requirements.txt
```

### 3. 启动服务

双击运行 `start_service.bat`

### 4. 配置为 Windows 服务（可选）

使用 NSSM (Non-Sucking Service Manager):

```cmd
# 下载 NSSM: https://nssm.cc/download

# 安装服务
nssm install AccountManager "C:\Python311\python.exe" "-m streamlit run app.py --server.port=8506"
nssm set AccountManager AppDirectory "D:\Account_manager"

# 启动服务
nssm start AccountManager
```

---

## 方案四：云平台部署

### Streamlit Cloud（免费）

1. 推送代码到 GitHub
2. 访问 [share.streamlit.io](https://share.streamlit.io)
3. 连接 GitHub 仓库并部署

### Railway / Render

1. 连接 GitHub 仓库
2. 配置启动命令：`streamlit run app.py --server.port=$PORT`
3. 自动部署

---

## 性能优化建议

### 1. 数据库优化

```bash
# 定期清理日志
sqlite3 data/account_manager.db "VACUUM;"

# 备份数据库
cp data/account_manager.db data/account_manager_backup_$(date +%Y%m%d).db
```

### 2. 内存优化

添加到启动命令：
```bash
streamlit run app.py --server.maxUploadSize=200 --server.enableXsrfProtection=false
```

### 3. 并发优化

使用 Nginx + 多实例：
```bash
# 启动多个实例
streamlit run app.py --server.port=8506 &
streamlit run app.py --server.port=8507 &
streamlit run app.py --server.port=8508 &

# Nginx 负载均衡
upstream streamlit_backend {
    server 127.0.0.1:8506;
    server 127.0.0.1:8507;
    server 127.0.0.1:8508;
}
```

---

## 监控与维护

### 健康检查

```bash
curl http://localhost:8506/_stcore/health
```

### 日志查看

```bash
# Docker
docker-compose logs -f --tail=100

# systemd
sudo journalctl -u account-manager -f

# Windows
查看控制台输出
```

### 自动备份脚本

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/account_manager"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp data/account_manager.db $BACKUP_DIR/account_manager_$DATE.db

# 保留最近30天的备份
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

---

## 故障排查

### 端口被占用

```bash
# Linux
sudo lsof -i :8506
sudo kill -9 <PID>

# Windows
netstat -ano | findstr :8506
taskkill /PID <PID> /F
```

### 数据库锁定

```bash
# 关闭所有连接
rm -f data/account_manager.db-wal
rm -f data/account_manager.db-shm
```

### 内存不足

```bash
# 增加系统交换空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 安全建议

1. **防火墙配置**
   ```bash
   # 仅允许内网访问
   sudo ufw allow from 192.168.0.0/16 to any port 8506
   ```

2. **反向代理 + SSL**
   - 使用 Nginx/Caddy
   - 配置 Let's Encrypt 证书

3. **定期更新**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

4. **数据加密**
   - 敏感数据库字段加密
   - 文件传输使用 HTTPS

---

## 联系支持

- 文档：查看 CLAUDE.md
- 问题反馈：GitHub Issues
- 版本：v2.0