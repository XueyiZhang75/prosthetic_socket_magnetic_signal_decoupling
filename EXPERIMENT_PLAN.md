# 磁解耦实验计划 v2：可辨识性驱动的 APMD

> 项目定位：Identifiability-guided magnetic decoupling of normal force and displacement in soft interfaces
> 更新日期：2026-06-02
> 本版整合：已完成的 A-P pilot 实验、Stage I+/J+ 惊喜发现、Stage O 盲测失败反思、SOCKET 聊天记录中的可行性分析，以及后续印章式 3D 打印压头的重做计划。

---

## 0. v2 主线

本项目不再被表述为一条 `B-F` 标定曲线，也不只是一个黑箱 `B -> [F, d]` 回归模型。v2 的核心贡献是一个实验框架：

```text
几何控制
  -> 路径激励
  -> same-d/different-F 与 same-F/different-d 状态对
  -> 局部 J=[j_F, j_d]
  -> κ / condition-number 可辨识图
  -> 解耦工作区
  -> 盲测反演
```

其中

```text
ΔB = j_F · ΔF + j_d · Δd
j_F = ∂B/∂F | d
j_d = ∂B/∂d | F
κ = |j_F^T j_d| / (||j_F|| ||j_d||)
```

我们要回答的问题不是“磁信号是否随压力变化”，而是：

> 在哪些几何、材料状态、路径激励和工作区内，三轴磁信号对 `F` 和 `d` 是局部可辨识的？

---

## 1. 当前数据如何处理

目前所有夹子式压头实验全部保留，但在 v2 中定位为 **pilot discovery**，不是最终 confirmatory 证据。

已知结论：

- Stage E/F/H 给出了基础 `F-d-B` 耦合曲线和探索性 Jacobian。
- 被动 Stage I/J 固定保持没有提供可靠 Jacobian 列；这不是失败，而是说明被动松弛/蠕变激励太弱。
- Stage I+ 已经证明 same-`d` / different-`F` 路径对可以产生可测 `ΔB`。
- Stage J+ 已经出现 usable/strong pair，证明 same-`F` / different-`d` 路径对有潜力。
- Stage O pilot blind test 当前 `NOT PASS`，说明现有夹子式压头、训练覆盖、几何重复性和局部模型还不足以支撑最终盲测。

后续换成印章式 3D 打印压头后，需要从 Stage A 到 Stage O 重新跑一遍 confirmatory 流程。旧数据用于设计实验、解释反思和展示发现过程；最终可辨识图和盲测性能以新压头数据为准。

---

## 2. 必须区分的三类信号来源

来自 PDF/聊天记录中的一个重要提醒：不能把柔性材料的坏特性直接美化成亮点。v2 实验必须区分三类来源。

### 2.1 电子/环境漂移

包括 MLX90393 零点漂移、温度、电源、环境磁场、线缆移动、电机扰动。它们通常与 loading/unloading 分支没有严格绑定。处理方式：每次正式实验前后做 no-contact B0，Stage B 记录环境和运动基线。

### 2.2 几何伪差

包括压头 lateral slip、tilt、contact drift、夹具松动、磁体姿态变化。磁场对几何极敏感，因此同一 `F` 或同一 `d` 下的 `ΔB` 可能只是几何变了。处理方式：印章式压头、同轴定位、重复接触几何检查、照片记录。

### 2.3 可控路径依赖

包括加载/卸载、预加载、松弛、蠕变带来的可重复材料状态差。只有这类信号可以作为系统辨识中的激励源。v2 的重点是把这类路径依赖变成可控、可重复、可量化的 same-`d`/different-`F` 和 same-`F`/different-`d` 状态对。

---

## 3. 硬件路线

### 3.1 Pilot：夹子式压头

当前夹子式压头数据保留为发现阶段。它已经帮助我们发现 I+/J+ 路径激励的价值，也暴露了几何重复性和盲测外推问题。

### 3.2 Confirmatory：印章式 3D 打印压头

新压头是 v2 的关键硬件升级，不是普通替换件。目标：

- 法向接触面积和接触中心固定。
- 压头、样品、磁体和 MLX90393 尽量同轴。
- 减少夹子式压头造成的横向滑移、倾斜和接触点漂移。
- 使 same-`d` 和 same-`F` 配对实验的几何条件更可重复。

换压头后必须重新执行 Stage A/B/C/D/E/F/G/I+/J+/N/O/P。旧 `F_max`、`d_max`、`B0`、Stage C 曲线、I+/J+ gate 不可直接沿用。

---

## 4. Pre-flight — 实验前准备与传感器标定

