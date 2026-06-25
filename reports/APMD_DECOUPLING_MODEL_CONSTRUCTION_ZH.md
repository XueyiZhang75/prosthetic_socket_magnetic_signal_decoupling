# APMD 解耦模型构造思路：从直接磁回归到主动路径对局部可辨识模型

## 写作定位

本文档用于把 APMD（Active Path-Pair Magnetic Decoupling，主动路径对磁解耦）的构造思路整理成一条连续的方法学证据链。主线不是简单解释“为什么不做 A 而做 B”，而是从最初的直接磁信号反演目标出发，逐步说明为什么直接 $\mathbf{B}\rightarrow(F,d)$ 在软材料磁触觉系统中会变成病态问题，以及 APMD 如何通过主动路径对把力相关响应和位移相关响应在三轴磁空间中分离出来，最终形成可用于模型训练和 held-out 验证的 local-identifiability features。

一句话概括为：在当前 bench-top 软磁触觉系统中，APMD 不是消除迟滞，而是主动构造可控路径历史，把迟滞导致的状态差异转化为可测量、可建模、可用于局部力-位移解耦的磁响应几何。

## 符号与术语约定

| 符号或术语 | 定义 | 用途 |
|---|---|---|
| $\mathbf{B}(t)$ | 三轴磁信号向量 | 原始磁观测量 |
| $\mathbf{B}_0$ | no-contact baseline 磁基线 | 去除环境磁场和零点偏移 |
| $\Delta\mathbf{B}$ | 相对 $\mathbf{B}_0$ 的磁变化 | 建模局部磁响应 |
| $F$ | 法向压缩力，$F>0$ 表示压缩 | 目标解耦变量 |
| $d$ | 从接触零点开始的相对压入位移 | 目标解耦变量 |
| $\eta$ | path history / material memory state | 表示软材料路径记忆 |
| $j_F$ | path-conditioned force-dominant local magnetic response direction | same-d/different-F 路径对估计 |
| $j_d$ | path-conditioned displacement-dominant local magnetic response direction | same-F/different-d 路径对估计 |
| same-d/different-F | 近似相同 $d$ 下制造不同 $F$ 的路径对 | 构造 $j_F$ |
| same-F/different-d | 近似相同 $F$ 下制造不同 $d$ 的路径对 | 构造 $j_d$ |
| local-identifiability | 局部 $j_F$ 与 $j_d$ 是否足够分离 | 判断能否稳定解耦 |
| held-out session | 完整排除在训练集外、仅用于测试的 session | 验证跨 session 泛化 |

其中三轴磁信号写作：

$$
\mathbf{B}(t)=
\begin{bmatrix}
B_x(t)\\
B_y(t)\\
B_z(t)
\end{bmatrix}.
$$

相对 no-contact baseline 的磁变化定义为：

$$
\Delta\mathbf{B}(t)=\mathbf{B}(t)-\mathbf{B}_0.
$$

## 1. 初始目标：直接用三轴磁信号估计 $F,d$

项目最初的目标很直接：软界面中嵌入磁体和三轴磁传感器后，接触加载会改变磁体和传感器之间的相对几何位置，也会改变软材料内部应力状态。因此，三轴磁信号应当包含关于法向力 $F(t)$ 和相对位移 $d(t)$ 的信息。最自然的建模想法就是训练一个从磁信号到两个机械量的回归器：

$$
\begin{bmatrix}
\hat{F}\\
\hat{d}
\end{bmatrix}
=f_\theta\left(B_x,B_y,B_z,\|\mathbf{B}\|\right).
$$

也就是：

$$
\mathbf{B}\rightarrow(F,d).
$$

如果系统是刚性、单值且无路径记忆的，这个想法是合理的。只要 $\mathbf{B}$ 与 $(F,d)$ 之间存在稳定的一一映射，模型就可以通过足够多的标定样本学习这个映射。但在软材料磁触觉系统中，磁信号不仅由当前 $F$ 和 $d$ 决定，还受到材料迟滞、loading/unloading 分支、preload 历史、松弛、蠕变和接触零点漂移等因素影响。因此，更真实的关系应写成：

$$
\mathbf{B}=g(F,d,\eta)+\varepsilon,
$$

其中 $\eta$ 表示 path history / material memory state，$\varepsilon$ 表示测量噪声、未建模扰动和残余误差。

这意味着直接磁回归面对的不是一个普通的回归难题，而是一个可辨识性问题。模型可以在训练集上拟合 $\mathbf{B}$ 与 $(F,d)$ 的相关性，但如果训练路径中 $F$ 和 $d$ 总是一起变化，它并不知道某个 $\Delta\mathbf{B}$ 究竟来自力变化、位移变化，还是路径记忆变化。

## 2. 核心障碍：软材料路径记忆导致强耦合

在普通单调压缩实验中，位移增加通常伴随力增加，磁体和传感器之间的几何关系也同时变化。因此实验中经常观测到：

$$
\Delta F\neq 0,\qquad \Delta d\neq 0.
$$

局部线性化后，磁变化可写成：

$$
\Delta\mathbf{B}\approx j_F\Delta F+j_d\Delta d+j_\eta\Delta\eta+\varepsilon.
$$

这里：

$$
j_F=\left.\frac{\partial\mathbf{B}}{\partial F}\right|_{d,\eta},
\qquad
j_d=\left.\frac{\partial\mathbf{B}}{\partial d}\right|_{F,\eta},
\qquad
j_\eta=\left.\frac{\partial\mathbf{B}}{\partial \eta}\right|_{F,d}.
$$

这三个方向分别表示力变化、位移变化和路径记忆变化在三轴磁空间中造成的局部响应。直接 loading 数据的问题在于，$\Delta F$、$\Delta d$ 和 $\Delta\eta$ 常常同时存在。因此，普通压缩实验中看到的磁变化：

$$
\Delta\mathbf{B}
$$

实际上是多个因素叠加后的混合响应。单纯把 $\mathbf{B}$ 喂给模型，模型可能只学到单调 loading 路径上的耦合投影，而不是两个彼此独立的物理变量。

因此，项目的核心问题从“磁信号能不能预测力和位移”转变为：

$$
\text{能否在实验上构造足够独立的 }\Delta F\text{ 和 }\Delta d\text{，从而估计 }j_F\text{ 和 }j_d?
$$

这就是 APMD 的出发点。

需要强调的是，后续由 same-d/different-F 和 same-F/different-d 路径对估计出的 $j_F$ 和 $j_d$ 不应被过度表述为数学上完全纯净的偏导数。更严谨的说法是：它们是由主动路径对估计出的、带有路径条件的 force-dominant 和 displacement-dominant local magnetic response directions。这个表述保留了局部线性化的物理意义，同时承认软材料路径记忆 $\Delta\eta$ 仍可能参与响应。

## 3. APMD 核心思想：主动 loading-unloading minor loop

APMD 的全称是 Active Path-Pair Magnetic Decoupling。它的核心不是被动记录软材料迟滞，而是主动利用迟滞。具体来说，我们人为设计 loading-unloading minor loop：

$$
\text{direct loading target}
\rightarrow
\text{deeper preload}
\rightarrow
\text{return / unloading target}.
$$

该路径通过调节以下 path-dose variables 来控制材料历史：

$$
d_{\mathrm{preload}},\qquad
\Delta d_{\mathrm{preload-extra}},\qquad
\tau_{\mathrm{hold}},\qquad
\tau_{\mathrm{recovery}},\qquad
\text{branch}.
$$

