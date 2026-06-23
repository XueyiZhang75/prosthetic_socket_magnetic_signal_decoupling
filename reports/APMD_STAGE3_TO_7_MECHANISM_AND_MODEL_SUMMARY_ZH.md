# APMD Stage 3-7 机制证据与 Stage 5-6 模型结果中文汇总

## 一句话核心论点

在当前台架式磁触觉实验系统中，主动构造路径对可以把软材料的迟滞、预压历史和恢复效应从传统意义上的误差来源，转化为可控制、可测量的局部磁响应方向；进一步地，这种由主动路径对得到的局部灵敏度几何信息，可以比普通磁回归和简单 loading/unloading 标签补偿更有效地支持力和位移解耦。

## 术语表

| 术语 | 在本项目中的含义 |
|---|---|
| APMD | Active Path-Pair Magnetic Decoupling，主动路径对磁解耦 |
| same-d/different-F 路径对 | direct-loading 和 return-unloading 两个状态在近似相同位移下记录，但对应不同力 |
| same-F/different-d 路径对 | loading 和 unloading 两个状态在近似相同力下记录，但对应不同位移 |
| path-dose | 对 preload depth、preload extra depth、preload hold time、recovery time 等路径激励强度进行控制 |
| local identifiability | 局部范围内，力相关磁响应方向和位移相关磁响应方向是否足够分开，从而具备解耦基础 |
| `j_F` | 由 same-d/different-F 路径对估计得到的局部磁响应方向，即力相关灵敏度方向 |
| `j_d` | 由 same-F/different-d 路径对估计得到的局部磁响应方向，即位移相关灵敏度方向 |
| held-out session | 完整排除在训练集之外、只用于模型测试的实验 session |

---

## Stage 3：主动路径对机制证据

Stage 3 的核心目的不是直接建立最终模型，而是证明主动路径对确实能构造出可分辨的磁信号状态。换句话说，它回答的是：软材料迟滞和路径历史是否真的可以作为一种可控激励，而不只是误差。

### 3.1 same-d/different-F 工作区扫描

**实验目的。**  
验证主动 preload-return 路径是否能在近似相同位移下产生不同力状态，并且这种不同力状态是否对应可重复的磁信号差异。

**正式数据。**

- 3.1A：`session_20260610_091145`，目标位移为 `2.40/2.60/2.80 mm`。
- 3.1B：`session_20260610_104017`，目标位移为 `3.00/3.20/3.40/3.60 mm`。
- 总共 21 组路径对，全部通过 same-d gate 和 strong magnetic gate。

**关键结果。**

| target d (mm) | median abs(Delta F) (N) | median Delta Bvec (uT) | 判定 |
|---:|---:|---:|---|
| 2.40 | 0.432 | 62.8 | strong |
| 2.60 | 0.515 | 110.2 | strong |
| 2.80 | 0.698 | 103.4 | strong |
| 3.00 | 0.814 | 155.4 | strong |
| 3.20 | 0.973 | 200.6 | strong |
| 3.40 | 1.183 | 227.8 | strong |
| 3.60 | 1.587 | 207.3 | strong |

**结论解释。**  
在相同命令位移下，仅仅改变材料经历的路径历史，就可以产生明显的力差异和磁信号差异。随着工作区从浅压入变到深压入，路径诱导的力差异和磁差异整体增强，其中 `d = 3.20-3.40 mm` 是当前系统中比较合适的局部工作区。

### 3.2 same-F/different-d 工作区扫描

**实验目的。**  
验证相反的控制变量情况：在近似相同力下，主动路径是否能产生不同位移状态，并且磁信号是否能区分这种位移状态。

**正式数据。**

- 接受的目标力点为 `1.50/1.80/2.50/3.20/3.75/4.30/4.90 N`。
- 每个力点都有 3 组正式可用路径对。
- `5.50 N` 不作为当前正式轮次的必要点。

**关键结果。**

- 已接受的所有路径对都满足 same-F gate。
- 位移差异通常在 `0.11-0.16 mm` 左右。
- 整个力范围内磁分离都比较强，代表性 Delta Bvec 大约在 `313-458 uT`。
- 磁响应主要由 `dBy` 和 `dBz` 主导，`dBx` 相对较小。

