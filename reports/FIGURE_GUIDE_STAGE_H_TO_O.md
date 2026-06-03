# Figure Guide: Stage H to Stage O

This guide is for the weekly group meeting. It separates figures into:

- Positive evidence: figures that support the current identifiability claim.
- Diagnostic evidence: figures that explain why a protocol was changed.
- Backup figures: useful if asked, but not necessary for the main story.

## Slide-Level Story

The story should be:

1. Stage H motivated force-related magnetic testing.
2. Passive Stage I/J holds were not strong enough for decoupling evidence.
3. I+ and J+ path-pair protocols produced cleaner local perturbations.
4. I+/J+ estimated force and displacement directions are separated.
5. The first blind test failed because the assembly/B0 state changed across
   sessions.
6. We will restart with a new indenter and collect I+ -> J+ -> O in one stable
   setup.

## Stage H Figures

### `reports/figs/H_main.png`

Purpose:

- Use as the bridge from last week's report.
- Shows that force-controlled/mechanically loaded states produce measurable
  magnetic changes.

How to read it:

- Look for whether magnetic magnitude and/or individual axes change when force
  changes.
- The key message is not yet "decoupling"; it is "there is signal worth
  testing more rigorously."

How to say it:

> Stage H showed that the magnetic signal responds during force-related
> loading, so this week I moved from correlation to identifiability: can the
> signal separate force and displacement?

Use:

- Optional first slide if the professor needs continuity from last week.

### `reports/figs/H_compare_EFH.png`

Purpose:

- Compare Stage E/F/H trends.

How to read it:

- Use it only to show that different protocols occupy related but not identical
  regions of the force-displacement-magnetic state space.

Use:

- Backup, not a main slide.

## Stage I: Fixed-Displacement Hold

### `reports/figs/I_failure_diagnostic.png`

Purpose:

- Diagnostic figure.
- Shows why passive fixed-displacement hold is not enough for `j_F`.

How to read it:

- Left panel: force relaxes over time while `d` is fixed.
- Middle panel: `|B|` drift is small and inconsistent, after removing obvious
  serial/outlier spikes for display.
- Right panel: the passive relaxation signal fails the `j_F` gate; the force
  relaxation exists, but median `R2` remains low.

How to say it:

> The fixed-displacement hold did create force relaxation, but the magnetic
> response during that passive relaxation was weak and inconsistent. So I did
> not use Stage I as the primary force-column evidence.

Use:

- Include as a "why we changed protocol" slide.

Do not say:

- Do not say this proves `j_F`.
- Do not use it as the main evidence for force decoupling.

### `reports/figs/I_main.png`

Purpose:

- Raw descriptive Stage I figure.

Use:

- Backup only. It contains raw traces and occasional spikes, so it is less
  suitable for the main talk than `I_failure_diagnostic.png`.

### `reports/figs/I_jF.png`

Purpose:

- Diagnostic gate figure for Stage I.

How to read it:

- It estimates first-pass slopes between magnetic features and force relaxation.
- Low `R2` values mean the passive relaxation did not provide a reliable local
  Jacobian column.

How to say it:

> The automated gate confirmed this: none of the passive Stage I holds passed
> the excursion and linearity criteria.

Use:

- Backup or one small inset if you want quantitative justification.

## Stage I+: Same-d / Different-F Path Probe

### `reports/figs/Iplus_same_d_diff_f.png`

Purpose:

- Positive evidence for the force/path column `j_F`.

How to read it:

- Panel a: direct and return states are at nearly matched displacement, but
  force is different by about `438-507 mN`.
- Panel b: the gates show displacement mismatch is small, force split is large
  enough, and magnetic vector change is above noise.
- Panel c: three-axis magnetic response changes between return and direct
  states.

How to say it:

> I+ intentionally constructs the perturbation that Stage I could not produce
> cleanly: approximately same displacement, different force/path state. All
> three repeats pass the live gates, so this gives stronger `j_F` evidence.

Key numbers:

- I+ session `session_20260601_160931`: `3/3` usable pairs.
- Median magnetic vector change: about `140.6 uT`.
- Median estimated force column:

```text
j_F = (30.8, -88.4, 267.2) uT/N
```

Use:

- Main positive evidence slide.

## Stage J: Fixed-Force Hold

### `reports/figs/J_failure_diagnostic.png`

Purpose:

- Cleaned diagnostic figure replacing the old misleading `J_main.png`.
- Shows why the original Stage J fixed-force hold should not be used as
  positive `j_d` evidence.

How to read it:

- Left panel: force does not remain fixed; one hold jumps far above target.
- Right panel: the controller keeps nudging displacement instead of producing
  a stable fixed-force creep segment.

How to say it:

> The original fixed-force hold was not reliable enough. The force did not
> stay fixed, and the controller kept moving the stage. Therefore I treated
> Stage J as a diagnostic failure and redesigned it as J+.

