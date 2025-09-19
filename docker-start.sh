#!/bin/bash

# GitHub Bot Docker 启动脚本
# 确保应用程序的完整性部署

set -e

echo "🚀 GitHub Bot Docker 部署开始..."

# 检查Docker和Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "⚠️  未找到 .env 文件"
    if [ -f .env.docker ]; then
        echo "📋 复制 .env.docker 到 .env"
        cp .env.docker .env
        echo "⚙️  请编辑 .env 文件，填写必要的配置（如 GITHUB_TOKEN）"
        echo "📖 配置说明请参考 .env 文件中的注释"
        read -p "按回车键继续（确保已配置 .env 文件）..."
    else
        echo "❌ 未找到环境配置文件"
        exit 1
    fi
fi

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data/database
mkdir -p data/logs

# 停止并清理旧容器
echo "🧹 清理旧容器..."
docker-compose down --remove-orphans 2>/dev/null || true

# 构建并启动服务
echo "🔨 构建 Docker 镜像..."
docker-compose build --no-cache

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 检查后端健康状态
echo "❤️  检查后端健康状态..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo "✅ 后端服务健康检查通过"
        break
    fi

    if [ $attempt -eq $max_attempts ]; then
        echo "❌ 后端服务启动失败"
        echo "📝 查看后端日志:"
        docker-compose logs backend
        exit 1
    fi

    echo "⏳ 等待后端服务启动... ($attempt/$max_attempts)"
    sleep 5
    ((attempt++))
done

# 检查前端服务
echo "🌐 检查前端服务..."
if curl -f http://localhost/ > /dev/null 2>&1; then
    echo "✅ 前端服务运行正常"
else
    echo "⚠️  前端服务可能有问题，请检查日志"
    docker-compose logs frontend
fi

echo ""
echo "🎉 GitHub Bot 部署完成!"
echo ""
echo "📱 访问地址:"
echo "   前端界面: http://localhost"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "📝 有用的命令:"
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo "   查看状态: docker-compose ps"
echo ""
echo "🔧 如果遇到问题:"
echo "   1. 检查 .env 文件配置"
echo "   2. 查看服务日志: docker-compose logs"
echo "   3. 确保端口 80 和 8000 未被占用"
echo ""