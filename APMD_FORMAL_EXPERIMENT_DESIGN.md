# APMD 正式实验设计方案

> 项目主线：Active Path-Pair Magnetic Decoupling, APMD  
> 核心目标：通过受控 loading-unloading minor loops，系统调节 preload depth、preload dwell time 和 recovery time，主动构造 near-same-d/different-F 与 near-same-F/different-d 的 path-pair states，利用柔性材料的迟滞、恢复、松弛和蠕变特性，将传统意义上的“路径误差源”转化为“可控可辨识激励源”，最终从三轴磁信号 `B=(Bx, By, Bz)` 中直接解耦法向力 `F` 和磁体-传感器相对位移 `d`。

---

## 0. 设计原则与文献启发

### 0.1 需要吸收的文献实验思想

已有软触觉传感文献并不只是在口头提到迟滞，而是进行了与本项目高度相关的实验：

1. **loading/unloading 分支实验**  
   Lim 等关于 MRE 磁触觉传感器的工作中，将传感器处于 loading 还是 unloading 的路径状态作为迟滞建模的一部分。他们通过磁通量向量变化识别 loading/unloading 状态，并比较考虑与不考虑迟滞分支的模型表现。

2. **重复压缩和 prestress/history 实验**  
   同一篇工作中还观察到连续预应力或重复变形会改变传感器物理响应，例如最大可测力随 prestress 历史变化。这提示我们不能只记录一次 loading/unloading，而需要把 preload 深度、preload 保持时间、循环次数和恢复时间作为正式变量。

3. **不同硬度材料的 force-depth loading/unloading 曲线**  
   GenForce 相关工作测量了不同硬度软材料在 loading 和 unloading 阶段的 force-depth 曲线，明确显示同一压入深度下 loading 阶段的接触力可高于 unloading 阶段。这说明“同一个几何状态对应不同力状态”不是偶然现象，而是软材料迟滞的典型表现。

4. **材料补偿思想**  
   GenForce 将材料硬度、迟滞和摩擦差异作为跨传感器力预测中的误差来源，并引入 material compensation。对本项目而言，这启发我们增加“材料/路径剂量”表征实验：不是简单补偿迟滞，而是先量化迟滞路径如何改变 `F-d-B` 关系，再决定哪些路径状态最适合解耦。

### 0.2 本方案从文献中吸收的具体实验元素

本实验计划不只比较两条曲线，而是把文献中的路径相关现象转化为以下可执行实验控制：

```text
loading / unloading branch labeling
repeated compression history tracking
preload depth scan
preload holding-time scan
recovery-time scan
force-depth branch curve measurement
path-dependent model features
passive baseline vs active path-pair contrast
```

### 0.3 固定采集规则

为了避免每个实验使用不同采样窗口，本方案统一规定：

```text
active target-state record = 45 s
active preload-state record = 30 s
active return/unloading target-state record = 45 s
state summary window = last 10 s median
minimum effective sampling rate = 10 Hz
minimum valid samples per target-state summary = 80
minimum valid samples per preload-state summary = 80
rest between active cycles = 120 s
```

说明：

- 45 s target-state 记录在 10 Hz 下约为 450 个样本，最后 10 s median 约使用 100 个样本，比之前 last 5 s 更稳健。
- preload-state 固定记录 30 s，而不是 15 s，是为了更充分地表征路径历史状态。
- passive hold 实验不是用于最终状态摘要，而是用于观察慢松弛/蠕变，因此单独使用更长时间。

### 0.4 通用坐标与控制定义

```text
d > 0: stamp head presses downward after contact
d = 0: daily contact point from force-change contact search
F > 0: compressive normal force
Mark-10 no-contact start position = 6 mm above the physical lower limit
Mark-10 physical lower limit = maximum safe compression endpoint
```

Mark-10 是位移控制设备。所有“固定力”或“回到目标力”的实验，本质上都是：

```text
control variable: small displacement command
measured variable: external force sensor reading
force matching: accepted only if force median falls inside tolerance
```

因此，本文档不再使用“精确固定 F”的说法，而使用：

```text
near-matched force
force-matched within tolerance
quasi-force-control by displacement nudges
```

### 0.5 数据保存与作图规则

每一次实验 session 都必须形成独立的数据与图像记录，避免后续作图覆盖旧 session 结果。

```text
raw data directory = decouple_data/session_<date_time>/
session figures directory = same folder as the corresponding session data
figure output format = png
do not overwrite figures from older sessions
do not save a new session figure only to shared reports/figs as the primary record
```

具体规定：

1. 每个实验 session 生成的 summary CSV、raw CSV、run log 和 quick-look figures 应保存在同一个 `session_<date_time>` 文件夹内。
2. 若需要为汇报或论文额外整理图片，可以另存到 `reports/figs`，但该文件只能作为汇报副本，不能替代 session 文件夹内的原始图像记录。
3. 同一类实验的不同 session 画图时，文件名应包含 session id 或直接保存在对应 session 文件夹内，避免覆盖旧 session 的图片。
4. 正式作图首选颜色顺序固定为：

```text
first color = black
second color = red
third color = blue
additional colors = chosen as needed
```

5. 若图中只有 2-3 个 repeats、paths 或 states，应优先使用黑、红、蓝，保持不同图之间的视觉一致性。

---

### 0.6 实验脚本与 session 台账

本节作为本文件的实验索引。每完成一次正式且可用的实验，采集脚本应自动在对应行补充新的 `session_<date_time>`。失败、中断、gate 未通过或不能作为证据使用的 session 不写入本 md，只保留在对应 `decouple_data/session_<date_time>/run_log.txt` 中。这样读本文件时，可以同时看到实验设计、执行脚本和已经完成的可用数据记录。

**记录规则**

```text
acquisition script = 实际采集数据的脚本
plot script = 生成该 session quick-look PNG 的脚本
analysis script = 汇总、gate、可辨识性或盲测分析脚本
accepted sessions = 可作为当前证据使用的 session
formal rerun session = 按本版 APMD_FORMAL_EXPERIMENT_DESIGN 执行后新增的 session
registry rule = acquisition script writes only successful usable sessions automatically
```

若某个实验还没有独立脚本，可以先写：

```text
script status = planned / parameterized from existing script
```

#### 阶段 1 脚本与 session 记录

| 实验 | 采集脚本 | 作图/分析脚本 | 当前记录 | 备注 |
|---|---|---|---|---|
| 实验 1.1 力传感器标定与稳定性检查 | `force_calibration.py`, `force_serial.py` | `replot_calibration.py` | `force_calibration_20260602_190856.csv/png`; terminal live check on 2026-06-03 after UNO ground-wire fix | 每天正式实验前仍需运行 `force_serial.py` 做 no-load 稳定性检查 |
| 实验 1.2 接触零点与位移重复性检查 | `stageD_safety_range.py`, `stageD_precycle.py` | `plot_stages_DE.py` 或 session-local summary | `session_20260602_201421` | 当前 `DISPLACEMENT_ZERO_ID = stageD_session_20260602_201421`; 新一轮正式实验可先做 quick contact check |
| 实验 1.3 无接触磁基线与运动伪差检查 | `stageB_baseline.py`, `stageC_pure_disp_auto.py` | `reports/make_stageBC_figs.py` | earlier Stage B/C sessions, not yet re-indexed in this formal table | 若后续 active path 信号异常，需要优先补做 |

#### 阶段 2 脚本与 session 记录

| 实验 | 采集脚本 | 作图/分析脚本 | 当前可用 session | formal rerun session |
|---|---|---|---|---|
| 实验 2.1 固定位移被动松弛实验 | `stageI_hold_disp.py` | `plot_stage_I.py` | `session_20260608_192027` | formal: `session_20260608_192027`; note=d=2.80 mm, median |dF|=244 mN, median dBvec=6.0 uT |
| 实验 2.2 近似同位移/异力主动路径对实验 | `apmd_same_d_different_f_path_pair.py` | `plot_apmd_same_d_different_f.py` | TBD after current-environment rerun | formal: `session_20260608_194434`; summary=`same_d_different_f_pair_summary.csv`; figure=`same_d_different_f_path_pair.png` |
| 实验 2.3 固定力被动蠕变实验 | `apmd_fixed_force_passive_creep.py` | planned: `plot_apmd_fixed_force_passive_creep.py` | TBD after current-environment rerun | TBD |
| 实验 2.4 近似同力/异位移主动路径对实验 | `apmd_same_f_different_d_path_pair.py` | planned: `plot_apmd_same_f_different_d.py` | current-environment rerun/reference: `session_20260609_173842`; summary=`same_f_different_d_pair_summary.csv`; note=3/3 complete, 2/3 strong, median `Δd=+0.170 mm`, median `ΔBvec=302.6 uT`, rep2 force gate borderline `|ΔF|=51.05 mN` | reference only; not auto-registered as formal because formal same-F gate is 3/3 and rep2 exceeds 50 mN by 1.05 mN |

#### 阶段 3 脚本与 session 记录

