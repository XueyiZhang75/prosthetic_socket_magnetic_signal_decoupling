# APMD Stage 3-7 最终机制证据与模型结果总结分析报告

## 0. 报告目的

这份报告用于把当前 APMD 实验路线中最关键的机制证据和模型结果串成一条完整逻辑链。它不是新的实验方案，也不重新判定任何失败 session；它只整理当前 formal design 和 reports 中已经接受的正式数据。

报告围绕两个问题展开：

1. 主动路径对是否真的能把软材料迟滞、预压历史和恢复效应从“误差源”转化成“可控可辨识激励源”？
2. 这种主动路径对得到的局部磁响应几何，是否比普通磁回归和简单 loading/unloading 标签补偿更有利于力-位移解耦？

一句话结论是：在当前 bench-top 磁触觉实验系统中，APMD 已经形成了较完整的局部机制证据链。Stage 3 证明主动路径对可以在控制变量条件下产生强磁分离；Stage 4 将这种现象转化为 `j_F/j_d` 局部灵敏度几何；Stage 5-6 证明把这种局部几何用于模型后可以显著改善 held-out 解耦；Stage 7 排除了无接触运动伪差和简单 repeated loading 两个主要替代解释。

需要明确边界：当前结论证明的是台架系统中的局部机制和局部模型可行性，不等于已经解决 prosthetic socket 的全范围力-位移解耦。

---

## 1. 术语和逻辑主线

| 术语 | 本报告中的含义 | 为什么重要 |
|---|---|---|
| APMD | Active Path-Pair Magnetic Decoupling，主动路径对磁解耦 | 项目核心概念 |
| same-d/different-F | 在近似相同位移下，通过不同路径状态构造不同力 | 用于估计力相关磁响应方向 `j_F` |
| same-F/different-d | 在近似相同力下，通过不同路径状态构造不同位移 | 用于估计位移相关磁响应方向 `j_d` |
| path-dose | preload depth、preload extra depth、hold time、recovery time 等路径激励强度 | 用于证明路径激励不是偶发现象，而是可控变量 |
| `j_F` | 由 same-d/different-F 路径对估计的局部力相关磁响应方向 | Stage 4 和 Stage 6.3 的核心输入 |
| `j_d` | 由 same-F/different-d 路径对估计的局部位移相关磁响应方向 | Stage 4 和 Stage 6.3 的核心输入 |
| held-out | 完整排除在训练集之外、只用于测试的数据 session | 用于证明模型不是只记住训练数据 |
| Lim-style branch label baseline | 只给模型加入 loading/unloading/preload branch 标签的补偿式模型 | 用于和文献中常见迟滞补偿方式对比 |
| local-identifiability model | 把 `j_F/j_d` 投影坐标和局部工作区信息加入模型 | 用于体现 APMD 不只是贴标签，而是使用主动路径对测得的局部几何 |

整条 Results 主线可以写成：

1. **主动路径对构造可分辨状态。** same-d/different-F 和 same-F/different-d 两类实验分别控制一个变量，改变另一个变量，证明磁信号确实能区分路径诱导的力/位移状态。
2. **路径激励强度可控。** preload depth 或 preload extra depth 改变后，磁响应强度随之改变；这说明路径激励不是随机漂移。
3. **路径记忆持续存在。** recovery time 从 30 s 增加到 300 s 后，响应略有下降但仍然 strong，说明路径记忆不是瞬时噪声。
4. **局部磁响应方向可分。** Stage 4 用 `j_F/j_d` 把现象变成局部灵敏度几何，发现候选工作区中力方向和位移方向夹角足够大。
5. **局部几何帮助模型解耦。** Stage 6.3 中 local-identifiability 模型明显优于普通磁回归和 Lim-style branch-label baseline。
6. **控制实验排除替代解释。** Stage 7 表明强磁分离不是无接触运动伪差，也不是简单 repeated loading 本身造成的。

---

## 2. 最终 Stage 3-7 证据图组设计和解读

### 图组 1：Stage 3.1 same-d/different-F 工作区扫描

**图的目的。**  
展示在相同目标位移 `d` 下，direct-loading 和 return-unloading 两种主动路径状态会产生明显不同的力，同时对应强磁信号差异。

**数据/session 来源。**

