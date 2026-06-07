#!/usr/bin/env bash
set -e

echo "======================================"
echo " 抖音来客后台智能体系统 · 启动脚本"
echo "======================================"

# 检查 .env
if [ ! -f .env ]; then
  echo "⚠️  未发现 .env 文件，从模板创建..."
  cp .env.example .env
  echo "✏️  请编辑 .env 填入 ANTHROPIC_API_KEY 后重新运行"
  exit 1
fi

# 安装依赖
if ! python -c "import fastapi" 2>/dev/null; then
  echo "📦 安装 Python 依赖..."
  pip install -r requirements.txt -q
fi

# 演示模式 or 服务模式
if [ "$1" = "--demo" ]; then
  echo ""
  echo "🎬 运行演示模式..."
  python main.py
else
  echo ""
  echo "🚀 启动 HTTP 服务..."
  echo "   API 文档:   http://localhost:8000/docs"
  echo "   健康检查:   http://localhost:8000/api/v1/health"
  echo "   管理面板:   打开 dashboard.html"
  echo ""
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