Pre-flight 是每一轮正式实验前的硬 gate。换压头、重新接线、更换放大器/Arduino 程序、移动力传感器、重新安装样品、或开始 stamp-head confirmatory run 时，都必须重新执行。

### 4.1 力传感器重新标定

**目的**：确保 `F_N` 标签可信。若力标签错了，I+/J+/O 的可辨识性结论都会失去意义。

**步骤**：

1. 力传感器、放大器、Arduino、串口程序和安装姿态全部固定后，预热 10-15 min。
2. 无载状态 tare，记录 tare raw 和环境条件。
3. 用砝码或标准载荷覆盖预计工作区，例如 `0, 25%, 50%, 75%, 100% F_max_expected`，上行/下行各 3 次。
4. 拟合 raw-to-N 转换，保存 slope/intercept、残差、R²、最大绝对误差和加载/卸载差异。
5. 标定系数在 Stage D 之前冻结；不能在看到 I+/J+/O 或 blind 误差后重新调标定。

**建议合格标准**：

- 线性拟合 R² 接近 1。
- 最大残差小于 `max(0.03 N, 2% working F range)`。
- 上行/下行 hysteresis 小于 `0.05 N` 或显著小于 I+/J+ 的目标 `ΔF`。
- 零点 5 min 漂移小于 `0.02-0.03 N`。

**输出**：

```text
force_calibration_<date>.csv
force_calibration_<date>.png
force_calibration_id
tare_raw
raw_to_N_coefficients
```

### 4.2 位移与接触零点检查

- 确认 Mark-10 位移方向：压下时 `d>0`。
- 做 1 mm 或 0.5 mm 小步移动检查，确认脚本记录的 `d_actual_mm` 与测试台显示一致。
- 在正式 Stage D 前，重复 3-5 次轻触，确认接触点 `d=0` 的漂移。
- 保存 `displacement_zero_id` 或当天接触点定义记录。

### 4.3 磁传感器与串口检查

- 确认 MLX90393 preset：静态用 `low_noise`，动态用 `fast`，禁用 `fastest`。
- 记录 MLX、force Arduino、Mark-10 串口号和开机 banner。
- 做 30-60 s no-contact B0 quick check。
- 轻微改变磁体距离，确认三轴 B 有合理响应。

### 4.4 元数据与干跑

正式实验前必须记录：

```text
head_id, sample_id, magnet_id, force_calibration_id,
displacement_zero_id, operator, date, room condition,
F_max_expected, d_max_expected, preload plan, rest-time plan
```

建议先做一次不保存为正式数据的 dry run，确认限位、急停、文件命名、数据列和脚本输出正常。

---

## 5. 统一坐标与数据约定

- `F`：法向压缩力，单位 N，`F>0` 表示压缩。
- `d`：从接触点开始的压缩位移，单位 mm，`d>0` 表示压入。
- `q`：磁体与传感器之间的轴向间隙；在压缩实验中通常与 `d` 反向变化。
- `B=(Bx, By, Bz)`，单位 µT。
- `B0`：同一装置、同一 session 中 no-contact 基线。
- `ΔB=B-B0`。

所有正式数据至少保留：

```text
time_s, session_id, stage, phase, path_mode, control_mode,
F_N, d_mm, q_mm,
Bx_uT, By_uT, Bz_uT,
delta_Bx_uT, delta_By_uT, delta_Bz_uT, Bmag_uT,
sample_id, magnet_id, head_id, force_calibration_id,
displacement_zero_id, repeat_id, note
```

新增 `head_id` 用于区分夹子式压头和印章式压头。

---

## 6. 阶段总览

```text
Pre-flight 力/位移/磁信号标定
  -> A 几何装置与压头控制
  -> B 噪声/B0/漂移/运动基线
  -> C 工作区内纯位移 B(q)
  -> D 接触点、安全范围、预循环
  -> E 单调 loading baseline
  -> F loading/unloading 路径分离
  -> G 重复性与路径稳定性
  -> X1 几何伪差检查
  -> X2 路径恢复/记忆清除
  -> X3 预加载强度扫描
  -> I/J 被动保持诊断
  -> I+ same-d/different-F 主实验
  -> J+ same-F/different-d 主实验
  -> L 路径激励矩阵
  -> N 可辨识图与工作区判定
  -> O1/O2 盲测
  -> P APMD 建模与对照
```

Stage H/K/M 不删除，但在 v2 中后移或降级：

- Stage H 力控 B-F：可选辅助，不阻塞主线。
- Stage K 速度影响：I+/J+/O2 跑通后再做。
- Stage M 偏载/横向位置：作为 future extension，第一版 confirmatory 不引入。

---