- `session_20260610_091145`：3.1A，target `d = 2.40/2.60/2.80 mm`。
- `session_20260610_104017`：3.1B，target `d = 3.00/3.20/3.40/3.60 mm`。
- 数据表：
  - `reports/experiment_3_1_complete_figure_data_summary.csv`
  - `reports/experiment_3_1_complete_figure_data_replicates.csv`
  - `reports/experiment_3_1_complete_figure_data.md`
- 当前 `reports` 文件夹中未检索到最终 3.1 PNG，因此这组图应标记为 data-backed figure set to be generated from these tables。

**应该看什么。**

1. direct-loading 和 return-unloading 是否在 same-d gate 内。
2. 相同 target d 下两条路径的 `F` 是否分开。
3. `Delta Bvec` 是否随着工作区加深而增强。
4. `d = 3.20-3.40 mm` 是否形成比较理想的工作区。

**关键定量结果。**

| target d (mm) | median abs(Delta F) (N) | median Delta Bvec (uT) | verdict |
|---:|---:|---:|---|
| 2.40 | 0.432 | 62.8 | strong |
| 2.60 | 0.515 | 110.2 | strong |
| 2.80 | 0.698 | 103.4 | strong |
| 3.00 | 0.814 | 155.4 | strong |
| 3.20 | 0.973 | 200.6 | strong |
| 3.40 | 1.183 | 227.8 | strong |
| 3.60 | 1.587 | 207.3 | strong |

共有 21/21 path pairs 通过 same-d 和 strong magnetic gate。

**解释。**  
这个实验是 APMD 最基础的控制变量证据之一。它说明在近似相同位移下，仅改变路径历史，就可以让材料进入不同力状态，并且这种力状态差异不是只体现在外部力传感器上，也体现在三轴磁信号中。

**支持的 claim。**  
主动路径对可以在相同位移下构造可分辨的力相关磁响应；深工作区的响应更强。

**边界和限制。**  
这不是完整模型训练数据，而是机制验证数据。它证明 same-d 条件下可分离，但不能单独证明 same-F 条件或模型预测能力。

---

### 图组 2：Stage 3.2 same-F/different-d 工作区扫描

**图的目的。**  
展示在近似相同目标力 `F` 下，loading 和 return-unloading 路径可以产生不同位移状态，并且这种位移差异对应强磁响应。

**数据/session 来源。**

- 图：`reports/experiment_3_2_style31_complete_abcde.png`
- 数据表：`reports/experiment_3_2_same_f_different_d_figure_data_replicates.csv`
- 接受的 formal target F：`1.50/1.80/2.50/3.20/3.75/4.30/4.90 N`
- `5.50 N` 当前不作为正式必要点。

![Stage 3.2 same-F/different-d 工作区扫描](experiment_3_2_style31_complete_abcde.png)

**应该看什么。**

1. force matching 是否在 same-F gate 内。
2. loading target 和 return-unloading target 的位移是否分开。
3. `Delta Bvec` 是否在不同 target F 下保持强响应。
4. 三轴贡献中是否主要由 `dBy` 和 `dBz` 主导。

**关键定量结果。**

- formal accepted force points 覆盖 `1.50-4.90 N`。
- 每个 accepted force point 有 3 个可用 path pairs。
- 典型 displacement split 约为 `0.11-0.16 mm`。
- `Delta Bvec` 在各 accepted target F 下保持约 `313-458 uT` 的强响应量级。
- 三轴响应以 `dBy` 和 `dBz` 为主，`dBx` 相对较小。

**解释。**  
3.2 是 3.1 的互补证据。3.1 证明“相同位移下可以区分力”，3.2 证明“相同力下可以区分位移”。如果只有 3.1，别人可能会认为这个机制只适用于 force split；3.2 补上之后，APMD 才形成了两个变量方向的控制变量证据。

**支持的 claim。**  
主动路径对不仅能构造力相关磁响应，也能构造位移相关磁响应。

**边界和限制。**  
same-F 实验对 force matching 很敏感，正式结论只使用 accepted reps 和 composite formal records，不使用失败或 bad match session。

---

### 图组 3：Stage 3.3-3.5 path-dose 和 recovery 图

