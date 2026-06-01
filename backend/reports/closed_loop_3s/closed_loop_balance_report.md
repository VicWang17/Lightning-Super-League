# Closed Loop Balance Test Report

Generated at: `2026-06-01T10:08:50.452016Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 1
- Contracts created: 4914
- Renewals/recontracts: 2014
- Retired players: 173
- Youth generated: 12288
- Youth signed: 0
- Rookie-market listings: 0
- Rookie-market signed: 0
- Free-agent listings created: 344
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -2.16
- Latest state score range: -8 / 1
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 0 / 1348 / 1931
- Latest component avg contract/recent/fitness/load/rust: -1.02 / 1.17 / -0.84 / -0.79 / -0.69

## Correlations

- Team top8 OVR vs points: 0.208
- Team wage bill vs points: 0.205
- Team max OVR vs points: 0.222
- Player OVR vs average rating: 0.621

## Long-Term Balance Signals

- Latest balance Gini: 0.192
- Latest top8 OVR Gini: 0.049
- Champion relegations next season: 0
- Repeat champions in same league: 11

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 2 | 1268 | 699 | 41 | 4096 | 0 | 0 | 0 | 41 | 0 | 12/15 | 55.5%/99.5% | -1.7/-8..3 | 0 |
| 3 | 1823 | 1187 | 66 | 4096 | 0 | 0 | 0 | 147 | 0 | 10/15 | 52.9%/96.5% | -2.0/-8..2 | 0 |
| 3 | 1823 | 128 | 66 | 4096 | 0 | 0 | 0 | 156 | 0 | 10/15 | 52.9%/96.5% | -2.2/-8..1 | 0 |

## Invariants

- [warning] S3 protected_rookies_still_active: 17 (rookie market listings still active after protection processing)

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
