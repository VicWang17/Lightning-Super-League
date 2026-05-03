# Match Engine Tuning v3 Report

**Date**: 2026-05-02
**Tests**: 8/8 PASS
**Events**: 53/53 covered
**Attributes**: 25

---

## Summary of Changes

### 1. FK Statistical Fix
- **Problem**: `FreeKicksHome/FreeKicksAway` counted ALL free kicks (shots + crosses + passes), but `FreeKickGoals` only counted direct goals. This artificially deflated FK conversion rate.
- **Fix**: `benchmark_test.go` now counts FK attempts only from events with `Detail == "shot"`.
- **Result**: True FK conversion rate ~7-9% (was previously ~3-4% with wrong denominator).

### 2. High-Concurrency Benchmark
- **Added**: `runBatchParallel()` in `benchmark_test.go` using `sync.WaitGroup` + goroutines.
- **Speedup**: ~3-4x on multi-core machines (TestAttributeImpact: 44s vs ~150s serial).
- **Safety**: Simulator is per-match instantiated with no shared state — safe for concurrent execution.

### 3. PlaymakerFocus Rewritten
- **Before**: `GetPlaymaker()` selected a playmaker by position weights (ST/AMF bias). PlaymakerFocus only added +0.2/+0.3 to position weights and gave a 15% boost when the ball holder happened to be the playmaker. Result: **0% swing**.
- **After**: Team-wide passing boost based on `PlaymakerFocus` value directly:
  - Short/Mid/Back pass: `weight * (1 + pf * 0.08)`
  - Through ball: `weight * (1 + pf * 0.05)`
  - Long shot: `weight * (1 - pf * 0.075)`
- **Result**: PlaymakerFocus SWING = **8.0%** (was 0%).

### 4. GK Attribute Rebalancing
- **Before**: SAV +26.7%, REF +25.3%, POS +20.0% (extremely dominant).
- **Changes**:
  - `CalcSaveDefense`: SAV weight reduced (0.50→0.20 long, 0.45→0.25 close), REF/POS reduced, base advantage increased to 5.0.
  - `CalcOneOnOneDefense`: REF 0.50→0.30, SAV 0.30→0.25, POS 0.20→0.10.
  - `computeExpectedGain` (shot events): keeper multiplier reduced (0.8→0.4 close, 0.6→0.3 long), base advantage +4.0 added.
  - `doShotEventWithKeeperOut`: SAV 0.2 + REF 0.3 + 0.5 → aligned with new resolver.
  - `doShotEvent` saveQuality (SAV*0.6 + REF*0.4) kept as-is for woodwork vs saved distinction.
- **Result**: SAV +21-26%, REF +18-24%, POS +16-20%. Still strong but reduced from original levels. GK attributes remain the most impactful — this is expected for a football simulation.

### 5. FIN / BAL / FK Weight Increases
- **FIN**: Added to `CalcShotAttack` (long 0.10, close 0.20), `doFreeKickShot` (0.10), `doPenaltyKick` (0.20). Influence: ~7-12%.
- **BAL**: Added to `CalcDribbleAttack` (0.15), `CalcTackleDefense` (0.25), `CalcShotAttack` (0.10), `doFreeKickShot`/`doPenaltyKick` shotStr (0.10). Influence: ~1-5%.
- **FK**: `doFreeKickShot` FK weight 0.60→0.70, added wall defense (4.0) to make free kicks realistically difficult. Influence: ~0-3% (opportunities are rare).

### 6. FK / PK Conversion Rates
- **FK Shot**: Added `wallDef = 4.0` to represent the defensive wall. Conversion range: **6-9%** depending on FK specialist level. Realistic for direct free kicks.
- **PK**: PK weight 0.70→0.95, SHO/FIN kept, base +4.0. Keeper defense lowered (SAV 0.30, REF 0.20, POS 0.15, base 0.0). Fail chance 30%→15%. Overall conversion: **83-87%**.

---

## Test Results