**图的目的。**  
说明主动路径激励强度不是偶然结果，而是可以通过 preload depth、preload extra depth、hold time 和 recovery time 系统调节。

**数据/session 来源。**

- Stage 3.3A same-d preload depth：`session_20260612_155336`
- Stage 3.3B same-d preload hold time：`session_20260612_180059`
- Stage 3.4A same-F preload extra depth：formal 3.4A 数据表和图
  - `reports/experiment_3_4A_same_f_path_dosage_complete.png`
  - `reports/experiment_3_4A_same_f_path_dosage_summary.csv`
  - `reports/experiment_3_4A_same_f_path_dosage_replicates.csv`
- Stage 3.4B same-F preload hold time：
  - `reports/experiment_3_4B_same_f_path_hold_time_complete.png`
  - `reports/experiment_3_4B_same_f_path_hold_time_summary.csv`
  - `reports/experiment_3_4B_same_f_path_hold_time_replicates.csv`
- Stage 3.5 recovery time：
  - `session_20260614_201905`
  - `reports/experiment_3_5A_recovery_time_path_memory_complete.png`
  - `reports/experiment_3_5A_recovery_time_path_memory_summary.csv`
  - `reports/experiment_3_5A_recovery_time_path_memory_replicates.csv`

![Stage 3.4A same-F preload extra depth path-dose](experiment_3_4A_same_f_path_dosage_complete.png)

![Stage 3.4B same-F preload hold-time path-dose](experiment_3_4B_same_f_path_hold_time_complete.png)

![Stage 3.5 recovery-time path memory](experiment_3_5A_recovery_time_path_memory_complete.png)

**应该看什么。**

1. preload depth 或 preload extra depth 增大时，`Delta Bvec` 是否增强。
2. hold time 是否也能显著增强响应。
3. recovery time 延长后，路径记忆是否消失。
4. same-d 和 same-F 两类路径剂量实验是否得到一致逻辑。

**关键定量结果。**

Same-d preload depth at target `d = 3.40 mm`：

| preload d (mm) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 3.60 | 1.004 | 166.3 |
| 3.70 | 1.284 | 205.8 |
| 3.80 | 1.519 | 242.6 |

Same-d preload hold time at target `d = 3.40 mm`, preload `d = 3.80 mm`：

| hold time (s) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 1.527 | 251.1 |
| 30 | 1.590 | 236.9 |
| 90 | 1.623 | 241.1 |

Same-F preload extra depth at `F = 3.75 N`：

| preload extra (mm) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 0.20 | 0.10 | 287.6 |
| 0.30 | 0.10 | 308.8 |
| 0.40 | 0.13 | 350.8 |

Same-F hold time at `F = 3.75 N`, preload extra `+0.40 mm`：

| hold time (s) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 0.20 | 550.1 |
| 30 | 0.12 | 347.8 |
| 90 | 0.14 | 392.5 |

Recovery time at target `d = 3.40 mm`, preload `d = 3.80 mm`：

| recovery time (s) | median abs(Delta F) (N) | median Delta Bvec (uT) |
|---:|---:|---:|
| 30 | 2.125 | 253.4 |
| 120 | 2.077 | 240.7 |
| 300 | 2.067 | 230.5 |

**解释。**  
路径剂量实验说明，路径历史的“最大压入深度”比“停留时间”更像主要控制变量。也就是说，材料被带到多深的 preload state，比它在 preload state 停留多久更直接地决定后续 return state 的磁响应差异。recovery 实验进一步说明，路径记忆会随恢复时间略有衰减，但在 300 s 内仍未消失。

**支持的 claim。**  
preload depth/extra depth 是主要路径剂量变量；路径记忆在恢复时间内保持存在。

**边界和限制。**  
当前 path-dose 实验集中在局部工作区，不代表所有材料、所有力范围、所有 socket 几何都具有相同剂量规律。

---

### 图组 4：Stage 4 local identifiability 图

**图的目的。**  
把 Stage 3 中“磁信号变了”的现象，转化成局部解耦所需的几何条件：力相关磁响应方向 `j_F` 和位移相关磁响应方向 `j_d` 是否足够分开。

**数据/session 来源。**