## Stage A — 几何装置与压头控制

**目的**：建立可重复的法向接触几何。

**必须记录**：

- `head_id`：clip_head 或 stamp_head_v1。
- `force_calibration_id` 与 `displacement_zero_id`。
- 压头接触面尺寸、材料、3D 打印方向。
- 样品、磁体、MLX90393 的相对位置。
- 接触点定义方式。
- 正视/侧视照片。

**新增合格标准**：

- 连续 5 次轻触接触点，`d=0` 的位置漂移小于 0.03-0.05 mm。
- 无明显侧向滑移、压头旋转、夹具松动。

---

## Stage B — 噪声、B0、漂移与运动基线

**保留并强化。**

每次正式 session 前后都记录：

- no magnet baseline。
- magnet no-contact B0。
- Mark-10/stage motion no-contact baseline。
- 实验结束后的 no-contact B0 复测。

**用途**：

- 判断电子/环境漂移。
- 判断电机或线缆运动是否引入磁扰动。
- 避免把 B0 drift 当成路径依赖信号。

---

## Stage C — 工作区内纯位移 B(q)

**修改重点**：旧远场 Stage C 只能作为流程证据。新压头下必须重做工作区内纯位移。

**目的**：

- 得到 `F≈0` 或低耦合条件下的 `B(q)`。
- 给 `j_d` 提供几何先验。
- 作为 J+/APMD 的对照，而不是最终解耦证据。

**建议设计**：

- 在预计压缩工作区附近加密采样，例如覆盖对应 `d≈3.5-5.0 mm` 的 q 范围。
- 小步长 0.05-0.10 mm，至少 3 次重复。
- 记录上行/下行，判断纯几何位移是否有明显迟滞。

**合格标准**：

- 至少一轴或 `|B|` 对 q 有稳定响应。
- 重复误差显著小于后续 I+/J+ 的 `ΔB`。

---

## Stage D — 接触点、安全范围与预循环

**保留并严格化。**

**目的**：

- 定义 `d=0`。
- 得到 conservative `F_max` 和 `d_max`。
- 决定预循环次数。

**v2 要求**：

- Pre-flight 力传感器标定必须已经通过，`force_calibration_id` 写入 session log。
- Stage D/E/F/I+/J+/O 必须在同一套装置、同一压头、同一接触定义下执行。
- 所有后续加载不得超过 D 给出的 conservative limit。
- 新样品或新压头先做 10-20 次预循环，直到 `F-d` 回线基本稳定。

---

## Stage E — 单调 loading baseline

**保留，但降级为 baseline。**

Stage E 不用于证明解耦。它用于回答：

- 单一路径下 `F` 与 `d` 是否高度相关？
- `B-F` 是否只是 `d` 增大导致的投影？
- 后续 APMD 是否真的优于 `F=h(d)` 和 `d=g(|B|)`？

**建议设计**：

- 在安全范围内取 8-12 个 `d` plateau。
- 重复 3-5 次。
- 每次前后记录 B0。

---

## Stage F — loading/unloading 路径分离

**保留并升级为第一类路径证据。**

**目的**：

- 从自然迟滞中寻找 same-`d` / different-`F` 点。
- 初步筛选哪些 `d` 区域路径分离最大。

**输出**：

- loading/unloading `F-d` 回线。
- loading/unloading `B-d` 和 `B-F` 回线。
- matched same-`d` pairs：`ΔF(d)`、`ΔB(d)`、方向一致性。

这些结果进入 Stage N 的 preliminary map。

---

## Stage G — 重复性与路径稳定性

**保留，但目标改为路径依赖是否可重复。**

**目的**：

- 判断材料是否已被预处理到稳定状态。
- 判断 loading/unloading 路径差异是否可重复。

**合格标准**：

- 连续 5 个循环中回线形状不持续漂移。
- I+/J+ 目标工作区附近的 `F-d-B` 关系稳定。
- 若第 1 次和第 5 次差异大，则增加预循环或延长恢复时间。

---

## Stage X1 — 几何伪差检查（新增）

**目的**：判断同一法向目标下 B 的变化是否来自几何伪差。

**设计**：

- 选择 1-2 个低风险 `d` target。
- 每个 target 重复接触/卸载/再接触 5 次。
- 尽量保持同一 `d` 和同一路径，不引入预加载。

**判定**：

- 若 `F` 和 `d` 接近但 `B` 大幅跳变，说明压头/样品/磁体几何重复性不足。
- 若印章式压头显著降低该误差，说明硬件升级有效。

---

## Stage X2 — 路径恢复与记忆清除（新增）

**目的**：定义 trial 之间需要休息多久，避免前一轮预加载污染后一轮。