主动路径对的目标是构造两类互补状态：

$$
\text{near-same-}d/\text{different-}F
$$

和：

$$
\text{near-same-}F/\text{different-}d.
$$

第一类路径对在位移近似相同的条件下制造力差异，用于估计力相关磁响应方向 $j_F$。第二类路径对在力近似相同的条件下制造位移差异，用于估计位移相关磁响应方向 $j_d$。这一步把软材料迟滞从误差源转化为可控激励源，使模型不再只能观察自然耦合的 $F-d-B$ 变化，而是可以获得两个局部方向的实验估计。

这条路线建立在前置实验控制之上。Pre-flight 阶段先固定 force calibration、接触零点、位移方向和 no-contact baseline $\mathbf{B}_0$，避免后续把标签误差、接触零点漂移或环境磁漂误认为路径记忆。随后，被动 Stage I/J 的 fixed-displacement relaxation 和 fixed-force creep 作为负结果说明：单纯等待材料自然松弛或蠕变产生的磁变化不足以稳定估计 $j_F$ 或 $j_d$。因此，项目从被动观察转向主动构造路径差异。

## 4. same-d/different-F 路径对推导 $j_F$

same-d/different-F 路径对的目标是在近似相同位移下制造不同力。实验流程可写成：

$$
d_{\mathrm{target}}
\rightarrow
d_{\mathrm{preload}}
\rightarrow
d_{\mathrm{return}}\approx d_{\mathrm{target}}.
$$

对应三个稳定状态：

$$
S_L=\text{direct-loading target state},
$$

$$
S_P=\text{preload state},
$$

$$
S_R=\text{return-unloading target state}.
$$

在 $S_L$ 和 $S_R$ 之间，我们希望：

$$
d_R\approx d_L,
$$

但由于 $S_R$ 之前经历过 deeper preload，材料内部状态已经改变，因此：

$$
F_R\neq F_L.
$$

对应的路径对差分量定义为：

$$
\Delta\mathbf{B}_{\mathrm{same-d}}=\mathbf{B}_R-\mathbf{B}_L,
$$

$$
\Delta F_{\mathrm{same-d}}=F_R-F_L,
$$

$$
\Delta d_{\mathrm{same-d}}=d_R-d_L\approx 0.
$$

正式 gate 用于保证这一路径对真正满足 near-same-d 条件，例如：

$$
|d_R-d_L|\leq 0.020\ \mathrm{mm}.
$$

同时要求 force split 和 magnetic split 通过阈值。记录规则采用 direct target、preload、return target 的稳定段，并用最后稳定窗口的 median 作为 state summary，以降低瞬时噪声和过渡段影响。

在局部线性式中：

$$
\Delta\mathbf{B}\approx j_F\Delta F+j_d\Delta d+j_\eta\Delta\eta+\varepsilon.
$$

由于 same-d gate 使：

$$
\Delta d\approx 0,
$$

磁变化主要沿力相关路径方向变化。于是对重复实验 $r$，可定义：

$$
j_F(d_{\mathrm{target}})
=
\operatorname{median}_r
\left(
\frac{\Delta\mathbf{B}^{(r)}_{\mathrm{same-d}}}
{|\Delta F^{(r)}_{\mathrm{same-d}}|}
\right).
$$

展开成三轴向量：

$$
j_F=
\begin{bmatrix}
j_{F,x}\\
j_{F,y}\\
j_{F,z}
\end{bmatrix}
=
\begin{bmatrix}
\Delta B_x/|\Delta F|\\
\Delta B_y/|\Delta F|\\
\Delta B_z/|\Delta F|
\end{bmatrix}.
$$

其单位为：

$$
\mu\mathrm{T}/\mathrm{N}.
$$

归一化后得到力方向单位向量：

$$
\hat{j}_F=\frac{j_F}{\|j_F\|}.
$$

这个方向告诉模型：在当前局部工作区内，磁信号沿三维空间哪个方向变化时，更像是力变化造成的。

Stage 3.1 的 formal same-d 工作区扫描提供了这一路径设计的实验证据：$21/21$ same-d path pairs 达到 strong gate，深工作区的 $\Delta B_{\mathrm{vec}}$ 达到 hundreds of $\mu\mathrm{T}$ 量级。这说明 near-same-d 条件下的 force split 不是偶然个例，而是可以在目标位移网格中重复制造的主动路径响应。

## 5. same-F/different-d 路径对推导 $j_d$

same-F/different-d 路径对的目标是在近似相同力下制造不同位移。由于 Mark-10 测试台本质上是位移控制设备，所谓 force matching 不是直接力控制，而是通过小位移步进或路径设计让 unloading target 的 force sensor reading 接近目标力。实验流程可写成：

$$
F_{\mathrm{target}}
\rightarrow
d_{\mathrm{preload}}
\rightarrow
F_{\mathrm{return}}\approx F_{\mathrm{target}}.
$$

对于 loading target state 和 unloading target state，我们要求：

$$
F_U\approx F_L,
$$

但路径历史不同，因此：

$$
d_U\neq d_L.
$$

对应路径对差分量为：

$$
\Delta\mathbf{B}_{\mathrm{same-F}}=\mathbf{B}_U-\mathbf{B}_L,
$$

$$
\Delta d_{\mathrm{same-F}}=d_U-d_L,
$$

$$
\Delta F_{\mathrm{same-F}}=F_U-F_L\approx 0.
$$

正式 same-F gate 可写成：

$$
|F_U-F_L|\leq 0.050\ \mathrm{N}.
$$

在局部线性式中，由于：

$$
\Delta F\approx 0,
$$

磁变化主要沿位移相关路径方向变化。因此：

$$
j_d(F_{\mathrm{target}})
=
\operatorname{median}_r
\left(
\frac{\Delta\mathbf{B}^{(r)}_{\mathrm{same-F}}}
{|\Delta d^{(r)}_{\mathrm{same-F}}|}
\right).
$$

展开成三轴向量：

$$
j_d=
\begin{bmatrix}
j_{d,x}\\
j_{d,y}\\
j_{d,z}
\end{bmatrix}
=
\begin{bmatrix}
\Delta B_x/|\Delta d|\\
\Delta B_y/|\Delta d|\\
\Delta B_z/|\Delta d|
\end{bmatrix}.
$$

其单位为：

$$
\mu\mathrm{T}/\mathrm{mm}.
$$

归一化后得到位移方向单位向量：

$$
\hat{j}_d=\frac{j_d}{\|j_d\|}.
$$

实际实验中，same-F matching 比 same-d matching 更难。如果某些 same-F pair 仍存在小的残余力误差，可以先用 same-d 实验得到的 $j_F$ 做一阶修正：

$$
\Delta\mathbf{B}_{\mathrm{corr}}
=
\Delta\mathbf{B}_{\mathrm{same-F}}-j_F\Delta F.
$$

再估计：

$$
j_d
=
\frac{\Delta\mathbf{B}_{\mathrm{corr}}}{\Delta d}.
$$

这一步体现了 APMD 的闭环逻辑：先用 same-d/different-F 路径对建立力方向，再用该方向去修正 same-F/different-d 中残余的力污染，从而更干净地估计位移方向。

