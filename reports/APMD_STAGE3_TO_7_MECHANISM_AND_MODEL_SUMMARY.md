# APMD Stage 3-7 Mechanism Evidence and Stage 5-6 Model Summary

## One-sentence argument

In the current bench-top magnetic tactile setup, active path-pair excitation converts soft-material hysteresis, preload history, and recovery effects from uncontrolled error sources into measurable local magnetic response directions, and the resulting local sensitivity geometry improves force-displacement decoupling beyond plain magnetic regression and simple loading/unloading label compensation.

## Terminology ledger

| Term | Meaning in this project |
|---|---|
| APMD | Active Path-Pair Magnetic Decoupling |
| same-d/different-F path pair | A direct-loading and return-unloading pair recorded at nearly the same commanded displacement but different force |
| same-F/different-d path pair | A loading and unloading pair recorded at nearly matched force but different displacement |
| path-dose | Controlled change of preload depth, preload extra depth, hold time, or recovery time |
| local identifiability | Whether local magnetic response directions for force-like and displacement-like changes are sufficiently separated for decoupling |
| `j_F` | Local magnetic sensitivity direction estimated from same-d/different-F pairs |
| `j_d` | Local magnetic sensitivity direction estimated from same-F/different-d pairs |
| held-out session | A complete session excluded from training and used only for testing |

---

## Stage 3: Mechanism Evidence From Active Path-Pair Experiments

### 3.1 same-d/different-F work-zone scan

**Purpose.** Test whether active preload-return paths can create different force states at nearly the same displacement.

**Formal data.**

- 3.1A: `session_20260610_091145`, target `d = 2.40/2.60/2.80 mm`.
- 3.1B: `session_20260610_104017`, target `d = 3.00/3.20/3.40/3.60 mm`.
- Total: 21 path pairs, all passed same-d and strong magnetic gates.

**Key results.**

| target d (mm) | median abs(Delta F) (N) | median Delta Bvec (uT) | Verdict |
|---:|---:|---:|---|
| 2.40 | 0.432 | 62.8 | strong |
| 2.60 | 0.515 | 110.2 | strong |
| 2.80 | 0.698 | 103.4 | strong |
| 3.00 | 0.814 | 155.4 | strong |
| 3.20 | 0.973 | 200.6 | strong |
| 3.40 | 1.183 | 227.8 | strong |
| 3.60 | 1.587 | 207.3 | strong |

**Interpretation.** At the same commanded displacement, changing the prior path produced a large force split and a repeatable magnetic split. The response strengthened from shallow to deeper work zones, with `d = 3.20-3.40 mm` emerging as a practical local work zone.

### 3.2 same-F/different-d work-zone scan

**Purpose.** Test the complementary control-variable case: can active paths create different displacement states at nearly matched force?

**Formal data.**

- Accepted target forces: `1.50/1.80/2.50/3.20/3.75/4.30/4.90 N`.
- Each force point has three accepted path pairs.
- `5.50 N` was not required for this formal round.

**Key results.**

- Force matching remained within the formal same-F gate for accepted pairs.
- Displacement split was typically `0.11-0.16 mm`.
- Magnetic split remained high across the force range, with representative Delta Bvec values around `313-458 uT`.
- The magnetic response was dominated by `dBy` and `dBz`, while `dBx` remained small.

**Interpretation.** This complements Stage 3.1: active path-pair excitation can isolate a displacement-like magnetic response under near-matched force, not only a force-like response under near-matched displacement.

### 3.3 same-d path-dose study

**Purpose.** Determine whether the same-d/different-F effect is controllable by changing the preload depth and preload hold time.

**3.3A preload-depth dose.**

At target `d = 3.40 mm`, increasing preload from `3.60` to `3.80 mm` systematically increased the path-induced force and magnetic split:

| preload d (mm) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 3.60 | 1.004 | 166.3 |
| 3.70 | 1.284 | 205.8 |
| 3.80 | 1.519 | 242.6 |

**3.3B preload-hold-time dose.**

At target `d = 3.40 mm` and preload `d = 3.80 mm`, hold time had a weaker and non-monotonic effect:

| preload hold (s) | mean abs(Delta F) (N) | mean Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 1.527 | 251.1 |
| 30 | 1.590 | 236.9 |
| 90 | 1.623 | 241.1 |

