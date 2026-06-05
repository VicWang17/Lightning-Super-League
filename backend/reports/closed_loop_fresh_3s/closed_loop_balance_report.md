# Closed Loop Balance Test Report

Generated at: `2026-06-05T10:58:42.191875Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 5846
- Renewals/recontracts: 1988
- Retired players: 137
- Youth generated: 6546
- Youth signed: 1195
- Rookie-market listings: 5351
- Rookie-market signed: 568
- Free-agent listings created: 5438
- Auto-fill players joined: 0
- Training sessions: 942105
- Training breakthroughs: 104845
- Transfer listings: 1800
- Transfer offers/counters/finals: 47 / 10 / 6
- Club transfers completed: 12
- Player releases to free market: 0

## Player State Signals

- Latest avg state score: 0.65
- Latest state score range: -7 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 2055 / 1211 / 1082
- Latest component avg contract/recent/fitness/load/rust: -0.36 / 0.75 / 0.71 / -0.72 / -0.74

## Training & Fatigue Signals

- Latest avg fatigue / fitness: 44.11 / 94.3
- Latest players fatigue>75 / fitness<50: 1098 / 0
- Latest avg attr progress total: 1.82
- Training sessions S1..Sn: 308757 / 316735 / 316613
- Breakthroughs S1..Sn: 22959 / 42057 / 39829

## Injury Signals

- Injuries minor/medium/major: 1412 / 0 / 0
- Latest active injuries / medium+ active: 5 / 0
- Latest avg team major injuries / max team major injuries: 0.00 / 0
- Latest avg max body wear / players wear>70 / wear>90: 1.3 / 0 / 0
- Latest avg team max-wear signal: 1.30

## Match Tactics Signals

- Tactical setups captured: 12594
- F01 share: 0.6%
- Formation usage: F01=74, F02=1524, F03=783, F04=919, F05=8, F06=1407, F07=5499, F08=2380
- Avg starter-bench lineup/state/fitness gap: 12.60 / 2.98 / -8.30

## Transfer Market Signals

- Listings S1..Sn: 600 / 600 / 600
- Offers S1..Sn: 43 / 4 / 0
- Counter offers S1..Sn: 9 / 1 / 0
- Final offers S1..Sn: 5 / 1 / 0
- Completed club transfers S1..Sn: 12 / 0 / 0
- Releases to free market S1..Sn: 0 / 0 / 0
- AI listings / initial offers / counters / finals: 1800 / 31 / 10 / 6
- AI bought / sold / released: 12 / 12 / 0

## Correlations

- Team top8 OVR vs points: 0.188
- Team wage bill vs points: 0.168
- Team max OVR vs points: 0.184
- Player OVR vs average rating: 0.544
- Youth budget pct vs best prospect score: 0.535
- Youth budget pct vs useful prospect rate: 0.573
- Youth budget pct vs avg potential max: 0.713

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 410 | 9.4% | 38.3 | 70.2 | 65.8 | 19.4% | 1.79 | 7.11 |
| medium | 67 | 10.0% | 39.9 | 75.9 | 68.5 | 32.5% | 2.25 | 7.43 |
| high | 291 | 22.0% | 41.6 | 79.1 | 72.7 | 51.0% | 3.03 | 8.14 |

## Long-Term Balance Signals

- Latest balance Gini: 0.177
- Latest top8 OVR Gini: 0.043
- Champion relegations next season: 0
- Repeat champions in same league: 31

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Signed | Rookie Signed | FA Listings | Training | Breakthroughs | Injuries/Major | Transfer Offers | Transfers | Releases | Roster Min/Max | Wage Avg/Max | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |
| 1 | 1581 | 53 | 35 | 418 | 121 | 2054 | 308757 | 22959 | 519/0 | 43 | 12 | 0 | 15/17 | 57.5%/83.0% | 46.5 | 93.5 | 0 |
| 2 | 1833 | 719 | 43 | 380 | 174 | 1687 | 316735 | 42057 | 433/0 | 4 | 0 | 0 | 16/17 | 57.7%/81.7% | 44.6 | 94.0 | 0 |
| 3 | 2432 | 1216 | 59 | 397 | 273 | 1697 | 316613 | 39829 | 460/0 | 0 | 0 | 0 | 15/17 | 60.5%/97.5% | 44.1 | 94.3 | 0 |

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
