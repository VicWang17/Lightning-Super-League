.PHONY: help infra-up infra-down infra-logs frontend backend match-engine dev init-system init-season dev-bootstrap console sim-status sim-next sim-matchday sim-season sim-results

# 加载根目录 .env（如果存在）
ifneq (,$(wildcard ./.env))
    include .env
    export
endif

# 检测 Python（优先使用虚拟环境）
# 对于在项目根目录执行的命令
ifneq (,$(wildcard backend/.venv/bin/python))
    PYTHON = backend/.venv/bin/python
else ifneq (,$(shell which python3 2>/dev/null))
    PYTHON = python3
else
    PYTHON = python
endif

# 对于 cd backend 后执行的命令
ifneq (,$(wildcard backend/.venv/bin/python))
    PYTHON_IN_BACKEND = .venv/bin/python
else ifneq (,$(shell which python3 2>/dev/null))
    PYTHON_IN_BACKEND = python3
else
    PYTHON_IN_BACKEND = python
endif

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
	@echo "  make dev-bootstrap 一键重置基础数据并创建赛季（会删除数据）"
	@echo ""
	@echo "本地开发:"
	@echo "  make frontend      启动前端 (npm run dev)"
	@echo "  make backend       启动后端 (uvicorn)"
	@echo "  make match-engine  启动 Go 比赛引擎服务"
	@echo "  make console       打开一键开发控制台"
	@echo "  make sim-status    查看当前测试状态"
	@echo "  make sim-next      推进下一个虚拟事件"
	@echo "  make sim-matchday  推进到下一个比赛日并打印结果"
	@echo "  make sim-season    快进到赛季结束"
	@echo "  make sim-results   显示最近比赛结果"
	@echo ""
	@echo "一键启动:"
	@echo "  make dev           启动基础设施 + 前端"

# 基础设施管理
infra-up:
	docker-compose -f docker-compose.infra.yml up -d
	@echo "等待数据库初始化..."
	@sleep 5
	@echo "✅ MySQL 和 Redis 已启动"
	@echo "   MySQL: localhost:$(DB_PORT)"
	@echo "   Redis: localhost:$(REDIS_PORT)"

# 系统初始化（删除所有数据并重新创建基础数据，不创建赛季）
init-system:
	@echo "⚡ 正在初始化系统基础数据..."
	cd backend && $(PYTHON_IN_BACKEND) -m scripts.init_system
	@echo "✅ 系统基础数据初始化完成"
	@echo ""
	@echo "下一步: 创建赛季和赛程"
	@echo "   make init-season"

# 赛季初始化（创建新赛季和完整赛程）
init-season:
	@echo "⚡ 正在初始化赛季..."
	cd backend && $(PYTHON_IN_BACKEND) -m scripts.init_season
	@echo "✅ 赛季初始化完成"

infra-down:
	docker-compose -f docker-compose.infra.yml down

infra-logs:
	docker-compose -f docker-compose.infra.yml logs -f

# 本地服务
frontend:
	cd frontend && VITE_API_URL=$(VITE_API_URL) npx vite --host 0.0.0.0 --port $(FRONTEND_PORT)

backend:
	cd backend && $(PYTHON_IN_BACKEND) -m uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

match-engine:
	cd match-engine && go run ./cmd/server

dev-bootstrap: infra-up
	@echo "⚠️  这会重建开发数据库数据..."
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m alembic upgrade head
	cd backend && ENV=dev PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.init_system
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.init_season
	@echo "✅ 开发数据和第一个赛季已准备好"

console:
	$(PYTHON) backend/scripts/dev_console.py

sim-status:
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.dev_sim status

sim-next:
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.dev_sim next-event

sim-matchday:
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.dev_sim matchday

sim-season:
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.dev_sim season

sim-results:
	cd backend && PYTHONPATH=. $(PYTHON_IN_BACKEND) -m scripts.dev_sim results

# 开发模式：启动基础设施 + 前端
dev: infra-up
	@echo "启动前端开发服务器..."
	cd frontend && VITE_API_URL=$(VITE_API_URL) npx vite --host 0.0.0.0 --port $(FRONTEND_PORT)