**Interpretation.** Preload depth is the stronger same-d path-dose variable. Holding time changes the response less than changing the maximum historical compression.

### 3.4 same-F path-dose study

**Purpose.** Determine whether the same-F/different-d effect is controllable by changing preload extra depth and preload hold time.

**3.4A preload-extra-depth dose.**

At target `F = 3.75 N`, increasing preload extra depth made the same-F displacement split more reliable and generally strengthened magnetic separation:

| preload extra (mm) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 0.20 | 0.10 | 287.6 |
| 0.30 | 0.10 | 308.8 |
| 0.40 | 0.13 | 350.8 |

**3.4B preload-hold-time dose.**

At `F = 3.75 N` and preload extra `+0.40 mm`, hold time again showed limited or non-monotonic benefit:

| preload hold (s) | median abs(Delta d) (mm) | median Delta Bvec (uT) |
|---:|---:|---:|
| 5 | 0.20 | 550.1 |
| 30 | 0.12 | 347.8 |
| 90 | 0.14 | 392.5 |

**Interpretation.** The active path dose is mainly controlled by how far the path enters the preload state, not simply by how long it stays there.

### 3.5 recovery-time path-memory decay

**Purpose.** Test whether the active path memory disappears after recovery time.

**Formal data.**

- `session_20260614_201905`.
- Target `d = 3.40 mm`, preload `d = 3.80 mm`, recovery before pair `30/120/300 s`.
- 9/9 pairs remained strong.

| recovery time (s) | median abs(Delta F) (N) | median Delta Bvec (uT) |
|---:|---:|---:|
| 30 | 2.125 | 253.4 |
| 120 | 2.077 | 240.7 |
| 300 | 2.067 | 230.5 |

**Interpretation.** Recovery time caused a mild decrease in magnetic separation, but did not remove the active path-pair effect. This supports the idea that the path memory is robust over the tested recovery window.

---

## Stage 4: Local Identifiability Analysis

**Purpose.** Convert Stage 3 path-pair observations into local magnetic sensitivity directions and select a local work zone for mechanism validation.

**Method.**

- `j_F` was estimated from same-d/different-F pairs as `Delta B / |Delta F|`.
- `j_d` was estimated from same-F/different-d pairs as `Delta B / |Delta d|`.
- The angle between `j_F` and `j_d` was used to evaluate whether force-like and displacement-like magnetic responses point in separable directions.
- The scaled condition number was computed after normalizing the two columns, so it reflected directional collinearity rather than unit choice.

**Key result.**

- Strict primary candidate: same-d `d = 3.40 mm` paired with same-F `F = 4.90 N`.
- Sensitivity angle: `48.5 deg`.
- Scaled condition number: `2.22`.
- Minimum magnetic noise ratio: `22.8`.
- Best-score practical candidate: `d = 3.20 mm`, `F = 4.90 N`, angle `41.9 deg`.

**Interpretation.** Stage 4 did not claim a universal prosthetic-socket work range. It identified a local mechanism-validation zone where the two active path-pair response directions are sufficiently separated to justify model-level decoupling tests.

---

## Stage 5: Model Dataset and Local Baseline Models

### 5.0 dataset construction

**Purpose.** Build a state-level and pair-level modeling dataset from accepted formal sessions.

**Data size.**

- Accepted path pairs: `87`.
- State summaries: `411`.
- Unique sessions: `31`.
- Dense local minor-loop states: `150` from two sessions.
- Dense local d grid: `[3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8]`.

**Interpretation.** The dataset is enough for a local proof-of-mechanism model, but not for a full socket-range deployment model.

### 5.2 grouped cross-validation baseline

**Validation rule.** Grouped cross-validation by `session_id`; rows from the same session were not split across train and validation folds.

**Models tested.**

- Plain magnetic ridge: `B -> F,d`.
- Path-label ridge: `B + path labels -> F,d`.
- Path-memory ridge: `B + path labels + protocol/history features -> F,d`.
- Path-memory random forest: nonlinear version of the path-memory model.

**Key results.**

| Model | F MAE (N) | d MAE (mm) | Meaning |
|---|---:|---:|---|
| plain magnetic ridge | 1.563 | 0.105 | baseline |
| path-label ridge | 1.332 | 0.092 | labels help modestly |
| path-memory ridge | 0.827 | 0.091 | best balanced Stage 5.2 model |
| path-memory RF | 0.695 | 0.150 | best force model, worse displacement |

