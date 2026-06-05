# Closed Loop Balance Test Report

Generated at: `2026-06-05T09:01:21.965610Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 5852
- Renewals/recontracts: 1953
- Retired players: 139
- Youth generated: 6571
- Youth signed: 1210
- Rookie-market listings: 5361
- Rookie-market signed: 558
- Free-agent listings created: 5464
- Auto-fill players joined: 0
- Training sessions: 943591
- Training breakthroughs: 105127
- Transfer listings: 1800
- Transfer offers/counters/finals: 53 / 19 / 0
- Club transfers completed: 13
- Player releases to free market: 0

## Player State Signals

- Latest avg state score: 0.73
- Latest state score range: -6 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 2091 / 1212 / 1043
- Latest component avg contract/recent/fitness/load/rust: -0.36 / 0.81 / 0.73 / -0.72 / -0.73

## Training & Fatigue Signals

- Latest avg fatigue / fitness: 42.06 / 95.1
- Latest players fatigue>75 / fitness<50: 970 / 0
- Latest avg attr progress total: 1.71
- Training sessions S1..Sn: 310146 / 316871 / 316574
- Breakthroughs S1..Sn: 22804 / 42133 / 40190

## Injury Signals

- Injuries minor/medium/major: 875 / 68 / 11
- Latest active injuries / medium+ active: 28 / 10
- Latest avg team major injuries / max team major injuries: 0.00 / 0
- Latest avg max body wear / players wear>70 / wear>90: 1.24 / 0 / 0
- Latest avg team max-wear signal: 1.24

## Match Tactics Signals

- Tactical setups captured: 0
- F01 share: 0.0%
- Formation usage: n/a
- Avg starter-bench lineup/state/fitness gap: 0.00 / 0.00 / 0.00

## Transfer Market Signals

- Listings S1..Sn: 600 / 600 / 600
- Offers S1..Sn: 50 / 2 / 1
- Counter offers S1..Sn: 19 / 0 / 0
- Final offers S1..Sn: 0 / 0 / 0
- Completed club transfers S1..Sn: 13 / 0 / 0
- Releases to free market S1..Sn: 0 / 0 / 0
- AI listings / initial offers / counters / finals: 1800 / 34 / 19 / 0
- AI bought / sold / released: 13 / 13 / 0

## Correlations

- Team top8 OVR vs points: 0.215
- Team wage bill vs points: 0.194
- Team max OVR vs points: 0.230
- Player OVR vs average rating: 0.555
- Youth budget pct vs best prospect score: 0.484
- Youth budget pct vs useful prospect rate: 0.601
- Youth budget pct vs avg potential max: 0.715

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 407 | 9.3% | 38.4 | 70.4 | 66.5 | 19.8% | 1.70 | 7.07 |
| medium | 74 | 10.0% | 40.0 | 74.9 | 68.4 | 31.4% | 2.07 | 7.32 |
| high | 287 | 22.0% | 41.3 | 79.3 | 72.7 | 53.7% | 3.05 | 8.25 |

## Long-Term Balance Signals

- Latest balance Gini: 0.179
- Latest top8 OVR Gini: 0.044
- Champion relegations next season: 0
- Repeat champions in same league: 24

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Signed | Rookie Signed | FA Listings | Training | Breakthroughs | Injuries/Major | Transfer Offers | Transfers | Releases | Roster Min/Max | Wage Avg/Max | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 1615 | 51 | 35 | 446 | 97 | 2048 | 310146 | 22804 | 954/11 | 50 | 13 | 0 | 16/17 | 58.3%/91.5% | 44.9 | 94.2 | 0 |
| 2 | 1828 | 756 | 32 | 371 | 171 | 1697 | 316871 | 42133 | 0/0 | 2 | 0 | 0 | 16/17 | 58.5%/87.2% | 43.3 | 94.8 | 0 |
| 3 | 2409 | 1146 | 72 | 393 | 290 | 1719 | 316574 | 40190 | 0/0 | 1 | 0 | 0 | 16/17 | 60.1%/93.7% | 42.1 | 95.1 | 0 |

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