| 实验 | 采集脚本 | 作图/分析脚本 | session 记录 | 脚本状态 |
|---|---|---|---|---|
| 实验 3.1A 近似同位移/异力路径对粗扫描 A | `python .\apmd_same_d_different_f_scan.py A` | planned: `plot_apmd_same_d_different_f_scan.py` | reference: `session_20260608_173406` for d=2.40/2.60/2.80, 2 repeats/point; note=deep scan reference only<br>formal: `session_20260610_091145`; summary=`same_d_different_f_scan_A_pair_summary.csv`; figure=`same_d_different_f_scan_A.png`; note=strong=9/9; same_d=9/9 | ready for formal rerun: targets `[2.40, 2.60, 2.80]`, preload map `+0.30 mm`, `SCAN_TRIALS = 3`, 9 planned pairs |
| 实验 3.1B 近似同位移/异力路径对粗扫描 B | `python .\apmd_same_d_different_f_scan.py B` | planned: `plot_apmd_same_d_different_f_scan.py` | reference: `session_20260608_173406` for d=3.00/3.20, 2 repeats/point; d=3.40/3.60 still need formal data<br>formal: `session_20260610_104017`; summary=`same_d_different_f_scan_B_pair_summary.csv`; figure=`same_d_different_f_scan_B.png`; note=strong=12/12; same_d=12/12 | ready for formal rerun: targets `[3.00, 3.20, 3.40, 3.60]`, preload map `+0.30 mm`, `SCAN_TRIALS = 3`, 12 planned pairs |
| 实验 3.2-150 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 150` | planned: `plot_apmd_same_f_different_d_scan.py` | formal: `session_20260610_153403`; summary=`same_f_different_d_scan_150_pair_summary.csv`; figure=not generated yet; note=3/3 strong, same-F=3/3 | target `1.50 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-180 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 180` | planned: `plot_apmd_same_f_different_d_scan.py` | formal: `session_20260611_093557`; summary=`same_f_different_d_scan_180_pair_summary.csv`; figure=not generated yet | target `1.80 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-250 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 250` | planned: `plot_apmd_same_f_different_d_scan.py` | formal: `session_20260611_110131`; summary=`same_f_different_d_scan_250_pair_summary.csv`; figure=not generated yet | target `2.50 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-320 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 320` | planned: `plot_apmd_same_f_different_d_scan.py` | formal composite: `session_20260611_142649` rep1/rep2 + `session_20260611_145735` rep1 as formal rep3; summary=`same_f_different_d_scan_320_formal_composite_summary.csv`; note=3/3 strong, same-F=3/3 | target `3.20 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-375 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 375` | planned: `plot_apmd_same_f_different_d_scan.py` | formal composite: `session_20260611_153032` rep1/rep2 + `session_20260611_155956` rep1 as formal rep3; summary=`same_f_different_d_scan_375_formal_composite_summary.csv`; note=3/3 strong, same-F=3/3 | target `3.75 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-430 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 430` | planned: `plot_apmd_same_f_different_d_scan.py` | formal: `session_20260611_164622`; summary=`same_f_different_d_scan_430_pair_summary.csv`; figure=not generated yet; note=3/3 strong, same-F=3/3 | target `4.30 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2-490 近似同力/异位移路径对单点扫描 | `python .\apmd_same_f_different_d_scan.py 490` | planned: `plot_apmd_same_f_different_d_scan.py` | formal composite: `session_20260611_173832` rep2 + `session_20260611_181124` rep1 + `session_20260611_183729` rep1; summary=`same_f_different_d_scan_490_formal_composite_summary.csv`; note=3/3 strong, same-F=3/3 | target `4.90 N`, preload `loading d + 0.30 mm`, `trials = 3`, 3 planned pairs |
| 实验 3.2 总结 近似同力/异位移路径对粗扫描 | `python .\apmd_same_f_different_d_scan.py <target>` | `plot_apmd_same_f_different_d_scan_31style.py` | formal complete through `1.50/1.80/2.50/3.20/3.75/4.30/4.90 N`; figure=`experiment_3_2_style31_complete_abcde.png`; note=`5.50 N` not required for this formal round | 3.2 判定完成，后续进入 3.3 |
| 实验 3.3A same-d preload-depth 路径剂量实验 | `python .\apmd_same_d_path_dosage.py` | `plot_apmd_same_d_path_dosage.py` | formal: `session_20260612_155336`; summary=`same_d_path_dosage_A_pair_summary.csv`; figure=`same_d_path_dosage_A.png`; dose summary=`same_d_path_dosage_A_dose_summary.csv`; note=9/9 strong, same-d=9/9, preload depth gives monotonic path-dose response | complete; `target d = 3.40 mm`, preload `3.60/3.70/3.80 mm`, 3 pairs/preload |
| 实验 3.3B same-d preload holding-time 路径剂量实验 | `python .\apmd_same_d_path_hold_time.py` | `plot_apmd_same_d_path_hold_time.py` | formal: `session_20260612_180059`; summary=`same_d_path_hold_time_B_pair_summary.csv`; figure=`same_d_path_hold_time_B.png`; hold summary=`same_d_path_hold_time_B_hold_summary.csv`; note=3.3B complete; strong=9/9; same_d=9/9; hold-time effect weak/non-monotonic | complete; `target d = 3.40 mm`, preload `3.80 mm`, preload hold `5/30/90 s`, 3 pairs/hold |
| 实验 3.4A-020 same-F preload-extra-depth 路径剂量实验 | `python .\apmd_same_f_path_dosage.py 020` | planned: `plot_apmd_same_f_path_dosage.py` | formal composite accepted: `session_20260612_203004` rep1 + `session_20260613_141828` rep1 + `session_20260613_162917` rep3; summaries=`same_f_path_dosage_A_extra020_pair_summary.csv`; note=2/3 strict strong + 1/3 boundary accepted weak_disp_split; same-F=3/3; b-signal=3/3; conclusion=`+0.20 mm` preload extra is a shallow/boundary dose, producing strong magnetic separation but marginal displacement split | `target F = 3.75 N`, preload extra `+0.20 mm`, 3 accepted pairs; proceed to 030 |
| 实验 3.4A-030 same-F preload-extra-depth 路径剂量实验 | `python .\apmd_same_f_path_dosage.py 030` | planned: `plot_apmd_same_f_path_dosage.py` | formal accepted: `session_20260613_174105`; summary=`same_f_path_dosage_A_extra030_pair_summary.csv`; note=boundary-corrected strong=3/3; original CSV has 1/3 strict strong + 2/3 `Δd=+0.1000 mm` boundary rows; same-F=3/3; b-signal=3/3; conclusion=`+0.30 mm` preload extra gives strong magnetic separation and sits at the displacement-split boundary for two repeats | `target F = 3.75 N`, preload extra `+0.30 mm`, 3 accepted pairs; proceed to 040 |
| 实验 3.4A-040 same-F preload-extra-depth 路径剂量实验 | `python .\apmd_same_f_path_dosage.py 040` | planned: `plot_apmd_same_f_path_dosage.py` | formal composite accepted: `session_20260613_192031` rep1/rep2 + `session_20260613_194759` rep1; summaries=`same_f_path_dosage_A_extra040_pair_summary.csv`; note=3/3 strong, same-F=3/3, b-signal=3/3; excluded=`session_20260613_192031` rep3 due bad F match | `target F = 3.75 N`, preload extra `+0.40 mm`, 3 accepted pairs; 3.4A complete |
| 实验 3.4B-005 same-F preload holding-time 路径剂量实验 | `python .\apmd_same_f_path_hold_time.py 005` | planned: `plot_apmd_same_f_path_hold_time.py` | formal composite accepted: `session_20260614_142325` rep1 + `session_20260614_145304` rep1 + `session_20260614_150342` rep1; summaries=`same_f_path_hold_time_B_hold005_pair_summary.csv`; note=3/3 strong, same-F=3/3, displacement-split=3/3, b-signal=3/3; excluded=`session_20260614_142325` rep2/rep3 and `session_20260614_150342` rep2/rep3 due bad F match | `target F = 3.75 N`, preload extra `+0.40 mm`, preload hold `5 s`, 3 accepted pairs; proceed to 030 |
| 实验 3.4B-030 same-F preload holding-time 路径剂量实验 | `python .\apmd_same_f_path_hold_time.py 030` | planned: `plot_apmd_same_f_path_hold_time.py` | formal: `session_20260614_171435`; summary=`same_f_path_hold_time_B_hold030_pair_summary.csv`; figure=`same_f_path_hold_time_B.png`; note=3/3 strong, same-F=3/3, displacement-split=3/3, b-signal=3/3; backup=`session_20260614_161258` rep1 strong; excluded=`session_20260614_154015` due bad F match | `target F = 3.75 N`, preload extra `+0.40 mm`, preload hold `30 s`, 3 accepted pairs; proceed to 090 |
| 实验 3.4B-090 same-F preload holding-time 路径剂量实验 | `python .\apmd_same_f_path_hold_time.py 090` | planned: `plot_apmd_same_f_path_hold_time.py` | formal composite accepted: `session_20260614_175601` rep1 + `session_20260614_183107` rep1 + `session_20260614_193530` rep1; summaries=`same_f_path_hold_time_B_hold090_pair_summary.csv`; note=3/3 strong, same-F=3/3, displacement-split=3/3, b-signal=3/3; excluded=`session_20260614_175601` rep2/rep3, `session_20260614_183107` rep2/rep3, and `session_20260614_190624` due gate failure | `target F = 3.75 N`, preload extra `+0.40 mm`, preload hold `90 s`, 3 accepted pairs; 3.4B complete |
| 实验 3.4B 总结 same-F preload holding-time 路径剂量实验 | `python .\apmd_same_f_path_hold_time.py 005/030/090` | `plot_apmd_same_f_path_hold_time.py` | formal complete through preload hold `5/30/90 s`; figure=`reports/experiment_3_4B_same_f_path_hold_time_complete.png`; summary=`reports/experiment_3_4B_same_f_path_hold_time_summary.csv`; replicate table=`reports/experiment_3_4B_same_f_path_hold_time_replicates.csv`; note=strong=9/9, same-F=9/9, displacement-split=9/9; hold-time effect is non-monotonic/limited, with 5 s strongest, 30 s weakest, 90 s intermediate | 3.4B 判定完成，后续进入 3.5 |
| 实验 3.5A same-d 恢复时间与路径记忆衰减实验 | `python .\apmd_recovery_time_path_memory.py A` | `plot_apmd_recovery_time_path_memory.py` | formal: `session_20260614_201905`; summary=`recovery_time_path_memory_3p5A_pair_summary.csv`; session figure=`recovery_time_path_memory_3p5A.png`; report figure=`reports/experiment_3_5A_recovery_time_path_memory_complete.png`; report summary=`reports/experiment_3_5A_recovery_time_path_memory_summary.csv`; replicate table=`reports/experiment_3_5A_recovery_time_path_memory_replicates.csv`; note=3.5A complete; strong=9/9; same-d=9/9; recovery time causes mild path-memory decay but does not remove active path-pair separation | `target d = 3.40 mm`, preload `3.80 mm`, preload hold `30 s`, recovery-before-pair `30/120/300 s`, 3 measured pairs/recovery plus 1 conditioning pair |

#### 阶段 4-7 脚本与 session 记录

