# Pilot Blind-Test Analysis

Training sessions: `session_20260601_160931, session_20260602_103531`
Blind sessions: `session_20260602_142058`

Training state points: 27
Blind state points: 10

## Error Metrics

| Output | Model | MAE | RMSE | Max abs |
|---|---|---:|---:|---:|
| F_N | Bxyz -> F | 6.3117 N | 6.3172 N | 6.6680 N |
| F_N | baseline F=h(d) | 0.9617 N | 0.9845 N | 1.1697 N |
| F_N | baseline mean | 0.3125 N | 0.3594 N | 0.5857 N |
| d_mm | Bxyz -> d | 2.9088 mm | 2.9158 mm | 3.1455 mm |
| d_mm | baseline d=g(|B|) | 0.3573 mm | 0.4042 mm | 0.5800 mm |
| d_mm | baseline mean | 0.3557 mm | 0.4040 mm | 0.5807 mm |

## Verdict

`NOT PASS`: Bxyz model must beat `F=h(d)` for force and `d=g(|B|)` for displacement by MAE.
