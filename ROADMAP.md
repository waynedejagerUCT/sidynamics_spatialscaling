# Roadmap: SEAICE_DYN_003 scale-dependent kinematics

Living document. Update task status as work completes. Scientific goals: [ProjectOutline.md](ProjectOutline.md). Model setup: [TechnicalScientificReference_SEAICE_DYN_003_v5.md](TechnicalScientificReference_SEAICE_DYN_003_v5.md).

**Last updated:** 2026-10-19

**Status key:** ✅ done · 🟡 in progress · ⬜ not started (unblocked) · ⛔ blocked (see *Blocked by*)

**Data versions**
- **v1:** current local output. ORCA2–ORCA025, 18 Mar – 31 Oct 2019, 8 `_icemod` fields.
- **v2:** rerun with 29 `_icemod` fields (v1 fields + partition, momentum balance, snow mass, native deformation, rheology state, `beta_evp`) and `nn_nevp = 500` (ORCA2–ORCA025; v1 used 100).
- **ORCA025 solver test (A17):** ORCA025 at `nn_nevp` = 100 (v1), 500 (v2) and 2000 (v2 configuration). ORCA025 v1 is therefore kept locally.

## Section overview

| # | Section | Status | Can start now? | Blocked by |
|---|---|---|---|---|
| A | Model reruns (WP2.1) | 🟡 | Yes | — |
| B | Observational data holdings | 🟡 | Yes | — |
| C | Shared foundations | ⬜ | Yes | — |
| D | Velocity-gradient diagnostics | ⬜ | Partly | C |
| E | Scaling with averaging scale | ⛔ | No | D |
| F | Vorticity attribution | ⛔ | No | D; A (v2) for momentum terms; A17 (ORCA025 100/500/2000) for the numerical test |
| G | Lagrangian analysis | ⬜ | Partly | C |
| H | Storm composites and case studies | ⛔ | No | D, E |
| I | Eq. 1 partition | ⛔ | Obs side partly | C, B4; A (v2) for model side |
| J | Synthesis | ⛔ | No | D–I |
| K | WP3 deployment design | ⛔ | No | A (GLOB16 2022), G |

Sections C, D, E and G and the observed side of I run on **v1 data**. The v2 reruns block only the momentum-balance, native-deformation and model-partition tasks.

---

## A. Model reruns (WP2.1)

**Status:** 🟡 · **Runs on:** produces v2 data · HPC

### Rerun status per member

| Member | v1 (2019, 8 fields) | v2 config generated | v2 72-step validation | v2 production | v2 archived locally | `nn_nevp` | 2022 run |
|---|---|---|---|---|---|---|---|
| ORCA2 | ✅ local | ✅ (29 fields, `nn_nevp = 500`; regenerated for production) | ✅ | ✅ job 1502542 (55:50; 1.8 GB) | ⬜ | 500 | ⛔ A10 |
| ORCA1 | ✅ local | ✅ | — (covered by ORCA2) | ✅ job 1502660 (1:28:31; 7.1 GB) | ⬜ | 500 | ⛔ A10 |
| ORCA05 | ✅ local | ✅ (A7 link verified) | — (covered by ORCA2) | ✅ job 1503915 (3:36:31; 41 GB; `namelist_cfg` hand-edited, see A6) | ⬜ | 500 | ⛔ A10 |
| ORCA025 | ✅ local (keep: A17 `nn_nevp = 100` member) | ⬜ | — (covered by ORCA2) | ⛔ A4 (scratch space; est. 7–9 h) | ⛔ | 500 | ⛔ A10 |
| ORCA025 (`nn_nevp = 2000`, A17; third setting after 100 and 500) | — | ⬜ | — (covered by ORCA2) | ⛔ A6 (ORCA025 at 500), A4 | ⛔ | 2000 | — |
| GLOB16 | ⛔ pending | ⬜ | ⛔ A3 | ⛔ A4, A11 | ⛔ A5 | open (A11) | ⛔ A10, A11 (WP3 reference) |

v1 output was removed from the HPC on 2026-10-16. Local copies are kept, and run records are in `~/Data/NEMO/SEAICE_DYN_003/SEAICE_DYN_003_runrecords.tgz`.

### Tasks

