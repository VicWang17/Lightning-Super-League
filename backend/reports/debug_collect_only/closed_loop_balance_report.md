# Closed Loop Balance Test Report

Generated at: `2026-06-01T08:51:03.540328Z`

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

- Latest avg state score: 0.0
- Latest state score range: 0 / 0
- Latest forms HOT/GOOD/NEUTRAL/LOW: 0 / 0 / 3840 / 0
- Latest component avg contract/recent/fitness/load/rust: 0.0 / 0.0 / 0.0 / 0.0 / 0.0

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
| 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 15/15 | 0.0%/0.0% | 0.0/0..0 | 0 |

## Invariants

- [warning] S1 missing_player_state_cache: 3840 (active roster player has not been state-recalculated)

## Suggested Interpretation

- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.
- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.
- If OVR-to-points correlation is near zero, strong players are not translating into team strength.
- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.
- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.
- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.