**结论解释。**  
3.2 和 3.1 是互补证据。3.1 证明了相同位移下可以构造不同力状态，3.2 证明了相同力下可以构造不同位移状态。因此，主动路径对不是只对某一个变量有效，而是可以在两个控制变量设计中分别构造出可分辨的磁响应。

### 3.3 same-d 路径剂量实验

**实验目的。**  
进一步回答 same-d/different-F 效应是否可控：如果改变 preload depth 或 preload hold time，路径诱导的力差异和磁差异是否会系统变化。

**3.3A：preload depth 剂量效应。**

在 target `d = 3.40 mm` 下，preload 从 `3.60 mm` 增加到 `3.80 mm` 时，路径诱导的力差和磁差整体增强：

| preload d (mm) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 3.60 | 1.004 | 166.3 |
| 3.70 | 1.284 | 205.8 |
| 3.80 | 1.519 | 242.6 |

**3.3B：preload hold time 剂量效应。**

在 target `d = 3.40 mm`、preload `d = 3.80 mm` 下，改变 hold time 的影响较弱，而且不是单调变化：

| preload hold (s) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 1.527 | 251.1 |
| 30 | 1.590 | 236.9 |
| 90 | 1.623 | 241.1 |

**结论解释。**  
对于 same-d 路径对来说，最大历史压入深度是更强的路径剂量变量；单纯延长 preload 保持时间并不能显著增强解耦所需的磁响应。

### 3.4 same-F 路径剂量实验

**实验目的。**  
进一步回答 same-F/different-d 效应是否可控：改变 preload extra depth 或 preload hold time 后，近似同力下的位移差和磁差是否会变化。

**3.4A：preload extra depth 剂量效应。**

在 target `F = 3.75 N` 下，preload extra depth 增大后，same-F 位移分离更可靠，磁分离整体更强：

| preload extra (mm) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 0.20 | 0.10 | 287.6 |
| 0.30 | 0.10 | 308.8 |
| 0.40 | 0.13 | 350.8 |

**3.4B：preload hold time 剂量效应。**

在 target `F = 3.75 N`、preload extra `+0.40 mm` 下，hold time 的影响同样有限且非单调：

| preload hold (s) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 0.20 | 550.1 |
| 30 | 0.12 | 347.8 |
| 90 | 0.14 | 392.5 |

**结论解释。**  
same-F 路径对也说明，真正决定路径激励强度的主要因素是路径进入 preload state 的深度，而不是简单保持时间。也就是说，主动路径激励的核心不是“等多久”，而是“走到多深的历史状态”。

### 3.5 recovery-time 路径记忆衰减实验

**实验目的。**  
验证主动路径记忆是否会随着恢复时间消失。如果恢复 30/120/300 s 后效应仍然存在，说明路径记忆不是瞬时噪声或短暂扰动。

**正式数据。**

- `session_20260614_201905`。
- target `d = 3.40 mm`，preload `d = 3.80 mm`。
- recovery-before-pair 为 `30/120/300 s`。
- 9/9 路径对仍然判定为 strong。

| recovery time (s) | median abs(Delta F) (N) | median Delta Bvec (uT) |
|---:|---:|---:|
| 30 | 2.125 | 253.4 |
| 120 | 2.077 | 240.7 |
| 300 | 2.067 | 230.5 |

**结论解释。**  
恢复时间会让磁分离略微下降，但不会消除主动路径对效应。这说明路径记忆在测试时间尺度内是稳定存在的，而不是立刻消失的瞬态效应。

---

## Stage 4：局部可辨识性分析

**实验目的。**  
Stage 4 的作用是把 Stage 3 中的现象证据转化为局部灵敏度几何。也就是说，不只是说“磁信号变了”，而是进一步判断：力相关磁响应方向和位移相关磁响应方向是否足够分开，从而具备解耦基础。

**分析方法。**

- 用 same-d/different-F 路径对估计 `j_F = Delta B / abs(Delta F)`。
- 用 same-F/different-d 路径对估计 `j_d = Delta B / abs(Delta d)`。
- 计算 `j_F` 和 `j_d` 两个磁响应方向之间的夹角。
- 夹角越大，说明两个方向越不共线，力和位移对磁信号的贡献越容易被区分。
- scaled condition number 用于衡量两个方向的病态程度，数值越低通常越有利于稳定解耦。