**Interpretation.** Path-aware and path-memory features improved the model over plain magnetic regression, especially for force. However, Stage 5.2 was still an internal cross-validation check rather than a final held-out proof.

### 5.3 dense-loop cross-session validation

**Purpose.** Test whether local dense-loop models transfer between two independently acquired dense-loop sessions.

**Data.**

- Dense-loop sessions: `session_20260615_112044` and `session_20260615_143640`.
- Total dense-loop states: `150`.
- Validation: train on one dense-loop session, test on the other, then reverse.

**Key results.**

| Model | F MAE (N) | d MAE (mm) |
|---|---:|---:|
| dense plain magnetic ridge | 0.991 | 0.035 |
| dense path-memory ridge | 0.413 | 0.023 |
| dense plain magnetic RF | 0.741 | 0.056 |
| dense path-memory RF | 0.323 | 0.039 |

**Interpretation.** In a local dense-loop setting, path-memory features improved cross-session prediction. Ridge gave the best displacement accuracy, while random forest gave the best force accuracy.

---

## Stage 6: Held-Out Validation and Local-Identifiability Model

### 6.1 held-out dense-loop acquisition

**Purpose.** Acquire an independent dense-loop session that was not used for training.

**Formal data.**

- Held-out session: `session_20260615_160438`.
- States: `39`.
- d grid: `[3.05, 3.15, 3.25, 3.35, 3.45, 3.55]`.
- Same-d-like pairs: `18/18`.
- Force-split pairs: `18/18`.
- Magnetic-split pairs: `18/18`.
- Median `|Delta F| = 2.543 N`.
- Median `Delta Bvec = 265.8 uT`.

**Interpretation.** The active path-pair mechanism remained strong in an interleaved held-out d grid, so the phenomenon was not limited to the exact training-grid points.

### 6.2 standard held-out model validation

**Purpose.** Train on Stage 5 data and test on the complete held-out Stage 6.1 session.

**Key results.**

| Model | F MAE (N) | d MAE (mm) | Interpretation |
|---|---:|---:|---|
| plain magnetic ridge | 1.774 | 0.051 | baseline |
| path-label ridge | 1.096 | 0.041 | best balanced standard held-out model |
| path-memory RF | 1.021 | 0.071 | best force model |

**Interpretation.** Standard path-label/path-memory models improved force prediction relative to plain magnetic regression, but the force MAE still did not meet the original `0.50 N` target. This motivated the Stage 6.3 local-identifiability model.

### 6.3 APMD local-identifiability model comparison

**Purpose.** Test whether Stage 4 sensitivity geometry provides information beyond simple loading/unloading/preload labels.

**Models compared.**

- Plain magnetic ridge.
- Lim-style branch-label ridge.
- APMD path-memory models.
- APMD local-identifiability models using Stage 4 `j_F/j_d` projection features and local zone information.

**Key results.**

| Model | F MAE (N) | d MAE (mm) | Status |
|---|---:|---:|---|
| plain magnetic ridge | 1.774 | 0.051 | weak baseline |
| Lim-style branch-label ridge | 1.096 | 0.041 | label compensation baseline |
| APMD local-ID RF | 0.128 | 0.086 | best force |
| APMD local-ID ridge | 0.286 | 0.036 | best balanced |

**Main interpretation.** The local-identifiability ridge reduced force MAE by `73.9%` relative to the Lim-style branch-label baseline while also passing the displacement target. This is the strongest current model-level support that APMD is not merely labeling hysteresis branches, but using actively measured local response geometry to improve decoupling.

---

## Stage 7: Mechanism Controls

### 7.1 no-contact motion artifact control

**Purpose.** Test whether the observed magnetic split could be caused by Mark-10 motion, electronics, or environmental magnetic drift without contact.

**Formal data.**

- Session: `session_20260616_152850`.
- Motion replay: nominal `3.40 -> 3.80 -> 3.40 mm` with no contact.
- 3 trials.

**Key results.**

- No-contact motion Delta Bvec: `1.29-2.03 uT`.
- B0 drift Delta Bvec: `3.37 uT`.
- Both were below the `10 uT` artifact gate.

