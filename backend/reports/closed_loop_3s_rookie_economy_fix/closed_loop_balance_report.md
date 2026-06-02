# Closed Loop Balance Test Report

Generated at: `2026-06-01T15:57:33.818567Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 9505
- Renewals/recontracts: 3104
- Retired players: 301
- Youth generated: 6394
- Youth signed: 3283
- Rookie-market listings: 3111
- Rookie-market signed: 2405
- Free-agent listings created: 3820
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: 0.58
- Latest state score range: -6 / 4
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 2268 / 923 / 708
- Latest component avg contract/recent/fitness/load/rust: -0.29 / 0.69 / -0.19 / -0.46 / -0.18

## Correlations

- Team top8 OVR vs points: 0.440
- Team wage bill vs points: 0.369
- Team max OVR vs points: 0.333
- Player OVR vs average rating: 0.655

## Long-Term Balance Signals

- Latest balance Gini: 0.168
- Latest top8 OVR Gini: 0.075
- Champion relegations next season: 0
- Repeat champions in same league: 26

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 8 | 3079 | 1176 | 98 | 2091 | 1055 | 1036 | 614 | 1270 | 0 | 15/18 | 31.2%/71.4% | 0.3/-7..4 | 0 |
| 9 | 3189 | 1044 | 90 | 2111 | 1073 | 1038 | 825 | 1283 | 0 | 14/18 | 26.0%/74.7% | 0.4/-6..4 | 0 |
| 10 | 3237 | 884 | 113 | 2192 | 1155 | 1037 | 966 | 1267 | 0 | 11/18 | 20.8%/85.6% | 0.6/-6..4 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
