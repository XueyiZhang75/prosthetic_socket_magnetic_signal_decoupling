# 磁解耦实验 — 进度索引与报告总览

> 项目:力–位移解耦模型 APMD（UVA AIME 磁解耦项目）
> 实验计划见 [`EXPERIMENT_PLAN.md`](../EXPERIMENT_PLAN.md)。
> 本目录每个 Stage 一份独立报告,含目的 / 方法 / 装置参数 / 数据产出 / 结果分析 / 结论 / 问题与下一步。

## 当前重点：stamp-head key rerun

暂时不做完整 A-P 重测。下一步先换印章式 3D 打印压头，执行一个极简关键证据包：

```text
Pre-flight quick -> D quick -> I+ -> J+ -> N-mini
```

目标是验证新主线是否成立：路径激励能否在更稳定的法向压头下继续产生 same-d/different-F 和 same-F/different-d 的可辨识证据。

操作协议见 [`STAMP_HEAD_KEY_RERUN_PROTOCOL.md`](STAMP_HEAD_KEY_RERUN_PROTOCOL.md)。

### Stamp-head setup record

- Date: 2026-06-02
- Head ID: `stamp_head_v1`
- Sample re-clamped: no
- Magnet/sensor position changed: no
- Head bottom geometry: circular, diameter 55 mm
- Force calibration route: flip the force-sensor + stamp-head assembly, place
  known weights on the upward stamp face, run full `force_calibration.py`, then
  reinstall and use software live tare in the experimental orientation
- Force calibration ID: `force_calibration_20260602_190856`
- Force calibration constants: `TARE_OFFSET = 77955`,
  `CALIBRATION_FACTOR = 89508.9179 counts/N`, `R2 = 0.999979`
- Force calibration files: `force_calibration_20260602_190856.csv`,
  `force_calibration_20260602_190856.png`
- Arduino upload: completed on 2026-06-02 with
  `TARE_OFFSET = 77955` and `CALIBRATION_FACTOR = 89508.9179`
- Installed-orientation force check: live tare median `-2906.20 mN`,
  robust std `4.74 mN`; unloaded tared readings stayed near zero
  (roughly within +/-15 mN before hand contact); manual contact produced
  positive readings up to `+8.7698 N`, so the compression sign is positive
- D quick first attempt: force-only threshold `25 mN` triggered at apparent
  non-contact while a visible gap remained. Rejected this contact point and
  reset Stage D to `F_CONTACT_N = 0.080 N`, `APPROACH_STEP_MM = 0.1 mm`,
  positive-force-only contact detection, and manual visual confirmation.
- D quick logic update: sample/fixture geometry makes the physical lower limit
  the maximum safe compression endpoint. Stage D now detects contact as a
  force change point: `F - rolling_baseline >= 0.080 N`,
  `step_delta_F >= 0.015 N`, and `dF/dd >= 0.12 N/mm`, followed by visual
  confirmation. A Phase B lower-limit stop is recorded as
  `physical_lower_limit`.
- D quick accepted session: `session_20260602_195717`. Contact change point at
  descent `0.39 mm`, contact force `0.1586 N`; Phase B reached target with
  `F_max_obs = 2.3388 N`, `d_max_obs = 1.7900 mm`,
  recommended `F_max = 1.871 N`, `d_max = 1.611 mm`, verdict `OK`.
- D mapping update after fixture clarification: the physical lower limit is the
  safe maximum compression endpoint. Stage D now runs automatically after start:
  algorithmic contact change point, no visual/step confirmations, then
  `0.1 mm` F-d-B mapping until physical lower limit, MLX saturation, emergency
  `8.0 N` force limit, or `12.0 mm` software depth backstop. The `2.2 N` level
  is recorded as a marker only, not a stopping target.
- D lower-limit mapping attempt: `session_20260602_201421`. Auto contact at
  descent `0.50 mm`, contact force `0.1731 N`. Mapping was smooth through
  `d = 3.19 mm`, `F = 8.3564 N`, `|B| = 13.63 mT`, but stopped by the
  emergency force limit before reaching the physical lower limit. The `2.2 N`
  marker was crossed at `d = 1.87 mm`, `F = 2.2643 N`.
