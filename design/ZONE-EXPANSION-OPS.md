# 闪电超级联赛 - 新区扩展运维手册

本文档描述在配置驱动架构下，如何安全地将新的联赛大区（Zone）上线到生产环境。

> **适用范围**：新区赛制与现有1区完全一致（8队/联赛、14轮双循环、4体系×8联赛结构）。如果新区需要不同的赛制规则，请参考《赛制配置开发指南》（待补充）。

---

## 1. 架构前提

当前后端已完成赛制解耦，所有硬编码参数已迁移到 `app/core/formats.py` 的 `FormatConfig` 中。

- **1区配置**：`DEFAULT_FORMAT`（code = `DEFAULT_8`）
- **业务代码**：`scheduler.py`、`promotion_service.py`、`cup_progression.py` 等均已改为从配置对象读取参数
- **关键结论**：只要新区绑定相同的 `FormatConfig`，业务代码**零改动**

```
Zone 1 (当前)  ──→  DEFAULT_FORMAT  ──→  4体系×8联赛×8队 = 256队
Zone 2 (新增)  ──→  DEFAULT_FORMAT  ──→  4体系×8联赛×8队 = 256队
Zone N (新增)  ──→  DEFAULT_FORMAT  ──→  4体系×8联赛×8队 = 256队
```

---

## 2. 扩展前检查清单

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 服务器资源充足 | ☐ | CPU/内存/数据库连接数是否支持 N×256 支球队同时运行 |
| 数据库容量充足 | ☐ | 每区每赛季约产生 4,000+ 条 Fixture 记录，评估表容量 |
| 当前赛季状态 | ☐ | 建议在**休赛期**执行扩展，避免赛季进行中插入新区数据 |
| 备份完成 | ☐ | 全量备份数据库，确保可回滚 |
| 代码版本 | ☐ | 确认当前部署版本已包含 `app/core/formats.py` 配置中心 |

---

## 3. 数据库变更（最小化）

### 3.1 给 `league_systems` 表增加 `zone_id` 字段

这是唯一必需的数据库 schema 变更。该字段用于隔离不同大区的数据。

```sql
-- MySQL
ALTER TABLE league_systems
ADD COLUMN zone_id INT NOT NULL DEFAULT 1 COMMENT '所属大区ID，1=当前区'
AFTER code;

CREATE INDEX idx_zone_id ON league_systems(zone_id);
```

> **注意**：`DEFAULT 1` 保证现有4个体系自动归属1区，无需刷数据。

### 3.2 （可选）给 `seasons` 表增加 `zone_id` 字段

如果未来需要按区独立赛季时间线（比如2区比1区晚开3天），建议加此字段：

```sql
ALTER TABLE seasons
ADD COLUMN zone_id INT NOT NULL DEFAULT 1 COMMENT '所属大区ID'
AFTER season_number;

CREATE INDEX idx_season_zone ON seasons(zone_id, season_number);
```

如果所有大区共用同一套赛季时间线，此字段可选。

---

## 4. 配置变更（零代码改动）

### 4.1 确认 `DEFAULT_FORMAT` 已注册

检查 `app/core/formats.py` 末尾：

```python
_FORMAT_REGISTRY: Dict[str, FormatConfig] = {
    DEFAULT_FORMAT.code: DEFAULT_FORMAT,
}
```

当前1区使用的就是这个配置。新区如果赛制相同，**直接复用**。

### 4.2 （可选）新区使用独立配置

如果未来某个新区需要微调参数（如赛季总天数从25天改为30天），可以注册新配置：

```python
# app/core/formats.py
ZONE2_FORMAT = FormatConfig(
    code="DEFAULT_8",
    name="默认8队双循环赛制",
    league=LeagueScheduleConfig(),
    cup=CupConfig(),
    season=SeasonTimelineConfig(total_days=30),  # 只改这里
    promotion=DEFAULT_PROMOTION,
    structure=SystemStructureConfig()
)

# 注册（线上可通过管理后台API动态调用 register_format）
register_format(ZONE2_FORMAT)
```

> **重要**：即使注册了新配置，也**不需要修改** `scheduler.py`、`promotion_service.py` 等任何业务文件。

---

## 5. 数据初始化（线上执行）

### 5.1 新增联赛体系

通过管理后台API或脚本执行：

```python
# 伪代码示例
for code in ["EAST", "WEST", "SOUTH", "NORTH"]:
    system = LeagueSystem(
        code=f"{code}_2",      # 2区体系编码
        name=f"{code_map[code]}2区",
        zone_id=2,             # 关键：标记为2区
        max_teams_per_league=8,
        format_code="DEFAULT_8"
    )
    db.add(system)
```

### 5.2 新增联赛

与 `init_system.py` 逻辑一致，但绑定 `zone_id=2` 的体系：

```python
# 每个体系内创建8个联赛（1+1+2+4）
# Level 1: 超级联赛
# Level 2: 甲级联赛
# Level 3: 乙级联赛A / 乙级联赛B
# Level 4: 丙级联赛A / B / C / D
```

### 5.3 新增球队和用户

- 2区需要 **256 支 AI 球队** + **256 个 AI 用户**
- 球员数据：每队18人，共 4,608 名球员
- **建议**：将球队/球员数据准备脚本化，线上通过 CLI 一键执行

```bash
# 示例：线上初始化2区基础数据
cd backend
python -m scripts.init_zone --zone 2
```

---

## 6. 赛季启动

### 6.1 区隔离原则

| 维度 | 隔离方式 |
|------|----------|
| 联赛赛季 | 按 `zone_id` 分别创建 Season 记录 |
| 赛程生成 | `SeasonScheduler.create_season()` 过滤本区联赛 |
| 杯赛 | 闪电杯、杰尼杯只包含本区球队 |
| 升降级 | `PromotionService` 只处理本区 `zone_id` 的联赛 |
| 积分榜查询 | API 层按 `zone_id` 过滤 |

