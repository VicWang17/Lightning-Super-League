.PHONY: help infra-up infra-down infra-logs frontend backend dev init-system init-season

# 默认显示帮助
help:
	@echo "Lightning Super League - 开发命令"
	@echo ""
	@echo "基础设施 (Docker):"
	@echo "  make infra-up      启动 MySQL + Redis"
	@echo "  make infra-down    停止基础设施"
	@echo "  make infra-logs    查看基础设施日志"
	@echo ""
	@echo "系统初始化:"
	@echo "  make init-system   初始化基础数据（联赛、球队、用户、球员）"
	@echo "  make init-season   创建新赛季（赛程、积分榜）"
	@echo ""
	@echo "本地开发:"
	@echo "  make frontend      启动前端 (npm run dev)"
	@echo "  make backend       启动后端 (uvicorn)"
	@echo ""
	@echo "一键启动:"
	@echo "  make dev           启动基础设施 + 前端"

# 基础设施管理
infra-up:
	docker-compose -f docker-compose.infra.yml up -d
	@echo "等待数据库初始化..."
	@sleep 5
	@echo "✅ MySQL 和 Redis 已启动"
	@echo "   MySQL: localhost:3306"
	@echo "   Redis: localhost:6379"

# 系统初始化（删除所有数据并重新创建基础数据，不创建赛季）
init-system:
	@echo "⚡ 正在初始化系统基础数据..."
	cd backend && python -m scripts.init_system
	@echo "✅ 系统基础数据初始化完成"
	@echo ""
	@echo "下一步: 创建赛季和赛程"
	@echo "   make init-season"

# 赛季初始化（创建新赛季和完整赛程）
init-season:
	@echo "⚡ 正在初始化赛季..."
	cd backend && python -m scripts.init_season
	@echo "✅ 赛季初始化完成"

infra-down:
	docker-compose -f docker-compose.infra.yml down

infra-logs:
	docker-compose -f docker-compose.infra.yml logs -f

# 本地服务
frontend:
	cd frontend && npm run dev

backend:
	cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 开发模式：启动基础设施 + 前端
dev: infra-up
	@echo "启动前端开发服务器..."
	cd frontend && npm run dev
