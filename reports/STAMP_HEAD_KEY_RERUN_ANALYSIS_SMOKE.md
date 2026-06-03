# Stamp-Head Key Rerun N-mini Analysis

This report uses only the specified I+ and J+ pair-summary sessions.
It is a quick local-identifiability check, not the full Stage N audit.

## Sessions

- I+ force-column session: `session_20260601_160931`
- J+ displacement-column session: `session_20260602_103531`

## Pair Columns

| Source | Usable pairs | Column estimate | Median signal | Median denominator |
|---|---:|---|---:|---:|
| I+ (session_20260601_160931) | 3/3 | (30.8, -88.4, 267.2) uT/N | 140.6 uT | 0.4826 |
| J+ (session_20260602_103531) | 4/6 | (-552.2, 3299.2, 544.5) uT/mm | 820.1 uT | 0.2400 |

## Local Identifiability

- Pair-column angle: 80.2 deg
- Absolute cosine: 0.170
- Column condition number: 12.15
- Verdict: `PASS`

## Interpretation Notes

- Pair-column angle=80.2 deg (abs cosine=0.17) from I+ j_F and J+ j_d estimates.
- I+ (session_20260601_160931): 3/3 usable pairs, median |delta B3|=140.6 uT.
- J+ (session_20260602_103531): 4/6 usable pairs, median |delta B3|=820.1 uT.
- Median j_F=(30.8, -88.4, 267.2) uT/N; median j_d=(-552.2, 3299.2, 544.5) uT/mm.
- The pair-column directions are well separated; this supports local identifiability.