| 阶段/实验 | 采集脚本 | 作图/分析脚本 | session 记录 | 备注 |
|---|---|---|---|---|
| 阶段 4 局部可辨识性候选区映射 | uses formal accepted Stage 3 path-pair report tables | `apmd_stage4_identifiability.py` | formal analysis complete: figure=`reports/apmd_stage4_identifiability_complete.png`; report=`reports/APMD_STAGE4_IDENTIFIABILITY_ANALYSIS.md`; summary=`reports/apmd_stage4_identifiability_summary.csv`; pair table=`reports/apmd_stage4_identifiability_pair_table.csv`; `j_F` table=`reports/apmd_stage4_jF_from_same_d_pairs.csv`; `j_d` table=`reports/apmd_stage4_jd_from_same_f_pairs.csv` | strict primary sensitivity-pair candidate: same-d `d=3.40 mm` paired with same-F `F=4.90 N`, angle=`48.5 deg`, scaled condition=`2.22`, min B/noise=`22.8`; best-score practical candidate: `d=3.20 mm` / `F=4.90 N`, angle=`41.9 deg`; this is a local mechanism-validation zone, not a prosthetic-socket full-range claim |
| 阶段 5.0 建模数据集整理 | no hardware acquisition; reads accepted formal Stage 3 raw rep CSVs plus Stage 5.1B dense-loop state summaries | `apmd_stage5_build_model_dataset.py` | complete: state dataset=`reports/apmd_stage5_model_dataset_states.csv`; pair dataset=`reports/apmd_stage5_model_dataset_pairs.csv`; summary=`reports/APMD_STAGE5_MODEL_DATASET_SUMMARY.md` | accepted path pairs=`87`; state summaries=`561`; unique sessions=`33`; includes 5.1B dense-loop states=`300` from four sessions; no raw-file matching warnings |
| 阶段 5.2 局部 baseline 解耦模型 | uses `reports/apmd_stage5_model_dataset_states.csv` | `apmd_stage5_fit_local_models.py` | complete: metrics=`reports/apmd_stage5_local_model_metrics.csv`; predictions=`reports/apmd_stage5_local_model_predictions.csv`; figure=`reports/apmd_stage5_local_model_baseline_comparison.png`; report=`reports/APMD_STAGE5_LOCAL_MODEL_BASELINE.md` | grouped CV by session; after four 5.1B dense-loop sessions, best F model=`magnetic_path_memory_random_forest`, F MAE=`0.590 N`; best balanced model=`magnetic_path_memory_ridge`, F MAE=`0.720 N`, d MAE=`0.107 mm`; path-memory ridge improves F vs plain magnetic ridge |
| 阶段 5.3 dense-loop 跨 session 验证 | no hardware acquisition; train/test between `session_20260615_112044` and `session_20260615_143640` | `apmd_stage5_dense_loop_cross_session_validation.py` | complete: metrics=`reports/apmd_stage5_dense_loop_cross_session_metrics.csv`; predictions=`reports/apmd_stage5_dense_loop_cross_session_predictions.csv`; figure=`reports/apmd_stage5_dense_loop_cross_session_validation.png`; report=`reports/APMD_STAGE5_DENSE_LOOP_CROSS_SESSION_VALIDATION.md` | leave-one-dense-loop-session-out validation; best F model=`dense_path_memory_random_forest`, F MAE=`0.323 N`, d MAE=`0.039 mm`; best d model=`dense_path_memory_ridge`, F MAE=`0.413 N`, d MAE=`0.023 mm`; path-memory ridge reduces F MAE by `58.3%` and d MAE by `33.3%` vs plain magnetic ridge |
| 实验 5.1A 建模数据采集：pairwise same-d 局部补充 | planned: `apmd_local_pairwise_same_d_dataset.py` | planned: `plot_apmd_stage5_model_dataset.py` | optional / not yet required | 可选补充；若 5.1B 后模型仍缺少局部点对，可在 selected d 附近做 `d -> d+0.4 -> d` |
| 实验 5.1B 建模数据采集：local minor-loop dense sampling | `python .\apmd_local_minor_loop_dense_sampling.py` | planned: `plot_apmd_stage5_model_dataset.py` | formal: `session_20260615_112044`; summary=`local_minor_loop_dense_5p1B_state_summary.csv`; figure=`local_minor_loop_dense_5p1B.png`; note=cycles=5; states=75/75; d_grid=[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6]; preload=3.80 mm; included in Stage 5/6 rebuilt outputs<br>formal: `session_20260615_143640`; summary=`local_minor_loop_dense_5p1B_state_summary.csv`; figure=`local_minor_loop_dense_5p1B.png`; note=cycles=5; states=75/75; d_grid=[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6]; preload=3.80 mm; included in Stage 5/6 rebuilt outputs<br>formal: `session_20260618_092135`; summary=`local_minor_loop_dense_5p1B_state_summary.csv`; figure=`local_minor_loop_dense_5p1B.png`; note=cycles=5; states=75/75; d_grid=[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6]; preload=3.80 mm; included in Stage 5/6 rebuilt outputs<br>formal: `session_20260618_135532`; summary=`local_minor_loop_dense_5p1B_state_summary.csv`; figure=`local_minor_loop_dense_5p1B.png`; note=cycles=5; states=75/75; d_grid=[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6]; preload=3.80 mm; included in Stage 5/6 rebuilt outputs | completed four dense-loop model-data sessions; total accepted states=300; common preload `3.8 mm`, loading/preload/unloading dense loop, `cycles=5` per session |
| 实验 5.1B-L 建模数据采集：Block L local minor-loop dense sampling | `python .\apmd_local_minor_loop_dense_sampling.py L` | planned: `plot_apmd_stage5_model_dataset.py` | formal accepted cycles only: `session_20260622_112307` cycles 1-5, states=75/75; `session_20260622_132503` cycles 1-5, states=75/75; `session_20260622_143801` cycles 1-3, states=45/45; `session_20260622_151834` cycles 1-3, states=45/45; `session_20260622_162129` cycles 1-4, states=60/60; total accepted cycles=20, total accepted states=300 | Block L lower work zone: d_grid=[2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0], preload=`3.20 mm`; incomplete/failed cycles are excluded from formal training data; accepted-cycle QC: same-d-like pairs=140/140, force-split pairs=140/140, magnetic-split pairs=140/140, median abs(Delta F)=1.543 N, median Delta Bvec=162.2 uT |
| 验证 6.1 local held-out dense-loop 验证 | `python .\apmd_stage6_local_heldout_dense_loop.py` | `apmd_stage6_predict_local_heldout.py` for next model-level test | formal accepted: `session_20260615_160438`; summary=`local_heldout_dense_loop_6p1_state_summary.csv`; figure=`local_heldout_dense_loop_6p1.png`; QC table=`reports/apmd_stage6_heldout_qc_by_d.csv`; note=cycles=3; states=39/39; held-out d grid=[3.05, 3.15, 3.25, 3.35, 3.45, 3.55]; preload=3.80 mm; same-d-like pairs=18/18; force-split pairs=18/18; magnetic-split pairs=18/18; median abs(Delta F)=2.543 N; median Delta Bvec=265.8 uT<br>formal accepted: `session_20260618_161152`; summary=`local_heldout_dense_loop_6p1_state_summary.csv`; figure=not generated yet; note=cycles=3; states=39/39; held-out d grid=[3.05, 3.15, 3.25, 3.35, 3.45, 3.55]; preload=3.80 mm; same-d-like pairs=18/18; force-split pairs=18/18; magnetic-split pairs=18/18; median abs(Delta F)=2.710 N; median Delta Bvec=206.5 uT | accepted as test-only held-out data; do not add these sessions to training before Stage 6.2 |
| 验证 6.1-L Block L local held-out dense-loop 验证 | `python .\apmd_stage6_local_heldout_dense_loop.py L` | planned: rebuild Block L model-level validation after local sensitivity calibration | formal primary strong cycles: `session_20260622_173504` cycles 1-3, states=39/39; `session_20260622_180702` cycle 1, states=13/13; `session_20260622_185538` cycles 1-2, states=26/26; total primary cycles=6, states=78/78 | Block L test-only held-out d_grid=[2.45, 2.55, 2.65, 2.75, 2.85, 2.95], preload=`3.20 mm`; primary strong QC: same-d-like pairs=36/36, force-split pairs=36/36, magnetic-split pairs=36/36; complete-but-not-primary cycles=`session_20260622_180702` cycle 2 and `session_20260622_185538` cycle 3 due one weak d=2.95 mm pair below 50 uT; excluded incomplete=`session_20260622_180702` cycle 3 |
| 验证 6.2 模型层 held-out 验证 | no new acquisition; use Stage 6.1 held-out sessions as test-only data | `python .\apmd_stage6_predict_local_heldout.py` | complete / partial pass: metrics=`reports/apmd_stage6_heldout_model_metrics.csv`; predictions=`reports/apmd_stage6_heldout_model_predictions.csv`; figure=`reports/apmd_stage6_heldout_model_validation.png`; report=`reports/APMD_STAGE6_HELDOUT_MODEL_VALIDATION.md` | train=`561` Stage 5 states; test=`78` states from `session_20260615_160438` and `session_20260618_161152`; best F model=`magnetic_path_memory_ridge`, F MAE=`0.796 N`; best d/balanced model=`magnetic_path_label_ridge`, F MAE=`0.839 N`, d MAE=`0.035 mm`; branch-label passes d target but force still requires local-ID geometry |
| 验证 6.3 APMD local-identifiability 模型对照 | no new acquisition; reused Stage 3 path-pair sensitivity and Stage 5/6 dense-loop states | `apmd_stage6_compare_local_identifiability_models.py` | complete / force pass with near d-gate: metrics=`reports/apmd_stage6_local_identifiability_model_metrics.csv`; predictions=`reports/apmd_stage6_local_identifiability_predictions.csv`; figure=`reports/apmd_stage6_local_identifiability_comparison.png`; report=`reports/APMD_STAGE6_LOCAL_IDENTIFIABILITY_MODEL.md` | train=`561` Stage 5 states, test=`78` held-out states; best local-ID ridge F MAE=`0.054 N`, d MAE=`0.056 mm`; Lim-style branch-label baseline F MAE=`0.839 N`, d MAE=`0.035 mm`; local-ID ridge improves F MAE vs Lim-style by `93.5%`; d is slightly above the strict `0.050 mm` gate but still close |
| 实验 6.4A high-force same-F 局部灵敏度补采 | `python .\apmd_high_force_same_f_local_sensitivity.py 800/1000/1200` 或一次性 `python .\apmd_high_force_same_f_local_sensitivity.py` | planned: rebuild Stage 4/6 local-ID features after accepted supplement | planned / next: target `8/10/12 N`, fixed preload `d=3.80 mm`, 3 usable pairs per F | purpose:补足 Stage 5/6 dense-loop 实际高力区的 `j_d` calibration；same-d 半点 `d=3.10/3.30/3.50 mm` 和 dense-loop shifted grid 先保留为后续可选，不在本轮执行 |
| 实验 6.4B-L Block L same-d 局部灵敏度补采 | `python .\apmd_same_d_different_f_scan.py L`; supplement `python .\apmd_same_d_different_f_scan.py L300` | planned: rebuild Block L `j_F` table after Block L same-F `j_d` calibration | formal complete: `session_20260622_203244` for `d=2.40/2.60/2.80 mm`, summary=`block_L_same_d_local_sensitivity_pair_summary.csv`; supplement formal: `session_20260623_091618` for `d=3.00 mm`, summary=`block_L_same_d_local_sensitivity_pair_summary.csv`; note=12/12 strong, same-d=12/12, force-split=12/12, B-signal=12/12 | purpose: 为 Block L lower work zone 单独估计 `j_F`，避免直接把 Block M 的 same-d force-sensitivity direction 外推到较浅工作区；next: Block L same-F `j_d` calibration |
| 实验 6.4C-L Block L same-F 局部灵敏度补采 | `python .\apmd_same_f_different_d_scan.py L300/L450/L600/L750/L900` | planned: rebuild Block L `j_d` table and Block L local-ID model after accepted supplement | planned / current next: target `3.00/4.50/6.00/7.50/9.00 N`, fixed preload `d=3.20 mm`, 3 usable pairs per F | purpose: 为 Block L lower work zone 单独估计 `j_d`，避免直接把 Block M 或 Stage 3.2 的 same-F displacement-sensitivity direction 外推到较浅工作区 |
| 实验 7.1 无接触运动伪差对照 | `python .\apmd_no_contact_motion_artifact.py` | auto-generated session-local `no_contact_motion_artifact.png` | formal: `session_20260616_152850`; summary=`no_contact_motion_artifact_pair_summary.csv`; figure=`no_contact_motion_artifact.png`; note=no-contact replay passed 3/3; B0 drift 3.4 uT | replay selected same-d active path without contact: nominal `3.40 -> 3.80 -> 3.40 mm`, 3 trials, pass gate `ΔBvec <= 10 uT` and `B0 drift <= 10 uT` |
| 实验 7.2 重复 loading branch 对照 | `python .\apmd_repeated_loading_control.py` | auto-generated session-local `repeated_loading_control.png` | formal: `session_20260616_170608`; summary=`repeated_loading_control_summary.csv`; figure=`repeated_loading_control.png`; note=repeated-loading control passed 5/5; max cycle-to-cycle ΔBvec 34.1 uT | target `d=3.40 mm`, no deeper preload, `5` loading cycles, pass gate cycle-to-cycle `ΔBvec <= 50 uT`; 用于证明 deeper preload path 是必要激励 |
| 实验 7.3 cross-day repeatability | same as selected best path-pair scripts | same as selected best path-pair plots | TBD | day 1/day 2 都需 3 pairs |
| 实验 7.4 材料/界面状态对照 | planned after primary model | planned after primary model | TBD | 非第一轮必需 |

**当前下一条正式记录应添加的位置**

```text
experiment = Stage 3 work-zone scan
completed through = 3.2 near-matched-force / different-displacement coarse scan
completed through = 3.3A same-d path-dose preload-depth scan
completed through = 3.3B same-d path-dose hold-time scan
completed through = 3.4A same-F preload-extra-depth dose response
3.4A analysis script = plot_apmd_same_f_path_dosage.py
3.4A figure = reports/experiment_3_4A_same_f_path_dosage_complete.png
3.4A summary table = reports/experiment_3_4A_same_f_path_dosage_summary.csv
3.4A replicate table = reports/experiment_3_4A_same_f_path_dosage_replicates.csv
020 status = accepted as shallow/boundary dose: 2 strict strong + 1 boundary accepted weak_disp_split
030 status = accepted: boundary-corrected strong=3/3, with 2 rows at Delta d = 0.1000 mm
040 status = accepted: 3 strict strong from session_20260613_192031 rep1/rep2 + session_20260613_194759 rep1
last completed analysis = Stage 4 local identifiability mapping from formal APMD path-pair data
3.5A acquisition script = python .\apmd_recovery_time_path_memory.py A
3.5A analysis script = plot_apmd_recovery_time_path_memory.py
3.5A figure = reports/experiment_3_5A_recovery_time_path_memory_complete.png
3.5A summary table = reports/experiment_3_5A_recovery_time_path_memory_summary.csv
3.5A replicate table = reports/experiment_3_5A_recovery_time_path_memory_replicates.csv
completed 3.5A = formal accepted: session_20260614_201905; recovery 30/120/300 s; 3 measured pairs per recovery
Stage 4 analysis script = python .\apmd_stage4_identifiability.py
Stage 4 figure = reports/apmd_stage4_identifiability_complete.png
Stage 4 report = reports/APMD_STAGE4_IDENTIFIABILITY_ANALYSIS.md
Stage 4 strict primary = same-d d=3.40 mm + same-F F=4.90 N; angle=48.5 deg; scaled condition=2.22; min B/noise=22.8
Stage 4 practical high-score = same-d d=3.20 mm + same-F F=4.90 N; angle=41.9 deg; score=0.660
Stage 5.0 dataset builder = python .\apmd_stage5_build_model_dataset.py
Stage 5.0 state dataset = reports/apmd_stage5_model_dataset_states.csv; rows=561
Stage 5.0 pair dataset = reports/apmd_stage5_model_dataset_pairs.csv; rows=87
Stage 5.0 summary = reports/APMD_STAGE5_MODEL_DATASET_SUMMARY.md
Stage 5.2 model script = python .\apmd_stage5_fit_local_models.py
Stage 5.2 metrics = reports/apmd_stage5_local_model_metrics.csv
Stage 5.2 predictions = reports/apmd_stage5_local_model_predictions.csv
Stage 5.2 figure = reports/apmd_stage5_local_model_baseline_comparison.png
Stage 5.2 report = reports/APMD_STAGE5_LOCAL_MODEL_BASELINE.md
Stage 5.2 key result after four 5.1B sessions = best F model magnetic_path_memory_random_forest, F MAE=0.590 N; best balanced model magnetic_path_memory_ridge, F MAE=0.720 N, d MAE=0.107 mm; path-memory ridge strongly improves F vs plain magnetic ridge
Stage 5.3 cross-session validation script = python .\apmd_stage5_dense_loop_cross_session_validation.py
Stage 5.3 metrics = reports/apmd_stage5_dense_loop_cross_session_metrics.csv
Stage 5.3 predictions = reports/apmd_stage5_dense_loop_cross_session_predictions.csv
Stage 5.3 figure = reports/apmd_stage5_dense_loop_cross_session_validation.png
Stage 5.3 report = reports/APMD_STAGE5_DENSE_LOOP_CROSS_SESSION_VALIDATION.md
Stage 5.3 key result = leave-one-dense-session-out validation across four dense-loop sessions; best overall model dense_path_memory_ridge F MAE=0.369 N, d MAE=0.017 mm; path-memory ridge improves both F and d vs plain magnetic ridge
completed Stage 6.1 = formal accepted: session_20260615_160438 and session_20260618_161152; each has 39/39 state summaries; combined held-out rows=78; same-d-like/force-split/magnetic-split pairs pass in both sessions; median |Delta F|=2.543 N and 2.710 N; median Delta Bvec=265.8 uT and 206.5 uT
Stage 6.1 figures = decouple_data/session_20260615_160438/local_heldout_dense_loop_6p1.png; decouple_data/session_20260618_161152/local_heldout_dense_loop_6p1.png if generated later
Stage 6.1 QC table = reports/apmd_stage6_heldout_qc_by_d.csv
previous recommendation = Stage 6.2 model-level held-out prediction on accepted Stage 6.1 sessions, now completed
Stage 6.2 planned script = python .\apmd_stage6_predict_local_heldout.py
completed Stage 6.2 = model-level held-out validation complete / partial pass
Stage 6.2 script = python .\apmd_stage6_predict_local_heldout.py
Stage 6.2 metrics = reports/apmd_stage6_heldout_model_metrics.csv
Stage 6.2 predictions = reports/apmd_stage6_heldout_model_predictions.csv
Stage 6.2 figure = reports/apmd_stage6_heldout_model_validation.png
Stage 6.2 report = reports/APMD_STAGE6_HELDOUT_MODEL_VALIDATION.md
Stage 6.2 key result = train 561 Stage 5 states, test 78 held-out states from two accepted held-out sessions; best F model magnetic_path_memory_ridge F MAE=0.796 N; best d/balanced model magnetic_path_label_ridge d MAE=0.035 mm, F MAE=0.839 N; d target passes, F target still needs local-ID geometry
recommended next experiment/analysis = Stage 6.3 existing-data APMD local-identifiability model comparison before any new acquisition
Stage 6.3 purpose = directly connect Stage 4 local sensitivity / branch geometry to Stage 5/6 model validation
Stage 6.3 model comparison = plain magnetic vs Lim-style branch-label compensation vs APMD path-memory vs APMD local-identifiability
Stage 6.3 key feature = project magnetic state changes onto local j_F/j_d directions derived from active path-pair experiments
completed Stage 6.3 = complete / force pass with near d-gate; best local-ID ridge F_MAE=0.054 N, d_MAE=0.056 mm; Lim-style branch-label baseline F_MAE=0.839 N, d_MAE=0.035 mm; local-ID ridge improves F_MAE vs Lim-style by 93.5%; d is slightly above the strict 0.050 mm gate
completed Stage 6.4B-L = formal accepted: session_20260622_203244 for d=2.40/2.60/2.80 mm and session_20260623_091618 for d=3.00 mm; total 12/12 strong same-d pairs, fixed preload d=3.20 mm
current next acquisition = Block L same-F local sensitivity supplement for j_d calibration
Block L same-F design pending = target force points should cover Block L dense-loop force range, fixed preload d=3.20 mm, 3 usable pairs per force
completed Stage 7.1 = formal accepted: session_20260616_152850; no-contact replay passed 3/3; B0 drift=3.4 uT
completed Stage 7.2 = formal accepted: session_20260616_170608; repeated-loading control passed 5/5; max cycle-to-cycle Delta Bvec=34.1 uT
recommended next experiment/analysis = Stage 7.3 cross-day repeatability or proceed to final mechanism/model summary if cross-day repeat is not required for the current report
Stage 6.4 principle = after Block L dense-loop training and held-out acquisition, first supplement Block L local same-d j_F calibration, then supplement Block L same-F j_d calibration, then rebuild Stage 4/6 local-ID features
Experiment 5.1B command = python .\apmd_local_minor_loop_dense_sampling.py
Experiment 5.1B design = d grid 3.0/3.1/3.2/3.3/3.4/3.5/3.6 mm, common preload 3.8 mm, loading/preload/unloading loop, 15 s loading/unloading states, 5 cycles, 75 planned state summaries per session; four formal sessions completed and included in current Stage 5/6 rebuilt outputs
design note = current modeling scope is local proof-of-mechanism, not prosthetic-socket full-range deployment; one initial conditioning pair is recorded but excluded from formal summary; recovery-time effect is mild and does not remove same-d path-pair separation
registry = automatic only after successful usable acquisition; diagnostic/reference sessions may be documented manually with note
```

