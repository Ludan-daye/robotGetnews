#!/bin/bash

# GitHub Bot WebUI 使用示例脚本
# 本脚本演示如何使用API进行用户注册、配置偏好、获取推荐等操作

BASE_URL="http://localhost:8000/api/v1"
CONTENT_TYPE="Content-Type: application/json"

echo "🤖 GitHub Bot WebUI 使用示例"
echo "================================"

# 检查服务是否运行
echo "1️⃣ 检查服务状态..."
if curl -s "$BASE_URL/health" > /dev/null; then
    echo "✅ 服务运行正常"
else
    echo "❌ 服务未运行，请先启动后端服务"
    echo "启动命令: cd backend && python main.py"
    exit 1
fi

# 注册用户
echo -e "\n2️⃣ 注册新用户..."
USER_EMAIL="demo@example.com"
USER_PASSWORD="demo123456"
USERNAME="demouser"

REGISTER_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/register" \
    -H "$CONTENT_TYPE" \
    -d "{
        \"email\": \"$USER_EMAIL\",
        \"username\": \"$USERNAME\",
        \"password\": \"$USER_PASSWORD\",
        \"timezone\": \"Asia/Shanghai\"
    }")

if echo "$REGISTER_RESPONSE" | grep -q "email"; then
    echo "✅ 用户注册成功"
else
    echo "⚠️ 用户可能已存在，继续登录..."
fi

# 用户登录
echo -e "\n3️⃣ 用户登录..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
    -H "$CONTENT_TYPE" \
    -d "{
        \"email\": \"$USER_EMAIL\",
        \"password\": \"$USER_PASSWORD\"
    }")

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ 登录失败，请检查用户名密码"
    exit 1
else
    echo "✅ 登录成功，获取到Token"
fi

AUTH_HEADER="Authorization: Bearer $TOKEN"

# 获取用户信息
echo -e "\n4️⃣ 获取用户信息..."
USER_INFO=$(curl -s -X GET "$BASE_URL/auth/me" -H "$AUTH_HEADER")
echo "$USER_INFO" | python3 -m json.tool

# 种入演示数据
echo -e "\n5️⃣ 种入演示数据..."
SEED_RESPONSE=$(curl -s -X POST "$BASE_URL/test/seed-demo-data" -H "$AUTH_HEADER")
echo "$SEED_RESPONSE" | python3 -m json.tool

# 创建推荐偏好
echo -e "\n6️⃣ 创建推荐偏好..."
PREFERENCE_RESPONSE=$(curl -s -X POST "$BASE_URL/preferences" \
    -H "$AUTH_HEADER" \
    -H "$CONTENT_TYPE" \
    -d '{
        "name": "机器学习与AI项目",
        "description": "专注于机器学习、深度学习和人工智能相关的开源项目",
        "keywords": ["machine learning", "deep learning", "artificial intelligence", "AI"],
        "languages": ["Python", "JavaScript"],
        "min_stars": 100,
        "max_stars": null,
        "notification_channels": ["email"],
        "max_recommendations": 10,
        "enabled": true
    }')

echo "$PREFERENCE_RESPONSE" | python3 -m json.tool

# 测试推荐引擎
echo -e "\n7️⃣ 测试推荐引擎..."
RECOMMENDATION_TEST=$(curl -s -X POST "$BASE_URL/test/test-recommendation-engine" -H "$AUTH_HEADER")
echo "$RECOMMENDATION_TEST" | python3 -m json.tool

# 获取最新推荐
echo -e "\n8️⃣ 获取最新推荐结果..."
LATEST_RECOMMENDATIONS=$(curl -s -X GET "$BASE_URL/projects/latest?limit=3" -H "$AUTH_HEADER")
echo "$LATEST_RECOMMENDATIONS" | python3 -m json.tool

# 查看推荐历史
echo -e "\n9️⃣ 查看推荐历史..."
HISTORY=$(curl -s -X GET "$BASE_URL/projects/history?page=1&page_size=3&keyword=tensorflow" -H "$AUTH_HEADER")
echo "$HISTORY" | python3 -m json.tool

# 查看通知渠道状态
echo -e "\n🔟 查看通知渠道状态..."
CHANNELS=$(curl -s -X GET "$BASE_URL/projects/channels" -H "$AUTH_HEADER")
echo "$CHANNELS" | python3 -m json.tool

echo -e "\n🎉 演示完成！"
echo "================================"
echo "📊 你可以访问以下地址查看API文档："
echo "   - Swagger UI: http://localhost:8000/docs"
echo "   - ReDoc: http://localhost:8000/redoc"
echo ""
echo "🔧 下一步你可以："
echo "   1. 配置真实的GitHub Token进行实际推荐"
echo "   2. 设置邮件/Telegram等通知渠道"
echo "   3. 创建更多偏好配置"
echo "   4. 集成到你的工作流程中"
echo ""
echo "Token (保存此Token用于后续API调用):"
echo "$TOKEN"