- Stamp-head contrast rerun settings selected from D-map:
  Stage I passive `D_HOLDS = [(160, 1.60)]`, Stage I+ `D_TARGETS_MM = [1.60]`
  with `D_PRELOAD_MM = 1.90`; Stage J passive `F_HOLDS = [(180, 1.80)]`,
  Stage J+ `F_TARGETS = [(180, 1.80)]` with `D_PRELOAD_EXTRA_MM = 0.30`,
  `D_PRELOAD_MAX_MM = 2.00`, and `D_SOFT_LIMIT_MM = 2.20`. All four use
  `HEAD_ID = stamp_head_v1`, `FORCE_CALIBRATION_ID =
  force_calibration_20260602_190856`, `DISPLACEMENT_ZERO_ID =
  stageD_session_20260602_201421`, and `F_HARD_LIMIT_N = 5.0`.
- Stage I passive contrast completed: `session_20260602_203043` at
  `d_actual = 1.59 mm`, 3 reps. Force relaxed by about `85-95 mN`, but magnetic
  response was weak (`Delta Bvec ~2-3 uT`, `Delta |B| ~2.4-4.0 uT`), close to
  short-term magnetic jitter. This is usable weak-path contrast for Stage I+.
  Analysis note: [`STAGE_I_STAMP_HEAD_PASSIVE_ANALYSIS.md`](STAGE_I_STAMP_HEAD_PASSIVE_ANALYSIS.md).
- Stage I+ first attempt `session_20260602_205536` aborted before usable data:
  live tare was `-1.3523 N`, far from the no-contact stamp-head baseline near
  `-2.9 N`, indicating the stamp head/sample was already touching or preloaded
  during software tare. The run was stopped by the new `5 N` hard-force guard at
  `F = 11.760 N`. Added pre-flight live-tare sanity checks and pre-contact
  force-abort guards before rerunning I+/J/J+.
- Stage I+ tuning rerun `session_20260602_210102`: all three pairs showed large
  path magnetic response, but only rep3 met the strict same-`d` criterion. Reps
  1-2 had `Delta d = +0.060 mm` and were marked `bad_d_match`. Tightened I+
  target-position tolerance to `0.02 mm` before the accepted rerun.
- Stage I+ accepted rerun `session_20260602_211458`: no-contact live tare was
  clean (`-2.9284 N`), and all three pairs were `strong` at `d_target = 1.60 mm`.
  Each pair stayed at `Delta d = +0.020 mm`; median `Delta F = -0.4432 N`,
  median `Delta Bvec = 118.0 uT`, and median `Delta |B| = +100.6 uT`. This is a
  clean same-`d` / different-`F` path-excitation contrast against passive Stage I
  (`Delta Bvec ~2-3 uT`). I+ is accepted; proceed to Stage J passive. Analysis
  note: [`STAGE_IPLUS_STAMP_HEAD_PATH_ANALYSIS.md`](STAGE_IPLUS_STAMP_HEAD_PATH_ANALYSIS.md).
- Stage J passive first-look run: `session_20260603_093056` at
  `F_target = 1.80 N`. Force control was stable enough
  (`Fmean = 1.778 N`, `Fstd = 8.0 mN`), and the controller drove a large
  stamp-head displacement creep (`Delta d = +0.520 mm`). The magnetic response
  stayed weak (`Delta |B| = -5.6 uT`, `||Delta B|| = 8.0 uT` first-to-last;
  head/tail means `||Delta B|| = 2.6 uT`). This is a useful passive same-`F`
  contrast: macroscopic creep exists, but passive fixed-force holding does not
  create a strong local magnetic response. Because this first-look run has only
  one trial, Stage J is now set to `N_TRIALS = 3` for the formal passive
  contrast rerun before Stage J+. Analysis note:
  [`STAGE_J_STAMP_HEAD_PASSIVE_ANALYSIS.md`](STAGE_J_STAMP_HEAD_PASSIVE_ANALYSIS.md).