Stage 3.2 的 same-F/different-d 扫描提供了互补证据：accepted force points 覆盖 $1.50\text{--}4.90\ \mathrm{N}$，典型 displacement split 约为 $0.11\text{--}0.16\ \mathrm{mm}$，对应磁分离保持在 hundreds of $\mu\mathrm{T}$ 量级。两类路径对合起来说明，APMD 不只是证明“磁信号会受路径影响”，而是分别制造了 force-related 和 displacement-related 两个局部磁响应方向。

## 6. path-dose 与 recovery 证明路径激励可控

在构造出 same-d 和 same-F 两类路径对后，下一步需要证明这些磁分离不是偶然漂移，而是可以通过路径参数系统调节。为此，引入 path-dose variables：

$$
d_{\mathrm{preload}},\qquad
\Delta d_{\mathrm{preload-extra}},\qquad
\tau_{\mathrm{hold}},\qquad
\tau_{\mathrm{recovery}}.
$$

观察三个响应量：

$$
S_B=\|\Delta\mathbf{B}\|_2,
$$

$$
S_F=|\Delta F|,
$$

$$
S_d=|\Delta d|.
$$

其中：

$$
\|\Delta\mathbf{B}\|_2
=
\sqrt{
(\Delta B_x)^2+
(\Delta B_y)^2+
(\Delta B_z)^2
}.
$$

对于 same-d/different-F，重点观察：

$$
|\Delta F|,\qquad \|\Delta\mathbf{B}\|_2.
$$

对于 same-F/different-d，重点观察：

$$
|\Delta d|,\qquad \|\Delta\mathbf{B}\|_2.
$$

正式结果显示，same-d preload-depth 实验中，在 target $d=3.40\ \mathrm{mm}$ 下，preload 从 $3.60\ \mathrm{mm}$ 增加到 $3.80\ \mathrm{mm}$ 时，mean $\Delta B_{\mathrm{vec}}$ 从 $166.3\ \mu\mathrm{T}$ 增加到 $242.6\ \mu\mathrm{T}$。same-F preload-extra-depth 实验中，在 target $F=3.75\ \mathrm{N}$ 下，preload extra 从 $0.20\ \mathrm{mm}$ 增加到 $0.40\ \mathrm{mm}$ 时，median $\Delta B_{\mathrm{vec}}$ 从 $287.6\ \mu\mathrm{T}$ 增加到 $350.8\ \mu\mathrm{T}$。

Recovery-time 实验进一步说明路径记忆不是瞬时噪声。在 target $d=3.40\ \mathrm{mm}$、preload $d=3.80\ \mathrm{mm}$ 下，recovery time 从 $30\ \mathrm{s}$ 增加到 $300\ \mathrm{s}$，median $\Delta B_{\mathrm{vec}}$ 从 $253.4\ \mu\mathrm{T}$ 温和下降到 $230.5\ \mu\mathrm{T}$，但 $9/9$ pairs 仍然保持 strong。

因此，路径激励的强度主要由 preload depth 或 preload extra depth 控制，而不是简单由随机漂移或等待时间决定。这个结论保证后续的 $j_F/j_d$ 不是从噪声中硬凑出来的方向，而是来自可控路径激励的局部灵敏度方向。

## 7. local identifiability 判断 $j_F/j_d$ 是否能形成解耦坐标

得到 $j_F$ 和 $j_d$ 后，下一步不是立刻训练模型，而是先判断这两个方向在三轴磁空间中是否足够分开。将两列局部灵敏度组成矩阵：

$$
J=
\begin{bmatrix}
| & |\\
j_F & j_d\\
| & |
\end{bmatrix}
\in\mathbb{R}^{3\times 2}.
$$

局部模型的理想形式为：

$$
\Delta\mathbf{B}\approx
J
\begin{bmatrix}
\Delta F\\
\Delta d
\end{bmatrix}.
$$

也就是：

$$
\Delta\mathbf{B}\approx j_F\Delta F+j_d\Delta d.
$$

如果 $j_F$ 和 $j_d$ 方向接近重合，那么不同的 $(\Delta F,\Delta d)$ 组合可能产生相似的 $\Delta\mathbf{B}$，反演会变得病态。APMD 因此使用两个核心指标评估局部可辨识性。

第一是夹角：

$$
\theta
=
\cos^{-1}
\left(
\frac{|j_F^\mathsf{T}j_d|}
{\|j_F\|\|j_d\|}
\right).
$$

这里使用绝对值，是因为 loading/return 的顺序可能改变符号，而真正关心的是两个方向是否共线。

第二是 scaled condition number。先将两个方向归一化：

$$
U=
\begin{bmatrix}
| & |\\
\hat{j}_F & \hat{j}_d\\
| & |
\end{bmatrix}.
$$

再计算：

$$
\kappa_s
=
\frac{\sigma_{\max}(U)}{\sigma_{\min}(U)}.
$$

其中 $\sigma_{\max}$ 和 $\sigma_{\min}$ 为奇异值。使用归一化方向是为了避免 $j_F$ 的单位 $\mu\mathrm{T}/\mathrm{N}$ 和 $j_d$ 的单位 $\mu\mathrm{T}/\mathrm{mm}$ 直接影响 condition number。

若令：

$$
c=|\hat{j}_F^\mathsf{T}\hat{j}_d|,
$$

则对两个归一化列向量：

$$
\kappa_s=\sqrt{\frac{1+c}{1-c}}.
$$

当两个方向正交时：

$$
c=0,\qquad \kappa_s=1.
$$

当两个方向接近共线时：

$$
c\rightarrow 1,\qquad \kappa_s\rightarrow \infty.
$$

因此，$\theta$ 越大、$\kappa_s$ 越小，局部解耦越稳定。正式筛选中还要求磁信号高于噪声，例如：

$$
\Delta B_{\mathrm{vec}}/\sigma_B\geq 10,
$$

并使用：

$$
\angle(\hat{j}_F,\hat{j}_d)\geq 45^\circ,
$$

$$
\kappa_s\leq 5
$$

作为候选工作区的推荐标准，同时检查 same-d 和 same-F 的 pass rate、重复方向一致性和 locality。

Stage 4 最终选出的 strict primary sensitivity-pair candidate 为：

$$
d=3.40\ \mathrm{mm},\qquad F=4.90\ \mathrm{N}.
$$

对应：

$$
\theta=48.5^\circ,
$$

$$
\kappa_s=2.22,
$$

$$
\min(B/\mathrm{noise})=22.8.
$$

这说明在该局部工作区，$j_F$ 和 $j_d$ 已经形成可用于局部解耦的磁响应坐标系。

## 8. state-level 与 pair-level 数据集构造

前面几步得到的是机制和局部方向。要训练模型，还需要把原始 time series 整理成结构化表格。APMD 使用两层数据结构：state-level rows 和 pair-level rows。

每个稳定状态整理成一行 state-level row：

$$
\mathrm{state}_i
=
\{
B_x,B_y,B_z,\|\mathbf{B}\|,F,d,
\mathrm{path\ label},
\mathrm{history\ variables}
\}.
$$

磁场 summary 来自稳定窗口，通常写作：

$$
\bar{\mathbf{B}}_i
=
\operatorname{median}_{t\in\mathrm{last}\ 10\ \mathrm{s}}
\mathbf{B}(t).
$$

磁场模长为：

$$
\|\mathbf{B}_i\|
=
\sqrt{B_{x,i}^2+B_{y,i}^2+B_{z,i}^2}.
$$

相对 baseline 的磁变化为：

