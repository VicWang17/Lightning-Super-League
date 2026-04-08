# 闪电超级联赛 - 技术选型文档

## 1. 技术选型总览

### 1.1 技术栈全景

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Frontend)                        │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ React 18 │ │ TypeScript │ │  Vite    │ │ Tailwind CSS     │  │
│  └──────────┘ └────────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                         通信层 (API/Realtime)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────────────┐  │
│  │ HTTP/REST  │ │ WebSocket  │ │ JWT Auth                   │  │
│  └────────────┘ └────────────┘ └────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                         后端层 (Backend)                         │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ FastAPI  │ │ SQLAlchemy │ │APScheduler│ │ Python 3.11+    │  │
│  └──────────┘ └────────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                         数据层 (Data)                            │
│  ┌──────────┐ ┌────────────┐                                    │
│  │  MySQL   │ │   Redis    │                                    │
│  │  8.0+    │ │  (Cache)   │                                    │
│  └──────────┘ └────────────┘                                    │
├─────────────────────────────────────────────────────────────────┤
│                       基础设施 (Infrastructure)                  │
│  ┌──────────┐ ┌────────────┐ ┌──────────┐                      │
│  │  Docker  │ │Docker Compose│ │  Nginx   │                      │
│  └──────────┘ └────────────┘ └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 版本要求

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 支持异步语法、类型提示 |
| Node.js | 18+ | LTS 版本，支持 Vite |
| MySQL | 8.0+ | 支持窗口函数、JSON 类型 |
| Redis | 7+ | 缓存、Session、实时数据 |

---

## 2. 后端技术栈详解

### 2.1 核心框架：FastAPI

```
选择理由：
- 原生异步支持 (async/await)，高并发性能优秀
- 自动 API 文档生成 (Swagger UI / ReDoc)
- Pydantic 模型校验，类型安全
- Python 生态丰富，开发效率高
```

**关键依赖：**
```python
fastapi==0.104.*
uvicorn[standard]==0.24.*      # ASGI 服务器
pydantic==2.5.*                # 数据校验
pydantic-settings==2.1.*       # 配置管理
python-jose[cryptography]==3.3.*  # JWT
passlib[bcrypt]==1.7.*         # 密码哈希
```

### 2.2 数据库：MySQL 8.0+

```
选择理由：
- 团队熟悉度高，运维简单
- 8.0+ 支持窗口函数（积分榜排名）
- 云厂商支持完善
- 招聘市场人才充足
```

**ORM：SQLAlchemy 2.0**
```python
sqlalchemy[asyncio]==2.0.*     # 异步 ORM
asyncmy==0.2.*                 # MySQL 异步驱动
alembic==1.12.*                # 数据库迁移
```

**关键设计：**
- 使用异步会话 (`AsyncSession`) 处理并发请求
- 复杂统计查询（如排名）使用原生 SQL + 窗口函数
- JSON 字段存储战术配置、比赛事件（MySQL 8.0 JSON 类型）

### 2.3 缓存：Redis

**用途：**
| 场景 | 实现 |
|------|------|
| 用户 Session | JWT 黑名单、刷新 Token |
| 热点数据缓存 | 球员列表、积分榜（TTL: 5分钟） |
| 分布式锁 | 转会竞价防止超卖 |
| 实时数据 | 在线人数、比赛文字直播缓存 |

```python
redis==5.0.*
```

### 2.4 定时任务：APScheduler

```
用途：
- 每两天触发比赛日
- 赛季节点处理（开始、结束、升降级）
- 定时清理过期数据
```

```python
apscheduler==3.10.*
```

### 2.5 后端目录结构