**关键结果。**

- 严格主候选组合：same-d `d = 3.40 mm` 与 same-F `F = 4.90 N`。
- 灵敏度夹角：`48.5 deg`。
- scaled condition number：`2.22`。
- 最小磁信噪比：`22.8`。
- 实用备选组合：`d = 3.20 mm`、`F = 4.90 N`，夹角 `41.9 deg`。

**结论解释。**  
Stage 4 并不是要证明全范围 socket 应用已经可行，而是证明在当前台架系统的局部工作区内，主动路径对确实可以提供两个相对分开的磁响应方向。这个结果是后续做局部解耦模型的基础。

---

## Stage 5：模型数据集与局部 baseline 模型

### 5.0 模型数据集整理

**目的。**  
把正式接受的 Stage 3 路径对数据，以及 Stage 5.1B 采集的 dense-loop 数据，整理成 state-level 和 pair-level 数据集，用于模型训练和验证。

**数据规模。**

- 接受的路径对：`87`。
- state summary：`411`。
- unique sessions：`31`。
- local minor-loop dense states：两个 session 共 `150` 个状态。
- dense local d grid：`[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8]`。

**结论解释。**  
这些数据已经足够做局部机制验证模型，但还不足以支持 socket 全范围部署模型。

### 5.2 grouped cross-validation baseline

**验证方式。**  
按 `session_id` 做 grouped cross-validation，同一个 session 的数据不会同时出现在训练集和验证集中。这比随机拆分更严格，因为它避免了同一次实验内部数据泄漏。

**测试的模型。**

- plain magnetic ridge：只用磁信号 `B -> F,d`。
- path-label ridge：磁信号加路径标签，例如 loading、unloading、preload。
- path-memory ridge：磁信号加路径标签、实验协议、历史状态等路径记忆特征。
- path-memory random forest：path-memory 模型的非线性版本。

**关键结果。**

| 模型 | F MAE (N) | d MAE (mm) | 含义 |
|---|---:|---:|---|
| plain magnetic ridge | 1.563 | 0.105 | 普通磁回归 baseline |
| path-label ridge | 1.332 | 0.092 | 路径标签有一定帮助 |
| path-memory ridge | 0.827 | 0.091 | Stage 5.2 中综合最平衡 |
| path-memory RF | 0.695 | 0.150 | force 最好，但 displacement 较差 |

**结论解释。**  
加入路径信息后，模型比只用磁信号更好，尤其是力预测明显改善。但 Stage 5.2 还只是内部交叉验证，不是最终 held-out 验证。

### 5.3 dense-loop cross-session 验证

**目的。**  
测试局部 dense-loop 模型是否能在两个独立采集的 dense-loop session 之间迁移。

**数据。**

- dense-loop sessions：`session_20260615_112044` 和 `session_20260615_143640`。
- dense-loop states 总数：`150`。
- 验证方式：用一个 dense-loop session 训练，另一个 session 测试，然后反向再做一次。

**关键结果。**

| 模型 | F MAE (N) | d MAE (mm) |
|---|---:|---:|
| dense plain magnetic ridge | 0.991 | 0.035 |
| dense path-memory ridge | 0.413 | 0.023 |
| dense plain magnetic RF | 0.741 | 0.056 |
| dense path-memory RF | 0.323 | 0.039 |

**结论解释。**  
在局部 dense-loop 数据中，path-memory 特征明显提升跨 session 预测能力。Ridge 对位移更稳定，random forest 对力更好。

---

## Stage 6：held-out 验证与 local-identifiability 模型

### 6.1 held-out dense-loop 数据采集

**目的。**  
采集一个完全不进入训练集的独立 dense-loop session，用来测试模型和机制是否能泛化到新的插值点。

**正式数据。**

- held-out session：`session_20260615_160438`。
- states：`39`。
- held-out d grid：`[3.05, 3.15, 3.25, 3.35, 3.45, 3.55]`。
- same-d-like pairs：`18/18`。
- force-split pairs：`18/18`。
- magnetic-split pairs：`18/18`。
- median abs(Delta F)：`2.543 N`。
- median Delta Bvec：`265.8 uT`。