$$
\Delta\mathbf{B}_i=\mathbf{B}_i-\mathbf{B}_0,
$$

$$
\Delta B_{\mathrm{vec},i}
=
\|\Delta\mathbf{B}_i\|_2.
$$

每个路径对整理成一行 pair-level row：

$$
\mathrm{pair}_k
=
\{
\Delta F,\Delta d,\Delta\mathbf{B},
\mathrm{gate\ pass},
\mathrm{preload\ dose},
\tau_{\mathrm{hold}},
\tau_{\mathrm{recovery}}
\}.
$$

Stage 5 当前正式数据集汇总为：

$$
N_{\mathrm{pairs}}=87,
$$

$$
N_{\mathrm{states}}=1461,
$$

$$
N_{\mathrm{sessions}}=47.
$$

这些数据既包括 accepted same-d/different-F 与 same-F/different-d path-pair states，也包括 shallow、lower、mid 和 upper work-zone dense-loop states。这样，模型数据集不只是普通磁信号表，而是保留了路径记忆、preload/recovery 条件、pair-level magnetic range 和 session id 的结构化证据。

## 9. 将 $j_F/j_d$ 转成 local-ID 模型特征

APMD 的模型层贡献不是简单给 loading/unloading 加标签。Branch label 只能告诉模型当前状态属于 direct loading、preload deep 或 return unloading，却不能告诉模型力变化和位移变化在三轴磁空间中分别沿哪个方向发生。local-identifiability features 的作用，就是把 Stage 4 得到的 $j_F/j_d$ 局部几何显式放入回归器。

对于每一个 state row，先根据其所在局部工作区选择对应的 $j_F$ 和 $j_d$，并归一化：

$$
\hat{j}_F=\frac{j_F}{\|j_F\|},
\qquad
\hat{j}_d=\frac{j_d}{\|j_d\|}.
$$

当前状态的磁变化为：

$$
\Delta\mathbf{B}_i
=
\begin{bmatrix}
\Delta B_{x,i}\\
\Delta B_{y,i}\\
\Delta B_{z,i}
\end{bmatrix}.
$$

计算其在力方向上的投影：

$$
p_F=\Delta\mathbf{B}_i^\mathsf{T}\hat{j}_F.
$$

计算其在位移方向上的投影：

$$
p_d=\Delta\mathbf{B}_i^\mathsf{T}\hat{j}_d.
$$

进一步计算 $\Delta\mathbf{B}_i$ 在 $j_F/j_d$ 张成平面上的残差。令：

$$
U=
\begin{bmatrix}
| & |\\
\hat{j}_F & \hat{j}_d\\
| & |
\end{bmatrix}.
$$

最小二乘投影系数为：

$$
\alpha=(U^\mathsf{T}U)^{-1}U^\mathsf{T}\Delta\mathbf{B}_i.
$$

投影后的磁变化为：

$$
\Delta\mathbf{B}_{\mathrm{proj}}=U\alpha.
$$

残差定义为：

$$
r=
\left\|
\Delta\mathbf{B}_i-\Delta\mathbf{B}_{\mathrm{proj}}
\right\|_2.
$$

如果 $r$ 很小，说明当前磁变化大部分可以由力方向和位移方向解释。如果 $r$ 很大，则说明当前状态可能包含局部模型没有捕捉到的因素，例如滑移、漂移、非局部变形、边界工作区误差或 calibration mismatch。

因此，local-identifiability feature set 可写成：

$$
x_{\mathrm{local}}
=
\left[
p_F,\ p_d,\ r,\ \|j_F\|,\ \|j_d\|,\ \theta,\ \kappa_s,\ \mathrm{local\ distance}
\right].
$$

完整模型输入为：

$$
x_i=
\left[
x_{\mathrm{mag}},\ x_{\mathrm{path}},\ x_{\mathrm{memory}},\ x_{\mathrm{local}}
\right].
$$

其中：

$$
x_{\mathrm{mag}}
=
\left[
B_x,\ B_y,\ B_z,\ \|\mathbf{B}\|,\ \Delta B_x,\ \Delta B_y,\ \Delta B_z,\ \Delta B_{\mathrm{vec}}
\right],
$$

$$
x_{\mathrm{path}}
=
\left[
\mathrm{loading/unloading/preload\ labels}
\right],
$$

$$
x_{\mathrm{memory}}
=
\left[
d_{\mathrm{preload}},\ \tau_{\mathrm{hold}},\ \tau_{\mathrm{recovery}},\ \mathrm{pair\ range},\ \mathrm{state\ index}
\right],
$$

$$
x_{\mathrm{local}}
=
\left[
p_F,\ p_d,\ r,\ \|j_F\|,\ \|j_d\|,\ \theta,\ \kappa_s
\right].
$$

这一步是模型构造的关键：APMD 先通过实验得到局部力方向和位移方向，再把磁信号投影到这两个方向上，形成可解释的解耦特征。

## 10. 多输出回归模型与理论局部反演公式的关系

模型的输出是：

$$
y_i=
\begin{bmatrix}
F_i\\
d_i
\end{bmatrix}.
$$

模型学习：

$$
\hat{y}_i=f_\theta(x_i)
=
\begin{bmatrix}
\hat{F}_i\\
\hat{d}_i
\end{bmatrix}.
$$

以 Ridge 为例，训练目标可写成：

$$
\min_W
\left\|Y-XW\right\|_F^2
+\lambda\left\|W\right\|_F^2.
$$

其中：

$$
X=
\begin{bmatrix}
x_1^\mathsf{T}\\
x_2^\mathsf{T}\\
\vdots\\
x_n^\mathsf{T}
\end{bmatrix},
$$

$$
Y=
\begin{bmatrix}
F_1 & d_1\\
F_2 & d_2\\
\vdots & \vdots\\
F_n & d_n
\end{bmatrix}.
$$

从理论上，如果局部关系完全线性，并且 $j_F/j_d$ 足够准确，则可以直接进行局部反演：

$$
\Delta\mathbf{B}
=
J
\begin{bmatrix}
\Delta F\\
\Delta d
\end{bmatrix}
+\varepsilon.
$$

普通最小二乘解为：

$$
\begin{bmatrix}
\widehat{\Delta F}\\
\widehat{\Delta d}
\end{bmatrix}
=
(J^\mathsf{T}J)^{-1}J^\mathsf{T}\Delta\mathbf{B}.
$$

考虑磁轴噪声权重和病态反演时，可写成正则化形式：

$$
\begin{bmatrix}
\widehat{\Delta F}\\
\widehat{\Delta d}
\end{bmatrix}
=
(J^\mathsf{T}WJ+\lambda I)^{-1}
J^\mathsf{T}W\Delta\mathbf{B}.
$$

但实际软材料系统存在非线性、路径记忆、残余漂移和工作区差异，因此本文档不把纯解析反演作为最终部署模型。相反，APMD 将解析反演中的量：

$$
p_F,\qquad p_d,\qquad r,\qquad \theta,\qquad \kappa_s
$$

作为特征交给回归模型。这样既保留局部几何的物理解释，又允许模型吸收非线性和路径记忆造成的残余变化。

整个模型链可以概括为：

$$
\text{active path-pair experiments}
\Rightarrow
j_F,j_d
\Rightarrow
\text{local magnetic coordinates}
\Rightarrow
\text{regression model}
\Rightarrow
\hat{F},\hat{d}.
$$

## 11. held-out sessions 验证设计