| ID | Task | Status | Blocked by |
|---|---|---|---|
| A1 | Map required outputs to SI3 field IDs; check `iom_put` calls and grids | ✅ | — |
| A2 | Add 21 fields to `common/file_def_nemo-ice.xml` (`_icemod`, 29 total), incl. `beta_evp` (+~3.7 GB ORCA025 uncompressed) | ✅ | — |
| A3 | ORCA2 72-step validation: 29 fields present, new ones non-zero over ice; `nn_nevp = 500` read by NEMO. Run 1 (job 1501899): 24/29 ok, `NN_NEVP=500` read; ridging/rafting fields never written (A14). Run 2 (job 1502021, 1:14, rebuilt `nemo.exe`): all 29 fields written; ridging ~1e-9 s⁻¹, rafting ~0, `lead_open` zero (filled by source; plausible after 18 h; kept). Output deleted; ORCA2 regenerated with production values | ✅ | — |
| A4 | Storage: **compression deferred** (only if required later; measured `nccopy -d 1 -s` 5.0× on ORCA2 validation). **HPC:** v2 output held on scratch until quota is reached, then downloaded. `quota -s` reports 0 (unusable) → measure with `du -sh /scratch/djgway001`. 2026-10-19, after clean-up (v2 restarts of ORCA2–05, Gate T0 netCDF in `VALIDATION/` 17.2 GB, global T0 weights, ORCA05 weights `.work/` and `*.compacted_BROKEN`, XIOS by-products, failed-job logs): **178 of 250 GB used, ~72 GB free**, holding ORCA2+ORCA1+ORCA05 v2 (~50 GB). **ORCA025 (~105–118 GB output + ~4 GB restarts) is blocked until ORCA2–ORCA05 are downloaded and cleared.** **Local:** v2 ORCA2–025 ≈ 175 GB vs 136 GB free; fits only if v1 (~62 GB) is replaced, **except ORCA025 v1**, which A17 needs as its `nn_nevp = 100` member. The A17 run (ORCA025, `nn_nevp = 2000`) needs another ~118 GB for a full season | ⬜ | — |
| A5 | Decide where GLOB16 is stored (≈ 1.5 TB uncompressed v2; 250 GB scratch quota) | ⛔ | A4 |
| A6 | Production v2 runs, cheapest first: ORCA2 → ORCA1 → ORCA05 → ORCA025 (ORCA025 ≈ 7–9 h at `nn_nevp = 500`, from ORCA05). ORCA2 ✅ 2026-10-18 (job 1502542): `verify_logs.sh` all PASS except stale validation restarts (step 72; delete); 55:50 vs v1 35:53 (1.56×) → rheology ≈ 14% of v1 runtime at ORCA2; MaxRSS 19.7 GB (v1 14.3); 1.8 GB (2.8× v1); all 29 fields written. In-model `beta_evp` max 666 (Oct), 0.0018% of ice cells > 500 — above the offline v1 estimate (max ~125), so the offline estimate may be biased **low** (better-converged v2 → lower Δ in compact ice → higher β); recheck the ORCA025 tail from its v2 `beta_evp`. ORCA1 ✅ (job 1502660): `verify_logs.sh` 0 FAIL; 1:28:31 vs v1 56:25 (1.57×, rheology ≈ 14% of v1 runtime, same as ORCA2); MaxRSS 13.2 GB; 7.1 GB; 29 fields ok; `beta_evp` Oct 99th 113 (offline v1 Sep estimate 57), max 857, 0.0004% > 500 — offline estimate again ~2× low. Revised estimates: ORCA05 ≈ 3–3.5 h, ORCA025 ≈ 6–8 h if rheology share stays ~14–20% (was 16–20 h). ORCA05 ✅ (job 1503915; 1502968 OOM-killed, A15): `verify_logs.sh` all PASS; 3:36:31 vs v1 2:01:12 (**1.79×** → rheology ≈ 20% of v1 runtime; share grows with resolution) → ORCA025 ≈ 7–9 h; MaxRSS 36.9 GB on task 0 (a NEMO rank; v1 39 GB); 41 GB, 31 files, 29 fields; `beta_evp` field check not yet run. **Hand edit:** ORCA05 `namelist_cfg` carries `nn_stocklist = 21888` only (`! DIAGNOSTIC`) — restart point only, no physics/output change (`namelist_ice_cfg`, `file_def_nemo-ice.xml` identical to ORCA1). Breaks the regenerate-don't-hand-patch rule: keep ORCA05's `namelist_cfg` as the true record and **do not regenerate ORCA05 before its config files are downloaded**. `verify_production.py` passed for ORCA2, ORCA1, ORCA05 (v2); their restarts then deleted. `setup_production.sh` (modified 2026-10-19 09:36) confirmed to differ from `.bak_stepmem` only by `--mem=0` on its two `srun` lines (297 dry-run echo, 308 launch), so it is clean for generating ORCA025. `lead_open` zero over ice in every month checked (kept for consistency across members; uninformative) | 🟡 | — |
| A7 | ORCA05 ice-weights name: correctly spelt `weights_bilin_glorys_orca05_ant40s_ice.nc` exists in `inputs/ORCA05_ANT40S/weights/`; no misspelt file (v1 link target `weights_bilinglorys_…` likely a stale link or paste artefact). After regenerating ORCA05, confirm the link resolves (`ls -lL`). `*.compacted_BROKEN` leftovers there can be deleted. Verified 2026-10-18: regenerated ORCA05 link resolves (17.7 MB); ORCA05 v2 ran on it (job 1503915). `*.compacted_BROKEN` files deleted 2026-10-19 | ✅ | — |
| A8 | ~~Solver variant runs (`--variant`)~~ dropped as a general sweep; replaced by one targeted three-setting test at ORCA025 (A17: `nn_nevp` 100/500/2000) alongside `beta_evp` maps (F4) | ✅ superseded by A17 | — |
| A9 | `rn_relast` under aEVP: unused (standard-EVP branch only, `icedyn_rhg_evp.F90:236-238`); `nn_nevp` is an iteration count. Offline β estimate (`scripts/estimate_beta_evp.py`) → decision: keep aEVP, `nn_nevp = 500` for ORCA2–ORCA025, `nn_rhg_chkcvg = 0` | ✅ | — |
| A10 | Decide whether the full hierarchy also runs 2022 | ⬜ | — |
| A11 | GLOB16: segment driver, memory decision, and `nn_nevp` (β ≈ 4× ORCA025; ~2000 iterations for equal convergence). The A17 convergence trend (100/500/2000 at ORCA025) informs the choice | ⬜ | — |
| A12 | Update the technical reference with v2 outputs | ⛔ | A6 |
| A13 | Apply `nn_nevp = 500` via `common/namelist_ice_cfg.template`; regenerate ORCA2 (29 fields, `nn_nevp = 500`) | ✅ | — |
| A15 | `srun` step memory: step got only `ntasks × 8000 MB` (ORCA05: 144 GB) despite full-node job; an XIOS server needed 113 GB (v2 has ~47 output fields vs ~26) → `OUT_OF_MEMORY` (job 1502968). Fix: `srun --mpi=pmix --mem=0 …` on both `srun` lines of `setup_production.sh` (backup `.bak_stepmem`); ORCA05 cleaned, regenerated, resubmitted (job 1503875). Confirmed by ORCA05 job 1503915 (completed). Note the step receives `mem=300G` even with `--mem=0` (job holds 375 GB): **300 GB is the effective step ceiling**. Recorded in technical reference | ✅ | — |
| A16 | ORCA025 XIOS memory risk: **low.** XIOS server memory reports show 8 KB buffers per client (32 KB total at ORCA2, 64 KB ORCA1, ~96 KB ORCA05), so XIOS is not the steady-state consumer; the 113 GB in job 1502968 was an artefact of the 144 GB step cap or a start-up transient. ORCA05 v2 peaked at 36.9 GB on a NEMO rank. Expected ORCA025 peak ~45–60 GB vs the 300 GB step ceiling. No XIOS change; watch `sstat` for the first 15 min of ORCA025 | ✅ | — |
| A14 | Ridging diagnostics fix: `ll_diag_rdg` set in `ice_dyn_rdgrft_init` via `iom_use()` before XIOS closedef → always `.FALSE.`. `MY_SRC/icedyn_rdgrft.F90` sets it `.TRUE.` (diagnostics only); `nemo.exe` rebuilt 2026-10-18 12:25. Confirmed in A3 run 2; recorded in technical reference build section | ✅ | — |
| A17 | **Three-setting solver-sensitivity test at ORCA025 (WP2.1 numerical control), committed 2026-10-19.** Compare ORCA025 at `nn_nevp` = **100** (v1, held locally), **500** (v2 production, A6) and **2000** (new run, v2 configuration otherwise identical to the 500 run). Three settings show the convergence trend: is the 500→2000 change smaller than the 100→500 change, and does it shrink at a rate that fits ~exp(−N/β)? One pair alone can't show that. **Compare:** vorticity, deformation, the vorticity/deformation ratio, drift, concentration and thickness, binned by β. Use in-model `beta_evp` for 500 and 2000, and the offline estimate (`scripts/estimate_beta_evp.py`) for 100, since v1 has no `beta_evp` field. Comparisons that include 100 are limited to the 8 v1 fields. **Why:** `beta_evp` masking alone is weakest for vorticity. β rises as Δ falls, so rotation-dominated, low-deformation ice is the least converged, and masking it would remove the cases the vorticity test needs. Masking also misses non-local effects of unconverged stress on later ice state. This test measures the numerical sensitivity directly at the finest completed member, and informs GLOB16 `nn_nevp` (A11). **Preconditions:** (i) keep ORCA025 v1 locally even if other v1 members are replaced (A4); (ii) confirm from the run records (`SEAICE_DYN_003_runrecords.tgz` vs v2 namelists) that v1 and v2 ORCA025 differ physically only in `nn_nevp`. The v2 changes to output fields, the ridging-diagnostic source fix and `srun --mem=0` should not affect the solution. **Steps:** 100 vs 500 can start once ORCA025 v2 at 500 is downloaded; the 2000 run starts after ORCA025 at 500 production completes (A6). **Cost of the 2000 run (unmeasured):** rheology ≈ 20% of v1 runtime per 100 iterations at ORCA05 (14% at ORCA2/ORCA1) → ~18–24 h if ORCA025 at 500 takes 7–9 h; storage ~118 GB for a full season (A4). **Open:** 2000 run over the full season (18 Mar – 31 Oct) or a shorter window (e.g. July, to overlap the swath data); if a window, all three settings are compared over it | ⛔ | A6 (ORCA025 at 500), A4 |

