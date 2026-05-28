# Economy System Technical Design

> Version: v1.0  
> Scope: technical design for implementing the first complete economy loop in Lightning Super League.

## 1. Goals

The economy system should make players feel a simple but meaningful loop:

```
win matches / develop youth -> earn money -> pay wages / invest in squad and youth -> improve results -> earn more money
```

The first implementation should favor a playable closed loop over simulation completeness.

### Design Principles

1. **Small number of decisions**
   - The player should mainly choose a season budget policy and a sponsor policy.
   - Avoid many independent economy sliders.

2. **Money must move through visible records**
   - Every income or expense that changes balance creates a finance transaction.
   - The finance UI should be explainable from the transaction list.

3. **Soft freedom, hard consequences**
   - The player can overspend.
   - Overspending should quickly produce strong penalties: frozen bidding, forced conservative budgets, sponsor reductions, and inbox warnings.

4. **Competition and youth are the main growth paths**
   - Match results, league ranking, cup progress, and youth development should matter most.
   - Ticket pricing, stadium construction, and deep sponsor negotiation are intentionally deferred.

5. **Wages affect player state, not direct visible attributes**
   - Wage satisfaction contributes to the future player state system.
   - The UI exposes only simple state arrows, while internal state can slightly modify effective match attributes.

## 2. Explicit Non-Goals

### Not In First Version

- Stadium upgrades.
- Ticket price management.
- Detailed attendance simulation.
- Real advertising integration.
- Sponsor negotiation.
- Full FFP system.
- Complex finance tax, loans, debt, agent fees, or amortization.

### Notes For Later

**FFP** means "Financial Fair Play". In football management games, it usually prevents clubs from sustaining large long-term losses or buying players far beyond their revenue. For this project, a full FFP system is not needed in v1. Its useful part is folded into `financial_health` and overspending penalties.

Real advertising and sponsor negotiation can be revisited later. Keep data fields extensible, but do not build product behavior around ads yet.

## 3. Core Economy Loop

### Season Timeline

The existing `Season` model uses a 42-day season:

- Days 1-30: league season.
- Cup days are interleaved.
- Day 31+: offseason.

Economy events should attach to the existing virtual clock and `EventQueue`.

| Time | Economy Event | Behavior |
| --- | --- | --- |
| Previous season day 20 | `BUDGET_WINDOW_OPENED` | Create inbox message and allow budget/sponsor selection for next season. |
| Previous season day 25 | `BUDGET_WINDOW_CLOSED` | Lock next season budget. Auto-apply recommendation if untouched. |
| Season day 1 | `SEASON_FINANCE_INITIALIZED` | Apply opening balance, broadcast income, sponsor base income, youth allocation, wage cap. |
| Every official match finish | `MATCH_FINANCE_SETTLED` | Apply win/draw bonus, sponsor performance bonus, cup participation/progress bonus if applicable. |
| Weekly or configured day interval | `WAGES_PAID` | Deduct wages. Recalculate wage pressure. |
| Season end | `SEASON_FINANCE_CLOSED` | Apply league prize, final health rating, carryover, inbox summary. |

### Player-Facing Economy Decisions

The player only needs two strategic decisions per season:

1. **Budget policy**
   - Balanced.
   - Youth Focus.
   - Transfer Push.
   - Wage Control.
   - Custom advanced allocation.

2. **Sponsor policy**
   - Stable sponsor.
   - Performance sponsor.

The UI can still expose a custom budget screen, but the default path should be one-click policies sent through inbox tasks.

## 4. Currency And Units

Use one internal currency unit: integer cents or integer base unit.

Recommended:

- DB storage: integer `amount` in smallest unit, not floating decimal, for new finance tables.
- Display: Chinese UI can display `万` by formatting `amount / 10000`.
- Existing `DECIMAL` fields can remain during migration, but new ledger entries should avoid decimal drift.

If the team prefers not to migrate existing `DECIMAL` fields immediately, keep `TeamFinance.balance` as `DECIMAL(15, 2)` and create a follow-up migration later.

## 5. Data Model

### Existing Model To Keep

`TeamFinance` already exists:

- `team_id`
- `balance`
- `weekly_wage_bill`
- `stadium_capacity`
- `ticket_price`
- `weekly_sponsor_income`
- `weekly_ticket_income`
- `transfer_budget`
- `wage_budget`

For v1, keep `stadium_capacity`, `ticket_price`, and `weekly_ticket_income` as dormant fields. Do not expose ticket operations yet.