- 图：`reports/apmd_stage4_identifiability_complete.png`
- 报告：`reports/APMD_STAGE4_IDENTIFIABILITY_ANALYSIS.md`
- 数据：
  - `reports/apmd_stage4_jF_from_same_d_pairs.csv`
  - `reports/apmd_stage4_jd_from_same_f_pairs.csv`
  - `reports/apmd_stage4_identifiability_summary.csv`
  - `reports/apmd_stage4_identifiability_pair_table.csv`

![Stage 4 local identifiability analysis](apmd_stage4_identifiability_complete.png)

**应该看什么。**

1. `j_F` 和 `j_d` 的夹角是否足够大。
2. scaled condition number 是否较低。
3. magnetic signal-to-noise 是否足够高。
4. 候选工作区是否位于 Stage 3 中响应强的区域。

**关键定量结果。**

- strict primary candidate：same-d `d = 3.40 mm` paired with same-F `F = 4.90 N`
- angle：`48.5 deg`
- scaled condition number：`2.22`
- min B/noise：`22.8`
- practical candidate：`d = 3.20 mm / F = 4.90 N`
- practical angle：`41.9 deg`

**解释。**  
夹角的意义是：如果力变化和位移变化在三轴磁空间里指向几乎同一个方向，那么模型很难判断磁信号变化到底来自力还是位移；如果两个方向足够分开，那么同一个磁空间中就存在两个可区分的局部解释方向。Stage 4 因此不是单纯选一个“信号最大”的点，而是在寻找“信号足够强且方向足够分开”的局部工作区。

**支持的 claim。**  
APMD 的主动路径对可以提供局部可辨识性基础，不只是产生大信号。

**边界和限制。**  
这是局部候选区，不是全局 socket 工作范围。后续若进入真实 socket，需要重新扩展工作区和重新估计局部灵敏度。

---

### 图组 5：Stage 6.3 模型对比图

**图的目的。**  
证明 `j_F/j_d` 局部几何不是只用于解释现象，也能作为模型输入改善 held-out 力-位移解耦。

**数据/session 来源。**

- 图：`reports/apmd_stage6_local_identifiability_comparison.png`
- 报告：`reports/APMD_STAGE6_LOCAL_IDENTIFIABILITY_MODEL.md`
- 数据：
  - training states：Stage 5 formal dataset，`411` states
  - held-out session：`session_20260615_160438`，`39` states
  - metrics：`reports/apmd_stage6_local_identifiability_model_metrics.csv`
  - predictions：`reports/apmd_stage6_local_identifiability_predictions.csv`

![Stage 6.3 local-identifiability model comparison](apmd_stage6_local_identifiability_comparison.png)

**应该看什么。**

1. plain magnetic baseline 是否误差最大。
2. Lim-style branch-label baseline 是否有改善但仍不足。
3. local-identifiability model 是否进一步降低 held-out force MAE。
4. force 和 displacement 是否都能达到当前局部目标。

**关键定量结果。**

| model | F MAE (N) | d MAE (mm) | interpretation |
|---|---:|---:|---|
| plain magnetic ridge | 1.774 | 0.051 | 只用磁信号，force 误差大 |
| Lim-style branch-label ridge | 1.096 | 0.041 | 加 branch label 后有所改善 |
| APMD local-ID RF | 0.128 | 0.086 | force 最好，但 displacement 较差 |
| APMD local-ID ridge | 0.286 | 0.036 | force 和 displacement 最平衡 |

local-ID ridge 相比 Lim-style branch-label baseline 的 force MAE 改善为 `73.9%`。

**解释。**  
这个结果是目前最关键的模型层证据。它说明 APMD 不是只告诉模型“这是 loading 还是 unloading”，而是把主动路径对测得的局部响应方向转化为模型输入。相比单纯 branch label，这种局部几何特征能显著改善 force prediction，同时保持较好的 displacement prediction。

**支持的 claim。**  
local-identifiability 模型优于普通磁回归和 branch-label baseline。

**边界和限制。**  
当前模型是 local proof-of-mechanism model，不是最终 socket model。模型在当前 selected local work zone 内通过 held-out 验证，但还需要 cross-day、high-force、socket-like geometry 等进一步验证。

---

### 图组 6：Stage 7 控制实验图

**图的目的。**  
排除两个关键替代解释：第一，强磁响应是否只是 Mark-10 运动或环境磁漂造成的；第二，强磁响应是否只是 repeated loading 自然漂移造成的。

