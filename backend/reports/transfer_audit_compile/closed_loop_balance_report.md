# Closed Loop Balance Test Report

Generated at: `2026-06-04T05:46:30.576923Z`

## Run Summary

- Seasons captured: 1
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 0
- Renewals/recontracts: 0
- Retired players: 0
- Youth generated: 0
- Youth signed: 0
- Rookie-market listings: 0
- Rookie-market signed: 0
- Free-agent listings created: 0
- Auto-fill players joined: 0
- Training sessions: 0
- Training breakthroughs: 0
- Transfer listings: 0
- Transfer offers/counters/finals: 0 / 0 / 0
- Club transfers completed: 0
- Player releases to free market: 0

## Player State Signals

- Latest avg state score: 0.3
- Latest state score range: -7 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1792 / 1401 / 1156
- Latest component avg contract/recent/fitness/load/rust: -0.37 / 0.84 / 0.28 / -0.78 / -0.67

## Training & Fatigue Signals

- Latest avg fatigue / fitness: 50.74 / 79.8
- Latest players fatigue>75 / fitness<50: 1581 / 546
- Latest avg attr progress total: 0.95
- Training sessions S1..Sn: 0
- Breakthroughs S1..Sn: 0

## Match Tactics Signals

- Tactical setups captured: 0
- F01 share: 0.0%
- Formation usage: n/a
- Avg starter-bench lineup/state/fitness gap: 0.00 / 0.00 / 0.00

## Transfer Market Signals

- Listings S1..Sn: 0
- Offers S1..Sn: 0
- Counter offers S1..Sn: 0
- Final offers S1..Sn: 0
- Completed club transfers S1..Sn: 0
- Releases to free market S1..Sn: 0
- AI listings / initial offers / counters / finals: 0 / 0 / 0 / 0
- AI bought / sold / released: 0 / 0 / 0

## Correlations

- Team top8 OVR vs points: n/a
- Team wage bill vs points: n/a
- Team max OVR vs points: n/a
- Player OVR vs average rating: n/a
- Youth budget pct vs best prospect score: n/a
- Youth budget pct vs useful prospect rate: n/a
- Youth budget pct vs avg potential max: n/a

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 0 | 0.0% | 0.0 | 0.0 | 0.0 | 0.0% | 0.00 | 0.00 |
| medium | 0 | 0.0% | 0.0 | 0.0 | 0.0 | 0.0% | 0.00 | 0.00 |
| high | 0 | 0.0% | 0.0 | 0.0 | 0.0 | 0.0% | 0.00 | 0.00 |

## Long-Term Balance Signals

- Latest balance Gini: 0.000
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Signed | Rookie Signed | FA Listings | Training | Breakthroughs | Transfer Offers | Transfers | Releases | Roster Min/Max | Wage Avg/Max | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 16/17 | 0.0%/0.0% | 50.7 | 79.8 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
- If avg fatigue stays >70 or fitness <60, training load or match recovery may be too harsh.
- If young_avg_attr_progress >3.5/season or old_avg_attr_progress >1.0/season, growth speed is unhealthy.
- If training breakthroughs are near zero, check whether training plans are being generated and completed.