---

## 阶段 1：系统准备与误差隔离

### 目标

在正式讨论路径激励前，先证明数据不是由力传感器漂移、磁场漂移、接触点漂移、压头几何不稳定、串口异常或运动伪差造成的。

### 实验 1.1：力传感器标定与稳定性检查

**目的**  
保证所有 `F_N` 标签可信。若力标签不可信，后续 same-d/different-F 和 same-F/different-d 结果都无法解释。

**正式设置**

```text
warm-up time = 15 min
calibration masses = 0, 44.2, 100.0, 168.9, 211.0, 229.7, 359.6 g
samples per mass = 60
post-upload no-load stability check = 60 s
force noise gate = sample std <= 5 mN
known-load back-check error gate = max(0.03 N, 2% of load)
```

**具体流程**

1. 固定力传感器、HX711、Arduino、压头和线缆连接。
2. 电子系统预热 15 min。
3. 空载 tare，记录 raw offset。
4. 依次放置已知砝码，每个质量点采样 60 个读数。
5. 拟合 raw-to-N 标定系数，保存 CSV 和标定图。
6. 将 `TARE_OFFSET` 和 `CALIBRATION_FACTOR` 写入 Arduino 并重新上传。
7. 重新安装压头后运行 `force_serial.py` 60 s。
8. 确认空载 tared force 接近 0，sample std 不超过 5 mN，轻触样品时力为正。

**输出**

```text
force_calibration_id
force_calibration_<date>.csv
force_calibration_<date>.png
Arduino calibration constants
force_serial stability log
```

### 实验 1.2：接触零点与位移重复性检查

**目的**  
定义当天 `d=0`，并确认 Mark-10 位移方向与脚本记录一致。

**正式设置**

```text
start position = 6 mm above the physical lower limit, with a clear visible gap above sample
contact search step = 0.10 mm
contact repeat trials = 5
contact repeatability gate = max-min contact position <= 0.020 mm
contact criterion = force-change point, not absolute force threshold
```

**具体流程**

1. 将 Mark-10 起点设为距离物理下限位上方 6 mm 的 no-contact 位置，此时压头和样品之间应有明显 air gap。
2. 做一次 0.5 mm 位移方向检查：压下时 `d_actual_mm` 增加。
3. 从起点开始小步下压，用 force change point 判断接触点。
4. 将接触点定义为 `d=0`。
5. 回到起点，重复轻触 5 次。
6. 若 5 次接触位置范围超过 0.020 mm，检查样品滑移、压头倾斜和夹具松动。

**输出**

```text
displacement_zero_id
contact_repeatability_log.csv
contact position max-min
```

### 实验 1.3：无接触磁基线与运动伪差检查

**目的**  
排除环境磁场、Mark-10 运动、电机、线缆移动或串口异常导致的磁信号伪差。

**正式设置**

```text
B0_start record = 60 s
no-contact motion path = start -> equivalent d=2.00 mm position -> hold 10 s -> start
B0_end record = 60 s
motion artifact gate = ΔBvec <= 10 uT
B0 drift gate = ΔBvec <= 10 uT
```

**具体流程**

1. 在无接触状态记录 `B0_start` 60 s。
2. 不接触样品，执行与正式实验等效的 Mark-10 位移轨迹。
3. 全程记录 `Bx, By, Bz, |B|`。
4. 实验结束后再次记录 `B0_end` 60 s。

**输出**

```text
B0_start.csv
no_contact_motion_control.csv
B0_end.csv
B0_drift_summary
```

---

## 阶段 2：被动基线与主动路径对可行性验证

### 目标

证明被动松弛/蠕变本身不足以产生强磁可辨识信号，而主动路径对可以显著放大磁信号差异。这一阶段是项目方向可行性的核心证据。

### 实验 2.1：固定位移被动松弛实验

**目的**  
观察固定 `d` 时，材料力松弛是否能带来可用磁信号变化。

**正式设置**

```text
target d = 2.80 mm
hold time = 120 s
trials = 3 usable trials
summary window = first 10 s median vs last 10 s median
effective sampling-rate gate = >= 10 Hz
pre-record settle = 5 s
rest between trials = 60 s
script force hard limit = OFF
```

**具体流程**

1. 记录 no-contact `B0`。
2. 从 no-contact 起点搜索接触点，并定义 `d=0`。
3. 压入到 `d=2.80 mm`。
4. 到达目标位移后等待 5 s。
5. 保持位移 120 s，同时记录 `F,d,B`。
6. 回撤到 no-contact 起点。
7. 休息 60 s。
8. 重复直到获得 3 个可用 trials。

**关键输出**

```text
ΔF = F_last10s_median - F_first10s_median
Δ|B| = |B|_last10s_median - |B|_first10s_median
ΔBvec = norm(B_last10s_median - B_first10s_median)
```

**解释标准**

若 `|ΔF| >= 0.080 N` 但 `ΔBvec < 10 uT`，说明被动松弛虽能改变力，但不能提供强磁可辨识激励。

### 实验 2.2：近似同位移/异力主动路径对实验

**目的**  
主动构造近似相同 `d` 但不同 `F` 的路径状态，检验磁信号是否能区分力状态。

**正式设置**

```text
target d = 2.80 mm
preload d = 3.10 mm
direct target record = 45 s
preload record = 30 s
return target record = 45 s
trials = 3 usable pairs
rest between trials = 120 s
state summary window = last 10 s median
same-d command target = d_return command equals d_direct command
same-d acceptance gate = |d_return - d_direct| <= 0.020 mm
force split target = |ΔF| >= 0.20 N
magnetic signal gate = ΔBvec >= 50 uT
script force hard limit = OFF
```

**具体流程**

1. 记录 no-contact `B0`。
2. 搜索接触点并定义 `d=0`。
3. 压入到 `d_target=2.80 mm`，形成 direct-loading target state。
4. 在 direct-loading target state 记录 45 s。
5. 继续压入到 `d_preload=3.10 mm`，形成 deeper preload state。
6. 在 preload state 记录 30 s。
7. 卸载回同一个 `d_target=2.80 mm` 命令位置，形成 return-unloading target state。
8. 在 return-unloading target state 记录 45 s。
9. 回撤到 no-contact 起点。
10. 休息 120 s。
11. 重复直到获得 3 个通过 same-d gate 的 pairs。

**关键输出**

```text
d_direct, d_return, Δd
F_direct, F_return, ΔF
ΔBx, ΔBy, ΔBz
Δ|B|, ΔBvec
ΔBvec / |ΔF|
```

**通过标准**

- 3/3 pairs 必须满足 `|d_return - d_direct| <= 0.020 mm`。
- 3/3 pairs 应满足 `|ΔF| >= 0.20 N`。
- 3/3 pairs 应满足 `ΔBvec >= 50 uT`。
- 若某个 pair 的 `|Δd| > 0.020 mm`，该 repeat 不作为正式主证据，需要补跑。

### 实验 2.3：固定力被动蠕变实验

**目的**  
观察在近似固定 `F` 时，控制器补偿材料蠕变导致的位移变化是否能产生强磁信号变化。

**当前 smoke test 设置**  
由于 `target F = 4.50 N` 在 `session_20260609_140100` 中出现明显 force-control oscillation，且 `target F = 4.40 N` 在 `session_20260609_143621` 中压到 `D_SOFT_LIMIT` 附近后中止，本轮继续用旧 Stage J 控制逻辑测试 `target F = 4.30 N`、`trials = 1`，并关闭 `D_SOFT_LIMIT`。若该点能稳定保持，再决定是否将正式 2.3 目标力改为 `4.30 N` 并恢复 `trials = 3`。

**正式设置**

```text
target F = 4.30 N
hold time = 180 s
trials = 1 smoke trial
force acquisition gate = |F_median - 4.30 N| <= 0.050 N
force hold std gate = F_std <= 0.020 N
acquisition max iterations = 100
acquisition step schedule = 0.04 / 0.10 / 0.14 / 0.18 mm by force error
hold correction interval = 3 s
hold correction step schedule = 0.03 / 0.05 / 0.08 mm by force error, capped at 0.08 mm
force evaluation = recent median force samples
correction trigger = |F_control - 4.30 N| > 0.050 N
Mark-10 correction tolerance = 0.020 mm
depth soft limit = OFF
force hard limit = OFF
summary window = first 10 s median vs last 10 s median
rest between trials = 120 s
```

**具体流程**

1. 记录 no-contact `B0`。
2. 搜索接触点并定义 `d=0`。
3. 用位移控制逐步压入，直到 `F_median` 进入 `4.30 ± 0.050 N`。
4. 等待 5 s 后重新评估 `F_median`。
5. 若 `F_median` 不在 `4.30 ± 0.050 N` 内，按旧 Stage J force error 步长表使用 `0.18/0.14/0.10/0.04 mm` 获取目标力。
6. 关闭 `D_SOFT_LIMIT`，不再用软件深度上限截断下压路径；仍依赖物理下限位保护最大压入。
7. 开始 180 s 近似固定力保持。
8. 保持期间每 3 s 评估一次近期中位力；若 `|F_control - 4.30 N| > 0.050 N`，按旧 Stage J hold 步长表使用 `0.03/0.05/0.08 mm` 位移小步修正，并记录 correction。
9. 控制移动到位容差使用旧 Stage J 设置 `0.020 mm`。
10. 本轮为旧逻辑回退测试，不启用额外 hold no-motion abort 逻辑。
11. 全程记录 `F,d,B`。
12. 回撤到 no-contact 起点。
13. 休息 120 s。
14. 重复直到获得 3 个可用 trials。

