# Pilot Blind-Test Analysis

Training sessions: `session_20260602_211458, session_20260603_150122, session_20260603_135934, session_20260603_153110`
Blind sessions: `session_20260603_143946`
Auxiliary preload states: `excluded`

Training state points: 30
Blind state points: 6

## Error Metrics

| Output | Model | MAE | RMSE | Max abs |
|---|---|---:|---:|---:|
| F_N | Bxyz -> F | 0.0765 N | 0.0910 N | 0.1575 N |
| F_N | baseline F=h(d) | 0.0696 N | 0.0810 N | 0.1545 N |
| F_N | baseline mean | 0.0759 N | 0.0857 N | 0.1141 N |
| d_mm | Bxyz -> d | 0.0390 mm | 0.0475 mm | 0.0805 mm |
| d_mm | baseline d=g(|B|) | 0.0432 mm | 0.0586 mm | 0.1038 mm |
| d_mm | baseline mean | 0.0994 mm | 0.1155 mm | 0.2183 mm |

## Verdict

`NOT PASS`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.