模型训练完成后，验证不能只依赖随机拆分的同一 session 内样本。因为同一 session 内相邻状态共享接触零点、磁基线、样品状态和路径历史，随机拆分容易高估模型泛化能力。因此 Stage 6 使用完整 held-out sessions：

$$
\text{training set}=\text{Stage 5 states with path-pair and local model data},
$$

$$
\text{test set}=\text{new sessions excluded entirely from training}.
$$

当前正式 Stage 6.3 使用：

$$
N_{\mathrm{train}}=1461,
$$

$$
N_{\mathrm{heldout}}=312,
$$

$$
N_{\mathrm{heldout\ sessions}}=9.
$$

held-out sessions 包括：

$$
\text{session\_20260615\_160438},
\text{session\_20260618\_161152},
\text{session\_20260624\_155402},
\text{session\_20260624\_164026},
\text{session\_20260622\_173504},
\text{session\_20260622\_180702},
\text{session\_20260622\_185538},
\text{session\_20260623\_201622},
\text{session\_20260623\_204724}.
$$

这些 session 不进入训练、不参与归一化选择、不参与模型选择。这个设置用于检验模型学到的是否是局部解耦规律，而不是某一次采集内部的局部模式。

## 12. 模型对比结果

Stage 6.3 设置了四类特征层级，用来区分不同信息源的贡献：

$$
\text{plain magnetic}
\rightarrow
\text{branch-label}
\rightarrow
\text{APMD path-memory}
\rightarrow
\text{APMD local-identifiability}.
$$

其中 local-identifiability model 使用 path-memory features 加上 $j_F/j_d$ projection coordinates。当前正式结果如下：

| 模型 | 主要信息 | $F$ MAE (N) | $d$ MAE (mm) | 解释 |
|---|---|---:|---:|---|
| `plain_magnetic_ridge` | 只用磁信号 | 1.542 | 0.057 | 直接 $\mathbf{B}\rightarrow(F,d)$ baseline |
| `lim_style_branch_ridge` | 磁信号 + branch label | 1.027 | 0.0497 | 文献式 branch-label hysteresis compensation baseline |
| `magnetic_path_memory_ridge` | 磁信号 + path memory | 1.013 | 0.0531 | 加入路径历史但不加入局部几何 |
| `apmd_local_identifiability_ridge` | path memory + $j_F/j_d$ 局部几何 | 0.082 | 0.0468 | balanced local-ID ridge 主叙事模型 |
| `apmd_local_identifiability_random_forest` | local-ID 非线性模型 | 0.0449 | 0.0439 | force 与 displacement 均最好，但 ridge 仍作为更可解释的主线模型 |

local-ID ridge 相对 Lim-style branch-label ridge，将 held-out force MAE 从 $1.027\ \mathrm{N}$ 降低到 $0.082\ \mathrm{N}$，force MAE 改善：

$$
92.0\%.
$$

local-ID random forest 的 force MAE 更低，为 $0.0449\ \mathrm{N}$，displacement MAE 为 $0.0439\ \mathrm{mm}$。因此主叙事可以采用 local-ID ridge 作为更可解释的双输出模型，同时把 local-ID RF 作为补充结果，说明 local-identifiability features 对 force decoding 特别强。

这一对比支持 APMD 的模型层 claim：性能提升不是简单来自“知道当前是 loading 还是 unloading”，而是来自主动路径对测得的局部磁响应几何。

## 13. 控制实验排除运动伪差和 repeated loading

为了让机制证据完整，还需要排除两个替代解释。

第一，强磁分离是否只是 Mark-10 运动、电机、线缆或环境磁漂造成？No-contact motion artifact control 复现类似运动路径但不接触样品，结果显示：

$$
\Delta B_{\mathrm{vec}}=1.29\text{--}2.03\ \mu\mathrm{T}.
$$

$\mathbf{B}_0$ drift 为：

$$
3.37\ \mu\mathrm{T}.
$$

这些值远低于主动路径对中的 hundreds of $\mu\mathrm{T}$ 磁分离。

第二，强磁分离是否只是简单重复 loading 的自然漂移？Repeated-loading control 在没有 deeper preload 的情况下重复压到同一 target $d=3.40\ \mathrm{mm}$，最大 cycle-to-cycle magnetic change 为：

$$
\Delta B_{\mathrm{vec}}=34.1\ \mu\mathrm{T}.
$$

该值低于 $50\ \mu\mathrm{T}$ control gate，也远低于主动路径对产生的强响应。因此，强磁分离主要来自：

$$
\text{deeper preload}+\text{return path}
$$

构造出的路径历史差异，而不是普通运动伪差、环境磁漂或简单重复加载漂移。

## 14. 从零开始构建模型的完整逻辑总结

整个 APMD 解耦模型可以压缩成一条连续构建逻辑。

第一步，提出原始目标：

$$
\mathbf{B}=(B_x,B_y,B_z)\Rightarrow(F,d).
$$

我们希望用磁信号同时估计法向力和相对位移。

第二步，发现强耦合。软材料系统中：

$$
\mathbf{B}=g(F,d,\eta)+\varepsilon,
$$

并且普通压缩数据满足：

$$
\Delta\mathbf{B}\approx j_F\Delta F+j_d\Delta d+j_\eta\Delta\eta.
$$

力、位移和路径记忆混在一起，直接磁回归容易学到耦合投影。

第三步，提出主动路径激励。用 loading-unloading minor loop：

$$
\text{direct target}\rightarrow\text{deeper preload}\rightarrow\text{return target}
$$

主动制造可控路径差异。

第四步，构造 same-d/different-F。控制：

$$
\Delta d\approx 0,
$$

制造：

$$
\Delta F\neq 0,
$$

得到：

$$
j_F\approx\frac{\Delta\mathbf{B}}{|\Delta F|}.
$$

第五步，构造 same-F/different-d。控制：

$$
\Delta F\approx 0,
$$

制造：

$$
\Delta d\neq 0,
$$

得到：

$$
j_d\approx\frac{\Delta\mathbf{B}}{|\Delta d|}.
$$

第六步，通过 path-dose 和 recovery 实验证明主动路径激励可控且具有记忆，而不是随机漂移。

第七步，做局部可辨识性分析。构造：

$$
J=[j_F,\ j_d],
$$

计算：

$$
\theta
=
\cos^{-1}
\left(
|\hat{j}_F^\mathsf{T}\hat{j}_d|
\right),
$$

$$
\kappa_s
=
\frac{\sigma_{\max}(U)}{\sigma_{\min}(U)}.
$$

选择夹角足够大、condition number 足够低、SNR 足够高的局部工作区。

第八步，构建 state-level 和 pair-level 模型数据集：

$$
x_i=
\left[
\mathbf{B},\Delta\mathbf{B},
\mathrm{path\ label},
\mathrm{memory\ features},
\text{local-ID features}
\right],
$$

$$
y_i=
\begin{bmatrix}
F_i\\
d_i
\end{bmatrix}.
$$

第九步，把局部几何转成模型特征：

$$
p_F=\Delta\mathbf{B}^\mathsf{T}\hat{j}_F,
\qquad
p_d=\Delta\mathbf{B}^\mathsf{T}\hat{j}_d,
$$

$$
r=
\left\|
\Delta\mathbf{B}
-
\operatorname{Proj}_{\operatorname{span}(j_F,j_d)}
(\Delta\mathbf{B})
\right\|_2.
$$

