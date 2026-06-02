# Closed Loop Balance Test Report

Generated at: `2026-06-02T07:45:19.333636Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 6116
- Renewals/recontracts: 2174
- Retired players: 122
- Youth generated: 6522
- Youth signed: 1232
- Rookie-market listings: 5290
- Rookie-market signed: 538
- Free-agent listings created: 5512
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -0.17
- Latest state score range: -6 / 4
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1276 / 2107 / 969
- Latest component avg contract/recent/fitness/load/rust: -0.37 / 0.96 / -0.46 / -0.63 / -0.67

## Correlations

- Team top8 OVR vs points: 0.218
- Team wage bill vs points: 0.189
- Team max OVR vs points: 0.192
- Player OVR vs average rating: 0.615
- Youth budget pct vs best prospect score: n/a
- Youth budget pct vs useful prospect rate: n/a
- Youth budget pct vs avg potential max: n/a

## Youth Budget Signals

| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| low | 571 | 10.0% | 38.0 | 70.3 | 65.5 | 27.2% | 1.81 | 7.12 |
| medium | 197 | 10.0% | 39.7 | 75.1 | 67.9 | 40.7% | 2.04 | 7.39 |
| high | 0 | 0.0% | 0.0 | 0.0 | 0.0 | 0.0% | 0.00 | 0.00 |

## Long-Term Balance Signals

- Latest balance Gini: 0.163
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 21

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 1 | 1584 | 35 | 27 | 2424 | 388 | 2036 | 130 | 2065 | 0 | 15/17 | 56.2%/90.3% | -0.1/-6..4 | 0 |
| 2 | 1906 | 809 | 36 | 2050 | 409 | 1641 | 170 | 1683 | 0 | 16/17 | 54.4%/88.0% | -0.1/-6..4 | 0 |
| 3 | 2626 | 1330 | 59 | 2048 | 435 | 1613 | 238 | 1764 | 0 | 17/17 | 52.0%/87.8% | -0.2/-6..4 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