---

## B. Observational data holdings

**Status:** 🟡 · **Runs on:** observational data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| B1 | OSISAF 455 daily, 75 km, 1990–2025 (`~/Data/seaicedrift/osisaf/24hr/south/merged`) | ✅ held | — |
| B2 | OSISAF S2S swath, 62.5 km, only 13–31 Jul 2019 held; decide whether to extend to the full 2019 season | ⬜ | — |
| B3 | Per-retrieval uncertainty: RO1 products pending; interim uses OSISAF native uncertainty fields | ⬜ | — |
| B4 | Sea-ice concentration product (needed for Eq. 1 obs side and state comparison): none located locally | ⬜ | — |
| B5 | Drifting-buoy reference: AWI 2019 buoys (`~/Data/insitu/AWIbuoys`), ISVP (`drift_bouys`); check coverage against model period | ⬜ | — |

---

## C. Shared foundations

**Status:** ⬜ · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| C1 | NEMO reader (note: monthly files split from the run start, e.g. `_201903-201904` = 18 Mar–18 Apr, 248 records; not calendar months): C-grid positions (`glamu/v/f`, `gphiu/v/f`), masks, metrics from `domain_cfg_<RES>_ANT40S.nc` | ⬜ | — |
| C2 | OSISAF 455 and swath readers (grids, time windows, uncertainty, flags) | ⬜ | — |
| C3 | Time matching: integrate 3 h model velocity over each satellite displacement window (24 h / swath pair) | ⬜ | C1, C2 |
| C4 | Regridding and coarsening to common effective scale (explicit scale parameter) | ⬜ | C1, C2 |
| C5 | Uncertainty propagation through coarsening and gradients | ⬜ | C2, B3 (interim OK) |