```
backend/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理 (Pydantic Settings)
│   ├── dependencies.py         # 依赖注入
│   │
│   ├── routers/                # API 路由层
│   │   ├── auth.py             # 认证相关
│   │   ├── teams.py            # 球队管理
│   │   ├── players.py          # 球员管理
│   │   ├── matches.py          # 比赛系统
│   │   ├── leagues.py          # 联赛/积分榜
│   │   ├── transfers.py        # 转会市场
│   │   └── scheduler.py        # 定时任务触发
│   │
│   ├── services/               # 业务逻辑层
│   │   ├── match_engine.py     # 比赛模拟引擎（预留 Go 接口）
│   │   ├── league_service.py   # 联赛逻辑
│   │   ├── transfer_service.py # 转会逻辑
│   │   ├── finance_service.py  # 经济系统
│   │   └── event_bus.py        # 事件总线（预留消息队列接口）
│   │
│   ├── repositories/           # 数据访问层
│   │   ├── base.py             # 基础 CRUD
│   │   ├── user_repo.py
│   │   ├── team_repo.py
│   │   └── match_repo.py
│   │
│   ├── models/                 # 数据库模型 (SQLAlchemy)
│   │   ├── user.py
│   │   ├── team.py
│   │   ├── player.py
│   │   ├── match.py
│   │   └── league.py
│   │
│   ├── schemas/                # Pydantic 模型 (DTO)
│   │   ├── user.py
│   │   ├── team.py
│   │   └── match.py
│   │
│   └── core/                   # 基础设施
│       ├── security.py         # JWT、密码处理
│       ├── exceptions.py       # 自定义异常
│       └── utils.py            # 工具函数
│
├── alembic/                    # 数据库迁移脚本
│   └── versions/
│
├── tests/                      # 测试
│   ├── unit/
│   └── integration/
│
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 3. 前端技术栈详解

### 3.1 核心框架：React 18

```
选择理由：
- 生态最丰富，组件库齐全
- 适合复杂交互（拖拽战术板、实时数据）
- Concurrent Features 提升用户体验
- 招聘市场人才充足
```

### 3.2 开发语言：TypeScript

```
选择理由：
- 游戏状态复杂，类型安全必要
- 更好的 IDE 支持（自动补全、重构）
- 减少运行时错误
```

### 3.3 构建工具：Vite

```
优势：
- 启动速度比 CRA 快 10 倍+
- 热更新几乎无感知
- 原生 ESM，Tree-shaking 更好
```

### 3.4 样式方案：Tailwind CSS

```
优势：
- 快速实现 PRD 配色（黑/蓝/绿）
- 无需维护 CSS 文件
- 响应式设计便捷
- 打包后体积小（PurgeCSS）
```

**配色方案（基于 PRD）：**
```js
// tailwind.config.js
colors: {
  primary: {
    dark: '#0a0a0a',      // 主背景黑色
    blue: '#3b82f6',      // 亮蓝色（强调）
    green: '#059669',     // 深绿色（成功/足球元素）
  },
  surface: '#1a1a1a',     // 卡片背景
  border: '#2a2a2a',      // 边框色
}
```

### 3.5 状态管理：Zustand

```
选择理由：
- 比 Redux 轻量，无样板代码
- 比 Context 性能好（避免不必要渲染）
- TypeScript 支持好
- 支持异步操作、持久化
```

### 3.6 关键第三方库

| 功能 | 库 | 用途 |
|------|-----|------|
| 路由 | `react-router-dom` | 页面导航 |
| 表单 | `react-hook-form` + `zod` | 转会报价、球员搜索表单 |
| 拖拽 | `@dnd-kit/core` | 战术板球员拖拽 |
| 图表 | `recharts` | 球员能力雷达图、数据统计 |
| 表格 | `@tanstack/react-table` | 球员列表、积分榜（排序/筛选） |
| 动画 | `framer-motion` | 页面切换、进球动画 |
| 请求 | `swr` 或 `@tanstack/react-query` | 数据获取、缓存、自动刷新 |

### 3.7 前端目录结构

```
frontend/
├── src/
│   ├── main.tsx                # 应用入口
│   ├── App.tsx                 # 根组件
│   ├── routes.tsx              # 路由配置
│   │
│   ├── components/             # 组件
│   │   ├── ui/                 # 基础 UI 组件
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Input.tsx
│   │   │
│   │   ├── layout/             # 布局组件
│   │   │   ├── Sidebar.tsx     # 左侧菜单
│   │   │   ├── Header.tsx      # 顶部导航
│   │   │   └── MainLayout.tsx  # 主布局
│   │   │
│   │   ├── charts/             # 图表组件
│   │   │   ├── RadarChart.tsx  # 球员能力雷达图
│   │   │   └── StatsBar.tsx    # 统计条形图
│   │   │
│   │   └── match/              # 比赛相关组件
│   │       ├── LiveFeed.tsx    # 文字直播
│   │       ├── TacticsBoard.tsx # 战术板
│   │       └── MatchStats.tsx  # 比赛统计
│   │
│   ├── pages/                  # 页面组件
│   │   ├── Home/               # 首页
│   │   │   └── Index.tsx
│   │   │
│   │   ├── Dashboard/          # 主界面（登录后）
│   │   │   └── Index.tsx
│   │   │
│   │   ├── Auth/               # 认证页面
│   │   │   ├── Login.tsx
│   │   │   └── Register.tsx
│   │   │
│   │   ├── Team/               # 球队管理
│   │   │   ├── Players.tsx     # 球员列表
│   │   │   ├── PlayerDetail.tsx
│   │   │   ├── Tactics.tsx     # 战术设置
│   │   │   └── Training.tsx    # 训练中心
│   │   │
│   │   ├── Match/              # 比赛
│   │   │   ├── Live.tsx        # 比赛日直播
│   │   │   ├── PreMatch.tsx    # 赛前准备
│   │   │   └── PostMatch.tsx   # 赛后统计
│   │   │
│   │   ├── Transfer/           # 转会市场
│   │   │   ├── Market.tsx      # 市场列表
│   │   │   ├── Watchlist.tsx   # 关注列表
│   │   │   └── History.tsx     # 转会历史
│   │   │
│   │   └── League/             # 联赛
│   │       ├── Table.tsx       # 积分榜
│   │       ├── Schedule.tsx    # 赛程
│   │       └── Stats.tsx       # 射手榜/助攻榜
│   │
│   ├── stores/                 # Zustand 状态管理
│   │   ├── authStore.ts        # 认证状态
│   │   ├── teamStore.ts        # 球队数据
│   │   ├── matchStore.ts       # 比赛数据
│   │   └── uiStore.ts          # UI 状态（主题、侧边栏）
│   │
│   ├── hooks/                  # 自定义 Hooks
│   │   ├── useAuth.ts          # 认证相关
│   │   ├── useWebSocket.ts     # WebSocket 连接
│   │   └── useAutoRefresh.ts   # 定时刷新数据
│   │
│   ├── api/                    # API 层
│   │   ├── client.ts           # Axios 配置
│   │   ├── auth.ts             # 认证 API
│   │   ├── team.ts             # 球队 API
│   │   ├── match.ts            # 比赛 API
│   │   └── types.ts            # API 类型定义
│   │
│   ├── types/                  # 全局类型定义
│   │   └── index.ts
│   │
│   ├── utils/                  # 工具函数
│   │   ├── format.ts           # 格式化（日期、数字）
│   │   └── constants.ts        # 常量
│   │
│   └── styles/                 # 全局样式
│       └── globals.css
│
├── public/                     # 静态资源
│   └── images/
│       ├── players/            # 球员头像
│       ├── teams/              # 队徽
│       └── bg/                 # 背景图
│
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

