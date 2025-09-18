#!/bin/bash
# GitHub Bot 启动脚本

echo "🚀 启动 GitHub Bot 服务..."

# 进入后端目录
cd "$(dirname "$0")/backend"

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行 setup.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 启动服务
echo "📡 服务启动中..."
echo "📱 Web界面: http://localhost:8000"
echo "📖 API文档: http://localhost:8000/docs"
echo "⏹️  停止服务请按 Ctrl+C"
echo ""

python main.py