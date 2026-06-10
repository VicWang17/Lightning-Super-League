# Closed Loop Balance Test Report

Generated at: `2026-06-10T16:03:35.924600Z`

## Run Summary

- Seasons captured: 0
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

- Latest avg state score: n/a
- Latest state score range: n/a / n/a
- Latest forms HOT/GOOD/NEUTRAL/LOW: n/a / n/a / n/a / n/a
- Latest component avg contract/recent/fitness/load/rust: n/a / n/a / n/a / n/a / n/a

## Training & Fatigue Signals

- Latest avg fatigue / fitness: n/a / n/a
- Latest players fatigue>75 / fitness<50: n/a / n/a
- Latest avg attr progress total: n/a
- Training sessions S1..Sn: 
- Breakthroughs S1..Sn: 

## Injury Signals

- Injuries minor/medium/major: 0 / 0 / 0
- Latest active injuries / medium+ active: n/a / n/a
- Latest avg team major injuries / max team major injuries: 0.00 / 0
- Latest avg max body wear / players wear>70 / wear>90: n/a / n/a / n/a
- Latest avg team max-wear signal: 0.00

## Match Tactics Signals

- Tactical setups captured: 1408
- F01 share: 0.0%
- Formation usage: F02=280, F03=22, F04=360, F06=366, F07=299, F08=81
- Avg starter-bench lineup/state/fitness gap: 7.89 / 1.38 / -9.55

## Transfer Market Signals

- Listings S1..Sn: 
- Offers S1..Sn: 
- Counter offers S1..Sn: 
- Final offers S1..Sn: 
- Completed club transfers S1..Sn: 
- Releases to free market S1..Sn: 
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

- Latest balance Gini: n/a
- Latest top8 OVR Gini: n/a
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Signed | Rookie Signed | FA Listings | Training | Breakthroughs | Injuries/Major | Transfer Offers | Transfers | Releases | Roster Min/Max | Wage Avg/Max | Fatigue | Fitness | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: |

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