再加入：

$$
\|j_F\|,\qquad \|j_d\|,\qquad \theta,\qquad \kappa_s.
$$

第十步，训练多输出回归模型：

$$
\begin{bmatrix}
\hat{F}\\
\hat{d}
\end{bmatrix}
=f_\theta(x).
$$

第十一步，用完整 held-out sessions 验证模型是否泛化到未参与训练的采集。

第十二步，得到结论：APMD local-identifiability features 显著改善 held-out force decoupling，并保持 displacement prediction 处于当前 local work-zone proof-of-mechanism 的可用范围内。当前结果支持 bench-top/local work-zone 机制证明，但不应被表述为已经覆盖 prosthetic socket full-range deployment。

## Claim-evidence map

| Claim | Evidence | Status |
|---|---|---|
| 直接 $\mathbf{B}\rightarrow(F,d)$ 受到强耦合限制 | 单一路径 loading 中 $F$ 和 $d$ 同步变化；plain magnetic ridge held-out force MAE 为 $1.542\ \mathrm{N}$ | supported |
| APMD 可以在 near-same-d 条件下构造力相关磁响应 | Stage 3.1 same-d scan 中 $21/21$ path pairs strong，深工作区 $\Delta B_{\mathrm{vec}}$ 达 hundreds of $\mu\mathrm{T}$ 量级 | supported |
| APMD 可以在 near-same-F 条件下构造位移相关磁响应 | Stage 3.2 accepted force points 覆盖 $1.50\text{--}4.90\ \mathrm{N}$，典型 $\Delta d$ 约 $0.11\text{--}0.16\ \mathrm{mm}$ | supported |
| 路径激励可由 preload depth / preload extra depth 调节 | same-d 和 same-F path-dose 实验中更深 preload 对应更强磁分离 | supported |
| 路径记忆在 recovery window 内仍存在 | $30\text{--}300\ \mathrm{s}$ recovery 后 $9/9$ pairs strong，median $\Delta B_{\mathrm{vec}}$ 仍高于 $230\ \mu\mathrm{T}$ | supported |
| $j_F/j_d$ 具备局部可辨识性 | Stage 4 strict candidate $d=3.40\ \mathrm{mm}$、$F=4.90\ \mathrm{N}$，$\theta=48.5^\circ$，$\kappa_s=2.22$，min B/noise $22.8$ | locally supported |
| local-ID features 优于 branch-label baseline | Stage 6.3 local-ID ridge force MAE $0.082\ \mathrm{N}$，Lim-style baseline $1.027\ \mathrm{N}$，改善 $92.0\%$ | supported within held-out local work zones |
| 强磁分离不是 no-contact motion artifact | no-contact $\Delta B_{\mathrm{vec}}=1.29\text{--}2.03\ \mu\mathrm{T}$，$\mathbf{B}_0$ drift $3.37\ \mu\mathrm{T}$ | supported |
| 强磁分离不是简单 repeated loading | repeated-loading control 最大 cycle-to-cycle $\Delta B_{\mathrm{vec}}=34.1\ \mu\mathrm{T}$ | supported |
| 当前结果支持 full socket range deployment | 当前数据来自 bench-top local work zones，未覆盖 socket-like full geometry/range | not supported |

## 数据来源与边界

本文档依据当前仓库最新正式报告和数据表整理，主要来源包括：

- `APMD_FORMAL_EXPERIMENT_DESIGN.md`
- `EXPERIMENT_PLAN.md`
- `reports/APMD_STAGE4_IDENTIFIABILITY_ANALYSIS.md`
- `reports/APMD_STAGE5_MODEL_DATASET_SUMMARY.md`
- `reports/APMD_STAGE6_HELDOUT_MODEL_VALIDATION.md`
- `reports/APMD_STAGE6_LOCAL_IDENTIFIABILITY_MODEL.md`
- `reports/apmd_stage6_local_identifiability_model_metrics.csv`

当前结论的边界是：结果支持 bench-top setup 中 selected local work zones 的 proof-of-mechanism，说明主动路径对可以提供有用的局部磁响应坐标，并在 held-out sessions 中改善力-位移解耦模型。若要面向 prosthetic socket full-range 应用，还需要 cross-day repeatability、更多材料/界面状态、更大 force-displacement range 以及 socket-like geometry 下的重新验证。

## 15. 升级优化总览：从两类路径对到主动局部响应算子识别

当前 APMD 主线不应被推翻。same-d/different-F 和 same-F/different-d 仍应作为核心 anchor，因为它们最清楚地展示了主动路径激励如何把强耦合的力和位移变量拆开。真正需要升级的是方法层级：不要把 APMD 讲成“两类特殊路径算两个方向”，而应讲成“主动路径激励识别局部磁-机械响应算子”。

升级后的总链条可写成：

$$
\text{active path excitation}
\Rightarrow
\text{local magnetic response operator}
\Rightarrow
\text{geometry-constrained model}
\Rightarrow
(F,d).
$$

也就是说，same-d 和 same-F 仍然是最重要的轴对齐路径对，但它们只是主动路径语言中的第一类路径。后续可加入 memory-isolation path pairs、oblique active paths、nested minor loops 和 dynamic spectroscopy paths，使 APMD 从 force-displacement local-ID 扩展为 force-displacement-memory aware active sensing。

## 16. 综合建议的来源、取舍和合理性

| 建议 | 来源 | 处理 | 合理性和升级价值 |
|---|---|---|---|
| 保留 same-d/different-F 与 same-F/different-d | 现有项目主线 + GPT + 本文判断 | 保留 | 已有 Stage 3/4/6 证据支持，是当前最稳定、最可解释的核心机制 |
| 将 $j_F/j_d$ 表述为 path-conditioned response directions | GPT | 保留，已纳入前文术语 | 更严谨，避免把路径对有限差分过度声称为纯偏导 |
| dual-coordinate / least-squares local-ID features | GPT | 保留，优先实施 | 不需要新实验，可直接检验非正交 $j_F/j_d$ 下的坐标改进 |
| weighted local Jacobian re-estimation | GPT | 保留，优先实施初版 | 比单个 ratio estimate 更稳健，也更像局部 system identification |
| memory-isolation path pairs 估计 $j_m$ | GPT + 本文判断 | 保留，最高优先级新实验 | 能把路径记忆从 nuisance / scalar feature 升级为显式几何方向 |
| oblique active paths | GPT | 保留，第二优先级实验 | 让 $J$ 由多方向扰动联合估计，而不只依赖两类轴对齐路径 |
| nested minor loops / reversal-memory features | GPT | 保留为后续机制深化 | 能表征最近 reversal depth，但实验复杂度高于 memory-isolation |
| rate / dwell / recovery spectroscopy | GPT + 本文判断 | 保留为长期增强 | 对真实动态步态更有意义，但不适合作为最近一轮主 claim |
| pairwise contrastive / consistency loss | GPT | 保留为模型实验或评估 | APMD 的 pair-level 结构很适合它，但应先做 evaluation 再决定是否进入训练 |
| D-optimal active path planning | GPT + 本文判断 | 保留为 Stage 8/9 方向 | 可把后续采样从人工经验升级为主动实验设计 |
| GPT 截图中的旧指标 | GPT 截图 | 抛弃 | 当前正式结果已更新，应使用 Stage 5/6 最新数字 |
| full socket range deployment claim | 不采用 | 抛弃 | 当前证据只支持 bench-top/local work-zone proof-of-mechanism |

