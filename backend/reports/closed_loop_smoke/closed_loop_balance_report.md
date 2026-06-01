# Closed Loop Balance Test Report

Generated at: `2026-06-01T09:09:23.423228Z`

## Run Summary

- Seasons captured: 1
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 1017
- Renewals/recontracts: 0
- Retired players: 36
- Youth generated: 4096
- Youth signed: 0
- Rookie-market listings: 0
- Rookie-market signed: 0
- Free-agent listings created: 26
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -1.39
- Latest state score range: -8 / 4
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 26 / 2231 / 1521
- Latest component avg contract/recent/fitness/load/rust: -0.39 / 1.15 / -0.66 / -0.68 / -0.8

## Correlations

- Team top8 OVR vs points: 0.214
- Team wage bill vs points: 0.197
- Team max OVR vs points: 0.260
- Player OVR vs average rating: 0.638

## Long-Term Balance Signals

- Latest balance Gini: 0.192
- Latest top8 OVR Gini: 0.048
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 1 | 1017 | 0 | 36 | 4096 | 0 | 0 | 0 | 26 | 0 | 13/15 | 57.0%/85.6% | -1.4/-8..4 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