### Recommended New Tables

#### `finance_transactions`

Ledger table. This is the source of truth for "why did my money change?"

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string/uuid | Primary key. |
| `team_id` | FK teams.id | Indexed. |
| `season_id` | FK seasons.id | Indexed. |
| `event_queue_id` | FK event_queues.id nullable | Idempotency trace. |
| `source_type` | enum/string | `broadcast`, `sponsor`, `match_bonus`, `cup_prize`, `league_prize`, `wage`, `transfer`, `youth`, `penalty`, `manual_adjustment`. |
| `direction` | enum | `income` or `expense`. |
| `amount` | bigint/decimal | Positive number. Direction determines sign. |
| `balance_after` | bigint/decimal | Snapshot after transaction. |
| `description` | string | User-readable short text. |
| `metadata` | JSON | fixture id, player id, sponsor id, policy id, etc. |
| `created_at` | datetime | Indexed. |

Rules:

- Never update a transaction amount after creation.
- Corrections use compensating transactions.
- Service methods must be idempotent by `(team_id, season_id, source_type, metadata.idempotency_key)`.

#### `team_season_finances`

Season snapshot and planning state.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string/uuid | Primary key. |
| `team_id` | FK teams.id | Unique with season. |
| `season_id` | FK seasons.id | Unique with team. |
| `opening_balance` | amount | Balance at season start. |
| `current_balance` | amount | Cached current balance. |
| `projected_income` | amount | Calculated before budget lock. |
| `projected_expense` | amount | Includes wages and youth allocation. |
| `locked_budget_total` | amount | Opening balance + projected income. |
| `transfer_budget` | amount | Soft limit. |
| `youth_budget` | amount | Deducted or reserved at season start. |
| `wage_budget` | amount | Soft limit for wage planning. |
| `reserve_budget` | amount | Warning threshold buffer. |
| `wage_cap` | amount | Hard-ish cap used for signing restrictions. |
| `wage_bill` | amount | Current season wage total or weekly wage bill depending on final convention. |
| `financial_health` | enum | `A`, `B`, `C`, `D`. |
| `overspend_level` | enum | `none`, `warning`, `restricted`, `crisis`. |
| `budget_locked_at` | datetime nullable | Filled at day 25. |
| `created_at` / `updated_at` | datetime | Standard. |

#### `team_budget_plans`

Stores next-season decisions before they lock.

| Field | Type | Notes |
| --- | --- | --- |
| `team_id` | FK teams.id |  |
| `target_season_id` | FK seasons.id |  |
| `policy` | enum | `balanced`, `youth_focus`, `transfer_push`, `wage_control`, `custom`. |
| `transfer_pct` | int | Sum with other pct fields must be 100. |
| `youth_pct` | int | Recommended range 5-25. |
| `wage_pct` | int | Recommended range 45-65. |
| `reserve_pct` | int | Recommended range 5-20. |
| `is_player_confirmed` | bool | False for auto recommendation. |
| `locked_at` | datetime nullable |  |

#### `sponsor_contracts`

Light strategy only.

| Field | Type | Notes |
| --- | --- | --- |
| `team_id` | FK teams.id |  |
| `season_id` | FK seasons.id |  |
| `policy` | enum | `stable`, `performance`. |
| `base_amount` | amount | Paid on season day 1. |
| `win_bonus` | amount | Performance policy only. |
| `draw_bonus` | amount | Optional, smaller. |
| `goal_bonus` | amount | Optional; keep disabled in v1 unless needed. |
| `max_bonus` | amount | Caps performance upside. |
| `health_modifier_pct` | int | Sponsor penalty/bonus from finance health. |
| `status` | enum | `pending`, `active`, `completed`. |

#### `inbox_messages`

FM-style mailbox for decisions and reports.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string/uuid | Primary key. |
| `user_id` | FK users.id nullable | Optional, if user-owned inbox. |
| `team_id` | FK teams.id nullable | Team context. |
| `season_id` | FK seasons.id nullable | Season context. |
| `category` | enum/string | `finance`, `sponsor`, `budget`, `contract`, `match`, `youth`, `system`. |
| `message_type` | string | `budget_opened`, `sponsor_choice`, `overspend_warning`, `season_finance_summary`, etc. |
| `title` | string |  |
| `body` | text |  |
| `priority` | enum | `low`, `normal`, `high`, `urgent`. |
| `status` | enum | `unread`, `read`, `archived`. |
| `requires_action` | bool | True for budget/sponsor choice. |
| `action_type` | string nullable | `choose_budget`, `choose_sponsor`, `review_finance`. |
| `action_payload` | JSON nullable | Options and target API references. |
| `expires_at` | datetime nullable | Budget/sponsor deadline. |
| `created_at` | datetime |  |
| `read_at` | datetime nullable |  |

