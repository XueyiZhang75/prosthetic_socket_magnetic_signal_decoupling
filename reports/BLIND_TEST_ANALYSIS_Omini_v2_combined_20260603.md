# Pilot Blind-Test Analysis

Training sessions: `session_20260602_211458, session_20260603_150122, session_20260603_135934, session_20260603_153110`
Blind sessions: `session_20260603_160658, session_20260603_161958`
Auxiliary preload states: `excluded`

Training state points: 30
Blind state points: 6

## Error Metrics

| Output | Model | MAE | RMSE | Max abs |
|---|---|---:|---:|---:|
| F_N | Bxyz -> F | 0.1575 N | 0.1931 N | 0.2880 N |
| F_N | baseline F=h(d) | 0.1244 N | 0.1683 N | 0.3497 N |
| F_N | baseline mean | 0.1193 N | 0.1530 N | 0.3192 N |
| d_mm | Bxyz -> d | 0.0272 mm | 0.0291 mm | 0.0446 mm |
| d_mm | baseline d=g(|B|) | 0.0158 mm | 0.0187 mm | 0.0287 mm |
| d_mm | baseline mean | 0.0656 mm | 0.0682 mm | 0.0883 mm |

## Verdict

`NOT PASS`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.