这些取舍的原则是：凡是能增强 APMD 主线且不破坏已有证据边界的内容保留；凡是会把未完成实验写成已有结果、或把 local proof-of-mechanism 扩大成 full deployment 的内容不采用。

## 17. 可直接在当前项目上实施的优化

第一项是叙事修正。全文应统一使用如下表述：$j_F$ 和 $j_d$ 是由主动路径对估计的 path-conditioned local response directions，而不是完全无路径记忆污染的严格偏导数。对应的局部模型仍然是：

$$
\Delta\mathbf{B}
\approx
j_F\Delta F+j_d\Delta d+j_\eta\Delta\eta+\epsilon.
$$

这个修正不削弱 APMD，反而使它更严谨。因为 APMD 的核心本来就是主动利用路径历史，而不是假设路径历史不存在。

第二项是增加 dual-coordinate local-ID features。当前 dot projection 为：

$$
p_F=\Delta\mathbf{B}^\mathsf{T}\hat{j}_F,
\qquad
p_d=\Delta\mathbf{B}^\mathsf{T}\hat{j}_d.
$$

当 $\hat{j}_F$ 和 $\hat{j}_d$ 不正交时，$p_F$ 会包含部分 displacement direction 贡献，$p_d$ 也会包含部分 force direction 贡献。因此应同时计算 least-squares coordinates：

$$
\begin{bmatrix}
c_F\\
c_d
\end{bmatrix}
=
(U^\mathsf{T}U)^{-1}U^\mathsf{T}\Delta\mathbf{B},
\qquad
U=[\hat{j}_F,\hat{j}_d].
$$

后续模型可比较三种 feature set：

$$
\text{APMD-dot},
\qquad
\text{APMD-dual},
\qquad
\text{APMD-dot+dual}.
$$

评估重点不仅是 held-out MAE，也包括 pair consistency residual。如果 dual-coordinate features 对 displacement MAE 或 pair residual 有改善，就说明局部几何坐标确实比简单投影更接近解耦数学。

第三项是 weighted local Jacobian re-estimation。当前 anchor 估计可写成：

$$
j_F\approx\frac{\Delta\mathbf{B}}{|\Delta F|},
\qquad
j_d\approx\frac{\Delta\mathbf{B}}{|\Delta d|}.
$$

更稳健的版本是把同一 local zone 内的多个 path pairs 联合起来，估计局部响应算子：

$$
\min_{j_F,j_d}
\sum_k w_k
\left\|
\Delta\mathbf{B}_k
-j_F\Delta F_k
-j_d\Delta d_k
\right\|_2^2
+\lambda(\|j_F\|^2+\|j_d\|^2).
$$

其中 $w_k$ 可由 gate pass、magnetic signal-to-noise ratio、repeat directional consistency 和 distance to local zone 决定。这一步能把 APMD 从“由两个 ratio estimate 得到两个方向”升级为“由主动路径扰动联合识别局部响应矩阵”。

第四项是 confidence / uncertainty 输出。模型不应只输出：

$$
[\hat F,\hat d].
$$

还应给出每个预测的局部可信度：

$$
\mathrm{confidence}
=
h(\kappa_s,\ r_{Fd},\ \sigma_J,\ \mathrm{distance\ to\ local\ zone}).
$$

其中 $r_{Fd}$ 是 $\Delta\mathbf{B}$ 在 $j_F/j_d$ 张成平面外的残差，$\sigma_J$ 是局部响应算子估计的不确定性。对未来 socket 场景而言，低 confidence prediction 比单纯错误预测更容易被系统层处理。

第五项是 pairwise consistency evaluation。APMD 的证据来自路径对，因此模型评价也应显式包含路径对约束。对 same-d pair，应检查：

$$
|\hat d_i-\hat d_j|\rightarrow 0.
$$

对 same-F pair，应检查：

$$
|\hat F_i-\hat F_j|\rightarrow 0.
$$

同时检查磁一致性：

$$
\left\|
\Delta\mathbf{B}_{ij}
-j_F(\hat F_j-\hat F_i)
-j_d(\hat d_j-\hat d_i)
\right\|_2.
$$

这一步优先作为 evaluation，而不是立即作为训练 loss。若它能明显区分 local-ID 与 baseline，再考虑引入 pairwise contrastive / consistency loss。

## 18. 需要补实验的新主动路径设计

第一优先级是 memory-isolation path pairs。该实验的目标是在近似相同 $F$ 和 $d$ 下制造不同路径历史：

$$
\Delta F\approx 0,
\qquad
\Delta d\approx 0,
\qquad
\Delta m\neq 0.
$$

建议在当前 strict local zone 附近进行，即 $d=3.40\ \mathrm{mm}$、$F=4.90\ \mathrm{N}$。设计两条路径回到同一目标状态：

$$
\text{Path A: shallow preload}\rightarrow(F_0,d_0),
$$

$$
\text{Path B: deep preload}\rightarrow(F_0,d_0).
$$

推荐 gate 为：

$$
|\Delta F|\leq 0.050\ \mathrm{N},
\qquad
|\Delta d|\leq 0.020\ \mathrm{mm}.
$$

如果在 gate 通过后仍有稳定磁差：

$$
\Delta\mathbf{B}_m\neq 0,
$$

则可定义 memory direction：

$$
j_m\approx\frac{\Delta\mathbf{B}_m}{\Delta m}.
$$

这里的 $m$ 不必一开始就是严格材料内变量，可先定义为 path-dose proxy，例如：

$$
m
=
(d_{\mathrm{preload}}-d_{\mathrm{target}})
\log(1+\tau_{\mathrm{hold}})
\exp(-\tau_{\mathrm{recovery}}/\tau_r).
$$

得到 $j_m$ 后，模型可新增：

$$
p_m=\Delta\mathbf{B}^\mathsf{T}\hat{j}_m,
$$

以及三方向残差：

$$
r_{Fdm}
=
\left\|
\Delta\mathbf{B}
-
\operatorname{Proj}_{\operatorname{span}(j_F,j_d,j_m)}
(\Delta\mathbf{B})
\right\|_2.
$$

这项实验的价值最大，因为它能把当前 $[j_F,j_d]$ 二维模型扩展为 $[j_F,j_d,j_m]$ 三维模型，使 APMD 从 force-displacement decoupling 升级为 force-displacement-memory aware sensing。

第二优先级是 oblique active paths。当前 same-d 和 same-F 是轴对齐路径，分别强调：

$$
\Delta d\approx 0
$$

或：

$$
\Delta F\approx 0.
$$

但真实使用场景中常见的是：

$$
\Delta F\neq 0,
\qquad
\Delta d\neq 0.
$$

因此可在同一 local zone 附近设计多种 path slopes：

$$
(\Delta F,\Delta d)
=
(a,0),(0,b),(a,b),(a,-b),(2a,b),(a,2b).
$$

每个 pair 观测 $\Delta\mathbf{B}$，再联合估计 $J$。若 oblique paths 能降低 $J$ 的不确定性、降低 residual 或改善 held-out path protocol，就可以把 APMD 叙事升级为 actively programmed local perturbations identify the magnetic response operator。

第三优先级是 nested minor loops / reversal-memory paths。该实验关注最近 reversal depth 对磁响应的影响。设计：

$$
d_0\rightarrow d_0+a\rightarrow d_0,
$$

$$
d_0\rightarrow d_0+b\rightarrow d_0,
$$