Use:

- Use this instead of `reports/figs/J_main.png`.

Do not use:

- Do not use `reports/figs/J_main.png` as a positive result. It includes
  invalid/unstable segments and can be misleading.

### `reports/figs/J_jq.png`

Purpose:

- Old diagnostic slope plot.

How to read it:

- Low `R2` and unstable slopes mean fixed-force hold does not provide reliable
  `j_d` evidence.

Use:

- Backup only. The cleaned `J_failure_diagnostic.png` is clearer for group
  meeting.

## Stage J+: Same-F / Different-d Path Probe

### `reports/figs/Jplus_success_only.png`

Purpose:

- Positive evidence for the displacement/path column `j_d`.
- This is the preferred J+ figure for group meeting.

How to read it:

- Left panel: loading and unloading force states are approximately matched.
- Middle panel: despite similar force, displacement differs by about
  `0.24-0.31 mm`.
- Right panel: the three-axis magnetic signal changes strongly between those
  two states.

How to say it:

> J+ constructs the complementary perturbation to I+: approximately same force,
> different displacement/path state. In the strong pairs, the force is matched,
> displacement separates, and the 3-axis magnetic vector changes clearly.

Key numbers:

- J+ session `session_20260602_103531`: `4/6` usable strong pairs.
- Median magnetic vector change: about `820.1 uT`.
- Median estimated displacement column:

```text
j_d = (-552.2, 3299.2, 544.5) uT/mm
```

Use:

- Main positive evidence slide.

### `reports/figs/Jplus_same_f_diff_d.png`

Purpose:

- Full J+ diagnostic figure including all pairs.

How to read it:

- It shows both strong and weaker/borderline pairs.
- Useful if asked about repeatability and why not every pair is perfect.

Use:

- Backup or appendix.

## Identifiability Summary

### `reports/STAGE_N_identifiability_readiness.md`

Purpose:

- Text/table evidence that combines I+, J+, and earlier stages.

How to read it:

- The most important line is:

```text
Pair-column angle = 80.2 deg, abs cosine = 0.17
```

How to say it:

> The force-column and displacement-column estimates are not collinear. This
> supports local identifiability, although the full readiness gate is not yet
> open because passive holds, small-q calibration, and blind validation still
> need improvement.

Use:

- One summary slide with the key numbers, not necessarily a screenshot.

## Stage O Blind Test

### `reports/BLIND_TEST_ANALYSIS.md`

Purpose:

- Blind-test result table.

How to read it:

- Main model `Bxyz -> [F,d]` must beat baselines.
- It did not:

```text
Bxyz -> F MAE = 6.31 N
baseline F=h(d) MAE = 0.96 N

Bxyz -> d MAE = 2.91 mm
baseline d=g(|B|) MAE = 0.36 mm
```

How to say it:

> The first blind test failed, but the failure is diagnostic. The magnetic
> baseline/geometry changed between calibration and blind sessions, so the
> model was extrapolating across assemblies rather than testing decoupling
> within one stable setup.

Important explanation:

```text
I+ training:    delta_Bz about 4287-5655 uT
J+ training:    delta_Bz about 4251-4765 uT
Stage O blind:  delta_Bz about 292-714 uT
```

Use:

- Main "limitation / next step" slide.

## Recommended PPT Figure Set

Main deck:

1. `H_main.png` if needed for continuity.
2. `I_failure_diagnostic.png` as passive hold diagnostic.
3. `Iplus_same_d_diff_f.png` as positive `j_F` evidence.
4. `J_failure_diagnostic.png` as Stage J failure/reason for redesign.
5. `Jplus_success_only.png` as positive `j_d` evidence.
6. A text/table slide with pair-column angle `80.2 deg`.
7. A text/table slide from `BLIND_TEST_ANALYSIS.md`.
8. Final plan slide: new indenter, repeat I+ -> J+ -> O in one stable setup.

Backup:

- `I_jF.png`
- `J_jq.png`
- `Jplus_same_f_diff_d.png`
- `H_compare_EFH.png`

## One Clean Verbal Script

> After Stage H, I tested whether the magnetic response can support actual
> force-displacement decoupling. Passive fixed-displacement and fixed-force
> holds were useful diagnostics, but not strong enough to estimate reliable
> Jacobian columns. I therefore redesigned the experiments into pairwise path
> probes. I+ gives same-displacement/different-force states, and J+ gives
> same-force/different-displacement states. These two protocols produced
> separated magnetic directions, with a pair-column angle around 80 degrees.
> The first blind test did not pass because the calibration and blind sessions
> were not in the same magnetic baseline/geometry state. Also, the current
> indenter causes instability near the high-displacement preload region. So the
> next step is to change the indenter and repeat I+, J+, and O continuously in
> one unchanged setup.