**关键输出**

```text
F_mean, F_std
number of corrections
Δd = d_last10s_median - d_first10s_median
Δ|B|, ΔBvec
ΔBvec / |Δd|
```

**解释标准**

若 `Δd` 较大但 `ΔBvec` 很小，说明被动固定力蠕变主要是宏观位移补偿，不一定形成局部磁可辨识状态。

### 实验 2.4：近似同力/异位移主动路径对实验

**目的**  
主动构造近似相同 `F` 但不同 `d` 的路径状态，检验磁信号是否能区分位移状态。

**正式设置**

```text
target F = 1.80 N
preload extra depth = +0.30 mm
loading target record = 45 s
preload record = 30 s
unloading target record = 45 s
trials = 3 usable pairs
rest between trials = 120 s
state summary window = last 10 s median
loading target acquisition gate = |F_loading - 1.80 N| <= 0.050 N
unloading target acquisition gate = |F_unloading - 1.80 N| <= 0.050 N
same-F pair gate = |F_unloading - F_loading| <= 0.050 N
force matching logic = original bracket-and-pick logic
force matching step = adaptive displacement command, minimum 0.020 mm
bracket handling = if adjacent positions straddle target F, use the closer force point
force evaluation window = 2 s median
displacement split target = |Δd| >= 0.10 mm
magnetic signal gate = ΔBvec >= 100 uT
```

**具体流程**

1. 记录 no-contact `B0`。
2. 搜索接触点并定义 `d=0`。
3. 沿 loading path 小步压入，直到 `F_median` 进入 `1.80 ± 0.050 N`。
4. 在 loading target state 记录 45 s。
5. 从当前位移继续压入 `+0.30 mm`，形成 preload state。
6. 在 preload state 记录 30 s。
7. 沿 unloading path 回撤，直到 `F_median` 进入 `1.80 ± 0.050 N`；若相邻位移点跨过目标力，则沿用旧实验逻辑，选择两点中力误差更小的状态作为 candidate unloading target。
8. 在 unloading target state 记录 45 s。
9. 回撤到 no-contact 起点。
10. 休息 120 s。
11. 重复直到获得 3 个通过 same-F gate 的 pairs；若 candidate unloading target 未通过 `|F_unloading - F_loading| <= 0.050 N`，该 repeat 不作为正式主证据，需要补跑。

**关键输出**

```text
F_loading, F_unloading, ΔF
d_loading, d_unloading, Δd
ΔBx, ΔBy, ΔBz
Δ|B|, ΔBvec
ΔBvec / |Δd|
```

**通过标准**

- 3/3 pairs 必须满足 `|F_unloading - F_loading| <= 0.050 N`。
- 3/3 pairs 应满足 `|Δd| >= 0.10 mm`。
- 3/3 pairs 应满足 `ΔBvec >= 100 uT`。
- 若某个 pair 的 `|ΔF| > 0.050 N`，该 repeat 不作为正式主证据，需要补跑。

---

## 阶段 3：路径剂量表征与工作区初筛

### 目标

阶段 2 证明主动路径对可行；阶段 3 进一步回答路径激励是否可控、在哪些目标位移/目标力附近最有效，以及 preload 深度、preload 保持时间、恢复时间是否系统影响结果。

### 实验 3.1：近似同位移/异力路径对粗扫描

**目的**  
扫描不同目标位移下，主动路径是否都能产生可重复的异力磁响应。

**正式矩阵**

| Block | Target d | Default preload d | Trials |
|---:|---:|---:|---:|
| 3.1A | 2.40 mm | 2.70 mm | 3 |
| 3.1A | 2.60 mm | 2.90 mm | 3 |
| 3.1A | 2.80 mm | 3.10 mm | 3 |
| 3.1B | 3.00 mm | 3.30 mm | 3 |
| 3.1B | 3.20 mm | 3.50 mm | 3 |
| 3.1B | 3.40 mm | 3.70 mm | 3 |
| 3.1B | 3.60 mm | 3.90 mm | 3 |

为降低单次长实验中断风险，实验 3.1 不再一次性运行全部 7 个目标位移，而是拆成两个独立 session：

```text
3.1A command = python .\apmd_same_d_different_f_scan.py A
3.1B command = python .\apmd_same_d_different_f_scan.py B
```

**固定设置**

```text
direct target record = 45 s
preload record = 30 s
return target record = 45 s
state summary window = last 10 s median
rest between trials = 120 s
same-d gate = |d_return - d_direct| <= 0.020 mm
```

**每个矩阵点流程**

1. 记录 `B0`。
2. 搜索接触点并定义 `d=0`。
3. 压入到 target d，记录 direct-loading state 45 s。
4. 压入到 preload d，记录 preload state 30 s。
5. 卸载回同一 target d 命令位置，记录 return-unloading state 45 s。
6. 回撤并休息 120 s。
7. 重复 3 次。

**输出**

```text
median |Δd|
median |ΔF|
median ΔBvec
median ΔBvec / |ΔF|
same-d pass rate
axis contribution: ΔBx, ΔBy, ΔBz
```

### 实验 3.2：近似同力/异位移路径对粗扫描

**目的**  
扫描不同目标力下，主动路径是否都能产生可重复的异位移磁响应。

**正式矩阵**

为降低单次运行失败风险，实验 3.2 正式执行时采用 **single-target session**：每个 `target F` 单独运行一个 session，成功则记录该力点，失败或中断只重测该力点。脚本仍保留 `A/B/C` 批量模式作为备用，但正式推荐使用单点命令。

