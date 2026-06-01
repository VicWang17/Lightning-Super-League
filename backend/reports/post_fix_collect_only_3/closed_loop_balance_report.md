# Closed Loop Balance Test Report

Generated at: `2026-06-01T10:38:46.349327Z`

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

## Player State Signals

- Latest avg state score: -2.14
- Latest state score range: -8 / 2
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 2 / 1327 / 1874
- Latest component avg contract/recent/fitness/load/rust: -1.0 / 1.16 / -0.82 / -0.78 / -0.7

## Correlations

- Team top8 OVR vs points: n/a
- Team wage bill vs points: n/a
- Team max OVR vs points: n/a
- Player OVR vs average rating: n/a

## Long-Term Balance Signals

- Latest balance Gini: 0.000
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 10/16 | 0.0%/0.0% | -2.1/-8..2 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
