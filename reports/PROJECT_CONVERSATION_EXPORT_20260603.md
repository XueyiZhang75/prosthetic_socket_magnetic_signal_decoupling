# Project Conversation Export - Path-Excited Magnetic Decoupling

Date: 2026-06-03  
Project: magnetic decoupling of normal force and relative displacement in a soft interface  
Head: `stamp_head_v1`, circular stamp head, diameter 55 mm  
Force calibration: `force_calibration_20260602_190856`  
Displacement zero: `stageD_session_20260602_201421`

## 1. Executive Summary / 核心总结

### English

The project started from a direct decoupling question: can the same 3-axis magnetic signal be used to estimate both normal force `F` and magnet-sensor relative displacement `d` in a soft interface?

The original passive experiments, Stage I and Stage J, relied on force relaxation and displacement creep. They showed that the soft material did change mechanically, but the corresponding magnetic changes were weak. This made the original route too plain and not sufficiently convincing.

The important new direction is path-excited identifiability. Instead of waiting for small passive viscoelastic drift, the experiment actively uses loading, preloading, and unloading paths to create paired states:

- same `d`, different `F`, to probe force-sensitive magnetic variation;
- same `F`, different `d`, to probe displacement-sensitive magnetic variation.

The I+/J+ experiments showed strong path-pair signals, and Stage O-mini v2 further reproduced both modes at held-out interpolation states. The physical phenomenon is now strong. The current simple global linear `Bxyz -> [F,d]` model has not yet passed strict blind-test baselines, so the next step is model development rather than more repetitive evidence for the phenomenon.

### 中文

这个项目最开始的问题是：能不能直接从同一组三轴磁信号里同时解耦出法向力 `F` 和磁体-传感器相对位移 `d`。

原始 Stage I 和 Stage J 依赖被动材料行为：Stage I 固定位移等待力松弛，Stage J 固定力等待位移蠕变。结果说明材料确实发生了力学变化，但磁信号变化太弱，因此原始路线缺少亮点。

新的主线是“路径激励可辨识性”。我们不再只是被动等待材料蠕变或松弛，而是主动利用 loading、preload、unloading 路径制造成对状态：

- 同一 `d` 下不同 `F`，用于观察磁信号是否包含力信息；
- 同一 `F` 下不同 `d`，用于观察磁信号是否包含位移信息。

I+/J+ 已经证明路径激励能制造强磁信号分离，Stage O-mini v2 又在 held-out 插值状态下复现了两类模式。现在物理现象已经很扎实。当前简单全局线性 `Bxyz -> [F,d]` 模型还没有通过严格盲测基线，因此下一步重点应转向路径感知模型和局部解耦模型。

## 2. Experimental Evolution / 实验路线演化

| Stage | English purpose | 中文理解 | Key result |
|---|---|---|---|
| Stage I | Fixed-displacement hold | 固定位移等待力松弛 | Force changed, magnetic drift weak |
| Stage J | Fixed-force hold | 固定力等待位移蠕变 | Displacement changed, magnetic drift weak |
| Stage I+ | Same-d / different-F path pair | 同一位移下通过路径制造不同力 | Strong force split and magnetic split |
| Stage J+ | Same-F / different-d path pair | 同一力下通过路径制造不同位移 | Strong displacement split and magnetic split |
| Stage O-mini v2 | Held-out validation | 用未训练插值点验证路径激励现象 | Both modes reproduced strongly |

## 3. Common Experimental Setup / 共同实验设置

- Stamp head: circular, diameter 55 mm.
- Sample, magnet, and MLX sensor geometry were kept unchanged during the key rerun.
- Start position: Mark-10 about 7 mm above the lower limit, with a clear visible air gap.
- Force sensor: live tare before each acquisition.
- Magnetic baseline: no-contact `B0` captured before each acquisition.
- Force calibration: `TARE_OFFSET = 77955`, `CALIBRATION_FACTOR = 89508.9179 counts/N`.
- Force hard limit in scripts: 5.00 N.
- Key data are stored under `decouple_data/session_*`.

## 4. Original Passive Experiments / 原始被动实验

### Stage I - fixed-displacement hold

English:

- Target displacement: about `d = 1.59-1.60 mm`.
- Hold duration: 120 s.
- Goal: observe force relaxation at fixed displacement.
- Result: force relaxed by roughly 95-111 mN across repeats, but magnetic drift was only a few uT.
- Interpretation: passive force relaxation existed, but it did not create a strong magnetic decoupling signal.

中文：

- 位移固定在约 `1.59-1.60 mm`。
- 保持 120 s。
- 目的是利用力松弛在同一位移下制造不同力。
- 结果力确实有松弛，但磁信号变化只有几 uT，不够明显。

Data:

- `decouple_data/session_20260602_203043/I_hold_disp_160_rep1.csv`
- `decouple_data/session_20260602_203043/I_hold_disp_160_rep2.csv`
- `decouple_data/session_20260602_203043/I_hold_disp_160_rep3.csv`

Recommended figures:

- `reports/figs/I_main.png`
- `reports/nature_figures/stage_I_fixed_displacement_hold.png`

### Stage J - fixed-force hold

English:

- Target force: `F = 1.80 N`.
- Hold duration: 120 s.
- Goal: observe displacement creep at fixed force.
- Clean trials showed displacement creep, but magnetic variation was weak.
- Interpretation: passive creep alone was not enough to demonstrate strong decoupling.

中文：

- 固定力目标为 `1.80 N`。
- 保持 120 s。
- 目的是利用位移蠕变在同一力下制造不同位移。
- 结果位移确实变化，但磁信号仍然较弱。

Data:

- `reports/stage_J_clean_trial_summary.csv`
- `decouple_data/session_20260603_122143/J_hold_force_180_rep3.csv`
- `decouple_data/session_20260603_124327/J_hold_force_180_rep1.csv`
- `decouple_data/session_20260603_124327/J_hold_force_180_rep2.csv`

Recommended figures:

- `reports/figs/J_clean_trials.png`
- `reports/nature_figures/stage_J_fixed_force_hold.png`

## 5. Key Insight / 新主线

### English

The passive protocols showed that viscoelasticity exists, but the magnetic response was too small. The key insight is to use the soft material's path dependence actively:

`direct loading -> preload -> unloading/return`

This converts hysteresis, relaxation, and soft-interface memory from an experimental nuisance into an identifiability tool.

### 中文

被动实验说明材料确实有粘弹性，但磁响应太弱。新的关键想法是主动利用柔性材料的路径依赖：

`直接加载 -> 预加载 -> 卸载返回`

这样就把迟滞、松弛、路径记忆从“误差来源”变成了“解耦激励来源”。

## 6. Stage I+ Results / 同一位移不同力

Protocol:

- Direct loading to target displacement.
- Record target state.
- Preload deeper.
- Unload back to the same target displacement.
- Compare direct and return states.

Acceptance gates:

- displacement mismatch <= 0.05 mm;
- force split >= 0.10 N;
- magnetic vector split >= 12.5 uT.

Key results:

| Session | Target d | Preload d | Repeats | Typical delta d | Typical delta F | Typical delta Bvec | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `session_20260602_211458` | 1.60 mm | 1.90 mm | 3/3 | 0.020 mm | 443 mN | 118 uT | strong |
| `session_20260603_150122` | 1.40 mm | 1.70 mm | 3/3 | 0.030 mm | 385 mN | 56 uT | strong |

English interpretation:

At nearly the same displacement, the path history produced force differences of hundreds of mN and measurable magnetic differences. This supports a local force-sensitive magnetic direction.

中文理解：

在几乎相同位移下，路径历史可以制造数百 mN 的力差，同时磁信号也明显变化。这说明磁信号中存在可用于区分力状态的信息。

Data and figures:

- `decouple_data/session_20260602_211458/Iplus_pair_summary.csv`
- `decouple_data/session_20260602_211458/Iplus_same_d_diff_f.png`
- `decouple_data/session_20260603_150122/Iplus_pair_summary.csv`
- `decouple_data/session_20260603_150122/Iplus_same_d_diff_f.png`

Scripts:

- `stageI_plus_same_d_diff_f.py`
- `plot_stage_I_plus.py`

## 7. Stage J+ Results / 同一力不同位移

Protocol:

- Direct loading to target force.
- Record loading state.
- Preload deeper by approximately loading depth + 0.30 mm.
- Return/unload to matched loading force.
- Compare loading and unloading states.

Key results:

| Session | Target F | Repeats | Typical delta F | Typical delta d | Typical delta Bvec | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `session_20260603_135934` | 1.80 N | 3/3 | 36.6 mN | 0.150 mm | 462.5 uT | strong |
| `session_20260603_153110` | 1.70 N | 3/3 | 23-32 mN | 0.160 mm | 449-464 uT | strong |
| `session_20260603_153110` | 1.90 N | 3/3 | 25-49 mN | 0.170 mm | 441-445 uT | strong |

English interpretation:

At approximately matched force, the path history generated 0.15-0.17 mm displacement splits with magnetic vector changes of about 440-464 uT. This supports a strong displacement-sensitive magnetic direction.

中文理解：

在近似相同力下，路径历史制造了 `0.15-0.17 mm` 的位移差，同时三轴磁矢量变化达到 `440-464 uT`。这比被动 Stage J 明显得多。

Data and figures:

- `decouple_data/session_20260603_135934/Jplus_pair_summary.csv`
- `decouple_data/session_20260603_135934/Jplus_same_f_diff_d.png`
- `decouple_data/session_20260603_153110/Jplus_pair_summary.csv`
- `decouple_data/session_20260603_153110/Jplus_same_f_diff_d.png`

Scripts:

- `stageJ_plus_same_f_diff_d.py`
- `plot_stage_J_plus.py`

## 8. Stage O-mini v2 Held-out Validation / 盲测插值验证

Training sessions:

- I+ same-d/different-F: `session_20260602_211458`, `session_20260603_150122`
- J+ same-F/different-d: `session_20260603_135934`, `session_20260603_153110`

Held-out sessions:

- same-F/different-d: `session_20260603_160658`
- same-d/different-F: `session_20260603_161958`

Held-out results:

| Held-out pair | Target | Controlled variable | Split variable | Magnetic split | Verdict |
|---|---:|---:|---:|---:|---|
| same-F / different-d | 1.75 N | delta F = -58.1 mN | delta d = +0.160 mm | delta Bvec = 437.8 uT | strong |
| same-F / different-d | 1.85 N | delta F = -12.1 mN | delta d = +0.150 mm | delta Bvec = 460.1 uT | strong |
| same-d / different-F | 1.50 mm | delta d = +0.020 mm | delta F = -427.5 mN | delta Bvec = 74.0 uT | strong |

English interpretation:

Both complementary path-excitation modes were reproduced at held-out interpolation states. The effect is not limited to the exact calibration targets.

中文理解：

Stage O-mini v2 是目前最关键的证明：I+/J+ 不是只在训练点上有效，而是在没有直接训练过的插值点上也能复现。

Data:

- `decouple_data/session_20260603_160658/O_blind_state_summary.csv`
- `decouple_data/session_20260603_160658/O_blind_states_rep1.csv`
- `decouple_data/session_20260603_161958/O_blind_same_d_pair_summary.csv`
- `decouple_data/session_20260603_161958/O_blind_same_d_150_rep1.csv`

Scripts:

- `stageO_blind_test.py`
- `stageO_same_d_blind_test.py`
- `blind_test_analysis.py`

Reports:

- `reports/STAGE_O_MINI_V2_HELDOUT_SUMMARY_20260603.md`
- `reports/BLIND_TEST_ANALYSIS_Omini_v2_combined_20260603.md`

## 9. Current Model Status / 当前模型状态

Current blind-test model:

- Training state points: 30
- Blind state points: 6
- Auxiliary preload states excluded
- Model: simple global linear ridge model, `Bxyz -> [F,d]`

Error metrics:

| Output | Bxyz model MAE | Baseline MAE | Status |
|---|---:|---:|---|
| F | 0.1575 N | 0.1244 N from F=h(d) | not final |
| d | 0.0272 mm | 0.0158 mm from d=g(abs(B)) | not final |

English interpretation:

The held-out experiments strongly support the path-excitation identifiability route, but the simple global linear model is not yet the final decoupling model.

中文理解：

现在不能说“最终模型已经成功”。更稳的说法是：物理现象和可辨识性证据已经很强，但模型还需要升级。下一步应做路径感知模型、局部模型或加入 paired constraints，而不是继续重复采集同类路径对。

## 10. Seven-Slide Presentation Plan / 7页英文汇报结构

### Slide 1

English title: `Can magnetic signals directly decouple force and displacement in a soft interface?`

Purpose:

- Introduce the original research question.
- Explain why direct decoupling of `F` and `d` is difficult.
- Emphasize identifiability rather than only fitting.

中文理解：第一页不要直接讲新路线，先讲原始问题和研究动机。

### Slide 2

English title: `Original passive protocol: wait for relaxation or creep`

Purpose:

- Present Stage I and Stage J.
- Show that passive relaxation/creep existed but magnetic changes were weak.

Recommended figures:

- `reports/figs/I_main.png`
- `reports/figs/J_clean_trials.png`

中文理解：这一页解释为什么原路线不够强。

### Slide 3

English title: `New hypothesis: use path excitation to amplify identifiability`

Purpose:

- Introduce loading -> preload -> unloading.
- Explain I+ and J+ as two complementary identifiability probes.

中文理解：这是故事转折页。

### Slide 4

English title: `I+: path excitation creates same-d / different-F states`

Purpose:

- Show I+ protocol details.
- Present `d=1.60` and `d=1.40` results.

Recommended figures:

- `decouple_data/session_20260602_211458/Iplus_same_d_diff_f.png`
- `decouple_data/session_20260603_150122/Iplus_same_d_diff_f.png`

### Slide 5

English title: `J+: path excitation creates same-F / different-d states`

Purpose:

- Show J+ protocol details.
- Present `F=1.70`, `1.80`, `1.90 N` results.

Recommended figures:

- `decouple_data/session_20260603_135934/Jplus_same_f_diff_d.png`
- `decouple_data/session_20260603_153110/Jplus_same_f_diff_d.png`

### Slide 6

English title: `O-mini v2: held-out path pairs reproduce both decoupling modes`

Purpose:

- Show that the phenomenon holds at interpolation targets.
- Present the three held-out pairs.

中文理解：这是最关键的证据页。

### Slide 7

English title: `Strong identifiability evidence, model still under development`

Purpose:

- State what has been validated.
- Honestly report current blind model status.
- Define next steps: path-aware/local model and formal O2 blind test.

Final takeaway:

`Path excitation converts soft-interface hysteresis from a nuisance into an identifiability tool.`

## 11. Complete Material Checklist / 材料清单

Recommended figures for PPT:

- `reports/figs/I_main.png`
- `reports/figs/J_clean_trials.png`
- `decouple_data/session_20260602_211458/Iplus_same_d_diff_f.png`
- `decouple_data/session_20260603_150122/Iplus_same_d_diff_f.png`
- `decouple_data/session_20260603_135934/Jplus_same_f_diff_d.png`
- `decouple_data/session_20260603_153110/Jplus_same_f_diff_d.png`

Key acquisition scripts:

- `stageI_hold_disp.py`
- `stageJ_hold_force.py`
- `stageI_plus_same_d_diff_f.py`
- `stageJ_plus_same_f_diff_d.py`
- `stageO_blind_test.py`
- `stageO_same_d_blind_test.py`

Key plotting and analysis scripts:

- `plot_stage_I.py`
- `plot_stage_J_clean_trials.py`
- `plot_stage_I_plus.py`
- `plot_stage_J_plus.py`
- `blind_test_analysis.py`

Key protocol/report documents:

- `reports/STAMP_HEAD_KEY_RERUN_PROTOCOL.md`
- `reports/STAMP_HEAD_KEY_RERUN_ANALYSIS_SMOKE.md`
- `reports/FIGURE_GUIDE_STAGE_H_TO_O.md`
- `reports/STAGE_O_MINI_V2_HELDOUT_SUMMARY_20260603.md`
- `reports/BLIND_TEST_ANALYSIS_Omini_v2_combined_20260603.md`

## 12. Suggested Discussion With Advisor / 和导师汇报时的建议表达

English:

The main update is not that the final inverse model is already solved. The main update is that the experiment has found a much stronger direction: path excitation can create identifiable magnetic states in a soft interface. Both same-d/different-F and same-F/different-d pairs were reproduced at held-out interpolation points. This suggests that the next phase should focus on path-aware modeling rather than more passive relaxation experiments.

中文：

不要说“最终解耦模型已经完成”。应该说“我们发现了一条更有辨识度的新实验路线”。路径激励能在 held-out 状态下制造可区分的磁信号，因此下一步应该围绕路径感知模型和局部解耦模型继续推进。
