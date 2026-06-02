# Closed Loop Balance Test Report

Generated at: `2026-06-01T19:05:04.471456Z`

## Run Summary

- Seasons captured: 3
- Invariant errors: 0
- Invariant warnings: 0
- Contracts created: 6654
- Renewals/recontracts: 1960
- Retired players: 110
- Youth generated: 6361
- Youth signed: 1880
- Rookie-market listings: 4481
- Rookie-market signed: 651
- Free-agent listings created: 4686
- Auto-fill players joined: 0

## Player State Signals

- Latest avg state score: -0.03
- Latest state score range: -7 / 5
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 1570 / 2093 / 945
- Latest component avg contract/recent/fitness/load/rust: -0.35 / 0.84 / -0.31 / -0.56 / -0.64

## Correlations

- Team top8 OVR vs points: 0.227
- Team wage bill vs points: 0.203
- Team max OVR vs points: 0.220
- Player OVR vs average rating: 0.633

## Long-Term Balance Signals

- Latest balance Gini: 0.174
- Latest top8 OVR Gini: 0.050
- Champion relegations next season: 0
- Repeat champions in same league: 20

## Season Table

| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | State Avg/Range | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: |
| 1 | 1681 | 17 | 21 | 2265 | 489 | 1776 | 195 | 1804 | 0 | 16/18 | 56.7%/87.0% | 0.1/-6..4 | 0 |
| 2 | 2138 | 730 | 36 | 2048 | 645 | 1403 | 192 | 1442 | 0 | 17/18 | 55.3%/100.0% | 0.1/-7..4 | 0 |
| 3 | 2835 | 1213 | 53 | 2048 | 746 | 1302 | 264 | 1440 | 0 | 18/18 | 51.4%/87.3% | -0.0/-7..5 | 0 |

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