| Single-target command | Target F | Default preload extra | Trials |
|---|---:|---:|---:|
| `python .\apmd_same_f_different_d_scan.py 150` | 1.50 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 180` | 1.80 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 250` | 2.50 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 320` | 3.20 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 375` | 3.75 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 430` | 4.30 N | +0.30 mm | 3 |
| `python .\apmd_same_f_different_d_scan.py 490` | 4.90 N | +0.30 mm | 3 |

当前 3.2 正式矩阵判定完成，纳入 `1.50/1.80/2.50/3.20/3.75/4.30/4.90 N` 共 7 个力点。`5.50 N` 不作为本轮正式矩阵必需点；若后续需要扩展高力区，可作为单独 high-force extension，而不影响当前 3.2 结论。`2.80/3.00 N` 等诊断或临时尝试点不作为正式 3.2 矩阵点；相关失败 session 只保留在各自 `run_log.txt` 中，不写入正式 session 台账。

**固定设置**

```text
loading target record = 45 s
preload record = 30 s
unloading target record = 45 s
state summary window = last 10 s median
rest between trials = 120 s
force matching step = adaptive displacement command, minimum 0.020 mm
force matching logic = original bracket-and-pick logic
same-F pair gate = |F_unloading - F_loading| <= 0.050 N
preload displacement dose = loading d + 0.30 mm
preload force cap = OFF
D soft limit = OFF
F hard limit = OFF
```

这里 `preload force cap = OFF` 的含义是：实验 3.2 的核心路径剂量是额外位移 `+0.30 mm`，因此 preload 阶段不再用 `target F + constant` 或固定力上限提前截断。preload 过程中产生的力峰值作为结果记录，用于后续判断不同目标力工作区的材料非线性和路径记忆强度。

**每个矩阵点流程**

1. 记录 `B0`。
2. 搜索接触点并定义 `d=0`。
3. 沿 loading path 到达 target F，记录 loading state 45 s。
4. 继续压入 preload extra，记录 preload state 30 s。
5. 沿 unloading path 回到 target F 容差范围内，记录 unloading state 45 s。
6. 回撤并休息 120 s。
7. 重复 3 次。

**输出**

```text
median |ΔF|
median |Δd|
median ΔBvec
median ΔBvec / |Δd|
same-F pass rate
axis contribution: ΔBx, ΔBy, ΔBz
```

### 实验 3.3：same-d 路径剂量实验

**目的**  
专门回答 preload 深度和 preload 保持时间是否会影响 same-d/different-F 路径对结果。

**target d 的选择规则**

优先使用阶段 3.1 中满足以下条件的 target d：

```text
same-d pass rate = 3/3
median |ΔF| >= 0.20 N
median ΔBvec >= 50 uT
repeat direction of ΔB is consistent
```

若阶段 3.1 尚未完成，则使用当前已验证工作点：

```text
target d = 3.40 mm
```

**3.3A：preload depth scan**

```text
target d = selected target d, default 3.40 mm
preload d = target d + 0.20, +0.30, +0.40 mm
preload hold = 30 s
direct target record = 45 s
return target record = 45 s
trials = 3 per condition
rest between trials = 120 s
```

**3.3B：preload holding-time scan**

先从 3.3A 选择一个最佳 preload depth，再固定该深度，扫描保持时间：

```text
3.3A formal result = session_20260612_155336
selected preload d for 3.3B = 3.80 mm
selection reason = largest absolute |ΔF| and ΔBvec while same-d remains 9/9 valid
mean |ΔF| at preload d 3.80 mm = 1.519 N
mean ΔBvec at preload d 3.80 mm = 242.6 uT
```

```text
preload hold = 5 s, 30 s, 90 s
trials = 3 per condition
```

```text
3.3B formal result = session_20260612_180059
same-d pass = 9/9
strong pass = 9/9
mean |ΔF| at hold 5/30/90 s = 1.527 / 1.590 / 1.623 N
mean ΔBvec at hold 5/30/90 s = 251.1 / 236.9 / 241.1 uT
mean ΔBvec/|ΔF| at hold 5/30/90 s = 164 / 149 / 149 uT/N
interpretation = preload holding time is not the dominant dose variable once preload depth is fixed
recommended default same-d preload hold = 30 s for consistency with formal protocol
```

**输出**

```text
ΔF vs preload depth
ΔBvec vs preload depth
ΔF vs preload hold
ΔBvec vs preload hold
same-d pass rate
irreversible B0 drift after each condition
```

### 实验 3.4：same-F 路径剂量实验

**目的**  
补充阶段 3.3 中缺失的 force-matched 路径剂量研究，回答 preload 深度和 preload 保持时间是否会影响 same-F/different-d 路径对结果。

**target F 的选择规则**

优先使用阶段 3.2 中满足以下条件的 target F：

```text
same-F pass rate = 3/3
median |Δd| >= 0.10 mm
median ΔBvec >= 100 uT
repeat direction of ΔB is consistent
```

若阶段 3.2 尚未完成，则使用当前已验证工作点：

```text
target F = 1.80 N
```

当前正式 3.2 已完成，因此 3.4A 使用：

```text
selected target F for 3.4A = 3.75 N
selection basis = 3/3 same-F, 3/3 strong, large ΔBvec, and less boundary risk than the deepest 4.90 N point
```

**3.4A：preload extra-depth scan**

```text
target F = 3.75 N
preload extra depth = +0.20, +0.30, +0.40 mm
execution mode = split into three single-dose sessions: 020, 030, 040
preload hold = 30 s
loading target record = 45 s
unloading target record = 45 s
trials = 3 per condition
same-F pair gate = |F_unloading - F_loading| <= 0.050 N
displacement split gate = |Δd| >= 0.10 mm, with numerical boundary tolerance so displayed/recorded +0.1000 mm is accepted; +0.0900 mm is not accepted
rest between trials = 120 s
```

为降低 same-F 匹配失败时的沉没成本，3.4A 不再一次性运行全部 9 个 pairs。正式顺序为：

```text
3.4A-020 command = python .\apmd_same_f_path_dosage.py 020
3.4A-030 command = python .\apmd_same_f_path_dosage.py 030
3.4A-040 command = python .\apmd_same_f_path_dosage.py 040
progression rule = move to the next preload-extra group after obtaining 3 accepted usable pairs in the current group
```

**3.4B：preload holding-time scan**

从 3.4A 结果选择 `preload extra = +0.40 mm` 作为固定路径剂量，再扫描 preload 保持时间：

```text
target F = 3.75 N
preload extra depth = +0.40 mm
preload hold = 5 s, 30 s, 90 s
trials = 3 per condition
execution mode = split into three single-hold sessions: 005, 030, 090
3.4B-005 command = python .\apmd_same_f_path_hold_time.py 005
3.4B-030 command = python .\apmd_same_f_path_hold_time.py 030
3.4B-090 command = python .\apmd_same_f_path_hold_time.py 090
```

**输出**

```text
Δd vs preload extra depth
ΔBvec vs preload extra depth
Δd vs preload hold
ΔBvec vs preload hold
same-F pass rate
irreversible B0 drift after each condition
```

### 实验 3.5：恢复时间与路径记忆衰减实验

**目的**  
借鉴文献中 repeated compression 和 prestress history 的观察，判断路径效应是否随材料恢复时间系统衰减。

**正式设置**

```text
3.5A selected path = same-d / different-F path-pair
target d = 3.40 mm
preload d = 3.80 mm
preload hold = 30 s
recovery time before measured pair = 30 s, 120 s, 300 s
trials = 3 measured pairs per recovery time
conditioning = 1 initial same-d path-pair, excluded from formal summary
```

**具体流程**

1. 执行 1 次 same-d path-pair 作为 conditioning pair，不计入 summary。
2. 回撤到 no-contact。
3. 等待指定 recovery time。
4. 执行 1 次 measured same-d path-pair。
5. 记录 `direct_loading -> preload -> return_unloading` 三个状态。
6. 回撤到 no-contact。
7. 对每个 recovery time 重复 3 个 measured pairs。
8. 比较不同 recovery time 下的 `ΔF, Δd, ΔBvec`。

**输出**

```text
ΔF recovery curve
Δd recovery curve
ΔBvec recovery curve
B0 drift after recovery
```

**解释标准**

若路径差异随 rest time 系统衰减，说明材料路径记忆是真实机制之一；若完全不衰减，则需要检查是否存在几何滑移或磁体位置永久改变。

---

## 阶段 4：局部可辨识性工作区映射

### 目标

从阶段 3 的粗扫描和路径剂量实验中选择候选局部区域，然后估计局部 `F` 方向和 `d` 方向的磁敏感性，寻找最适合证明力-位移可辨识机制的区域。

这里的“工作区”指当前实验台、当前样品和当前压头几何下的局部 mechanism-validation zone。它不等同于 prosthetic socket 真实应用中的完整力/位移范围。

### 4.1 粗筛评分

每个候选工作区计算：

```text
same-d score = median(ΔBvec / |ΔF|) × same-d pass rate
same-F score = median(ΔBvec / |Δd|) × same-F pass rate
stability score = repeat directional consistency of ΔB
artifact penalty = B0 drift + failed gates + visible slip
```

选择 top 2-3 个候选工作区进入局部加密。

### 4.2 局部加密扫描

以最佳候选点为中心，做更细扫描：

```text
d_target = d_best - 0.10, d_best, d_best + 0.10 mm
F_target = F_best - 0.10, F_best, F_best + 0.10 N
preload extra = +0.20, +0.30, +0.40 mm
trials = 3 per condition
```

若 `d_best` 或 `F_best` 接近安全边界，则只向安全方向加密。

### 4.3 局部灵敏度估计

对通过 gate 的 path-pairs 计算：

```text
j_F ≈ ΔB / ΔF     from near-matched-d/different-F pairs
j_d ≈ ΔB / Δd     from near-matched-F/different-d pairs
```

每个工作区输出：

```text
|j_F|
|j_d|
angle(j_F, j_d)
condition number of [j_F, j_d]
noise-normalized sensitivity = ΔBvec / σ_B_noise
```

### 4.4 最佳工作区判定

推荐通过标准：

```text
ΔBvec / σ_B_noise >= 10
angle(j_F, j_d) >= 45 deg
condition number <= 5
same-d pass rate >= 2/3
same-F pass rate >= 2/3
repeat directional consistency = pass
```

最终选择：

```text
strict primary sensitivity-pair candidate = passes angle/condition/noise gates
practical high-score candidate = highest combined score, even if one strict gate is marginal
secondary work zone = backup if primary fails cross-day validation
```

---

## 阶段 5：APMD 解耦模型数据采集与建模

### 目标

在阶段 4 筛选出的局部候选区内采集建模数据，建立能够同时输出 `F` 和 `d` 的局部 proof-of-mechanism 解耦模型，并检验路径记忆特征是否优于普通磁回归和机械基线。

阶段 5 的模型不声明覆盖 prosthetic socket 的完整真实受力范围。它的目标是证明主动路径激励在一个可辨识局部区域内确实能帮助从磁信号解耦 `F` 和 `d`。

### 实验 5.1：建模数据采集

阶段 5.1 不再继续补充离散现象验证点，而是采集局部模型训练所需的连续路径数据。已有 3.1/3.3/3.5 的结果已经足够证明机制；5.1 的目标是让模型在 selected local work zone 内学习连续的 `F-d-B-path` 映射。

#### 实验 5.1A：pairwise same-d 局部补充（可选）

**用途**

如果 5.1B 后模型在某些局部 d 点附近误差仍高，再补充严格 pairwise 的 same-d 数据。该实验不是当前优先项。

```text
target d = selected local d points
preload d = target d + 0.40 mm
direct target record = 45 s
preload record = 30 s
return target record = 45 s
trials = 3-5 usable pairs per d
```

#### 实验 5.1B：local minor-loop dense sampling（当前优先）

**目的**

在同一个局部 hysteresis loop 内补充 `d=3.1/3.3/3.5 mm` 等中间点，使模型不只学习几个离散 path-pair，而是学习 selected work zone 内的连续 loading/unloading branch。

**正式设置**

```text
script = python .\apmd_local_minor_loop_dense_sampling.py
loading d = 3.0 -> 3.1 -> 3.2 -> 3.3 -> 3.4 -> 3.5 -> 3.6 mm
preload d = 3.8 mm
unloading d = 3.6 -> 3.5 -> 3.4 -> 3.3 -> 3.2 -> 3.1 -> 3.0 mm
cycles = 5
record per loading/unloading state = 15 s
record per preload state = 30 s
summary window = last 5 s median
rest between cycles = 120 s
start position = 6 mm above physical lower limit
force hard limit = OFF
```

**Block L 扩展设置（lower work zone）**

Block L 用来把当前 local-identifiability 模型从原来的 Block M `d=3.0-3.6 mm` 扩展到较浅工作区 `d=2.4-3.0 mm`。Block L 不改变 5.1B 的运动逻辑，只改变 dense-loop 的局部位移网格和 common preload：

```text
script = python .\apmd_local_minor_loop_dense_sampling.py L
loading d = 2.4 -> 2.5 -> 2.6 -> 2.7 -> 2.8 -> 2.9 -> 3.0 mm
preload d = 3.2 mm
unloading d = 3.0 -> 2.9 -> 2.8 -> 2.7 -> 2.6 -> 2.5 -> 2.4 mm
cycles = 5
record per loading/unloading state = 15 s
record per preload state = 30 s
summary window = last 5 s median
rest between cycles = 120 s
start position = 6 mm above physical lower limit
force hard limit = OFF
```

Block L 的 `d=3.0 mm` 与 Block M 的起点重叠。这个重叠点不是重复错误，而是两个 work-zone block 的 bridge/anchor：Block L 的 path history 是 `previous max d = 3.2 mm`，Block M 的 path history 是 `previous max d = 3.8 mm`，后续建模时必须保留 `work_zone_id`、`preload_d`、`previous_max_d` 和 branch/path-memory 特征，不能把两个 `d=3.0 mm` 状态直接平均。

**Block L 正式训练记录**

```text
accepted training cycles = 20
accepted training states = 300
accepted sessions/cycles:
  session_20260622_112307: cycles 1-5
  session_20260622_132503: cycles 1-5
  session_20260622_143801: cycles 1-3
  session_20260622_151834: cycles 1-3
  session_20260622_162129: cycles 1-4
excluded data:
  session_20260622_142751: no completed states
  session_20260622_151834 cycle 4: incomplete
  session_20260622_162129 cycle 5: incomplete
QC:
  complete state summaries = 300
  same-d-like pairs = 140/140
  force-split pairs = 140/140
  magnetic-split pairs = 140/140
  median |Delta F| = 1.543 N
  median Delta Bvec = 162.2 uT
next step:
  run Block L held-out dense-loop validation
  python .\apmd_stage6_local_heldout_dense_loop.py L
```

**每个 cycle 流程**

1. 记录 no-contact `B0`。
2. 搜索接触点或确认当天 contact zero。
3. 沿 loading branch 依次到达 `3.0/3.1/3.2/3.3/3.4/3.5/3.6 mm`，每个状态记录 15 s。
4. 到达 common preload state `3.8 mm`，记录 30 s。
5. 沿 unloading branch 依次回到 `3.6/3.5/3.4/3.3/3.2/3.1/3.0 mm`，每个状态记录 15 s。
6. 回撤到 no-contact 起点。
7. 休息 120 s。
8. 重复 5 个 cycles。

**关键输出**

```text
local_minor_loop_dense_5p1B_cycle<cycle>.csv
local_minor_loop_dense_5p1B_state_summary.csv
```

每个 cycle 包含 15 个状态：

```text
7 loading states + 1 preload state + 7 unloading states
```

5 个 cycles 共得到 75 个 state summaries，可作为 Stage 5 local model 的主要训练数据。

### 建模 5.2：输入特征

**基础磁特征**

```text
Bx, By, Bz
|B|
Bx-B0x, By-B0y, Bz-B0z
```

**路径记忆特征**

```text
path_label = loading / preload / unloading / recovery
previous_max_d
previous_max_F
preload_depth
preload_hold_time
time_since_preload
time_since_unloading
cycle_index
```

### 建模 5.3：必须比较的模型

| 模型 | 输入 | 目的 |
|---|---|---|
| 机械基线 | `F=h(d)` | 检查磁模型是否优于普通力-位移耦合 |
| 单变量磁基线 | `d=g(|B|)` | 检查三轴和路径信息是否必要 |
| 普通磁回归 | `Bx,By,Bz -> [F,d]` | 检查纯磁信号能力 |
| Lim-style 分支补偿模型 | `B + loading/unloading/preload label -> [F,d]` | 文献对照：把路径差异作为 hysteresis compensation label |
| APMD 路径记忆模型 | `B + branch + previous max d + preload depth + dwell/recovery/cycle memory -> [F,d]` | 利用主动路径历史，而不是只给 loading/unloading 标签 |
| APMD 局部可辨识模型 | `B + local j_F/j_d coordinates + work-zone id -> [F,d]` | 直接检验 Stage 4 夹角/局部灵敏度是否能帮助解耦 |
| work-zone-aware gating model | `B -> work-zone/gate -> local model -> [F,d]` | 面向后续 socket 扩展：不同工作区使用不同局部模型，而不是强行一个全局模型平均所有结构 |

### 评估指标

```text
F_MAE, F_RMSE, F_max_error
d_MAE, d_RMSE, d_max_error
path-state classification accuracy
held-out target performance
cross-day performance
```

---

## 阶段 6：留出状态盲测验证

### 目标

证明现象和局部模型不是只在训练点成立，而能在 selected local work zone 附近外推到未见目标和未见路径对。

该阶段仍属于 mechanism-level validation，不等同于 prosthetic socket 全范围验证。

### 验证 6.1：local held-out dense-loop acquisition

**设计**

```text
purpose = collect a new test-only dense-loop session inside the selected local work zone
training dense-loop d grid = 3.00/3.10/3.20/3.30/3.40/3.50/3.60 mm
held-out dense-loop d grid = 3.05/3.15/3.25/3.35/3.45/3.55 mm
preload d = 3.80 mm
cycles = 3
state record = 15 s
preload record = 30 s
summary window = last 5 s median
rest between cycles = 120 s
planned state summaries = 39
command = python .\apmd_stage6_local_heldout_dense_loop.py
```

**Block L held-out 扩展设置**

Block L 的 held-out session 只在 Block L 完成至少 4 个 training dense-loop sessions 后运行，并且必须作为 test-only session，不得提前加入训练集：

```text
purpose = collect Block L test-only dense-loop session
training dense-loop d grid = 2.40/2.50/2.60/2.70/2.80/2.90/3.00 mm
held-out dense-loop d grid = 2.45/2.55/2.65/2.75/2.85/2.95 mm
preload d = 3.20 mm
cycles = 3
state record = 15 s
preload record = 30 s
summary window = last 5 s median
rest between cycles = 120 s
planned state summaries = 39
command = python .\apmd_stage6_local_heldout_dense_loop.py L
```

**通过标准**

```text
session completes all 39 planned state summaries
d_actual is within normal Mark-10 command tolerance for each state
loading and unloading branches both cover the full held-out d grid
no hardware abort, serial dropout, or contact-loss event
this session is not included in model training before Stage 6.2 evaluation
```

**设计理由**  

5.1B 的训练数据已经覆盖 selected local work zone 内的 `3.00-3.60 mm` dense loop。6.1 不再重复同一组 d 点，而是采集中间插值点 `3.05/3.15/3.25/3.35/3.45/3.55 mm`，用来检查模型是否真正学到局部 `F-d-B-path` 映射，而不是只记住训练网格。

**正式采集结果**

```text
accepted session = session_20260615_160438
state summary = local_heldout_dense_loop_6p1_state_summary.csv
quick-look figure = local_heldout_dense_loop_6p1.png
QC table = reports/apmd_stage6_heldout_qc_by_d.csv
completed states = 39/39
cycles = 3
loading states = 18
preload states = 3
unloading states = 18
sample count per state = 113-114
mean |d_median - d_target| = 0.0149 mm
same-d-like branch pairs = 18/18 pass |d_unloading - d_loading| <= 0.05 mm
force split = 18/18 pass |Delta F| >= 0.20 N
magnetic split = 18/18 pass Delta Bvec >= 50 uT
median |Delta F| = 2.543 N
median Delta Bvec = 265.8 uT
status = accepted as Stage 6.1 test-only held-out dataset
```

**Block L 正式 held-out 结果**

本轮只把完全 strong 的 6 个完整 cycles 作为 Block L primary held-out。两个虽然完整但在 `d=2.95 mm` 有 1 个 pair 的 `Delta Bvec` 低于 50 uT 的 cycle 暂不计入 primary held-out，可作为后续 robustness 参考，但不作为正式主证据。

```text
accepted primary session/cycles =
  session_20260622_173504 cycles 1-3
  session_20260622_180702 cycle 1
  session_20260622_185538 cycles 1-2