**结论解释。**  
主动路径对机制在插值的 held-out d grid 上仍然很强，说明现象不是只存在于训练时测过的固定点上。

### 6.2 标准 held-out 模型验证

**目的。**  
用 Stage 5 数据训练模型，然后用完整的 Stage 6.1 held-out session 测试模型。

**关键结果。**

| 模型 | F MAE (N) | d MAE (mm) | 解释 |
|---|---:|---:|---|
| plain magnetic ridge | 1.774 | 0.051 | 普通磁信号 baseline |
| path-label ridge | 1.096 | 0.041 | 标准 held-out 中综合最好 |
| path-memory RF | 1.021 | 0.071 | force 最好 |

**结论解释。**  
路径标签和路径记忆模型比普通磁回归更好，但 force MAE 仍没有达到原先 `0.50 N` 的目标。这说明单纯加 label 或一般路径记忆还不够，因此需要进一步把 Stage 4 的局部灵敏度几何真正放进模型里。

### 6.3 APMD local-identifiability 模型对比

**目的。**  
测试 Stage 4 得到的 `j_F/j_d` 局部灵敏度几何，是否能比简单 loading/unloading/preload 标签提供更多有用信息。

**对比模型。**

- plain magnetic ridge：只用磁信号。
- Lim-style branch-label ridge：磁信号加 branch label，可理解为文献中较常见的迟滞标签补偿方式。
- APMD path-memory models：磁信号加路径历史和实验协议特征。
- APMD local-identifiability models：在 path-memory 基础上加入 Stage 4 的 `j_F/j_d` 投影坐标和局部工作区信息。

**关键结果。**

| 模型 | F MAE (N) | d MAE (mm) | 状态 |
|---|---:|---:|---|
| plain magnetic ridge | 1.774 | 0.051 | 弱 baseline |
| Lim-style branch-label ridge | 1.096 | 0.041 | 标签补偿 baseline |
| APMD local-ID RF | 0.128 | 0.086 | force 最好 |
| APMD local-ID ridge | 0.286 | 0.036 | 综合最平衡 |

**核心结论。**  
APMD local-identifiability ridge 相比 Lim-style branch-label baseline，把 force MAE 降低了 `73.9%`，同时 displacement MAE 达到 `0.036 mm`。这是目前最强的模型层证据：我们的优势不只是给 loading/unloading 贴标签，而是把主动路径对测得的局部响应方向作为几何信息用于解耦。

---

## Stage 7：机制对照实验

### 7.1 无接触运动伪差对照

**目的。**  
排除 Mark-10 运动、电机、电子系统、环境磁场漂移等无接触因素造成磁信号差异的可能性。

**正式数据。**

- session：`session_20260616_152850`。
- 无接触复现路径：名义路径 `3.40 -> 3.80 -> 3.40 mm`。
- 共 3 次 trials。

**关键结果。**

- no-contact motion Delta Bvec：`1.29-2.03 uT`。
- B0 drift Delta Bvec：`3.37 uT`。
- 两者都低于 `10 uT` artifact gate。

**结论解释。**  
主动路径对实验中的磁分离通常是几百 uT，而无接触运动伪差只有约 1-2 uT。因此，强磁分离不能由无接触运动或环境漂移解释。

### 7.2 无 deeper preload 的 repeated-loading 对照

**目的。**  
测试重复 loading 到同一个 target state 是否也能产生类似主动路径对的强磁变化。如果不能，则说明 deeper preload 和 return path 是必要激励。

**正式数据。**

- session：`session_20260616_170608`。
- target `d = 3.40 mm`。
- 5 个 repeated loading cycles。
- 不使用 deeper preload。

**关键结果。**

- 固定 target position 在各个 cycle 中保持一致。
- 力保持在约 `10.27-10.31 N`。
- 相对于 cycle 1 的最大 cycle-to-cycle Delta Bvec 为 `34.1 uT`。
- 所有 cycles 都通过 `50 uT` low-memory control gate。

**结论解释。**  
单纯重复 loading 分支无法复现主动路径对中的强磁分离。因此，强磁分离不是“重复压几次自然就会发生”，而是需要 deeper preload 和 return path 共同构造的主动路径历史。