**数据/session 来源。**

Stage 7.1 no-contact motion artifact：

- session：`session_20260616_152850`
- 图：`decouple_data/session_20260616_152850/no_contact_motion_artifact.png`
- summary：`decouple_data/session_20260616_152850/no_contact_motion_artifact_pair_summary.csv`
- B0 summary：`decouple_data/session_20260616_152850/no_contact_motion_artifact_B0_summary.csv`

![Stage 7.1 no-contact motion artifact control](../decouple_data/session_20260616_152850/no_contact_motion_artifact.png)

Stage 7.2 repeated-loading control：

- session：`session_20260616_170608`
- 图：`decouple_data/session_20260616_170608/repeated_loading_control.png`
- summary：`decouple_data/session_20260616_170608/repeated_loading_control_summary.csv`

![Stage 7.2 repeated loading control](../decouple_data/session_20260616_170608/repeated_loading_control.png)

**应该看什么。**

1. 无接触运动时 `Delta Bvec` 是否接近主动路径对的 hundreds of uT 量级。
2. B0 drift 是否超过 artifact gate。
3. repeated loading 不经过 deeper preload 时，cycle-to-cycle magnetic change 是否能达到 active path-pair 的强响应。

**关键定量结果。**

Stage 7.1：

- no-contact motion `Delta Bvec = 1.29-2.03 uT`
- B0 drift `Delta Bvec = 3.37 uT`
- 均低于 `10 uT` artifact gate

Stage 7.2：

- repeated loading target `d = 3.40 mm`
- force stayed near `10.27-10.31 N`
- max cycle-to-cycle `Delta Bvec = 34.1 uT`
- 低于 `50 uT` low-memory control gate

**解释。**  
无接触运动伪差只有约 1-2 uT，远低于 active path-pair 中常见的 100-500 uT 磁分离。因此，强磁分离不能解释为设备运动或环境磁漂。repeated loading control 进一步说明，仅重复 loading branch 不足以产生强磁分离，deeper preload 和 return path 是关键激励。

**支持的 claim。**  
控制实验排除了运动伪差和简单重复 loading 两个主要替代解释。

**边界和限制。**  
Stage 7.1 和 7.2 是当前台架设置下的控制实验。若更换传感器、样品、磁体位置或 socket-like setup，需要重新做对应 artifact control。

---

## 3. Results 主线：从现象到模型

### 3.1 主动路径对可以构造控制变量下的强磁分离

Stage 3.1 和 Stage 3.2 是 APMD 机制的核心起点。它们不是普通重复实验，而是两组互补的控制变量实验：3.1 固定位移、改变路径导致力不同；3.2 固定力、改变路径导致位移不同。

在 Stage 3.1 中，21/21 same-d path pairs 均达到 strong。随着 target d 从 `2.40 mm` 增加到 `3.60 mm`，median `|Delta F|` 从 `0.432 N` 增加到 `1.587 N`，median `Delta Bvec` 从 `62.8 uT` 增强到深工作区的约 `200 uT` 以上。这说明主动路径可以把“同一位移对应不同力”这一软材料迟滞现象，转化成可测量的磁信号差异。

在 Stage 3.2 中，same-F/different-d 路径对在 `1.50-4.90 N` 范围内形成正式 accepted 数据。它说明同一目标力下，loading 和 unloading 路径可以对应不同位移，并产生强磁响应。这一点非常关键，因为如果只有 Stage 3.1，APMD 只能说明力方向可分；加入 Stage 3.2 后，APMD 才同时获得力相关和位移相关两个方向的控制变量证据。

### 3.2 preload depth/extra depth 是主要路径剂量变量

Stage 3.3-3.4 的作用是回答“这个强磁分离能不能调控”。如果强磁分离只是偶然漂移，那么改变 preload 条件不应该呈现稳定趋势。实验结果显示，改变最大历史压入深度比改变停留时间更有效。

在 same-d 条件下，target `d = 3.40 mm` 时，preload d 从 `3.60 mm` 增加到 `3.80 mm`，mean `Delta Bvec` 从 `166.3 uT` 增加到 `242.6 uT`。在 same-F 条件下，target `F = 3.75 N` 时，preload extra 从 `0.20 mm` 增加到 `0.40 mm`，median `Delta Bvec` 从 `287.6 uT` 增加到 `350.8 uT`。这些结果说明，材料经历过的最大压入深度是路径记忆强度的重要控制量。

