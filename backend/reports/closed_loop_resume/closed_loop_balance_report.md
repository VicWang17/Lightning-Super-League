# Closed Loop Balance Test Report

Generated at: `2026-06-01T10:17:28.141988Z`

## Run Summary

- Seasons captured: 1
- Invariant errors: 1
- Invariant warnings: 0
- Contracts created: 2564
- Renewals/recontracts: 1507
- Retired players: 110
- Youth generated: 4054
- Youth signed: 49
- Rookie-market listings: 17
- Rookie-market signed: 17
- Free-agent listings created: 224
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -2.14
- Latest state score range: -8 / 2
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 2 / 1327 / 1874
- Latest component avg contract/recent/fitness/load/rust: -1.0 / 1.16 / -0.82 / -0.78 / -0.7

## Correlations

- Team top8 OVR vs points: 0.269
- Team wage bill vs points: 0.240
- Team max OVR vs points: 0.193
- Player OVR vs average rating: 0.617

## Long-Term Balance Signals

- Latest balance Gini: 0.193
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 4 | 2564 | 1507 | 110 | 4054 | 49 | 17 | 17 | 224 | 0 | 10/16 | 46.4%/92.6% | -2.1/-8..2 | 1 |

## Invariants

- [error] S4 teams_above_15: 2 (team active roster above maximum)

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
