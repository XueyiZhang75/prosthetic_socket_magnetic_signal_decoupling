# Pilot Blind-Test Analysis

Training sessions: `session_20260602_211458, session_20260603_150122, session_20260603_135934, session_20260603_153110`
Blind sessions: `session_20260603_160658`
Auxiliary preload states: `excluded`

Training state points: 30
Blind state points: 4

## Error Metrics

| Output | Model | MAE | RMSE | Max abs |
|---|---|---:|---:|---:|
| F_N | Bxyz -> F | 0.1656 N | 0.1909 N | 0.2880 N |
| F_N | baseline F=h(d) | 0.0679 N | 0.0895 N | 0.1404 N |
| F_N | baseline mean | 0.0633 N | 0.0669 N | 0.0981 N |
| d_mm | Bxyz -> d | 0.0280 mm | 0.0297 mm | 0.0446 mm |
| d_mm | baseline d=g(|B|) | 0.0185 mm | 0.0217 mm | 0.0287 mm |
| d_mm | baseline mean | 0.0775 mm | 0.0778 mm | 0.0883 mm |

## Verdict

`NOT PASS`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.