相比之下，hold time 的影响较弱且不单调。same-d hold time 从 5 s 到 90 s 时，`Delta Bvec` 大致保持在 `236.9-251.1 uT`；same-F hold time 虽然在 5 s 条件下出现较大响应，但整体不表现为简单随时间增强。因此，当前数据更支持“preload depth/extra depth 是主剂量变量”，而不是“停留时间越长越好”。

### 3.3 路径记忆在恢复时间内保持存在

Stage 3.5 进一步检查路径记忆是否只是瞬时效应。恢复时间从 30 s 增加到 300 s 后，median `Delta Bvec` 从 `253.4 uT` 下降到 `230.5 uT`，有轻微衰减，但 9/9 pairs 仍然 strong。

这个结果对机制解释很重要。它说明路径历史不是采样瞬间的噪声，也不是刚刚卸载后才存在的短暂状态。至少在当前 30-300 s 的恢复窗口内，路径记忆仍然能形成可测量的磁响应差异。

### 3.4 `j_F/j_d` 局部响应方向具备可辨识性

Stage 4 把 Stage 3 的实验现象转成局部几何问题。same-d/different-F 提供力相关方向 `j_F`，same-F/different-d 提供位移相关方向 `j_d`。如果这两个方向在磁空间里几乎重合，那么即使信号很大，也不利于解耦；如果它们方向分开，模型就有可能把磁信号分解成力相关分量和位移相关分量。

Stage 4 的 strict primary candidate 是 `d = 3.40 mm / F = 4.90 N`，夹角 `48.5 deg`，scaled condition number `2.22`，min B/noise `22.8`。这说明当前局部工作区中 `j_F` 和 `j_d` 不是完全共线，而是存在可用于解耦的方向差异。

这个分析也解释了为什么后续模型不应该只使用 branch label。branch label 只能告诉模型“当前状态属于哪一条路径”，但 `j_F/j_d` 能告诉模型“力变化和位移变化分别在磁空间里朝哪个方向走”。这就是 APMD 与单纯迟滞标签补偿的关键区别。

### 3.5 local-identifiability 模型优于普通磁回归和 branch-label baseline

Stage 5-6 的模型结果把机制推进到 prediction 层面。Stage 5.2 的 grouped cross-validation 显示，plain magnetic ridge 的 `F MAE = 1.563 N`，加入 path label 后降到 `1.332 N`，加入 path memory 后进一步降到 `0.827 N`。这说明路径信息确实能改善模型，但还不能充分证明 `j_F/j_d` 局部几何的作用。

Stage 6.2 使用完整 held-out session 作为测试集，plain magnetic ridge 的 `F MAE = 1.774 N`，Lim-style branch-label ridge 降到 `1.096 N`，但 force 仍未达到原先 `0.50 N` 的目标。这个结果说明，只给模型 branch label 有帮助，但不够。

Stage 6.3 加入 local-identifiability features 后，APMD local-ID ridge 达到 `F MAE = 0.286 N` 和 `d MAE = 0.036 mm`。相对于 Lim-style branch-label baseline，force MAE 改善 `73.9%`。这说明 local `j_F/j_d` 几何不只是解释工具，而是能作为模型输入改善 held-out 解耦。

### 3.6 控制实验排除了运动伪差和简单 repeated loading

Stage 7 是让整条机制证据更可信的关键。Stage 7.1 表明，在无接触运动条件下，Mark-10 按类似路径移动产生的 `Delta Bvec` 只有 `1.29-2.03 uT`，B0 drift 也只有 `3.37 uT`。这远低于主动路径对中的 hundreds of uT 磁分离。

Stage 7.2 表明，在没有 deeper preload 的 repeated loading control 中，最大 cycle-to-cycle `Delta Bvec = 34.1 uT`，低于 `50 uT` gate，也远低于 active path-pair 的强响应。这个结果说明，仅仅重复 loading 到目标位置并不能复制 APMD 的强磁分离。