**设计**：

- 预加载到固定深度。
- 释放后等待 10 s、30 s、60 s、120 s。
- 回到同一目标 `d` 或 `F`，记录 `F,d,B` 是否恢复。

**输出**：

- recovery time constant。
- 后续 I+/J+/O 的最短 `INTER_TARGET_REST_S`。

---

## Stage X3 — 预加载强度扫描（新增）

**目的**：找到既能制造足够路径差异、又不破坏几何稳定性的 preload。

**设计**：

在同一目标点附近扫描 preload：

```text
preload depth = target d + 0.2, +0.4, +0.6 mm
```

或用安全范围的比例表示：

```text
preload = 70%, 85%, 95% of d_max
```

**输出**：

- `ΔF` 是否随 preload 增加。
- `Δd` 是否随 preload 增加。
- `ΔB` 是否稳定增加。
- 是否出现 slip、force cap 或不可逆漂移。

X3 的结果决定 I+/J+/O 的 preload 设置。

---

## Stage H — 力控 B-F（可选辅助）

Stage H 不再作为核心 gate。若力控稳定，它可以补充 same-`F` 状态；若力控不稳定，不阻塞主线。

保留用途：

- 对照 displacement-control 与 force-control 的差异。
- 检查 `B-F` 是否受路径和 `d` 强烈影响。

---

## Stage I — 被动固定位移保持（诊断）

**保留为负结果和诊断。**

旧实验显示：固定 `d` 等待力松弛时，`F` 的变化不足以产生稳定、线性的 `B-F` 关系。

v2 解释：

- 被动松弛激励太弱。
- 单纯等待不能可靠估计 `j_F`。
- 因此需要 Stage I+ 主动路径激励。

后续可少量重复，但不作为主要验收门槛。

---

## Stage I+ — same-d / different-F 主实验

**升为核心实验。**

**目的**：估计 `j_F = ∂B/∂F | d`。

**路径**：

```text
direct loading 到目标 d
  -> 记录状态 A
preload 到更深 d
  -> unloading 回到同一目标 d
  -> 记录状态 B
比较 A/B：same d, different F, different B
```

**建议设计**：

- 目标 `d` 不只 4.30 mm，应覆盖 3-4 个工作点，例如按新安全范围选 `40%, 55%, 70%, 85% d_max`。
- 每个 `d` 至少 5 个 usable pair。
- preload 深度由 X3 决定。

**合格标准**：

- `|Δd| <= 0.03-0.05 mm`。
- `|ΔF| >= 0.2 N` 或大于该工作区力噪声的 5 倍。
- `|ΔB3| >= max(3σ_dynamic, 30 µT)`。
- `ΔB/ΔF` 方向在重复间基本一致。

---

## Stage J — 被动固定力保持（诊断）

**保留为负结果和诊断。**

旧实验显示：固定力保持/蠕变控制在软样品上不稳定，难以直接估计 `j_d`。

v2 解释：

- 被动 force-hold 不可靠。
- 直接等待 creep 不足以构成主证据。
- 因此需要 Stage J+ 路径配对和插值匹配。

---

## Stage J+ — same-F / different-d 主实验

**升为核心实验。**

**目的**：估计 `j_d = ∂B/∂d | F`。

**路径**：

```text
loading 路径经过目标 F
  -> 记录/插值得到状态 A
preload 到更深状态
  -> unloading 路径回到同一目标 F
  -> 记录/插值得到状态 B
比较 A/B：same F, different d, different B
```

**关键修改**：

不要依赖测试台刚好停在同一个 `F`。应尽量记录 loading/unloading 附近的连续数据，并在分析中插值到同一 `F_match`。

**合格标准**：

- 优先 `|ΔF| <= 0.05 N`，可接受上限 `<=0.08 N`。
- `|Δd| >= 0.15-0.20 mm`。
- `|ΔB3| >= max(3σ_dynamic, 30 µT)`。
- 若仍有残余 `ΔF`，用 I+ 的 `j_F` 修正：

```text
ΔB_corr = ΔB_Jplus - j_F · ΔF
j_d = ΔB_corr / Δd
```

---

## Stage K — 加载速度影响（后移）

Stage K 不作为第一轮 confirmatory 必做项。等 I+/J+/O2 跑通后，再检查不同速度是否改变路径依赖。

若速度影响显著：

- 后续实验固定速度。
- 或把 loading rate / path age 加入模型输入。

---

## Stage L — 路径激励矩阵

**重写。**

旧 L 是“多深度/多样本填二维网格”。v2 改为系统化路径激励矩阵：

```text
d target × preload depth × path mode × repeat
```

