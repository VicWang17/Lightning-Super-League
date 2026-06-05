# Lightning Super League

Lightning Super League 是一个在线足球经理游戏项目。当前实现由 React 前端、FastAPI 后端、MySQL/Redis 基础设施和独立 Go 比赛引擎组成，核心玩法围绕赛季事件队列、联赛/杯赛赛程、球队经营、球员成长、训练、财政、转会、青训和比赛推演闭环展开。

项目当前更接近“可运行的游戏后台和模拟系统”，而不是单纯的展示型前端。后端负责账号、球队、赛季、经济和状态持久化；Go 引擎负责比赛过程中的控球、区域推进、战术影响、体能衰减、事件生成和结果统计；前端提供面向玩家的管理界面。

## 当前功能

### 账号与球队

- 用户注册、登录、登出、当前用户信息查询。
- JWT access token 和 refresh token 认证。
- 前端 API 客户端支持 401 后自动刷新 token，并在刷新失败时回到登录页。
- 系统初始化脚本会创建 4 个联赛体系、32 个联赛、256 支 AI 球队和对应 AI 用户。
- 球队详情页支持查看阵容、球员、基础信息和战术配置。

### 联赛、杯赛与赛季

- 赛季模型包含赛季编号、状态、当前天数、联赛轮次、杯赛轮次和休赛期配置。
- 支持创建新赛季、启动赛季、查询当前赛季、赛季日历、今日比赛、球队赛程。
- 联赛体系按大区、级别和联赛组织，包含积分榜、赛程、最近比赛、排行榜等查询接口。
- 杯赛包含闪电杯和杰尼杯，支持小组赛、淘汰赛、赛程、分组、晋级图、球队参与状态和杯赛详情查询。
- 升降级和附加赛逻辑由 `PromotionService` 和赛季事件驱动流程处理。

### 事件驱动赛季循环

赛季不是通过简单 day-by-day 循环推进，而是创建赛季时写入 `EventQueue`，再按虚拟时间顺序消费事件。当前事件类型覆盖：

- 赛季开始、赛季结束。
- 比赛日批量处理。
- 杯赛推进。
- 升降级处理。
- 赛季财政初始化、比赛财政结算、工资发放、赛季财政关闭。
- 预算窗口打开和关闭。
- 训练日。
- 青训刷新和青训训练。
- 转会报价过期、挂牌截止、AI 转会市场扫描、AI 报价响应。

开发接口和脚本可以查看事件队列、重试失败事件、删除事件、推进下一个事件、处理到期事件或快进赛季。

### 比赛系统

比赛推演由 `match-engine` 目录下的 Go 引擎实现。后端会根据 fixture 构造冻结的比赛请求，将球队、阵型、战术、球员状态和随机种子传给引擎。

Go 引擎当前实现：

- HTTP 服务入口：`/health` 和 `/api/v1/engine/matches/{match_id}/start`。
- 进程模式入口：`cmd/jsonsimulate`，由 Python 后端直接传入 JSON 并读取结果。
- 支持 `instant`、`accelerated`、`realtime` 三种模式；当前 HTTP 服务同步返回最终结果。
- 50 分钟常规比赛时长模型，上下半场各 25 分钟，并包含补时逻辑。
- 需要分胜负的比赛支持加时和点球。
- 生成比赛事件、比分、球员数据、球队数据、战术摘要和比赛设置摘要。
- 计算控球矩阵、区域影响、球员体能衰减、技能影响、换人、攻防事件和叙事事件。
- 提供 step/preview 能力，用于逐步观察候选事件、状态快照和控制矩阵。

后端保存比赛结果后，会更新 fixture、积分榜、球员赛季数据、球队比赛统计、财政流水、训练/疲劳/伤病状态和纪录。

### 球员系统

- 球员模型包含位置、惯用脚、状态、年龄偏移、属性、潜力、性格、合同类型、阵容角色、近期状态等信息。
- 支持球员列表、球员详情、历史、转会记录、成长记录、合同信息和状态快照查询。
- 支持球员号码分配。
- `PlayerStateService` 维护比赛状态缓存、疲劳、伤病、停赛、近期表现等派生状态。
- `PlayerGenerator` 用于初始化球员和青训球员。

### 战术与阵容