---

## D. Velocity-gradient diagnostics (divergence, shear, total deformation, vorticity)

**Status:** ⬜ · **Runs on:** v1 data (D1–D5); v2 data (D6) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| D1 | C-grid operators: divergence (T), vorticity (F), shear, total deformation | ⬜ | C1 |
| D2 | Synthetic-field tests (solid-body rotation, pure divergence) on trimmed ORCA grids | ⬜ | D1 |
| D3 | First complete case: ORCA025 vs OSISAF 455, Mar–Oct 2019, at common scale | ⬜ | D2, C3–C5 |
| D4 | Extend to all members; vorticity/deformation ratio; significance masks | ⬜ | D3 |
| D5 | Swath comparison (Jul 2019 window) | ⬜ | D4, B2 |
| D6 | Check offline operators against native `icediv`/`iceshe` | ⛔ | A6 |

---

## E. Scaling with averaging scale

**Status:** ⛔ · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| E1 | Repeat D at multiple coarse-graining scales; scaling exponents per member and obs | ⛔ | D4 |
| E2 | Identify the scale at which vorticity and deformation features are resolved or lost | ⛔ | E1 |

---

## F. Vorticity attribution (outline sequence, steps 1–3)

**Status:** ⛔ · **Runs on:** v1 data (F1–F2); v2 data (F3–F4) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| F1 | Step 1: locate vorticity misfits beyond retrieval uncertainty | ⛔ | D4 |
| F2 | Step 2a: test against curl of air–ice and ocean–ice stress, and ocean-current vorticity (v1 fields) | ⛔ | F1 |
| F3 | Step 2b: test against internal stress, Coriolis and tilt (`intstrx`, `corstrx`, `dssh_dx`) | ⛔ | F1, A6 |
| F4 | Step 2c: numerical contribution, using two pieces of evidence: (i) `beta_evp` maps, binning misfits by β/`nn_nevp` and flagging cells with β ≳ `nn_nevp`; (ii) the ORCA025 `nn_nevp` 100/500/2000 sequence (A17), compared with the misfit. If the misfit is larger than the 500–2000 difference and that difference is shrinking with N, numerics are excluded at ORCA025 | ⛔ | F1, A6, A17 |
| F5 | Step 3: interpret any residual (continuum / rotational physics) | ⛔ | F2–F4 |

