# Pilot Blind-Test Analysis

Training sessions: `session_20260602_211458, session_20260603_135934`
Blind sessions: `session_20260603_143946`
Auxiliary preload states: `excluded`

Training state points: 12
Blind state points: 6

## Error Metrics

| Output | Model | MAE | RMSE | Max abs |
|---|---|---:|---:|---:|
| F_N | Bxyz -> F | 0.2091 N | 0.2453 N | 0.4133 N |
| F_N | baseline F=h(d) | 0.0853 N | 0.0997 N | 0.1708 N |
| F_N | baseline mean | 0.0985 N | 0.1273 N | 0.2095 N |
| d_mm | Bxyz -> d | 0.0498 mm | 0.0532 mm | 0.0716 mm |
| d_mm | baseline d=g(|B|) | 0.0649 mm | 0.0867 mm | 0.1653 mm |
| d_mm | baseline mean | 0.1142 mm | 0.1334 mm | 0.2625 mm |

## Verdict

`NOT PASS`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.