## 6. Economy Formulas

The values below are implementation defaults, not permanent balance numbers. Put them in configuration so they can be tuned without touching service logic.

### Projected Income

```
projected_income =
  broadcast_income
  + sponsor_expected_income
  + expected_competition_bonus
  + expected_league_prize
```

For v1, no ticket income.

### Broadcast Income

```
broadcast_income = league_base_broadcast[level] * reputation_multiplier
```

Suggested `league_base_broadcast`:

| League Level | Amount |
| --- | --- |
| 1 | 350000 |
| 2 | 280000 |
| 3 | 220000 |
| 4 | 180000 |

`reputation_multiplier`: clamp 0.8-1.2.

If reputation is not implemented, use:

```
reputation_multiplier = 1.0 + clamp((last_season_rank_score - 0.5) * 0.2, -0.1, 0.1)
```

Or simply use `1.0` for MVP.

### Sponsor Policy

Stable:

```
base_amount = sponsor_base[level] * health_modifier
performance_bonus = 0
```

Performance:

```
base_amount = sponsor_base[level] * 0.65 * health_modifier
win_bonus = sponsor_base[level] * 0.045
draw_bonus = sponsor_base[level] * 0.015
max_bonus = sponsor_base[level] * 0.55
```

Expected performance sponsor income should be about 5-12% higher than stable if the team performs well, and worse if it underperforms.

### Match Result Income

After each official match:

- Stable sponsor: no match sponsor payout.
- Performance sponsor: payout win/draw bonuses until `max_bonus`.
- Cup matches: participation/progress bonus can be settled on fixture finish or round completion.

League wins do not need a separate match prize in v1 unless the economy feels too slow. Prefer league ranking prize at season end.

### League Prize

At season end:

```
league_prize = league_prize_table[level][rank]
```

Keep this visible in finance summary because it reinforces competitive goals.

### Youth Budget

At season start:

```
youth_budget = locked_budget_total * youth_pct
```

Recommended:

- Minimum: 5%.
- Maximum: 25%.
- If team is in `crisis`, force 5%.

Implementation options:

1. Deduct youth budget immediately as an expense transaction.
2. Reserve it and deduct gradually when youth generation happens.

Recommended v1: deduct immediately. It makes the cost visible and avoids hidden reserved-money bugs.

### Wages

Keep existing player `wage` field, but define one convention:

- Prefer `wage` = season wage.
- `wage_bill` = sum of active first-team player season wages.
- `WAGES_PAID` can deduct `wage / wage_payment_count` on scheduled intervals.

If current data treats wage as weekly wage, add a migration note and normalize before balancing.

### Wage Cap

```
wage_cap = projected_income * wage_cap_ratio
```

Base ratio:

| Health | Wage Cap Ratio |
| --- | --- |
| A | 0.70 |
| B | 0.65 |
| C | 0.58 |
| D | 0.50 |

The wage cap is a signing and warning constraint, not a direct forced payment cap.

## 7. Overspending And Penalties

Budget limits are soft, but penalties should be strong.

### Overspend Levels

```
budget_pressure = committed_expense / locked_budget_total
wage_pressure = wage_bill / wage_cap
cash_pressure = current_balance / projected_income
```

| Level | Trigger | Effects |
| --- | --- | --- |
| `none` | wage <= 90% cap and balance healthy | Normal. |
| `warning` | wage > 90% cap or reserve spent | Inbox warning. UI turns yellow. |
| `restricted` | wage > 100% cap or balance < 0 | New auction bids disabled. Sponsor performance bonus -20%. Youth next season max 10%. |
| `crisis` | wage > 115% cap or balance < -10% projected income | Auction bids disabled, free-market signing blocked except minimum contracts, next youth forced 5%, sponsor base -30%, automatic "sell players" inbox task. |

Do not auto-sell players in v1 unless there is no other way out. It feels punitive and requires transfer-market robustness. Use inbox escalation first.

### Financial Health Rating

Calculated at season end:

| Rating | Condition | Next Season Effect |
| --- | --- | --- |
| A | positive balance, wage <= 80% cap, no restricted/crisis days | +5% sponsor base, +5% wage cap ratio. |
| B | non-negative balance, wage <= cap | Normal. |
| C | negative balance or wage > cap | -10% sponsor base, wage cap ratio lowered. |
| D | crisis reached or large deficit | -30% sponsor base, transfer restrictions start next season. |

This replaces full FFP for now.

## 8. Wage Satisfaction And Future State System

The economy system should produce a hidden `wage_satisfaction` value for each player.

### Contract Inputs

When signing or renewing:

```
recommended_wage = wage_table[ovr] * league_factor * age_factor * contract_type_factor
wage_ratio = offered_wage / recommended_wage
```

Suggested interpretation:

| Wage Ratio | Satisfaction |
| --- | --- |
| < 0.80 | -2 |
| 0.80 - 0.94 | -1 |
| 0.95 - 1.14 | 0 |
| 1.15 - 1.29 | +1 |
| >= 1.30 | +2 |

### Hidden Match Impact

The future state system can combine wage satisfaction with form, fatigue, morale, and personality:

```
state_score = base_form + morale + fatigue_modifier + wage_satisfaction * personality_weight
effective_attr = base_attr * (1 + state_score * 0.005)
```

Recommended bounds:

- Wage effect alone should stay within roughly -2% to +2% for most players.
- Extreme money-sensitive personality can reach -3% to +3%.
- Player-facing UI only shows arrows: down, flat, up.

### Personality

Do not build the full personality discovery game in economy v1. Add a field or placeholder for later:

- `money_sensitivity`: low, normal, high.

If not present, default all players to `normal`.

## 9. Services

### `FinanceService`

Responsibilities:

- Create finance season snapshots.
- Calculate projected income.
- Lock budget plans.
- Apply income/expense transactions.
- Recalculate team balance and cached finance fields.
- Calculate wage cap, wage pressure, overspend level, and health rating.
- Provide finance overview DTOs.

Important methods:

```python
initialize_season_finance(season_id: str) -> None
open_budget_window(season_id: str) -> None
lock_budget_plan(team_id: str, target_season_id: str) -> TeamSeasonFinance
apply_transaction(command: FinanceTransactionCommand) -> FinanceTransaction
settle_match_finance(fixture_id: str) -> None
pay_wages(season_id: str, period_key: str) -> None
close_season_finance(season_id: str) -> None
recalculate_team_finance(team_id: str, season_id: str) -> FinanceOverview
```

### `SponsorService`

Responsibilities:

- Generate two sponsor choices for each team: stable and performance.
- Auto-select recommended sponsor if player misses deadline.
- Settle performance bonuses after matches.

### `InboxService`

Responsibilities:

- Create decision messages.
- Mark read/archive.
- Return action payloads for UI.
- Expire unresolved decisions and trigger defaults.

Decision messages should be the main entry point for:

- Budget window opened.
- Sponsor selection.
- Overspend warning.
- Wage cap warning.
- Season finance summary.

## 10. EventQueue Integration

Add economy event handlers:

| Event Type | Handler |
| --- | --- |
| `BUDGET_WINDOW_OPENED` | `FinanceService.open_budget_window` |
| `BUDGET_WINDOW_CLOSED` | `FinanceService.lock_all_budget_plans` |
| `SEASON_FINANCE_INITIALIZED` | `FinanceService.initialize_season_finance` |
| `MATCH_FINANCE_SETTLED` | `FinanceService.settle_match_finance` |
| `WAGES_PAID` | `FinanceService.pay_wages` |
| `SEASON_FINANCE_CLOSED` | `FinanceService.close_season_finance` |

Idempotency:

- Each handler should safely return if matching transactions already exist.
- Use `event_queue_id` and domain keys such as `fixture_id`, `season_id`, `period_key`.

## 11. API Design

### Finance

```
GET /api/v1/teams/{team_id}/finance/overview
GET /api/v1/teams/{team_id}/finance/transactions?season_id=&type=&page=
GET /api/v1/teams/{team_id}/finance/budget-plan?target_season_id=
PUT /api/v1/teams/{team_id}/finance/budget-plan
POST /api/v1/teams/{team_id}/finance/budget-plan/apply-policy
GET /api/v1/teams/{team_id}/finance/sponsor-options?target_season_id=
POST /api/v1/teams/{team_id}/finance/sponsor-contract
```

### Inbox

```
GET /api/v1/inbox?team_id=&status=&category=&page=
GET /api/v1/inbox/{message_id}
POST /api/v1/inbox/{message_id}/read
POST /api/v1/inbox/{message_id}/archive
POST /api/v1/inbox/{message_id}/action
```