因此，Stage 7 支持一个重要结论：APMD 的主要信号不是设备运动伪差，也不是简单重复 loading 漂移，而是由 deeper preload 和 return path 构造出来的主动路径历史差异。

---

## 4. 综合 claim-evidence map

| Claim | Evidence | Status |
|---|---|---|
| 主动路径对可以在控制变量条件下构造可分辨磁状态 | Stage 3.1 中 21/21 same-d pairs strong；Stage 3.2 中 `1.50-4.90 N` same-F points accepted | 已支持 |
| preload depth/extra depth 是主要路径剂量变量 | 3.3A 和 3.4A 中更深 preload 带来更强响应；3.3B 和 3.4B 中 hold time 效果较弱或不单调 | 已支持 |
| 路径记忆在恢复时间内仍然存在 | 3.5 中 30/120/300 s recovery 后 9/9 pairs 仍 strong | 已支持 |
| `j_F/j_d` 局部响应方向具备可辨识性 | Stage 4 strict candidate angle `48.5 deg`，scaled condition `2.22`，min B/noise `22.8` | 局部支持 |
| local-identifiability model 优于 branch-label baseline | Stage 6.3 local-ID ridge `F MAE = 0.286 N`, `d MAE = 0.036 mm`，force MAE 比 Lim-style baseline 改善 `73.9%` | 局部支持 |
| 强磁响应不是无接触运动伪差 | Stage 7.1 no-contact `Delta Bvec <= 2.03 uT`，B0 drift `3.37 uT` | 已支持 |
| 强磁响应不是简单 repeated loading | Stage 7.2 repeated loading max `Delta Bvec = 34.1 uT`，低于 `50 uT` gate | 已支持 |
| 当前系统已解决 socket 全范围解耦 | 当前数据是 bench-top local work zone 数据，不覆盖 socket 全范围和高力复杂边界 | 尚不支持 |

---

## 5. 当前结论和建议写法

当前最稳妥的结论可以这样写：

APMD 在当前台架系统中已经完成了从现象、路径剂量、局部可辨识性、模型验证到控制实验的完整局部证据链。主动路径对能够在 near-matched displacement 和 near-matched force 两种控制变量条件下产生强磁分离；preload depth 和 preload extra depth 是主要路径剂量变量；路径记忆在 30-300 s recovery window 内仍然保持；由 same-d 和 same-F 路径对估计的 `j_F/j_d` 局部响应方向具备可辨识性；将这些局部几何特征加入模型后，local-identifiability model 在 held-out session 上显著优于 plain magnetic regression 和 Lim-style branch-label baseline；无接触运动和简单 repeated loading control 均不能解释 observed magnetic split。

但要避免这样写：

- “已经实现 prosthetic socket 全范围力-位移解耦”
- “该方法对所有材料和所有力范围都适用”
- “loading/unloading 标签已经被完全替代”
- “迟滞被完全消除”

更准确的表述是：

APMD does not remove hysteresis. It turns selected hysteretic path history into controlled excitation and uses the resulting local magnetic response geometry for decoupling.

对应中文是：

APMD 不是消除迟滞，而是主动构造可控路径历史，把迟滞导致的状态差异转化为可测量、可建模、可用于局部解耦的磁响应几何。

---

## 6. 后续工作建议

当前不建议继续盲目补大量重复数据。更合理的下一步是把现有证据组织成论文或汇报 Results 结构：

1. 完成最终 Stage 3-7 多面板证据图组。
2. 将 Stage 3.1 的正式数据重新生成最终 PNG 图，补齐 currently data-backed figure set。
3. 将 Stage 3.2、3.4、3.5、Stage 4、Stage 6.3、Stage 7 的现有图统一风格。
4. 写 Results section：
   - active path pairs create controlled magnetic separations；
   - path-dose controls response strength；
   - path memory persists after recovery；
   - local sensitivity directions support identifiability；
   - local-ID model improves held-out decoupling；
   - controls rule out motion artifact and repeated loading.
5. 只有当后续面向 socket 应用时，再增加：
   - cross-day repeatability；
   - larger socket-like force range；
   - different material/interface conditions；
   - socket-like geometry validation。

这条路线能保证汇报时的逻辑是闭合的：先证明现象，再证明可控，再证明可辨识，再证明模型有用，最后排除替代解释。