**Interpretation.** The active path-pair magnetic splits of hundreds of uT cannot be explained by no-contact motion artifact or B0 drift.

### 7.2 repeated-loading control without deeper preload

**Purpose.** Test whether repeated loading to the same target state alone can create a magnetic change comparable to active path-pair excitation.

**Formal data.**

- Session: `session_20260616_170608`.
- Target `d = 3.40 mm`.
- Five repeated loading cycles without deeper preload.

**Key results.**

- Fixed target position was maintained across cycles.
- Force stayed near `10.27-10.31 N`.
- Maximum cycle-to-cycle Delta Bvec vs cycle 1 was `34.1 uT`.
- All cycles passed the `50 uT` low-memory control gate.

**Interpretation.** Repeating the loading branch alone did not reproduce the strong active path-pair magnetic split. This supports the claim that the deeper preload and return path are necessary active excitations.

---

## Integrated Claim-Evidence Map

| Claim | Evidence | Status |
|---|---|---|
| Active path-pair excitation creates separable magnetic states under controlled variables. | Stage 3.1: 21/21 same-d pairs strong; Stage 3.2: 1.50-4.90 N same-F pairs strong. | Supported |
| Maximum historical compression is a stronger path-dose variable than dwell time. | 3.3A and 3.4A show stronger effects with larger preload depth/extra depth; 3.3B and 3.4B show weak or non-monotonic hold-time effects. | Supported |
| Path memory persists over the tested recovery window. | 3.5A remains strong at 30/120/300 s recovery, with Delta Bvec decreasing only mildly from 253.4 to 230.5 uT. | Supported |
| Local magnetic response directions can be used for decoupling. | Stage 4 identifies a local `j_F/j_d` candidate with angle 48.5 deg and scaled condition 2.22. | Supported locally |
| Local-identifiability features outperform simple branch-label compensation. | Stage 6.3 local-ID ridge improves force MAE by 73.9% relative to Lim-style branch-label ridge while maintaining d MAE 0.036 mm. | Supported locally |
| The observed magnetic split is not a motion artifact. | Stage 7.1 no-contact Delta Bvec <= 2.03 uT and B0 drift 3.37 uT, far below active path-pair response. | Supported |
| The observed magnetic split is not caused by repeated loading alone. | Stage 7.2 repeated loading max Delta Bvec 34.1 uT, below 50 uT gate and far below active path-pair response. | Supported |
| The method is ready for full prosthetic-socket force range. | Current data are local bench-top mechanism-validation data, not full socket-range deployment. | Not yet supported |

---

## Current Overall Conclusion

The current evidence supports the central APMD mechanism: actively constructed path pairs can use soft-material hysteresis and preload history as controlled excitation sources for magnetic force-displacement decoupling. Stage 3 established the phenomenon across same-d/different-F and same-F/different-d designs. Stage 4 converted the phenomenon into local sensitivity geometry. Stage 5-6 showed that this geometry improves local held-out prediction beyond plain magnetic regression and simple branch-label compensation. Stage 7 ruled out two major alternative explanations: no-contact motion artifact and repeated loading without deeper preload.

The claim should remain bounded. The current result is a local mechanism-validation and modeling result in the bench-top setup. It does not yet claim full-range prosthetic-socket deployment, cross-day stability, or robustness across different sample geometries and interface conditions.

## Recommended Next Step

For the immediate report or proposal, the next step should be integration rather than more routine acquisition:

1. Build a final Stage 3-7 evidence figure set:
   - Stage 3.1 same-d work-zone figure.
   - Stage 3.2 same-F work-zone figure.
   - Stage 3.3-3.5 path-dose and recovery figure.
   - Stage 4 local identifiability figure.
   - Stage 6.3 model comparison figure.
   - Stage 7 control figure.
2. Write the Results narrative around the evidence chain:
   - controlled active path pairs,
   - path-dose controllability,
   - local sensitivity separation,
   - held-out model improvement,
   - artifact and repeated-loading controls.
3. Keep Stage 7.3 cross-day repeatability as optional follow-up, not required for the current mechanism proof.
4. Reserve additional data acquisition for targeted needs:
   - cross-day repeatability,
   - larger socket-like force range,
   - different interface/material conditions,
   - model failure zones identified by prediction residuals.