---

## 综合 Claim-Evidence Map

| 主张 | 证据 | 状态 |
|---|---|---|
| 主动路径对可以在控制变量条件下构造可分辨磁状态。 | Stage 3.1 中 21/21 same-d pairs strong；Stage 3.2 中 1.50-4.90 N same-F pairs strong。 | 已支持 |
| 最大历史压入深度比保持时间更能控制路径剂量。 | 3.3A 和 3.4A 中 preload depth/extra depth 增加时响应增强；3.3B 和 3.4B 中 hold-time 效应弱且非单调。 | 已支持 |
| 路径记忆在测试恢复时间范围内不会消失。 | 3.5A 中 recovery 30/120/300 s 后仍然 strong，Delta Bvec 仅从 253.4 uT 缓慢降到 230.5 uT。 | 已支持 |
| 局部磁响应方向可用于解耦。 | Stage 4 中 `j_F/j_d` 候选组合夹角 48.5 deg，scaled condition 2.22。 | 局部支持 |
| local-identifiability 特征优于简单 branch-label 补偿。 | Stage 6.3 中 local-ID ridge 相比 Lim-style baseline force MAE 改善 73.9%，同时 d MAE 为 0.036 mm。 | 局部支持 |
| 强磁分离不是运动伪差。 | Stage 7.1 无接触 Delta Bvec 不超过 2.03 uT，B0 drift 为 3.37 uT，远小于主动路径对响应。 | 已支持 |
| 强磁分离不是简单重复 loading 导致的。 | Stage 7.2 repeated loading 最大 Delta Bvec 为 34.1 uT，低于 50 uT gate，也远小于主动路径对响应。 | 已支持 |
| 当前方法已经可以直接用于 prosthetic socket 全范围解耦。 | 当前仍是台架局部机制验证，不是 socket 全范围应用验证。 | 尚未支持 |

---

## 当前整体结论

目前的实验和模型结果已经支持 APMD 的核心机制：主动构造路径对可以利用软材料的迟滞和预压历史，产生可控制、可重复、可用于局部解耦的磁响应差异。Stage 3 证明了 same-d/different-F 和 same-F/different-d 两种互补路径对都可以产生强磁分离；Stage 4 把这种现象转化为局部 `j_F/j_d` 灵敏度几何；Stage 5-6 进一步证明，把这种路径几何信息用于模型后，可以比普通磁回归和简单 branch-label 补偿取得更好的 held-out 解耦效果；Stage 7 排除了无接触运动伪差和简单 repeated loading 两个主要替代解释。

但是，结论边界必须写清楚：当前结果证明的是 bench-top setup 中的局部机制可行性和局部模型可行性，还不能直接声称已经解决 prosthetic socket 的全范围力-位移解耦。后续如果要走向 socket 应用，还需要做 cross-day 稳定性、更大力范围、不同材料/界面状态和真实 socket 几何下的验证。

## 建议的下一步

当前不建议继续盲目补大量数据，而是先把现有证据整理成完整汇报或论文 Results 逻辑：

1. 形成最终 Stage 3-7 证据图组：
   - Stage 3.1 same-d 工作区扫描图。
   - Stage 3.2 same-F 工作区扫描图。
   - Stage 3.3-3.5 path-dose 和 recovery 图。
   - Stage 4 local identifiability 图。
   - Stage 6.3 模型对比图。
   - Stage 7 控制实验图。
2. 写 Results 主线：
   - 主动路径对可以构造控制变量下的强磁分离。
   - preload depth/extra depth 是主要路径剂量变量。
   - 路径记忆在恢复时间内保持存在。
   - `j_F/j_d` 局部响应方向具备可辨识性。
   - local-identifiability 模型优于普通磁回归和 branch-label baseline。
   - 控制实验排除了运动伪差和简单重复 loading。
3. Stage 7.3 cross-day repeatability 可以作为可选补充，不是当前机制证明必须项。
4. 只有当后续模型残差或真实应用场景暴露具体问题时，再进行定向补采，例如：
   - cross-day repeatability；
   - 更大 socket-like force range；
   - 不同界面/材料状态；
   - 模型误差集中的局部工作区。

