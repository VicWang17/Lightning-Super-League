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

## 系统初始化

项目使用分阶段初始化设计。根据你的使用方式选择对应的流程：

### 方式一：本地开发（推荐）

只使用 Docker 启动数据库，后端和前端在本地运行：

```bash
# 1. 启动基础设施（仅 MySQL + Redis）
make infra-up
# 或: docker-compose -f docker-compose.infra.yml up -d

# 2. 初始化基础数据（联赛、球队、球员等）- 正式上线后只需运行一次
make init-system

# 3. 创建新赛季（赛程、积分榜）- 每个新赛季都需运行
make init-season

# 4. 启动后端（本地运行）
make backend

# 5. 启动前端（本地运行）
make frontend
```

### 方式二：完整 Docker 部署

使用 Docker 启动所有服务（前端 + 后端 + 数据库）：

```bash
# 1. 启动所有服务
docker-compose up -d

# 2. 进入后端容器执行初始化
docker-compose exec backend /bin/bash

# 3. 在容器内初始化基础数据
python -m scripts.init_system

# 4. 在容器内创建新赛季
python -m scripts.init_season

# 5. 退出容器
exit
```

**注意**：使用完整 Docker 部署时，不需要 `make infra-up`，因为 `docker-compose.yml` 已经包含了 MySQL 和 Redis。

### 详细说明

#### `make init-system` - 系统基础数据初始化

**用途**: 初始化游戏基础数据，正式上线后**只需运行一次**。

**功能**:
- 删除并重新创建所有数据库表
- 创建 4 个联赛体系（东区/西区/南区/北区）
- 创建 16 个联赛（每个体系 4 个级别）
- 创建 256 支球队和 AI 用户（使用 `data/teams_and_users.py` 中的命名）
- 创建 4608 名球员（每队 18 人）
- **不创建赛季和赛程**

**注意**: 这会删除所有现有数据，请谨慎使用！

#### `make init-season` - 赛季初始化

**用途**: 创建新赛季和完整赛程，**每个新赛季开始时都需要运行**。

**功能**:
- 创建新赛季记录（自动递增赛季编号）
- 生成 30 轮联赛赛程（使用圆形轮转算法 + 随机打乱，确保主客场分布均匀）
- 生成闪电杯赛程（64 队，小组赛 + 淘汰赛）
- 生成杰尼杯赛程（192 队，淘汰赛）
- 创建积分榜记录
- 自动启动赛季

**赛程说明**:
- 联赛：30 天，每天一轮，每队与其他 15 队各主客场一次
- 杯赛：第 6, 9, 12, 15, 18, 21, 24, 27 天进行
- 休赛期：第 31-42 天

### 手动运行脚本

如果需要通过 Python 直接运行：

```bash
cd backend

# 初始化基础数据
python -m scripts.init_system

# 创建新赛季
python -m scripts.init_season
```

### 开发环境登录

使用 `ENV=dev` 运行初始化时，AI 用户的默认密码为 `ai_password`：

```bash
ENV=dev make init-system
```

示例登录账号：
- 邮箱: `ai_east_l1_001@lightning.dev`
- 密码: `ai_password`

所有 AI 用户的密码都是 `ai_password`。

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