### 6.2 启动新区第1赛季

```python
# 伪代码：只给2区创建赛季
zone2_systems = await db.execute(
    select(LeagueSystem).where(LeagueSystem.zone_id == 2)
)
zone2_leagues = ...  # 获取2区所有联赛
zone2_teams = ...    # 获取2区所有球队

season = await scheduler.create_season(
    season_number=1,
    start_date=datetime.utcnow(),
    leagues=zone2_leagues,
    teams_by_league=zone2_teams,
    format_config=get_format("DEFAULT_8")  # 绑定配置
)
```

---

## 7. 上线步骤（推荐灰度）

### 7.1 预发布环境验证

1. 在 staging 数据库执行 schema 变更（加 `zone_id`）
2. 运行 `init_zone --zone 2` 初始化2区数据
3. 模拟跑完2区一个完整赛季（25天）
4. 对比1区和2区的数据一致性：
   - 联赛比赛场数：32联赛 × 14轮 × 4场 = 1,792 场
   - 闪电杯：8组 × 3轮 × 2场 + 淘汰赛 = 56 场
   - 杰尼杯：4体系 × (24 + 16 + 8 + 4 + 2 + 1) = 220 场
   - 升降级：28直升 + 28直降 + 附加赛

### 7.2 生产环境上线

```
Step 1: 维护窗口期，暂停用户注册（可选）
Step 2: 数据库备份（mysqldump 全量）
Step 3: 执行 ALTER TABLE 加 zone_id
Step 4: 部署最新代码（确认 formats.py 已包含）
Step 5: 运行 init_zone --zone 2 创建2区基础数据
Step 6: 启动2区第1赛季
Step 7: 开放用户注册/选区，观察24小时
```

### 7.3 回滚方案

| 场景 | 回滚操作 |
|------|----------|
| 数据初始化失败 | 删除 `zone_id=2` 的所有数据（体系、联赛、球队、用户、球员） |
| 赛季生成异常 | 删除 `zone_id=2` 的 Season、Fixture、CupCompetition、CupGroup 记录 |
| 严重Bug | 数据库还原到备份点，代码回滚到上一版本 |

```sql
-- 清理2区数据的SQL（谨慎执行）
DELETE FROM fixtures WHERE season_id IN (
    SELECT id FROM seasons WHERE zone_id = 2
);
DELETE FROM cup_groups WHERE competition_id IN (
    SELECT id FROM cup_competitions WHERE season_id IN (
        SELECT id FROM seasons WHERE zone_id = 2
    )
);
DELETE FROM cup_competitions WHERE season_id IN (
    SELECT id FROM seasons WHERE zone_id = 2
);
DELETE FROM seasons WHERE zone_id = 2;
DELETE FROM league_standings WHERE league_id IN (
    SELECT id FROM leagues WHERE system_id IN (
        SELECT id FROM league_systems WHERE zone_id = 2
    )
);
DELETE FROM players WHERE team_id IN (
    SELECT id FROM teams WHERE current_league_id IN (
        SELECT id FROM leagues WHERE system_id IN (
            SELECT id FROM league_systems WHERE zone_id = 2
        )
    )
);
DELETE FROM teams WHERE current_league_id IN (
    SELECT id FROM leagues WHERE system_id IN (
        SELECT id FROM league_systems WHERE zone_id = 2
    )
);
DELETE FROM users WHERE id IN (
    SELECT user_id FROM teams WHERE current_league_id IN (
        SELECT id FROM leagues WHERE system_id IN (
            SELECT id FROM league_systems WHERE zone_id = 2
        )
    )
);
DELETE FROM leagues WHERE system_id IN (
    SELECT id FROM league_systems WHERE zone_id = 2
);
DELETE FROM league_systems WHERE zone_id = 2;
```

---

## 8. API 层适配（前端需要知道的）

### 8.1 新增选区入口

用户注册/登录后，需要选择所在大区：

```
GET /api/zones
Response: [
  {"id": 1, "name": "1区", "status": "active", "teams_count": 256},
  {"id": 2, "name": "2区", "status": "active", "teams_count": 256}
]
```

### 8.2 现有接口加 zone 过滤

所有联赛相关接口应支持 `zone_id` 参数：

```
GET /api/leagues?zone_id=2
GET /api/standings?zone_id=2&season=1
GET /api/fixtures?zone_id=2&day=5
```

> **兼容性**：不传 `zone_id` 时默认返回1区数据，保证老用户无感知。

---

## 9. 监控与告警

新区上线后需要重点监控：

| 监控项 | 阈值建议 | 说明 |
|--------|----------|------|
| 每日比赛生成数 | = 本区理论值 | 1区=128场/天，2区=128场/天 |
| 赛季结束处理耗时 | < 30s | 升降级计算+球队位置变更 |
| 数据库连接数 | < 80% 上限 | 每增加一区并发略增 |
| 杯赛晋级异常 | = 0 | 杰尼杯预选赛胜者数量是否匹配 |

---

## 10. 总结：一次新区扩展的最小操作集

| 步骤 | 操作 | 风险等级 |
|------|------|----------|
| 1 | 数据库加 `zone_id` 字段 | 低 |
| 2 | 运行 `init_zone --zone N` 初始化数据 | 中 |
| 3 | 启动新区第1赛季 | 低 |
| 4 | 前端/API 增加选区入口 | 低 |

**核心结论**：在配置驱动架构下，扩展一个与1区赛制相同的新区，**业务代码零改动**，运维操作集中在数据库字段 + 数据初始化 + API 层过滤。
