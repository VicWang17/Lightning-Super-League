# Closed Loop Balance Test Report

Generated at: `2026-06-03T07:41:43.047170Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 6037
- Renewals/recontracts: 2089
- Retired players: 139
- Youth generated: 6552
- Youth signed: 1274
- Rookie-market listings: 5278
- Rookie-market signed: 506
- Free-agent listings created: 5486
- Auto-fill players joined: 0
- Training sessions: 955371
- Training breakthroughs: 2713

## Player State Signals

- Latest avg state score: 0.4
- Latest state score range: -6 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1677 / 1943 / 732
- Latest component avg contract/recent/fitness/load/rust: -0.37 / 0.89 / 0.18 / -0.62 / -0.68

## Training & Fatigue Signals

- Latest avg fatigue / fitness: 44.82 / 74.6
- Latest players fatigue>75 / fitness<50: 1353 / 940
- Latest avg attr progress total: 3.62
- Training sessions S1..Sn: 311452 / 321583 / 322336
- Breakthroughs S1..Sn: 26 / 1102 / 1585

## Correlations

- Team top8 OVR vs points: 0.240
- Team wage bill vs points: 0.223
- Team max OVR vs points: 0.270
- Player OVR vs average rating: 0.630
- Youth budget pct vs best prospect score: 0.530
- Youth budget pct vs useful prospect rate: 0.612
- Youth budget pct vs avg potential max: 0.713

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 413 | 9.2% | 38.0 | 70.4 | 65.5 | 24.0% | 1.76 | 7.12 |
| medium | 65 | 10.0% | 39.8 | 75.2 | 67.6 | 40.2% | 2.22 | 7.42 |
| high | 290 | 22.0% | 41.4 | 79.1 | 72.1 | 59.6% | 2.98 | 8.17 |

## Long-Term Balance Signals

- Latest balance Gini: 0.170
- Latest top8 OVR Gini: 0.045
- Champion relegations next season: 0
- Repeat champions in same league: 24

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Training | Breakthroughs | Roster Min/Max | Wage Avg/Max | State Avg/Range | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | 1565 | 58 | 36 | 2453 | 421 | 2032 | 112 | 2063 | 0 | 311452 | 26 | 15/17 | 57.0%/93.4% | 0.3/-6..5 | 49.5 | 73.4 | 0 |
| 2 | 1864 | 753 | 42 | 2051 | 414 | 1637 | 165 | 1680 | 0 | 321583 | 1102 | 16/17 | 55.3%/92.8% | 0.4/-6..5 | 46.5 | 74.0 | 0 |
| 3 | 2608 | 1278 | 61 | 2048 | 439 | 1609 | 229 | 1743 | 0 | 322336 | 1585 | 17/17 | 53.2%/93.8% | 0.4/-6..5 | 44.8 | 74.6 | 0 |

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
