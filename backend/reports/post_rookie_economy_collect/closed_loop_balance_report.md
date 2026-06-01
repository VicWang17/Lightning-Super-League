# Closed Loop Balance Test Report

Generated at: `2026-06-01T11:59:27.046714Z`

## Run Summary

- Seasons captured: 1
- Invariant errors: 0
- Invariant warnings: 1
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

- Latest avg state score: -0.1
- Latest state score range: -8 / 3
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1416 / 1843 / 997
- Latest component avg contract/recent/fitness/load/rust: -0.59 / 0.81 / -0.37 / -0.57 / -0.39

## Correlations

- Team top8 OVR vs points: n/a
- Team wage bill vs points: n/a
- Team max OVR vs points: n/a
- Player OVR vs average rating: n/a

## Long-Term Balance Signals

- Latest balance Gini: 0.000
- Latest top8 OVR Gini: 0.053
- Champion relegations next season: 0
- Repeat champions in same league: 0

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15/18 | 0.0%/0.0% | -0.1/-8..3 | 0 |

## Invariants

- [warning] S8 protected_rookies_still_active: 2622 (rookie market listings still active after protection processing)

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