primary complete cycles = 6
primary state summaries = 78/78
held-out d grid = 2.45/2.55/2.65/2.75/2.85/2.95 mm
preload d = 3.20 mm
same-d-like branch pairs = 36/36 pass |d_unloading - d_loading| <= 0.05 mm
force split = 36/36 pass |Delta F| >= 0.20 N
magnetic split = 36/36 pass Delta Bvec >= 50 uT

complete but not primary =
  session_20260622_180702 cycle 2: one d=2.95 mm pair Delta Bvec = 45.1 uT
  session_20260622_185538 cycle 3: one d=2.95 mm pair Delta Bvec = 48.9 uT

excluded incomplete =
  session_20260622_180702 cycle 3

status = accepted as Block L test-only primary held-out dataset
```

### 验证 6.2：模型层 held-out 验证

**拆分原则**

训练集只使用 Stage 3 accepted path-pair 数据和四个 Stage 5.1B dense-loop session。Stage 6.1 采集的新 session 必须整体作为 test-only held-out session，不允许随机拆分相邻状态点。目前正式 held-out 使用 `session_20260615_160438` 和 `session_20260618_161152`，共 78 个 state。

**通过标准**

| 输出 | 通过标准 |
|---|---|
| `F` | held-out `F_MAE <= 0.50 N`，且 APMD path-memory 模型小于 plain magnetic baseline |
| `d` | held-out `d_MAE <= 0.05 mm`，且 APMD path-memory 模型小于 plain magnetic baseline |
| path state | 能区分 loading 与 unloading target state |
| robustness | held-out 插值点误差不明显集中在某一个 branch 或某一个 d 区间 |

### 验证 6.3：APMD local-identifiability 模型对照（已完成）

**目的**

Stage 5-6 的第一版模型已经证明：加入 path label / path memory 后，`d` 的 held-out 预测可以达到局部目标，但 `F` 的 held-out 误差仍偏大。这个结果说明目前模型还没有充分利用 Stage 4 的核心信息：主动路径对实验得到的局部 `j_F/j_d` 灵敏度方向和 branch geometry。

因此，下一步先不急着大规模补采，而是用已有数据做一个更明确的模型对照：检验 “APMD 局部可辨识坐标” 是否比文献式 loading/unloading label 补偿更能解释 held-out `F,d`。

**核心思想**

主动路径对不是只用来证明现象，也不应该只变成一个 `loading/unloading` label。它应该提供局部坐标系：

```text
j_F(d) = Delta B_same-d / |Delta F|
j_d(F) = Delta B_same-F / |Delta d|
J_local = [j_F, j_d]
```

这里 `j_F` 表示“近似同位移时，力变化在磁空间里的方向”，`j_d` 表示“近似同力时，位移变化在磁空间里的方向”。如果这两个方向夹角足够大，说明同一个三轴磁信号空间里存在两个相对独立的局部解释方向，这是 Stage 4 夹角分析的建模意义。

对每一个 dense-loop state，用最近工作区的 `j_F/j_d` 把磁信号投影成局部可辨识坐标：

```text
unit_j_F = j_F / ||j_F||
unit_j_d = j_d / ||j_d||
p_F = Delta B · unit_j_F
p_d = Delta B · unit_j_d
residual = ||Delta B - projection_on_span(j_F, j_d)||
```

这样模型输入不再只是 `B` 或 `B + label`，而是加入了由主动路径对实验估计出来的局部力方向、局部位移方向和剩余项。

**使用数据**

```text
training states = reports/apmd_stage5_model_dataset_states.csv
held-out test sessions = session_20260615_160438 + session_20260618_161152
j_F source = reports/apmd_stage4_jF_from_same_d_pairs.csv
j_d source = reports/apmd_stage4_jd_from_same_f_pairs.csv
selected local zone = d about 3.20-3.60 mm, F about 3.75-4.90 N
```

**必须比较的模型**

| 模型 | 输入 | 作用 |
|---|---|---|
| Plain magnetic baseline | `Bx, By, Bz, |B|` | 检查纯磁信号能做到什么程度 |
| Lim-style branch compensation | `B + loading/unloading/preload label` | 文献式 hysteresis compensation 对照 |
| APMD path-memory model | `B + branch + previous max d + preload depth + cycle index` | 检查路径历史是否优于简单 branch label |
| APMD local-identifiability model | `B + p_F + p_d + residual + work_zone_id + branch` | 直接检验主动路径对估计的 `j_F/j_d` 是否帮助解耦 |

**成功标准**

```text
primary target: APMD local-identifiability F_MAE <= 0.75 N on held-out session
ideal target:   APMD local-identifiability F_MAE <= 0.50 N
d target:       d_MAE <= 0.05 mm
relative target: local-identifiability model reduces F_MAE by >= 15% vs Lim-style branch compensation
```

若结果满足：

```text
APMD local-identifiability > APMD path-memory > Lim-style label > plain magnetic
```

则可以说明我们的路线不是简单地“加 loading/unloading label 补偿迟滞”，而是主动路径对提供了可辨识的局部坐标，帮助模型分解 `F` 和 `d`。

**输出**

```text
reports/apmd_stage6_local_identifiability_model_metrics.csv
reports/apmd_stage6_local_identifiability_predictions.csv
reports/apmd_stage6_local_identifiability_comparison.png
reports/APMD_STAGE6_LOCAL_IDENTIFIABILITY_MODEL.md
```

**当前正式结果**

```text
status = force pass / near d-gate
train states = 561
held-out states = 78 from session_20260615_160438 + session_20260618_161152
plain magnetic ridge = F_MAE 1.807 N, d_MAE 0.045 mm
Lim-style branch-label ridge = F_MAE 0.839 N, d_MAE 0.035 mm
APMD path-memory ridge = F_MAE 0.796 N, d_MAE 0.063 mm
best local-ID ridge = F_MAE 0.054 N, d_MAE 0.056 mm
best local-ID RF = F_MAE 0.062 N, d_MAE 0.065 mm
local-ID ridge improvement vs Lim-style F_MAE = 93.5%
```

这个结果说明，Stage 4 的 `j_F/j_d` 局部灵敏度不是只用于解释现象，而是可以作为模型输入显著改善 held-out force prediction。也就是说，APMD 与文献式 branch-label compensation 的区别在这里被模型层面体现出来：不是只告诉模型“这是 loading/unloading”，而是把主动路径对估计出的局部力方向和局部位移方向作为可辨识坐标交给模型。

需要注意的是，local-ID ridge 的 `d_MAE = 0.056 mm` 略高于严格 `0.050 mm` gate，而 Lim-style branch-label ridge 的 `d_MAE = 0.035 mm` 更好。因此当前结论应表述为：local-ID geometry 对 force 解耦提供了非常强的帮助，displacement 仍需在后续模型组合或定向补采中进一步优化。实际可采用“force 用 local-ID ridge / displacement 用 branch-label ridge”的双输出组合，或在 6.4 中只补强 displacement 误差集中的局部点。

### 实验 6.4A：high-force same-F 局部灵敏度补采（当前执行）

**目的**

当前 Stage 6.3 已经证明 local-identifiability geometry 对 held-out force prediction 有明显帮助，但 Stage 4 的 `j_d` 来源主要是 Stage 3.2 same-F/different-d 路径对，而 Stage 3.2 正式力点最高到 `4.90 N`。相比之下，Stage 5/6 dense-loop 数据在 selected local work zone 内实际覆盖了更高的力区，尤其是 direct-loading 和 preload states 可达到约 `8-18 N`。因此，本轮不先补更多 dense-loop，也不广泛重跑 Stage 3，而是优先补一组高力区 same-F/different-d local sensitivity，用来增强 `j_d` 在模型真实使用力区内的校准。

换句话说，6.4A 的目标不是再证明 same-F 现象存在，而是让 local-ID model 里的位移相关方向 `j_d` 不再只依赖低力点外推。

```text
primary target F = 8.00, 10.00, 12.00 N
optional extension F = 6.00 or 14.00 N, only if time allows
preload rule = fixed preload d = 3.80 mm
trials = 3 usable pairs per F
state record = 45 s loading target, 30 s preload, 45 s unloading target
same-F gate = |F_unloading - F_loading| <= 0.050 N
usable relaxed gate for diagnosis only = <= 0.100 N
displacement split gate = |Delta d| >= 0.10 mm
magnetic split gate = Delta Bvec >= 100 uT
script = apmd_high_force_same_f_local_sensitivity.py
```

**推荐执行方式**

为了降低 same-F 高力点的失败成本，正式推荐单点运行：

```text
python .\apmd_high_force_same_f_local_sensitivity.py 800
python .\apmd_high_force_same_f_local_sensitivity.py 1000
python .\apmd_high_force_same_f_local_sensitivity.py 1200
```

如果当天系统非常稳定，也可以一次性运行：

```text
python .\apmd_high_force_same_f_local_sensitivity.py
```

**为什么 fixed preload d = 3.80 mm**

Stage 5.1B 和 Stage 6.1 的 dense-loop 数据都使用 common preload `d=3.80 mm`。因此 6.4A 也使用固定 `3.80 mm`，而不是 `loading d + 0.30 mm`。这样补采得到的 `j_d` 更直接对应当前模型数据中的 path history，而不是重新引入另一种 preload 规则。

**当前不做的补采**

```text
same-d half-grid d = 3.10/3.30/3.50 mm: optional later
shifted dense-loop grid = 3.05/3.15/.../3.55 mm: optional later
global socket-range force expansion: not part of current local proof-of-mechanism
```

**预期结论**

如果高力 same-F local sensitivity 补采后，Stage 4/6 重新估计的 local-ID features 能进一步稳定 held-out force/displacement prediction，说明此前误差主要来自 `j_d` 高力区校准不足，而不是 APMD 机制本身失败。若补采后 improvement 很小，再考虑是否需要 shifted dense-loop 或更复杂的模型形式。

### 实验 6.4B-L：Block L same-d 局部灵敏度补采（已完成）

**目的**

Block L 已经完成 lower work zone 的 dense-loop 训练数据和 held-out 数据，但如果直接重跑 local-ID 模型，会面临一个问题：Block L 的 `j_F` 局部力方向仍可能依赖 Block M 或 Stage 3 深工作区的 same-d/different-F 数据外推。由于 `j_F` 是局部灵敏度方向，不应假设在不同 preload depth 和不同压入区间完全相同，因此本实验专门为 Block L 估计自己的 same-d force-sensitivity direction。

**正式设置**

```text
script = python .\apmd_same_d_different_f_scan.py L
single-point supplement command = python .\apmd_same_d_different_f_scan.py L300
target d = 2.40, 2.60, 2.80, 3.00 mm
preload d = 3.20 mm fixed for all target d
trials = 3 usable pairs per target d
direct target record = 45 s
preload record = 30 s
return target record = 45 s
summary window = last 10 s median
rest between pairs = 120 s
same-d gate = |d_return - d_direct| <= 0.020 mm
force split target = |Delta F| >= 0.20 N
magnetic signal gate = Delta Bvec >= 50 uT
force hard limit = OFF
```

**为什么不用 `target d + 0.30 mm`**

Block L dense-loop 的 common preload 是 `3.20 mm`。本次 same-d calibration 的目标不是复刻原 Stage 3.1 的工作区扫描，而是为 Block L 模型提供与 dense-loop path history 对齐的 `j_F`。因此，所有 target d 都使用同一个 fixed preload `3.20 mm`，这样得到的 `j_F` 更接近 Block L 训练/held-out 数据实际经历的最大路径深度。

**通过后输出**

```text
block_L_same_d_local_sensitivity_pair_summary.csv
block_L_same_d_local_sensitivity_<target>_rep<idx>.csv
session-local figure = block_L_same_d_local_sensitivity.png
```

如果 4 个 target d 都得到 3/3 strong pairs，则 Block L 的 `j_F` calibration 完成；下一步再补 Block L same-F/different-d 的 `j_d` calibration。

**正式结果**

```text
session_20260622_203244:
  d=2.40 mm: 3/3 strong
  d=2.60 mm: 3/3 strong
  d=2.80 mm: 3/3 strong