- 后端为 Go 引擎构造阵型和战术参数。
- 当前包含 8 个阵型需求配置，例如平衡、高压、强攻、防守、控球、边路等方向。
- 当前战术预设包含 balanced、high_press、possession、counter、deep_defense、wide_attack、all_out。
- 前端提供球队战术页面，比赛请求会携带阵型、战术和 lineup metrics。

### 训练、疲劳与伤病

- 支持训练项目列表、训练模板列表、周训练计划、训练日历、球员疲劳和训练历史。
- 训练计划按赛季日和训练时段保存，时段包含 morning、afternoon、evening。
- 支持套用训练模板、一键按位置分组、保存训练计划。
- 训练结算会写入训练结果，并通过成长服务、疲劳服务和伤病服务影响球员状态。
- 赛季事件中的 `TRAINING_DAY` 会为球队生成或结算训练。

### 财政与预算

- 财政系统使用幂等交易流水，所有收入和支出都会更新球队余额和赛季财政快照。
- 支持财政概览、交易分页、收入详情、支出详情和预算规划。
- 赛季财政包含开季余额、预测收入、预测支出、转会预算、青训预算、工资预算、预备金、工资帽、财务健康度和超支等级。
- 支持预算策略预设：balanced、youth_focus、transfer_push、wage_control。
- 支持赞助合同、比赛收入、工资支付、赛季结算和财政健康修正。

### 转会与自由市场

- 支持市场球员列表、挂牌列表、公开报价、收到的报价、发出的报价和转会历史。
- 支持球员估价、挂牌、撤销挂牌、发送报价、接受报价、拒绝报价、反报价、最终报价和解约预览/执行。
- 估价基于 OVR、年龄、潜力、状态、联赛级别等因子。
- 支持报价链约束、每日报价额度、报价过期、挂牌截止和冷却期。
- AI 球队可以扫描市场并对报价做出响应。
- 自由市场支持自由球员列表、详情和签约。

### 青训

- 每队青训营容量为 8。
- 赛季事件会在指定日期刷新青训候选球员，并按球队青训投入和联赛级别影响生成质量。
- 青训训练会按成长速度、年龄和随机因子提升属性，并写入青训快照。
- 支持从青训营签约、释放或进入自由市场等闭环操作。
- 前端提供青训营和年轻球员页面。

### 邮件与通知

- 游戏内邮件模型支持分类、优先级、已读状态、团队和赛季关联。
- 后端提供邮件列表、详情、未读统计、标记已读和批量已读接口。
- 财政、转会、青训等系统可以写入邮件提醒。

### 纪录中心

- 比赛结束后自动检测并更新纪录。
- 纪录维度包括全服、联赛和球队。
- 纪录类别覆盖比赛级、球员级、球队级、赛季级和生涯累计。
- 当前包含最大比分胜利、单场总进球、最快进球、单场进球、单场助攻、帽子戏法、连胜/连败、赛季数据和生涯累计等方向。
- 前端提供纪录中心页面。

### 开发控制与模拟

- `make console` 打开开发控制台。
- `make sim-status` 查看当前测试状态。
- `make sim-next` 推进下一个虚拟事件。
- `make sim-matchday` 推进到下一个比赛日并打印结果。
- `make sim-season` 快进到赛季结束。
- `make sim-results` 显示最近比赛结果。
- 后端还提供 `/api/v1/dev/*` 系列接口，用于事件、时钟和模拟调试。

## 技术栈

### 前端

- React 18
- TypeScript
- Vite 5
- React Router
- Zustand
- TanStack React Query
- Tailwind CSS
- Headless UI
- Framer Motion
- Recharts
- lucide-react、pixelarticons

### 后端

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2 asyncio
- Alembic
- MySQL 8
- Redis 7
- APScheduler
- python-jose、passlib
- pytest、pytest-asyncio

### 比赛引擎

- Go 1.22
- 标准库 HTTP 服务
- 独立命令行模拟入口
- 可作为 HTTP 服务运行，也可由后端以进程模式调用

### 基础设施

