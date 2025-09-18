# GitHub Bot WebUI 🤖

一个智能的GitHub项目推荐系统，支持Web界面配置和多渠道推送。

## 🌟 核心功能

- **🧠 智能推荐**：基于关键词、编程语言、Star数量等多维度推荐
- **⚙️ 灵活配置**：通过Web界面轻松设置偏好和过滤条件
- **📊 评分机制**：智能评分算法，提供推荐理由
- **📱 多渠道推送**：支持邮件、Telegram、企业微信、Slack
- **⏰ 定时任务**：支持自动化每日/每周推荐
- **👥 多用户**：支持多用户独立配置
- **📈 历史记录**：完整的推荐历史和搜索功能

## 🏗️ 系统架构

```
github-bot-webui/
├── backend/                   # FastAPI 后端
│   ├── api/                   # REST API 端点
│   │   ├── auth.py           # 用户认证
│   │   ├── preferences.py    # 偏好配置
│   │   ├── projects.py       # 项目推荐
│   │   └── test_endpoints.py # 测试端点
│   ├── core/                  # 核心配置
│   │   ├── config.py         # 配置管理
│   │   ├── database.py       # 数据库连接
│   │   └── exceptions.py     # 异常处理
│   ├── models/                # 数据库模型
│   │   ├── user.py           # 用户模型
│   │   ├── preference.py     # 偏好模型
│   │   ├── repo_cache.py     # 仓库缓存
│   │   └── recommendation.py # 推荐记录
│   ├── services/              # 业务服务
│   │   ├── github_client.py  # GitHub API客户端
│   │   ├── recommendation_engine.py # 推荐引擎
│   │   └── job_service.py    # 任务执行服务
│   └── utils/                 # 工具类
├── database/                  # SQLite 数据库文件
└── docs/                      # 文档
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- GitHub Personal Access Token
- SQLite（内置）

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/Ludan-daye/robotGetnews
cd github-bot-webui
```

2. **配置环境变量**
```bash
cp .env.sample .env
# 编辑 .env 文件，设置必要的环境变量
```

3. **安装依赖**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **启动后端服务**
```bash
python main.py
```

服务将在 http://localhost:8000 启动

## 📝 配置说明

### 必需的环境变量

在 `.env` 文件中配置以下变量：

```bash
# GitHub API 配置
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_API_BASE_URL=https://api.github.com

# 应用配置
SECRET_KEY=your-super-secret-key
DEBUG=true

# 数据库配置
DATABASE_URL=sqlite:///./database/githubbot.db

# 邮件配置（可选）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Telegram配置（可选）
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# 企业微信配置（可选）
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key
```

### GitHub Token 申请

1. 访问 GitHub Settings > Developer settings > Personal access tokens
2. 点击 "Generate new token"
3. 选择权限：`public_repo` 即可
4. 复制生成的token到 `.env` 文件中

## 🔧 使用指南

### 1. 用户注册和登录

```bash
# 注册新用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myusername",
    "password": "securepassword123",
    "timezone": "Asia/Shanghai"
  }'

# 登录获取Token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

### 2. 配置推荐偏好

```bash
# 创建推荐偏好
curl -X POST http://localhost:8000/api/v1/preferences \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "AI与机器学习项目",
    "keywords": ["machine learning", "artificial intelligence", "deep learning"],
    "languages": ["Python", "JavaScript"],
    "min_stars": 100,
    "notification_channels": ["email"],
    "max_recommendations": 10,
    "enabled": true
  }'
```

### 3. 获取推荐结果

```bash
# 手动触发推荐任务
curl -X POST http://localhost:8000/api/v1/projects/runs/trigger \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force_refresh": false
  }'

# 查看最新推荐
curl -X GET "http://localhost:8000/api/v1/projects/latest?limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 查看历史推荐（支持过滤）
curl -X GET "http://localhost:8000/api/v1/projects/history?keyword=tensorflow&page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 推荐结果示例

```json
{
  "id": 1,
  "repo": {
    "full_name": "tensorflow/tensorflow",
    "description": "An Open Source Machine Learning Framework for Everyone",
    "language": "Python",
    "stargazers_count": 185000,
    "html_url": "https://github.com/tensorflow/tensorflow"
  },
  "score": 0.85,
  "reason": {
    "matched_keywords": ["machine learning"],
    "language_match": true,
    "star_score": 1.0,
    "freshness_score": 0.8,
    "total_score": 0.85
  },
  "created_at": "2024-01-15T09:00:00Z"
}
```

## 🧮 评分算法

推荐引擎使用多维度评分算法：

- **关键词匹配** (40%)：在项目名称、描述中匹配关键词
- **编程语言** (25%)：匹配用户偏好的编程语言
- **项目热度** (20%)：基于Star数量的对数评分
- **活跃程度** (10%)：基于最近更新时间
- **主题标签** (5%)：匹配GitHub topics标签

## 📊 API文档

启动服务后，访问以下地址查看完整API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/register` | POST | 用户注册 |
| `/api/v1/auth/login` | POST | 用户登录 |
| `/api/v1/auth/me` | GET | 获取当前用户信息 |
| `/api/v1/preferences` | GET/POST/PUT | 偏好配置管理 |
| `/api/v1/projects/latest` | GET | 获取最新推荐 |
| `/api/v1/projects/history` | GET | 查询历史推荐 |
| `/api/v1/projects/runs/trigger` | POST | 手动触发推荐 |
| `/api/v1/projects/channels` | GET | 查看通知渠道状态 |

## 🧪 测试功能

系统提供了测试端点，可以使用演示数据快速体验功能：

```bash
# 1. 种入演示数据
curl -X POST http://localhost:8000/api/v1/test/seed-demo-data \
  -H "Authorization: Bearer YOUR_TOKEN"

# 2. 测试推荐引擎
curl -X POST http://localhost:8000/api/v1/test/test-recommendation-engine \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔍 故障排查

### 常见问题

1. **GitHub API限制**
   - 确保GitHub Token有效且权限正确
   - 注意API调用频率限制（每小时5000次）

2. **数据库错误**
   - 检查数据库文件权限
   - 确保数据库目录存在

3. **依赖问题**
   - 确保Python版本≥3.9
   - 重新安装依赖：`pip install -r requirements.txt`

### 日志查看

```bash
# 查看详细日志
python main.py --log-level DEBUG
```

## 🔮 后续开发计划

- [ ] React前端界面开发
- [ ] 定时任务调度器
- [ ] 多种通知渠道集成
- [ ] 推荐算法优化
- [ ] 用户行为分析
- [ ] Docker容器化部署

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！
