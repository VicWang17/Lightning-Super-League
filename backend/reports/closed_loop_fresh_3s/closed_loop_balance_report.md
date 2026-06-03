# Closed Loop Balance Test Report

Generated at: `2026-06-03T13:18:24.221663Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 6007
- Renewals/recontracts: 2085
- Retired players: 122
- Youth generated: 6535
- Youth signed: 1229
- Rookie-market listings: 5306
- Rookie-market signed: 509
- Free-agent listings created: 5497
- Auto-fill players joined: 0
- Training sessions: 949764
- Training breakthroughs: 20165

## Player State Signals

- Latest avg state score: 0.3
- Latest state score range: -7 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1792 / 1401 / 1156
- Latest component avg contract/recent/fitness/load/rust: -0.37 / 0.84 / 0.28 / -0.78 / -0.67

## Training & Fatigue Signals

- Latest avg fatigue / fitness: 50.74 / 79.8
- Latest players fatigue>75 / fitness<50: 1581 / 546
- Latest avg attr progress total: 0.95
- Training sessions S1..Sn: 310099 / 319270 / 320395
- Breakthroughs S1..Sn: 2023 / 8358 / 9784

## Correlations

- Team top8 OVR vs points: 0.174
- Team wage bill vs points: 0.159
- Team max OVR vs points: 0.160
- Player OVR vs average rating: 0.448
- Youth budget pct vs best prospect score: 0.564
- Youth budget pct vs useful prospect rate: 0.600
- Youth budget pct vs avg potential max: 0.708

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 408 | 9.3% | 38.0 | 70.0 | 65.0 | 22.4% | 1.72 | 7.00 |
| medium | 75 | 10.0% | 39.6 | 74.7 | 67.4 | 40.8% | 2.17 | 7.44 |
| high | 285 | 22.0% | 41.1 | 78.9 | 72.5 | 58.4% | 3.09 | 8.17 |

## Long-Term Balance Signals

- Latest balance Gini: 0.169
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 22

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Training | Breakthroughs | Roster Min/Max | Wage Avg/Max | State Avg/Range | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: |
| 1 | 1543 | 39 | 22 | 2439 | 397 | 2042 | 120 | 2064 | 0 | 310099 | 2023 | 15/17 | 57.2%/83.1% | 0.3/-6..5 | 53.5 | 80.7 | 0 |
| 2 | 1890 | 756 | 39 | 2048 | 397 | 1651 | 165 | 1687 | 0 | 319270 | 8358 | 16/17 | 55.7%/92.0% | 0.3/-6..5 | 52.3 | 79.6 | 0 |
| 3 | 2574 | 1290 | 61 | 2048 | 435 | 1613 | 224 | 1746 | 0 | 320395 | 9784 | 16/17 | 53.4%/81.3% | 0.3/-7..5 | 50.7 | 79.8 | 0 |

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