---

## G. Lagrangian analysis

**Status:** ⬜ · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| G1 | Parcels/OpenDrift setup with native C-grid velocities; seeding strategy | ⬜ | C1 |
| G2 | Observed trajectories from OSISAF fields (and buoys, B5) | ⬜ | C2 |
| G3 | Pathways, cumulative distance, retention zones | ⬜ | G1, G2 |
| G4 | Single-parcel and pair dispersion | ⬜ | G1, G2 |
| G5 | Meandering index (model subsampled to satellite timestep) | ⬜ | G1, C3 |
| G6 | Parcel-triangle deformation and rotation; cross-check with D | ⬜ | G1, D4 |

---

## H. Storm composites and case studies (WP2.4)

**Status:** ⛔ · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| H1 | Storm detection/tracking (ERA5 or `_sbcwind` `wspd`) | ⬜ | — |
| H2 | Storm-relative composites of vorticity and deformation | ⛔ | H1, D4 |
| H3 | Cyclone case studies (prefer events in the swath window) | ⛔ | H2, D5 |

---

## I. Eq. 1 partition (WP2.3)

**Status:** ⛔ · **Runs on:** observational data (I1); v2 data (I2) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| I1 | Observed: advective terms from drift, Θ as residual | ⛔ | C4, B4 |
| I2 | Model: advective = `afxdyn` − net ridging/rafting; non-advective = `afxthd` + net ridging/rafting | ⛔ | A6 |
| I3 | Compare over matched time windows and effective scale | ⛔ | I1, I2 |

---

## J. Synthesis

**Status:** ⛔ · **Runs on:** v1 and v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| J1 | Localise model deficiencies by variable, region, season and scale | ⛔ | D–I |
| J2 | Update README Aim/Approach with results | ⛔ | J1 |

---

## K. WP3 deployment design

**Status:** ⛔ · **Runs on:** v2 data (GLOB16 2022) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| K1 | Evaluate GLOB16 2022 reference realisation against retrievals (MIZ focus) | ⛔ | A10, A11 + GLOB16 2022 run, D |
| K2 | Lagrangian release experiments for candidate array geometries | ⛔ | K1, G6 |
| K3 | Array design and site recommendations for InSync Theme 2 | ⛔ | K2 |