$$
d_0\rightarrow d_0+c\rightarrow d_0,
\qquad
a<b<c.
$$

每次回到同一个 $d_0$ 后记录 $F$ 和 $\mathbf{B}$，估计 reversal-depth sensitivity：

$$
j_R
\approx
\frac{
\mathbf{B}_{\mathrm{return}}(d_{\mathrm{rev},2})
-
\mathbf{B}_{\mathrm{return}}(d_{\mathrm{rev},1})
}
{d_{\mathrm{rev},2}-d_{\mathrm{rev},1}}.
$$

这能把 path memory 从简单 preload label 升级为 reversal-memory coordinate。

第四优先级是 rate / dwell / recovery spectroscopy。该实验面向动态粘弹性响应，不建议作为当前最近一轮主实验，但适合后续 socket-like dynamic loading。可以设计不同 loading rates：

$$
d(t)=d_0+vt,
\qquad
v\in\{v_1,v_2,v_3\}.
$$

记录 $\dot d$、$\dot F$、$\dot{\mathbf{B}}$，估计：

$$
j_v=\frac{\partial\mathbf{B}}{\partial \dot d}.
$$

也可以做小幅正弦扰动：

$$
d(t)=d_0+A\sin(2\pi ft),
$$

并提取磁响应幅值和相位：

$$
H_B(f)=
\frac{\mathcal{F}[\mathbf{B}](f)}
{\mathcal{F}[d](f)}.
$$

第五项是 held-out path protocol。已有 held-out sessions 很重要，但下一步还应留出未见过的路径协议。例如 train 使用 preload extra $0.20/0.30\ \mathrm{mm}$，test 使用 $0.40\ \mathrm{mm}$；train 使用 recovery $30/120\ \mathrm{s}$，test 使用 $300\ \mathrm{s}$；train 使用 axis-aligned same-d/same-F，test 使用 oblique paths。这样能验证模型是否学到了更一般的 active-path decoupling geometry。

## 19. 后续模型框架

后续模型建议分三层。

第一层是主动路径识别层。该层不直接预测 $F,d$，而是输出局部响应算子：

$$
J_{Fd}=[j_F,j_d].
$$

若 memory-isolation 实验通过 gate，则扩展为：

$$
J_{Fdm}=[j_F,j_d,j_m].
$$

同时输出局部几何质量：

$$
\theta,\qquad
\kappa_s,\qquad
\sigma_J,\qquad
r.
$$

第二层是局部坐标特征层。对二维模型：

$$
c_{Fd}
=
(U^\mathsf{T}U)^{-1}U^\mathsf{T}\Delta\mathbf{B}.
$$

对三维 memory-aware 模型：

$$
c_{Fdm}
=
(U_m^\mathsf{T}U_m)^{-1}U_m^\mathsf{T}\Delta\mathbf{B}.
$$

由此得到：

$$
c_F,\quad c_d,\quad c_m,\quad r_{Fd},\quad r_{Fdm}.
$$

第三层是预测层。最终输入可写成：

$$
x=
[
\mathbf{B},
\Delta\mathbf{B},
c_F,c_d,c_m,
r,\theta,\kappa_s,
m_{\mathrm{dose}},
\mathrm{branch},
\mathrm{dynamic\ features}
].
$$

输出为：

$$
[\hat F,\hat d]=f_\theta(x).
$$

训练时先保留普通 supervised loss：

$$
\mathcal{L}_{\mathrm{state}}
=
\sum_i
\left[
(\hat F_i-F_i)^2
\alpha(\hat d_i-d_i)^2
\right].
$$

若 pairwise consistency evaluation 证明有效，再加入：

$$
\mathcal{L}
=
\mathcal{L}_{\mathrm{state}}
\lambda\mathcal{L}_{\mathrm{pair}}
\mu\mathcal{L}_{\mathrm{gate}}.
$$

这会把当前普通回归器升级为 active-path-informed, geometry-constrained, memory-aware decoupling model。

## 20. 推荐实施顺序与验收标准

第一阶段不需要新实验，直接基于当前 Stage 5/6 数据实施。内容包括：统一 $j_F/j_d$ 的 path-conditioned 表述；加入 dual-coordinate features；比较 APMD-dot、APMD-dual 和 APMD-dot+dual；增加 pairwise consistency evaluation；输出 confidence / uncertainty 指标。验收标准至少包括 held-out $F$ MAE、$d$ MAE、pair consistency residual 和 confidence-error correlation。

第二阶段补一个小而关键的 memory-isolation 实验。目标是在 $d=3.40\ \mathrm{mm}$、$F=4.90\ \mathrm{N}$ 附近构造 same-F/same-d/different-history pairs，并估计 $j_m$。只有当 near-same-F 和 near-same-d gates 同时通过时，才能声称该实验识别了 memory direction。

第三阶段扩展 oblique active paths。目标是在同一 local zone 内采集多个不同 $(\Delta F,\Delta d)$ 方向的路径对，并用 weighted least-squares 重新估计 $J$。若该方法改善 condition number、降低 residual 或改善 held-out path protocol，则进入主模型路线。

第四阶段再做 nested minor loops 和 rate/dwell/recovery spectroscopy。它们适合机制深化和动态应用扩展，但不应提前作为当前主结论。

第五阶段建立 held-out path protocol。验证模型不仅能泛化到未见过的 sessions，也能泛化到未见过的路径参数和路径类型。

| 优化项 | 是否可直接实施 | 是否需要新实验 | 进入主叙事条件 |
|---|---:|---:|---|
| path-conditioned $j_F/j_d$ 表述 | 是 | 否 | 立即采用 |
| dual-coordinate features | 是 | 否 | 改善 MAE 或 pair residual |
| weighted local $J$ re-estimation | 是，初版可做 | 否 | 降低 residual 或提高 confidence-error correlation |
| confidence / uncertainty | 是 | 否 | confidence 与 error 呈合理相关 |
| pairwise consistency evaluation | 是 | 否 | 能区分 local-ID 与 baseline |
| memory-isolation $j_m$ | 否 | 是 | same-F/same-d gates 通过且 $\Delta\mathbf{B}_m$ 高于噪声 |
| oblique active paths | 否 | 是 | 改善 $J$ 的稳定性或 held-out path performance |
| nested minor loops | 否 | 是 | reversal-depth response 可重复 |
| dynamic spectroscopy | 否 | 是 | 动态特征稳定且改善 held-out path protocol |
| D-optimal active path planning | 部分可模拟 | 最终需要实验 | 能指导下一批路径并提高 identifiability |

最终推荐的论文级创新表述可以从：

> APMD constructs near-same-d/different-F and near-same-F/different-d path pairs to estimate local force- and displacement-dominant magnetic response directions for force-displacement regression.

升级为：

> APMD actively programs path perturbations to identify a local magnetic response operator for soft magnetic tactile sensing. The operator spans force-, displacement-, and path-memory-dominant response directions, and its non-orthogonal local coordinates, residuals, and confidence metrics are embedded into a geometry-constrained model for force-displacement decoupling.

对应中文为：APMD 不只是设计两类路径对来估计 $j_F/j_d$，而是主动编程迟滞路径，通过多类路径激励识别软磁触觉系统的局部磁-机械响应算子。该算子包含力方向、位移方向和路径记忆方向；模型再把实时磁变化投影到这个局部坐标系中，实现可解释的力-位移解耦。