---

## 4. 基础设施与部署

### 4.1 容器化：Docker

**开发环境：**
```yaml
# docker-compose.yml
version: "3.8"
services:
  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+asyncmy://user:pass@db:3306/lightning
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./backend:/app
    depends_on:
      - db
      - redis

  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: lightning
      MYSQL_USER: user
      MYSQL_PASSWORD: pass
      MYSQL_ROOT_PASSWORD: rootpass
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
```

### 4.2 反向代理：Nginx

**生产环境配置：**
```nginx
server {
    listen 80;
    server_name lightning-league.com;

    # 前端静态资源
    location / {
        root /var/www/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket 代理（比赛直播）
    location /ws {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 5. 演进路线图

### Phase 1: M1/M2（核心基础）- 3~4 个月

```
目标：快速交付可玩版本

后端：
├── FastAPI 单体应用
├── MySQL + Redis
├── APScheduler 定时任务
└── 纯 Python 比赛引擎

前端：
├── React + Vite + Tailwind
├── Zustand 状态管理
└── 基础页面实现

不引入：
- 消息队列
- 微服务拆分
- 复杂缓存策略
```

### Phase 2: M3（性能优化）- 第 4~6 个月

```
根据监控数据决定优化方向：

可能的优化：
├── 比赛引擎改为 Go 服务（HTTP 调用）
├── 引入 Redis Streams 做异步事件
└── 数据库读写分离
```

### Phase 3: M4+（长期演进）

```
按需扩展：
├── 服务拆分（如需要）
├── 引入消息队列（NATS/RabbitMQ）
└── 数据分析（ClickHouse 等）
```

---

## 6. 选型决策总结

### 6.1 核心决策矩阵

| 决策点 | 选择 | 放弃选项 | 理由 |
|--------|------|----------|------|
| 后端语言 | Python | Go/Node.js | 开发效率优先，快速验证玩法 |
| 后端框架 | FastAPI | Django/Flask | 原生异步、自动文档、类型安全 |
| 数据库 | MySQL 8.0 | PostgreSQL | 团队熟悉，运维简单，8.0+ 功能足够 |
| 前端框架 | React | Vue/Angular | 生态最丰富，复杂交互支持好 |
| 构建工具 | Vite | CRA/Webpack | 启动快，热更新体验好 |
| 状态管理 | Zustand | Redux/Mobx | 轻量，无样板代码 |

### 6.2 关键设计原则

1. **简单优先**：不引入不必要的复杂度（消息队列、微服务）
2. **异步默认**：后端所有 IO 操作使用 async/await
3. **预留接口**：比赛引擎、事件总线抽象化，便于未来替换
4. **类型安全**：前后端都使用 TypeScript/Pydantic 强类型
5. **单体起步**：服务边界清晰，但部署为单体，降低初期运维成本

### 6.3 风险与应对

| 风险 | 可能性 | 应对策略 |
|------|--------|----------|
| Python 比赛引擎性能不足 | 中 | 预留 HTTP 接口，可切换 Go 服务 |
| MySQL 复杂查询性能差 | 低 | 应用层缓存 + 优化索引 |
| 前端状态管理混乱 | 低 | Zustand 规范 + 按领域拆分 Store |
| 定时任务调度复杂 | 中 | APScheduler 成熟方案，充分测试 |

---

## 7. 相关文档

- [产品需求文档 (PRD)](./prd.md)
- [开发路线图](./roadmap.md)
- API 文档：启动后端后访问 `/docs` (Swagger UI)

---

*文档版本：v1.0*
*最后更新：2026-04-09*
