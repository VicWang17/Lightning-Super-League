# ⚡ 闪电超级联赛 (Lightning Super League)

一款在线足球经理游戏，打造你的足球帝国，征服绿茵场。

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL + Redis
- **前端**: React + TypeScript + Vite + Tailwind CSS
- **基础设施**: Docker + Docker Compose

## 快速开始

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- Make (可选，用于简化命令)

### 启动项目

#### 方式一：Docker 全栈启动（推荐）

```bash
# 使用 Make (推荐)
make build    # 构建镜像
make up       # 启动服务
make dev      # 启动并查看日志

# 或使用 Docker Compose 直接启动
docker-compose up -d    # 后台启动
docker-compose up       # 前台启动 (查看日志)
```

#### 方式二：本地独立启动后端

适用于仅开发后端或前端已单独启动的场景：

```bash
# 1. 先启动基础设施（MySQL + Redis）
make infra-up

# 2. 启动后端服务
make backend

# 或手动启动（需在 backend 目录下）
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**本地启动后端的前提条件：**
- Python 3.11+
- 安装依赖：`pip install -r backend/requirements.txt`
- 配置环境变量（复制 `backend/.env.example` 到 `backend/.env`）

服务启动后访问:
- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- MySQL: localhost:3306
- Redis: localhost:6379

### 常用命令

```bash
make logs           # 查看所有日志
make logs-backend   # 查看后端日志
make logs-frontend  # 查看前端日志
make shell-backend  # 进入后端容器
make shell-db       # 进入 MySQL
make down           # 停止服务
make clean          # 清理所有数据
```

## 项目结构

```
.
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── config.py     # 配置管理
│   │   ├── dependencies.py  # 依赖注入
│   │   ├── core/         # 核心工具
│   │   ├── models/       # 数据库模型
│   │   ├── schemas/      # Pydantic 模型
│   │   ├── routers/      # API 路由
│   │   ├── services/     # 业务逻辑
│   │   └── repositories/ # 数据访问
│   ├── alembic/          # 数据库迁移
│   ├── tests/            # 测试
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/             # React 前端
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── pages/        # 页面
│   │   ├── stores/       # Zustand 状态
│   │   ├── hooks/        # 自定义 Hooks
│   │   ├── api/          # API 层
│   │   └── styles/       # 样式
│   ├── public/
│   ├── Dockerfile
│   └── package.json
│
├── docker/               # Docker 配置
│   ├── mysql/init/       # 数据库初始化脚本
│   └── nginx/            # Nginx 配置
│
├── docker-compose.yml    # Docker Compose 配置
└── Makefile             # 开发命令
```

## 开发指南

### 后端开发

```bash
# 进入后端容器
docker-compose exec backend /bin/bash

# 运行迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 运行测试
pytest
```

### 前端开发

```bash
# 本地开发 (不使用 Docker)
cd frontend
npm install
npm run dev

# 或进入前端容器
docker-compose exec frontend /bin/sh
```

## 环境变量

复制 `.env.example` 到 `.env` 并根据需要修改:

```bash
cp .env.example .env
```

## 设计文档

- [产品需求文档 (PRD)](design/prd.md)
- [技术选型文档](design/TECH-STACK.md)
- [UI 设计文档](design/UI-DESIGN.md)
- [开发路线图](design/roadmap.md)

## License

MIT