`POST /inbox/{id}/action` should call the relevant domain service based on `action_type`. The frontend should not need to understand every decision implementation detail.

## 12. Frontend Pages

### Finance Center

Existing pages can be connected to real APIs:

- `FinanceOverview`
- `BudgetPlanning`
- `Income`
- `Expense`

Recommended changes:

- Remove ticket/stadium controls from v1 UI.
- Add sponsor policy block to budget/inbox flow.
- Display budget pressure and wage pressure prominently.
- Transaction list should use ledger data, not mock categories.

### New Inbox Page

Add route:

```
/inbox
```

MVP views:

- Message list with category, priority, unread state, deadline.
- Message detail.
- Action footer for decisions.

Required message actions:

- Choose budget policy.
- Choose sponsor policy.
- Review overspend warning.
- Open finance summary.

The inbox page should feel like Football Manager mail: important club operations arrive as messages, and the player can act from the message.

## 13. Integration With Other Systems

### Match Engine

Economy does not call the Go engine directly.

Flow:

1. Match result is persisted by FastAPI.
2. `MATCH_FINANCE_SETTLED` runs.
3. Sponsor performance bonus and cup rewards are paid.
4. Finance transaction and inbox notices are created if needed.

### Transfer Market

Before bid or signing:

- Check `overspend_level`.
- Check current balance and soft transfer budget.
- If `restricted` or `crisis`, block bid/signing according to rules.
- On successful transfer, create `transfer` transaction.

### Youth System

At season start:

- Youth budget is deducted or reserved.
- Youth generation receives `youth_budget` and `team_financial_health`.

Suggested youth impact:

- Higher youth budget increases candidate count and probability of high potential.
- `crisis` teams are forced to 5% youth budget but still get a low-cost development path.

### Contract And Player State

When signing/renewing:

- Finance service checks wage cap after proposed wage.
- Contract service calculates `wage_ratio`.
- Player state service stores/updates hidden wage satisfaction.

Match engine later consumes effective attributes after state modifiers are applied by FastAPI snapshot building.

## 14. MVP Implementation Plan

### Phase 1: Ledger And Finance Overview

- Add `finance_transactions`.
- Add `team_season_finances`.
- Implement `FinanceService.apply_transaction`.
- Replace team finance mock API with DB-backed overview.
- Connect finance overview and transaction pages.

### Phase 2: Season Economy Events

- Add economy event handlers.
- Initialize season finance.
- Pay broadcast and stable sponsor income.
- Pay wages on schedule.
- Close season finance and calculate health.

### Phase 3: Budget And Sponsor Decisions

- Add `team_budget_plans`.
- Add `sponsor_contracts`.
- Implement budget policies and sponsor policy selection.
- Add default auto-selection at deadline.
- Connect budget page to API.

### Phase 4: Inbox

- Add `inbox_messages`.
- Add inbox API.
- Add frontend `/inbox`.
- Send budget, sponsor, warning, and season summary messages.

### Phase 5: Transfer/Youth/Contract Coupling

- Enforce transfer restrictions.
- Deduct youth budget and feed youth generation.
- Add wage cap checks to signing/renewal.
- Store hidden wage satisfaction for future state system.

## 15. Testing Strategy

### Unit Tests

- Transaction idempotency.
- Budget policy percentage validation.
- Sponsor stable/performance payout calculation.
- Wage cap and overspend level calculation.
- Health rating calculation.

### Integration Tests

- Season start creates finance snapshot and opening transactions.
- Match settlement pays sponsor performance bonus once.
- Wage payment deducts correct amount once per period.
- Budget window auto-locks default plan when no player choice exists.
- Crisis team cannot place transfer bid.

### Fast-Forward Simulation

Add a dev script that simulates several seasons with deterministic results:

```
python backend/scripts/dev_sim_economy.py --seasons 5 --teams 32
```

Track:

- Average balance by league level.
- Number of teams in each health rating.
- Number of restricted/crisis teams.
- Youth budget distribution.
- Transfer budget usage.

## 16. Open Balance Questions

These should be tuned after the first deterministic simulation:

1. How often should wage payments happen in a 42-day season?
2. Should cup participation pay per match or per round reached?
3. How much sponsor performance upside is fun without making stable sponsor useless?
4. What crisis penalty is strong enough without trapping a team forever?
5. Should AI teams use the same budget policies or a simpler automatic policy?