- Docker Compose
- MySQL
- Redis
- 可选 Nginx 反向代理配置

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── core/              # 时钟、事件、配置、日志、安全、中间件
│   │   ├── models/            # SQLAlchemy ORM 模型
│   │   ├── routers/           # FastAPI 路由
│   │   ├── schemas/           # Pydantic 响应/请求模型
│   │   ├── services/          # 业务服务
│   │   └── console/           # 开发控制台
│   ├── alembic/               # 数据库迁移
│   ├── data/                  # 初始化数据
│   ├── scripts/               # 初始化、模拟、压测和开发脚本
│   └── tests/                 # 单元测试和集成测试
├── frontend/
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── components/        # 布局与通用 UI
│   │   ├── hooks/             # 查询 hooks
│   │   ├── pages/             # 业务页面
│   │   ├── stores/            # Zustand store
│   │   └── types/             # 前端类型
│   └── public/                # 静态资源和头像
├── match-engine/
│   ├── cmd/                   # server、simulate、jsonsimulate 等入口
│   ├── internal/domain/       # 比赛领域模型
│   ├── internal/engine/       # 推演核心
│   ├── internal/api/          # JSON DTO
│   └── preview/               # 引擎预览工具
├── design/                    # 产品和系统设计文档
├── reports/                   # 闭环模拟报告
├── docker-compose.yml
├── docker-compose.infra.yml
└── Makefile
```

## 本地开发

### 1. 准备环境变量

```bash
cp .env.example .env
```

关键配置：

```bash
DB_PORT=3306
REDIS_PORT=6379
BACKEND_PORT=8000
FRONTEND_PORT=5173
DATABASE_URL=mysql+asyncmy://lightning:lightning_pass@localhost:3306/lightning_league
REDIS_URL=redis://localhost:6379/0
VITE_API_URL=http://localhost:8000/api/v1
MATCH_ENGINE_URL=http://localhost:8080
MATCH_ENGINE_TRANSPORT=http
MATCH_ENGINE_MODE=instant
```

注意：前端 `VITE_API_URL` 应包含 `/api/v1`，因为 `frontend/src/api/client.ts` 会直接在这个 base URL 后拼接业务 endpoint。

### 2. 启动 MySQL 和 Redis

```bash
make infra-up
```

等价命令：

```bash
docker-compose -f docker-compose.infra.yml up -d
```

### 3. 安装依赖

后端：

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

前端：

```bash
cd frontend
npm install
```

比赛引擎：

```bash
cd match-engine
go test ./...
```

### 4. 初始化数据库和赛季

开发环境一键重建数据并创建第一个赛季：

```bash
make dev-bootstrap
```

该命令会执行：

- 启动基础设施。
- 执行 Alembic 迁移。
- 初始化联赛、球队、AI 用户、球员、工资配置等基础数据。
- 创建新赛季、联赛赛程、杯赛赛程、积分榜和事件队列。

如果需要分步执行：

```bash
make init-system
make init-season
```

`make init-system` 默认会重建 schema 和基础数据，适合开发环境，不适合保留现有数据的环境。

### 5. 启动服务

启动 Go 比赛引擎：

```bash
make match-engine
```

启动后端：

```bash
make backend
```

启动前端：

```bash
make frontend
```

默认访问地址：

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000/api/v1
- FastAPI Docs：http://localhost:8000/docs
- 比赛引擎健康检查：http://localhost:8080/health

## 比赛引擎运行模式

后端通过 `MATCH_ENGINE_TRANSPORT` 决定如何调用 Go 引擎。

### HTTP 模式

```bash
MATCH_ENGINE_TRANSPORT=http
MATCH_ENGINE_URL=http://localhost:8080
```

需要单独运行：

```bash
make match-engine
```

适合接近真实部署的本地联调。

### Process 模式

```bash
MATCH_ENGINE_TRANSPORT=process
MATCH_ENGINE_MODE=instant
```

后端会在需要比赛结果时直接从 `match-engine` 目录运行 `jsonsimulate` 或 `go run ./cmd/jsonsimulate`。这种模式不需要长驻 Go 服务，适合闭环测试和本地批量模拟。

可以提前构建二进制以减少反复 `go run` 的成本：

```bash
cd match-engine
go build -o jsonsimulate ./cmd/jsonsimulate
```

## 常用开发命令

```bash
make help
make infra-up
make infra-down
make infra-logs
make dev-bootstrap
make backend
make frontend
make match-engine
make console
make sim-status
make sim-next
make sim-matchday
make sim-season
make sim-results
```

## 测试与校验

后端测试：

```bash
cd backend
PYTHONPATH=. pytest
```

前端类型检查和构建：

```bash
cd frontend
npm run build
```

前端 lint：

```bash
cd frontend
npm run lint
```

比赛引擎测试：

```bash
cd match-engine
go test ./...
```

闭环平衡测试脚本位于：

```text
backend/scripts/closed_loop_balance_test.py
```

典型运行方式：

```bash
cd backend
PYTHONPATH=. PYTHONUNBUFFERED=1 MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant python -m scripts.closed_loop_balance_test
```

模拟报告会写入 `backend/reports/` 或 `reports/closed_loop/` 下的对应目录，包含赛季摘要、球队指标、球员指标、事件结果和不变量检查。

## API 模块

后端路由统一挂载在 `/api/v1` 下，主要模块包括：

- `/auth`：注册、登录、刷新 token、登出、当前用户。
- `/users`：用户查询、更新、删除。
- `/teams`：球队、阵容、战术、球员状态。
- `/players`：球员详情、状态、合同、历史、成长、转会。
- `/leagues`：联赛列表、详情、积分榜、赛程、排行榜。
- `/cups`：杯赛列表、详情、分组、赛程、晋级图。
- `/matches`：比赛列表、详情、直播数据、统计、阵容、手动模拟。
- `/seasons`：赛季列表、当前赛季、创建、启动、下一天、日历、今日比赛。
- `/clock`：虚拟时钟状态。
- `/records`：纪录中心。
- `/mail`：邮件列表、详情、未读统计、标记已读。
- `/finance`：概览、流水、预算、收入、支出、赞助。
- `/free-market`：自由球员市场。
- `/youth-academy`：青训营、青训刷新、训练、签约。
- `/training`：训练项目、模板、计划、结算、疲劳、历史。
- `/transfers`：转会市场、挂牌、报价、反报价、解约、历史。
- `/dev`：开发调试、事件队列和模拟推进。
- `/internal`：比赛引擎回调和内部接口。

## 前端页面

当前前端路由覆盖：

- `/login`、`/register`
- `/dashboard`
- `/team/players`
- `/team/players/:id`
- `/team/players/:id/history`
- `/team/players/:id/transfers`
- `/team/players/:id/growth`
- `/team/tactics`
- `/training/weekly`
- `/training/calendar`
- `/training/fatigue`
- `/training/history`
- `/match/schedule`
- `/match/pre`
- `/match/live`
- `/match/post`
- `/match/:id`
- `/leagues`
- `/leagues/:id`
- `/cups`
- `/cups/:id`
- `/transfer/market`
- `/transfer/free-market`
- `/transfer/watchlist`
- `/transfer/my-listings`
- `/transfer/public-offers`
- `/transfer/my-offers`
- `/transfer/history`
- `/youth/academy`
- `/youth/young-players`
- `/records`
- `/mail`
- `/finance/overview`
- `/finance/budget`
- `/finance/income`
- `/finance/expense`

## 数据库与迁移

后端使用 SQLAlchemy ORM 和 Alembic。迁移文件位于：

```text
backend/alembic/versions/
```

执行迁移：

```bash
cd backend
PYTHONPATH=. alembic upgrade head
```

开发环境可使用：

```bash
make dev-bootstrap
```

这会重建开发数据并创建赛季，适合需要完整模拟世界的场景。

## Docker

只启动基础设施：

```bash
docker-compose -f docker-compose.infra.yml up -d
```

启动完整 Compose：

```bash
docker-compose up
```

完整 Compose 包含 frontend、backend、db、redis，并提供可选 production profile 下的 nginx。实际开发时通常更推荐用 Compose 启动 MySQL/Redis，再分别用 `make backend`、`make frontend`、`make match-engine` 启动本地服务，便于热更新和调试。

## 当前实现边界

- Go 比赛引擎的 HTTP 模式当前同步返回最终结果；`realtime` 和 `accelerated` 主要影响服务端等待和模式字段，实时推送层还可以继续扩展。
- `/internal` 路由中预留了比赛引擎 API key 校验，当前生产级内网访问控制仍需补齐。
- `MATCH_ENGINE_FALLBACK_RANDOM` 存在兜底配置，但本项目的主要比赛逻辑应使用 Go 引擎。
- `make init-system` 和 `make dev-bootstrap` 是开发重建命令，会影响数据库内容。
- 前端有完整页面骨架和主要业务接口接入，但部分页面的体验完整度取决于后端当前数据和事件推进状态。