推荐最小矩阵：

- 3-4 个 `d target`。
- 2 个 preload depth。
- loading 与 unloading 两条路径。
- 每格 5 次重复。

**目的**：

- 扩大 same-`d` / same-`F` 可配对区域。
- 找出 `j_F` 和 `j_d` 方向分离最大的 green zone。
- 不是盲目铺满整个 `(F,d)` 平面，而是围绕可辨识性优化采样。

---

## Stage M — 偏载/横向位置（future extension）

Stage M 暂时从第一版 confirmatory 主线中移出。偏载会引入横向位移和姿态伪差，容易掩盖法向力-位移解耦主问题。

只有当中心法向 green zone 和 O2 盲测通过后，再考虑：

- socket 曲面。
- 偏载。
- 剪切/横向力。
- 多 taxel 阵列。

---

## Stage N — 可辨识图与工作区判定

**Stage N 是 v2 的核心分析。**

输出不只是一个 readiness verdict，而是：

- `j_F(d,F)` map。
- `j_d(d,F)` map。
- `angle(j_F, j_d)` map。
- condition-number map。
- `κ` heatmap。
- green/yellow/red work-zone map。

**建议判定**：

- Green：两列信号都高于噪声，夹角足够大，condition number 可接受，重复性稳定。
- Yellow：有部分可辨识证据，但 pair 数不足、夹角偏小或重复性一般。
- Red：两列近共线、信号弱、几何伪差大或模型外推。

只有 green zone 允许进入 O2 confirmatory blind test。

---

## Stage O — O1/O2 盲测

### O1：Pilot blind test

当前夹子式压头下的盲测属于 O1。它允许失败，作用是暴露问题。

当前结论：

- `Bxyz -> [F,d]` 未能 beat 单变量 baseline。
- 说明当前几何、训练覆盖和局部模型不足。
- 这个结果保留在 `reports/BLIND_TEST_ANALYSIS.md`，不手动覆盖。

### O2：Confirmatory blind test

印章式压头和 Stage N green zone 确定后再做。

规则：

- 盲测点必须提前在 green zone 内随机或半随机选定。
- 盲测 session 不参与归一化、模型选择、调参或工作区选择。
- loading/unloading 状态都要覆盖。
- 至少 10-20 个 blind state points。
- 结果必须同时对比 `F=h(d)`、`d=g(|B|)`、mean baseline 和 APMD。

---

## Stage P — APMD 建模

模型阶梯保留，但 v2 要防止过早黑箱化。

### Baselines

1. `F_hat = h(d)`：机械位移基线。
2. `d_hat = g(|B|)`：磁幅值位移基线。
3. `[F_hat, d_hat] = f(Bx,By,Bz)`：普通多输出线性/岭回归。

### APMD 主模型

1. 用 Stage C 给出几何位移先验。
2. 用 I+/J+ 或 L 的局部状态对估计 `J=[j_F, j_d]`。
3. 在 green zone 内做局部反演：

```text
[ΔF, Δd]^T = (J^T W J + λI)^-1 J^T W ΔB
```

4. 用 O2 盲测验证是否同时优于单变量 baselines。

**成功标准**：

- O2 中 `F` MAE 优于 `F=h(d)`。
- O2 中 `d` MAE 优于 `d=g(|B|)`。
- 误差只在预定义 green zone 内报告，不外推到未验证区域。

---

## 6. 最小可执行 confirmatory 流程

换印章式压头后，如果时间紧，最小流程是：

```text
Pre-flight -> A -> B -> C -> D -> E -> F -> G -> X1 -> X2/X3 -> I+ -> J+ -> N -> O2 -> P
```

可暂缓：

```text
H, K, M, 多样本扩展
```

---

## 7. 最终图表清单

1. 装置和印章式压头图。
2. B0/no-contact/stage-motion baseline。
3. 工作区内纯位移 `B(q)`。
4. `F-d` loading/unloading 回线。
5. Stage F matched same-`d` / different-`F` 图。
6. Stage I+ same-`d` / different-`F` pair 图。
7. Stage J+ same-`F` / different-`d` pair 图。
8. `j_F` 与 `j_d` 三维向量夹角图。
9. `κ` / condition-number heatmap。
10. Green/yellow/red decoupling work-zone map。
11. O2 blind predicted-vs-true `F` 和 `d`。
12. Baseline vs APMD 误差对比。

---

## 8. 一句话总结

v2 的实验目标是：在严格控制几何伪差和环境漂移的前提下，主动利用柔性材料的可重复路径依赖制造可辨识激励，找到磁信号能够同时解耦法向力 `F` 和相对位移 `d` 的工作区。