- Stage J 3-trial formal rerun attempt `session_20260603_094854` was not
  accepted. Trial 2 did not run because reset-to-start triggered a downward
  overshoot from an already above-start position; trial 3 contained two large
  force outliers (`2.756 N` and `1.387 N`). Stage J was updated to skip
  downward start trimming when already at/above the no-contact start and to
  recheck/reacquire the force target after the 5 s pre-hold settle. Rerun Stage J
  3 trials before proceeding to J+.
- Stage J rerun attempt `session_20260603_100748` was aborted before data
  collection. The contact search hit the precontact abort guard
  (`F = 1.5568 N` at `pos = -0.1900 mm`) before a baseline was established,
  indicating the start position was still too close to contact. Stage J preflight
  now recommends a more conservative start: about `7 mm` above the physical
  lower limit, with a clearly visible air gap. If a visible gap exists but the
  raw live-tare baseline shifts from the historical `-2.9 N`, Stage J now asks
  for an explicit visual-gap `YES` confirmation before accepting that shifted
  baseline for the session.
- Stage J rerun attempt `session_20260603_102014` was aborted at preflight. The
  user entered lowercase `yes`, while the visual-gap override requires uppercase
  `YES`; more importantly, the live-tare statistics were unstable
  (`sample std = 510 mN`, range `-2.932` to `-1.421 N`). Stage J was updated to
  reject unstable live-tare statistics before offering any visual-gap override.
- Stage J rerun attempt `session_20260603_102526` showed a stable robust
  no-contact median near the historical baseline (`live_tare_N = -2.8631 N`,
  robust std `1.6 mN`) but rare force-channel outliers inflated sample std and
  range. This points to intermittent force-channel glitches rather than true
  sample contact. Stage J was updated to accept robust-stable expected-baseline
  tare and to record hold rows with short-window median force readings instead
  of single-sample force readings.

## 当前进度

| Stage | 内容 | 状态 | 报告 |
|---|---|---|---|
| A | 装置搭建与坐标固定 | ✅ 完成（流程熟悉版） | [STAGE_A_setup.md](STAGE_A_setup.md) |
| B | 噪声重测 + 信号健康 + 基线 | ✅ 完成 | [STAGE_B_baseline.md](STAGE_B_baseline.md) |
| C | 纯位移标定 B(q) | ✅ 完成 | [STAGE_C_pure_disp.md](STAGE_C_pure_disp.md) |
| D | 接触点与安全范围 | 🔄 下一步 | — |
| E | 基础压缩曲线 | ⬜ 待做 | — |
| F | 加载-卸载滞后 | ⬜ 待做 | — |
| G | 重复性 | ⬜ 待做 | — |
| H | 力控 B–F | ⬜ 待做 | — |
| I | 固定位移保持 → j_F | ✅ stamp-head passive 对照完成 | [STAGE_I_STAMP_HEAD_PASSIVE_ANALYSIS.md](STAGE_I_STAMP_HEAD_PASSIVE_ANALYSIS.md) |
| J | 固定力保持 → j_q | 🔄 需 3-trial 正式对照 | [STAGE_J_STAMP_HEAD_PASSIVE_ANALYSIS.md](STAGE_J_STAMP_HEAD_PASSIVE_ANALYSIS.md) |
| K | 变速 | ⬜ 待做 | — |
| L | 多深度网格 | ⬜ 待做 | — |
| M | 偏载（选做） | ⬜ 待做 | — |
| N | 合并 + 雅可比 & κ | ⬜ 待做 | — |
| O | 盲测 | ⬜ 待做 | — |
| P | 建模 | ⬜ 待做 | — |

## 说明

- 本轮为**第一遍走流程**,目的是熟悉整套实验的操作节奏与数据格式;装置的剛性固定、
  力通道标定等细节在正式轮再按标准收紧。报告中明确标注「流程熟悉版」处。
- 关键沿用结论(Stage 1):静态采集用 `low_noise`,动态用 `fast`,禁用 `fastest`;
  静态真实信号下限 ΔB>1.8 µT,动态 >12.6 µT。
