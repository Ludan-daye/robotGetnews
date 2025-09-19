# 🐳 GitHub Bot Docker 部署指南

这份指南将帮你使用Docker快速部署GitHub项目推荐机器人，确保应用的完整性和可移植性。

## 📋 系统要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 至少 2GB 可用内存
- 端口 80 和 8000 未被占用

## 🚀 快速启动

### 1. 克隆项目

```bash
git clone https://github.com/Ludan-daye/robotGetnews.git
cd robotGetnews
```

### 2. 配置环境变量

```bash
# 复制环境配置模板
cp .env.docker .env

# 编辑配置文件
nano .env  # 或使用其他编辑器
```

### 3. 必要配置

在 `.env` 文件中至少需要配置：

```bash
# 应用安全密钥 (必须修改!)
SECRET_KEY=your-super-secret-key-here

# GitHub API Token (必填)
GITHUB_TOKEN=ghp_your_github_token_here
```

### 4. 一键启动

```bash
# 使用自动化脚本
./docker-start.sh
```

或手动启动：

```bash
# 创建数据目录
mkdir -p data/database data/logs

# 启动服务
docker-compose up -d
```

### 5. 访问应用

- **前端界面**: http://localhost
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 🔧 详细配置

### 环境变量说明

| 变量名 | 说明 | 是否必填 | 默认值 |
|--------|------|----------|--------|
| `SECRET_KEY` | JWT加密密钥 | ✅ 是 | - |
| `GITHUB_TOKEN` | GitHub API Token | ✅ 是 | - |
| `SMTP_HOST` | 邮件服务器地址 | ❌ 否 | - |
| `SMTP_USERNAME` | 邮件用户名 | ❌ 否 | - |
| `SMTP_PASSWORD` | 邮件密码 | ❌ 否 | - |
| `TELEGRAM_BOT_TOKEN` | Telegram机器人Token | ❌ 否 | - |

### GitHub Token 获取

1. 访问 [GitHub Settings → Tokens](https://github.com/settings/tokens)
2. 点击 "Generate new token (classic)"
3. 设置描述：`GitHub Bot API Access`
4. 选择权限：`public_repo` (或 `repo` 如需私有仓库)
5. 生成并复制Token

### 邮件通知配置 (可选)

如需邮件推送功能，配置SMTP：

```bash
# Gmail 示例
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # 使用应用专用密码
SMTP_TLS=true
EMAIL_FROM=your-email@gmail.com
```

## 🛠️ 常用命令

### 服务管理

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 完全清理（包括数据）
docker-compose down -v
```

### 更新应用

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build
```

### 数据备份

```bash
# 备份数据库
cp data/database/githubbot.db backup/githubbot-$(date +%Y%m%d).db

# 备份整个数据目录
tar -czf backup/data-$(date +%Y%m%d).tar.gz data/
```

## 📊 服务架构

```
┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │
│   (Nginx:80)    │────│   (FastAPI:8000)│
│                 │    │                 │
└─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Database      │
                       │   (SQLite)      │
                       └─────────────────┘
```

### 容器说明

- **frontend**: Nginx容器，提供Web界面和API代理
- **backend**: Python FastAPI容器，提供API服务
- **数据持久化**: SQLite数据库和日志存储在宿主机

## 🔍 故障排除

### 常见问题

#### 1. 端口被占用

```bash
# 检查端口占用
netstat -tulpn | grep :80
netstat -tulpn | grep :8000

# 修改端口映射（docker-compose.yml）
ports:
  - "8080:80"    # 前端改为8080端口
  - "8001:8000"  # 后端改为8001端口
```

#### 2. 服务启动失败

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend

# 检查配置文件
cat .env
```

#### 3. GitHub API限制

```bash
# 检查API配额
curl -H "Authorization: token YOUR_TOKEN" \
  https://api.github.com/rate_limit
```

#### 4. 权限问题

```bash
# 确保数据目录权限
sudo chown -R $USER:$USER data/
chmod -R 755 data/
```

### 健康检查

```bash
# 检查后端健康状态
curl http://localhost:8000/api/v1/health

# 检查前端服务
curl http://localhost/

# 检查容器健康状态
docker-compose ps
```

## 🔒 安全建议

1. **修改默认密钥**：务必修改 `SECRET_KEY`
2. **网络安全**：生产环境建议使用HTTPS
3. **Token权限**：GitHub Token使用最小权限原则
4. **定期更新**：保持Docker镜像和依赖更新
5. **备份数据**：定期备份数据库和配置

## 📈 性能优化

### 资源限制

```yaml
# docker-compose.yml 中添加资源限制
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
```

### 缓存优化

```bash
# 启用Redis缓存 (可选)
# 在 .env 中添加
REDIS_URL=redis://redis:6379/0
```

## 📞 支持

如遇问题，请：

1. 查看日志：`docker-compose logs`
2. 检查配置：确保 `.env` 文件正确
3. 提交Issue：[GitHub Issues](https://github.com/Ludan-daye/robotGetnews/issues)

---

🎉 享受使用GitHub项目推荐机器人！