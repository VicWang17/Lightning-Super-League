# Closed Loop Balance Test Report

Generated at: `2026-06-01T11:42:50.322612Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 3
- Contracts created: 9523
- Renewals/recontracts: 4633
- Retired players: 216
- Youth generated: 7002
- Youth signed: 3067
- Rookie-market listings: 3935
- Rookie-market signed: 1313
- Free-agent listings created: 4444
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -0.1
- Latest state score range: -8 / 3
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1416 / 1843 / 997
- Latest component avg contract/recent/fitness/load/rust: -0.59 / 0.81 / -0.37 / -0.57 / -0.39

## Correlations

- Team top8 OVR vs points: 0.296
- Team wage bill vs points: 0.256
- Team max OVR vs points: 0.265
- Player OVR vs average rating: 0.670

## Long-Term Balance Signals

- Latest balance Gini: 0.189
- Latest top8 OVR Gini: 0.053
- Champion relegations next season: 0
- Repeat champions in same league: 20

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 5 | 3369 | 1603 | 69 | 2898 | 1150 | 1748 | 474 | 1890 | 0 | 16/18 | 45.1%/88.5% | -0.4/-6..4 | 0 |
| 6 | 3088 | 1582 | 75 | 2048 | 944 | 1104 | 387 | 1278 | 0 | 15/18 | 41.7%/86.0% | -0.1/-7..4 | 0 |
| 7 | 3066 | 1448 | 72 | 2056 | 973 | 1083 | 452 | 1276 | 0 | 15/18 | 36.4%/75.6% | -0.1/-8..3 | 0 |

## Invariants

- [warning] S5 protected_rookies_still_active: 1274 (rookie market listings still active after protection processing)
- [warning] S6 protected_rookies_still_active: 1991 (rookie market listings still active after protection processing)
- [warning] S7 protected_rookies_still_active: 2622 (rookie market listings still active after protection processing)

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