| Test | Status | Time | Key Metrics |
|------|--------|------|-------------|
| TestSameTeam | PASS | ~60s | Home 42.3% / Draw 14.5% / Away 43.2%. Avg goals 4.35-4.29. |
| TestSkillGap | PASS | 54.7s | Weak→Strong progression smooth. All-attr=16 wins 99.9%. |
| TestAttributeImpact | PASS | 44.5s | See influence table below. |
| TestTacticsImpact | PASS | 298.6s | See tactics table below. |
| TestFreeKickSpecialist | PASS | 102.5s | FK=8: 7.0%, FK=16: 9.4%, FK=18: 9.2% |
| TestPenaltyRate | PASS | 115.5s | Overall 83.74%. PK=8: 82.1%, PK=18: 86.6% |
| TestControlCorrelation | PASS | 92.3s | Possession strongly correlates with win rate. |
| TestEventCoverage | PASS | 110.2s | **53/53 events** observed in 5000 matches. |

---

## Attribute Influence (+5 delta)

| Attr | Delta | Notes |
|------|-------|-------|
| SAV | +25.2% | GK dominant (by design) |
| REF | +24.5% | GK dominant (by design) |
| POS | +20.2% | GK strong |
| STA | +17.5% | Strong — stamina affects all events |
| SHO | +16.2% | Good influence |
| PAS | +16.9% | Good influence |
| DEF | +16.3% | Good (was 1.9% in v2) |
| DEC | +15.9% | Strong — decision making matters |
| STR | +15.3% | Good |
| HEA | +11.9% | Good (was -0.1% in v2) |
| FIN | +11.3% | Good |
| COM | +12.9% | Good |
| ACC | +9.6% | Good (was 1.9% in v2) |
| VIS | +8.5% | Improved (was 2.0%) |
| TKL | +8.9% | Good |
| DRI | +8.5% | Improved (was 0.7%) |
| RUS | +9.6% | Good |
| CRO | +3.9% | Low but acceptable |
| CON | +5.3% | Moderate |
| BAL | +1.5% | Low — only affects dribble/tackle/shot balance |
| FK | +0.9% | Low — few opportunities |
| PK | +3.5% | Low — few opportunities |

## Tactics Influence (SWING)

| Tactic | SWING | Notes |
|--------|-------|-------|
| DefensiveCompactness | **14.0%** | Best range (was 5.5%) |
| PassingStyle | **17.5%** | High variance — needs review in future |
| PlaymakerFocus | **8.0%** | Fixed! (was 0%) |
| TacklingAggression | **8.0%** | Good |
| AttackTempo | **6.5%** | Good |
| CrossingStrategy | **7.0%** | Good |
| ShootingMentality | **6.0%** | Acceptable (was 14%) |
| PressingIntensity | **4.0%** | Acceptable (was 1.5%) |
| DefensiveLineHeight | **4.5%** | Acceptable |
| AttackWidth | **1.5%** | Low |
| MarkingStrategy | **1.0%** | Low |
| OffsideTrap | **1.0%** | Low |

---

## Known Issues / Future Work

1. **Average goals per match (~8.6 total) is high** for a football simulation. Could reduce by:
   - Lowering shot event weights
   - Increasing keeper base advantage further
   - Increasing defender block chance
   
2. **DRI/BAL/CRO influence remains low** relative to other attributes. These are niche attributes that only affect specific events. Acceptable for now.

3. **GK attributes (SAV/REF/POS) remain the most impactful**. This is realistic — a good keeper changes everything in football. The relative delta has been reduced from v2 levels.

4. **PlaymakerFocus** now works correctly but the optimal value is 4 (max), with 0 also being strong. The middle values (1-3) are weaker. This creates a "go big or go home" dynamic.

---

## Files Modified

- `match-engine/internal/engine/simulator.go` — PlaymakerFocus rewrite, keeper rebalancing, FK/PK tuning, wall defense
- `match-engine/internal/engine/resolver.go` — CalcSaveDefense, CalcOneOnOneDefense, CalcDribbleAttack/Defense, CalcPassAttack, CalcThroughAttack, CalcLongPassAttack, CalcCrossAttack, CalcShotAttack
- `match-engine/internal/engine/simulator_events_extra.go` — BAL in counter_attack/drop_ball, dribble weights
- `match-engine/internal/engine/benchmark_test.go` — FK stat fix, runBatchParallel added