session_20260623_091618:
  d=3.00 mm: 3/3 strong

total accepted same-d pairs = 12/12
same-d gate = 12/12
force-split gate = 12/12
magnetic-split gate = 12/12
fixed preload d = 3.20 mm
median |Delta F| by target =
  d=2.40 mm: 1.120 N
  d=2.60 mm: 1.211 N
  d=2.80 mm: 1.318 N
  d=3.00 mm: 0.884 N
median Delta Bvec by target =
  d=2.40 mm: 179.9 uT
  d=2.60 mm: 207.6 uT
  d=2.80 mm: 150.3 uT
  d=3.00 mm: 135.1 uT
status = Block L j_F calibration complete
```

### 实验 6.4C-L：Block L same-F 局部灵敏度补采（当前执行）

**目的**

Block L 已经完成 lower work zone 的 dense-loop 训练数据、held-out 数据，以及 same-d/different-F 的 `j_F` calibration。下一步需要为同一个 Block L 工作区补自己的 same-F/different-d `j_d` calibration。这样后续重建 local-identifiability model 时，`j_F` 和 `j_d` 都来自同一个 preload history 和同一个 lower work zone，而不是把 Block M 或 Stage 3.2 的深工作区方向直接外推过来。

**正式设置**

```text
script = python .\apmd_same_f_different_d_scan.py L300/L450/L600/L750/L900
target F = 3.00, 4.50, 6.00, 7.50, 9.00 N
fixed preload d = 3.20 mm
loading target record = 45 s
preload record = 30 s
unloading target record = 45 s
trials = 3 usable pairs per target F
rest between pairs = 120 s
state summary window = last 10 s median
same-F gate = |F_unloading - F_loading| <= 0.050 N
displacement split target = |Delta d| >= 0.10 mm
magnetic signal gate = Delta Bvec >= 100 uT
force hard limit = OFF
depth soft limit = OFF
```

**为什么固定 preload d = 3.20 mm**

Block L dense-loop 的 common preload 是 `3.20 mm`。本实验不是重新做 Stage 3.2 的全局 same-F 扫描，而是为了给 Block L 模型估计局部位移相关磁响应方向 `j_d`。因此所有 force target 都使用同一个 fixed preload `3.20 mm`，让 `j_d` 与 Block L 训练/held-out 数据的实际最大路径深度保持一致。

**推荐执行方式**

为了降低 same-F 匹配失败的成本，每个力点单独运行并单独登记；失败时只重测当前力点，不影响已通过力点：

```text
python .\apmd_same_f_different_d_scan.py L300
python .\apmd_same_f_different_d_scan.py L450
python .\apmd_same_f_different_d_scan.py L600
python .\apmd_same_f_different_d_scan.py L750
python .\apmd_same_f_different_d_scan.py L900
```

**通过后输出**

```text
F target
F_loading, F_unloading, Delta F
d_loading, d_unloading, Delta d
Delta Bx, Delta By, Delta Bz
Delta Bvec
j_d(F) = Delta B / |Delta d|
```

如果 5 个 target F 都得到 3/3 strong pairs，则 Block L 的 `j_d` calibration 完成；下一步重建 Block L local-ID features，并把 Block L 与 Block M 的模型结果分开评估，再决定是否合并成 multi-block work-zone-aware model。

---

## 阶段 7：机制与伪差对照验证

### 目标

证明主动路径对信号来自可控材料路径记忆，而不是随机漂移、线缆运动、压头滑移、磁体永久位移或单纯几何误差。

### 实验 7.1：无接触运动伪差对照

```text
condition = no contact
script = python .\apmd_no_contact_motion_artifact.py
motion path = replay selected same-d active path-pair
nominal target d = 3.40 mm
nominal preload d = 3.80 mm
replay command sequence = direct target -> preload -> return target
direct target record = 45 s
preload record = 30 s
return target record = 45 s
trials = 3
artifact gate = return-direct ΔBvec <= 10 uT
B0 drift gate = B0_end - B0_start ΔBvec <= 10 uT
formal registry policy = only register if 3/3 trials pass artifact gate and B0 drift gate passes
```

**具体流程**

1. 保持 MLX、样品、磁体几何尽量接近正式 APMD 设置。
2. 但必须让压头在整个 replay 过程中不接触样品；如果第一次 replay move 有可见接触，立即 abort。
3. Mark-10 起点仍为距离物理下限位上方约 6 mm。
4. 记录 `B0_start`。
5. 不搜索接触点，不重新定义 `d=0`，而是按 selected contact experiment 的相对运动深度复刻 Mark-10 轨迹。
6. 依次 replay `3.40 -> 3.80 -> 3.40 mm` 对应的 direct/preload/return 运动位置。
7. 每个 trial 输出 raw CSV 和 return-direct `ΔBvec` summary。
8. 三个 trial 后记录 `B0_end` 并计算 drift。
9. 若 `3/3` trials 的 `ΔBvec <= 10 uT` 且 `B0 drift <= 10 uT`，该 session 自动记录到 formal design。

若无接触运动路径的 `ΔBvec` 远小于接触路径对，说明主信号不是运动伪差。

### 实验 7.2：重复 loading branch 对照

```text
target d = 3.40 mm
no deeper preload
repeat loading-to-target and retract = 5 cycles
record target state = 45 s
state summary window = last 10 s median
rest between cycles = 120 s
contact reference = search contact once before cycle 1, then keep the same absolute target position for all cycles
control reference = cycle 1 loading target state
control metric = ΔBvec of each later cycle relative to cycle 1
control gate = max cycle-to-cycle ΔBvec <= 50 uT
script = python .\apmd_repeated_loading_control.py
```

具体流程：

1. 记录 no-contact `B0`。
2. 从 no-contact 起点只搜索一次接触点，并定义该 session 的 fixed `d=0`。
3. 由该 fixed contact reference 计算唯一的绝对目标位置 `target_pos = contact_pos - 3.40 mm`。
4. cycle 1 沿 loading branch 压入到这个固定绝对目标位置。
5. 在 target state 记录 `45 s`。
6. 回撤到 no-contact 起点。
7. 休息 `120 s`。
8. cycles 2-5 不再重新搜索接触点，均压入同一个绝对目标位置。
9. 用每个 cycle 的末 `10 s` 中位值计算相对 cycle 1 的 `ΔF, Δd, ΔBx, ΔBy, ΔBz, ΔBvec`。
10. 若 `5/5` cycles 均完成，且最大 cycle-to-cycle `ΔBvec <= 50 uT`，该 session 自动记录到 formal design。

若无 deeper preload 的重复 loading branch 不产生接近 active same-d path-pair 的大 `ΔBvec`，则说明 active preload path 是必要激励，而不是单纯重复 loading 或回撤休息造成的循环伪差。

### 实验 7.3：cross-day repeatability

```text
selected best same-d path-pair = 3 pairs on day 1 and day 2
selected best same-F path-pair = 3 pairs on day 1 and day 2
same head/sample geometry unless intentionally changed
```

输出：

```text
day-to-day ΔF consistency
day-to-day Δd consistency
day-to-day ΔBvec consistency
axis contribution consistency
```

### 实验 7.4：材料/界面状态对照

若时间允许，增加一个材料或界面状态对照，用来呼应文献中的 hardness/material compensation 思路。

优先级从高到低：

```text
same sample, changed preload history
same sample, changed recovery time
same sample, changed surface friction condition
different soft interface stiffness, if available
```

该实验不作为第一轮建模必需条件，但可作为论文后续扩展和回答审稿人问题的储备。

---

## 阶段 8：prosthetic socket 应用范围扩展

### 目标

在局部 proof-of-mechanism 模型通过 Stage 5-6 验证之后，再把 APMD 从实验台局部工作区扩展到 prosthetic socket 相关的更宽力/位移范围。

这一阶段不作为当前机制验证的前置条件。它用于回答应用问题：

```text
local model 是否能扩展到 multi-zone model
高力范围下 j_F 与 j_d 是否仍然可分
socket-like geometry/interface 是否改变路径记忆特征
```

### 推荐路线

```text
application force range = 5, 10, 15, 20 N, then refine as needed
work-zone strategy = multi-zone rather than one fixed global work zone
model strategy = local models or mixture-of-experts before attempting one global model
fixture = socket-like curved/soft interface after flat-bench validation
```

### 进入条件

```text
Stage 5 local model beats mechanical and plain magnetic baselines
Stage 6 held-out local validation passes
Stage 7 artifact and repeated-loading controls do not explain the signal
```

### 解释边界

当前 Stage 1-7 的结论应表述为：

```text
active path-pair excitation enables local identifiability in the current soft magnetic testbed
```

不应提前表述为：

```text
the method already solves full prosthetic-socket force/displacement decoupling
```

---

## 正式命名规则

旧编号可保留在脚本和历史数据文件名中，但正式汇报和论文中建议使用以下名称：

| 实验目的 | 正式中文名 | 正式英文名 |
|---|---|---|
| 固定 `d` 等待松弛 | 固定位移被动松弛实验 | Fixed-Displacement Passive Relaxation Test |
| 固定 `F` 等待蠕变 | 固定力被动蠕变实验 | Fixed-Force Passive Creep Test |
| 同位移附近制造异力 | 近似同位移/异力主动路径对实验 | Near-Matched-Displacement / Different-Force Active Path-Pair Test |
| 同力附近制造异位移 | 近似同力/异位移主动路径对实验 | Near-Matched-Force / Different-Displacement Active Path-Pair Test |
| 扫描路径强度 | 路径剂量表征实验 | Path-Dosage Characterization Test |
| 检查恢复 | 恢复时间与路径记忆衰减实验 | Recovery-Time and Path-Memory Decay Test |
| 排除运动伪差 | 无接触运动伪差对照实验 | No-Contact Motion Artifact Control Test |
| 建立工作区图 | 局部可辨识性工作区映射 | Local Identifiability Workspace Mapping |
| 最终模型验证 | 留出状态盲测验证 | Held-Out Blind Validation |

---

## 当前已完成结果在本方案中的位置

| 已完成内容 | 正式方案中的位置 | 当前结论 |
|---|---|---|
| 固定位移被动松弛数据 | 实验 2.1 | `ΔF` 明显，但 `ΔBvec` 很小 |
| 近似同位移/异力主动路径对 | 实验 2.2 | same-d gate 内产生强 `ΔF` 和强 `ΔBvec` |
| 固定力被动蠕变数据 | 实验 2.3 | `Δd` 大，但 `ΔBvec` 很小 |
| 近似同力/异位移主动路径对 | 实验 2.4 | same-F gate 内产生强 `Δd` 和强 `ΔBvec` |
| same-d 工作区扫描 | 实验 3.1 | 深工作区产生更强 same-d/different-F 磁响应，`d≈3.2-3.4 mm` 是主要候选区 |
| same-F 工作区扫描 | 实验 3.2 | `F=1.5-4.9 N` 范围内均有强 same-F/different-d 响应，`F≈4.9 N` 是主要候选力区 |
| same-d 路径剂量与恢复时间 | 实验 3.3、3.5 | preload depth 有明显影响；preload hold/recovery time 影响较弱或温和 |
| same-F 路径剂量与 hold time | 实验 3.4 | preload extra depth 对 displacement split 有明显影响；hold-time 效果不如 preload depth 稳定 |
| 局部可辨识性映射 | 阶段 4 | strict primary sensitivity-pair candidate 为 `d=3.40 mm` + `F=4.90 N`，`angle=48.5 deg`，scaled condition=`2.22` |
| O-mini held-out pilot | 阶段 6 初步验证 | 现象层 strong，但简单全局 `Bxyz -> [F,d]` 模型尚不足 |

这说明项目目前已经完成“现象可行性验证、路径剂量表征、恢复时间控制、工作区粗筛和局部可辨识性映射”。下一步应进入 Stage 5：在 selected local work zone 内采集模型数据并建立局部 proof-of-mechanism 解耦模型。

当前结论边界：

```text
已经支持：主动路径激励可以把软材料迟滞/路径记忆转化为局部可辨识激励源。
尚未支持：该方法已经覆盖 prosthetic socket 的完整真实受力范围。
```

