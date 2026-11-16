# Roadmap: SEAICE_DYN_003 scale-dependent kinematics

Living document: what is done and what is left. Scientific goals: [ProjectOutline.md](ProjectOutline.md). How the data were generated (configuration, set-up, compute environment, scientific choices): [TechnicalScientificReference_SEAICE_DYN_003_v5.md](TechnicalScientificReference_SEAICE_DYN_003_v5.md) ("tech ref").

**Last updated:** 2026-11-16 · All simulation and analysis use the 2019 season (18 Mar – 31 Oct); no 2022 runs planned.

**Status key:** ✅ done · 🟡 in progress · ⬜ not started, unblocked · ⛔ blocked (a task in *Blocked by* is not done)

**Data:** v1, v2 and `ORCA025_NEVP2000` — definitions and locations in README §Data; configuration in tech ref §1. **Analysis uses v2** (decided 2026-11-11); v1 only as the `nn_nevp = 100` setting of the ORCA025 solver test (A16, F6).

## Section overview

| # | Section | WP | Status | Open / unblocked | Blocked by |
|---|---|---|---|---|---|
| A | Model runs | 2.1 | 🟡 | 5 / 3 | — |
| B | Observational data holdings | 2.2 inputs | 🟡 | 4 / 4 | — |
| C | Shared foundations | 2.2 | 🟡 | 6 / 2 | — |
| D | Velocity-gradient diagnostics | 2.2 | 🟡 | 6 / 3 | C |
| E | Scaling with averaging scale | 2.2 | ⛔ | 2 / 0 | D4 |
| F | Vorticity attribution | 2.2 | 🟡 | 6 / 1 | D4 |
| G | Lagrangian analysis | 2.2 | ⛔ | 6 / 0 | C1, C2, C6 |
| H | Storm composites and case studies | 2.4 | ⬜ | 3 / 1 | D4, D5 |
| I | Eq. 1 partition | 2.3 | ⬜ | 3 / 1 | C4, B4 |
| J | Synthesis | 2.2–2.4 | ⛔ | 2 / 0 | D–I |
| K | Deployment design | 3.1–3.2 | ⛔ | 3 / 0 | A20, D, G6 |

**Next up** (proposed order)
1. C2–C5, C7: comparison pipeline (design note revised to the spatial outline 2026-11-16, under review; temporal matching, C3, is the next discussion; unblocks D3, G2).
2. D2 and D6: operator tests into the repository; native `icediv`/`iceshe`.
3. F6: ORCA025 solver-test comparison binned by β (needs v1 and the 2000 run from the HDD).
4. B2 and B4 decisions: swath extension; concentration product.

---

## A. Model runs (WP2.1)

**Status:** 🟡 · **Runs on:** HPC

### Run status per member

| Member | v1 (8 fields) | v2 config | v2 validation | v2 production | v2 archived | `nn_nevp` |
|---|---|---|---|---|---|---|
| ORCA2 | ✅ | ✅ | ✅ | ✅ | ✅ HDD | 500 |
| ORCA1 | ✅ | ✅ | — (via ORCA2) | ✅ | ✅ HDD | 500 |
| ORCA05 | ✅ | ✅ (hand-edited, A6) | — (via ORCA2) | ✅ | ✅ HDD | 500 |
| ORCA025 | ✅ (A16 100 setting) | ✅ | — (via ORCA2) | ✅ | ✅ local + HDD | 500 |
| ORCA025_NEVP2000 | — | ✅ (hand-copy exception, A16) | — | ✅ | ✅ local + HDD | 2000 |
| GLOB16 | — | ⛔ A10 | ⛔ A19 | ⛔ A20 | ⛔ A5 | open (A10) |

All v1 and v2 output MD5-verified and on the external HDD; run statistics and verification: tech ref §11, §12.

### Open tasks

| ID | Task | Status | Blocked by |
|---|---|---|---|
| A4 | Storage: all v1 and v2 output and all domains (global and 40°S) on the external HDD; v2 ORCA2–ORCA025 also local (393 GB disk; v1 and the 2000 run on the HDD only); HPC keeps run directories without output (scratch 118 GB); open: HDD copy of the HPC weights for ORCA2, ORCA1, ORCA025 (recommended); layout: README §Data | 🟡 | — |
| A5 | Decide where GLOB16 output is stored (~1.5 TB; 250 GB scratch); inputs in place (A18) | ⬜ | — |
| A10 | GLOB16 run design; informed by A16; `rn_Dt`: 900 s inadmissible (CFL ~757 s); choose 600, 450 or 300 s (`nn_itend` 32 832 / 43 776 / 65 664), a stated caveat, boundable by a two-timestep ORCA025 test; segments (~1.5 TB): `ln_rst_list = .false.`, same rank count, continuous `nn_it000`, keep each restart (~49 GB) until read, check drift continuity at the first boundary; `nn_nevp` ~2000; memory: one node (300 GB step) unconfirmed, record first-segment MaxRSS; multi-node blocked by `dia_mlr_init` deadlock (try `transport_protocol = p2p`); likely more than 2 XIOS servers; set `--time` ~2× estimate | ⬜ | — |
| A19 | GLOB16 validation run: generated configuration at the chosen `rn_Dt`, `nn_nevp` and ranks; all 29 fields written; measure memory and s/step | ⛔ | A10 |
| A20 | GLOB16 2019 production in segments; verify; archive | ⛔ | A19, A5 |

<details>
<summary>Completed tasks (A1–A3, A6–A9, A11–A18)</summary>

| ID | Task | Status |
|---|---|---|
| A1 | Map required outputs to SI3 field IDs | ✅ |
| A2 | Add 21 `_icemod` fields (29 total, incl. `beta_evp`) | ✅ |
| A3 | ORCA2 72-step validation of the v2 set-up; all 29 fields written after the ridging fix (A13) | ✅ |
| A6 | v2 production ORCA2 → ORCA025: all complete, verified and archived; ORCA05 `namelist_cfg` hand-edited (restart point only); details: tech ref §9.2, §12 | ✅ |
| A7 | ORCA05 ice-weights link checked and resolved | ✅ |
| A8 | General solver-variant runs dropped; superseded by A16 | ✅ |
| A9 | aEVP decision: keep aEVP; `nn_nevp = 500` for ORCA2–ORCA025; `rn_relast` unused under aEVP; details: tech ref §9.4 | ✅ |
| A11 | Technical reference updated for v2 and the 2000 run | ✅ |
| A12 | Apply `nn_nevp = 500` via the common template | ✅ |
| A13 | Ridging-diagnostics source fix; `nemo.exe` rebuilt | ✅ |
| A14 | `srun --mem=0` fix for job-step memory; effective step ceiling 300 GB | ✅ |
| A15 | ORCA025 XIOS memory risk assessed: low; no change needed | ✅ |
| A16 | ORCA025 solver-test runs, `nn_nevp` 100 / 500 / 2000: done, verified, local and on HDD; 2000 run 20.9 h; first results: rotation-dominated share within ~2 points across settings; ζ and deformation differ from 2000 by ≤ 8% of the field; largest differences outside high-β ice; variant rules: `cn_exp` ≤ 29 characters, pass `--domain` to `verify_production.py`; full comparison: F6; details: tech ref §1, §9.2, §12 | ✅ |
| A17 | Leftovers deleted (local and HPC), closed 2026-11-09: 2000-run output and restarts, backups and empty directories; scratch 228 → 118 GB; run directories kept | ✅ |
| A18 | GLOB16 trimmed domain and weights rebuilt (2026-11-09): re-trim identical to the original, all three weights files pass the full check, backed up to HDD; ORCA05 weights still lost (rebuild only if ORCA05 is rerun); details: tech ref §5.4, §7.4 | ✅ |

</details>

---

## B. Observational data holdings (WP2.2 inputs)

**Status:** 🟡 · **Runs on:** observational data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| B1 | OSISAF 455 daily, 75 km: merged (multi-sensor) 1990–2025 (`~/Data/seaicedrift/osisaf/OSI455/south/merged`); single-sensor AMSR2 2019, SH only (`OSI455/south/single_sensor/2019`; true per-pixel `t0`/`t1`, satellite-only, 2 Apr – 1 Nov, October usable) | ✅ held | — |
| B2 | OSISAF S2S swath, 62.5 km: only 13–31 Jul 2019 held; decide whether to extend to the full season | ⬜ | — |
| B3 | Per-retrieval uncertainty: RO1 products pending; interim: OSISAF native uncertainty | ⬜ | — |
| B4 | Sea-ice concentration product for Eq. 1 and state comparison: none held yet | ⬜ | — |
| B5 | Drifting-buoy reference (AWI 2019 in `~/Data/insitu/AWIbuoys`; ISVP): check coverage against the model period | ⬜ | — |

---

## C. Shared foundations (WP2.2)

**Status:** 🟡 · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| C1 | NEMO reader: grid, masks, record loading and version switch done (`scripts/kinematics.py`); open: shared multi-file time-series reader; U/V positions for G1 | 🟡 | — |
| C2 | Readers for OSI455_merged, OSI455_single and S2S, one stream each: vectors rebuilt from physical start and end points (never projected `dX`/`dY`); per-pixel windows, uncertainty, flags (`scripts/satdrift.py`) | ⬜ | — |
| C3 | Time matching of the model to each satellite displacement window: method is an open decision (design note D2), discussed next | ⛔ | C1, C2 |
| C4 | Spatial comparability (design note D1, D4, D5): sample each member at each product's native nodes (ocean-only stencil; optional tracking-window average); shared model–observation mask; native cell-corner gradient tensor; tensor aggregation onto common EASE2 boxes (150/225/300 km, optional 450/600 km) | ⛔ | C1, C2 |
| C5 | Correlated-error Monte Carlo through each product's route at every rung (native to coarsest): significance and noise-bias correction of squared quantities | ⛔ | C2, C4, B3 (interim OK) |
| C6 | v2 ORCA2–ORCA05 copied locally (2026-11-11); all 35 `.nc` files per member match the HPC MD5 lists; read through `DATA_ROOTS["v2"]` | ✅ | — |
| C7 | Re-estimate satellite effective resolution (the 350–400 km figure is a bound, not the resolution): three-cornered hat ORCA025 / OSI455_single / S2S on matched windows; check against the tracking-window floor (design note §5) | ⛔ | C2–C4 |

---

## D. Velocity-gradient diagnostics (WP2.2: divergence, shear, total deformation, vorticity)

**Status:** 🟡 · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| D1 | C-grid operators (divergence, shear, total deformation, vorticity) implemented (`scripts/kinematics.py`); open: coastal free-slip bias (`fmask = 0` on land F-points) | 🟡 | — |
| D2 | Synthetic-field tests: prototype run (routes agree within 0.25% on linear fields; coastal T-point vorticity −29% in the first row; ORCA05 seam clean inside `interior_cols`). To add (design note §11): cell-corner operator on OSI455 and S2S cells; frame and projection invariance; tensor-aggregation consistency across rungs; coastal artefacts removed by the shared mask. Tests move to `tests/test_operators.py` with the pipeline | 🟡 | — |
| D3 | Test case: ORCA025 vs OSI455_merged, OSI455_single and S2S, July 2019; native rungs plus 150/225/300 km; shared masks, Monte Carlo noise, free-drift null | ⛔ | D2, C3–C5 |
| D4 | All members × products × rungs (OSI455_merged Apr–Sep, OSI455_single Apr–Oct): vorticity, divergence, strain, total deformation, Okubo–Weiss; significance masks; correlation and variance ratio reported separately; results below a member's effective resolution flagged (ORCA1 < 150 km, ORCA2 < 300 km); product vs product at ≥ 150 km | ⛔ | D3, C6 |
| D5 | S2S beyond July 2019: rerun D4 for S2S over the season if B2 extends the holdings (July S2S is already part of D3–D4) | ⛔ | D4, B2 |
| D6 | Check offline operators against native `icediv`/`iceshe` | ⬜ | — |

---

## E. Scaling with averaging scale (WP2.2)

**Status:** ⛔ · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| E1 | Scaling exponents per member and product from the D4 ladder outputs (the ladder itself is built in C4) | ⛔ | D4 |
| E2 | Identify the scale at which vorticity and deformation features are resolved or lost | ⛔ | E1 |

---

## F. Vorticity attribution (WP2.2 attribution sequence, steps 1–3)

**Status:** 🟡 · **Runs on:** v2 data; F0 v1, F6 the three ORCA025 settings · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| F0 | v1 preview of F4 (no observations): convergence falls and rotation dominance rises with resolution; rotation-dominated ice is the least converged; supports A16; figures: `plots/plot_beta_vortdef_hierarchy.py`, `plots/plot_beta_rotation_timeseries.py` | ✅ | — |
| F1 | Step 1: locate vorticity misfits beyond retrieval uncertainty | ⛔ | D4 |
| F2 | Step 2a: test against curl of air–ice and ocean–ice stress, and ocean-current vorticity | ⛔ | F1 |
| F3 | Step 2b: test against internal stress, Coriolis and tilt | ⛔ | F1 |
| F4 | Step 2c: numerical contribution from `beta_evp` maps and the 100/500/2000 sequence; numerics excluded if the misfit exceeds the 500–2000 difference and that difference shrinks with N | ⛔ | F1, F6 |
| F5 | Step 3: interpret any residual (continuum / rotational physics) | ⛔ | F2–F4 |
| F6 | ORCA025 solver-test comparison (A16 runs) binned by β: vorticity, deformation, their ratio, drift, concentration, thickness; does 500 → 2000 change less than 100 → 500? (offline β for 100; `beta_evp` for 500 and 2000) | ⬜ | — |

---

## G. Lagrangian analysis (WP2.2)

**Status:** ⛔ · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| G1 | Parcels/OpenDrift setup with native C-grid velocities; seeding strategy | ⛔ | C1, C6 |
| G2 | Observed trajectories from OSISAF fields (and buoys, B5) | ⛔ | C2 |
| G3 | Pathways, cumulative distance, retention zones | ⛔ | G1, G2 |
| G4 | Single-parcel and pair dispersion | ⛔ | G1, G2 |
| G5 | Meandering index (model subsampled to satellite timestep) | ⛔ | G1, C3 |
| G6 | Parcel-triangle deformation and rotation; cross-check with D | ⛔ | G1, D4 |

---

## H. Storm composites and case studies (WP2.4)

**Status:** ⬜ · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| H1 | Storm detection/tracking (ERA5 or `_sbcwind` `wspd`) | ⬜ | — |
| H2 | Storm-relative composites of vorticity and deformation | ⛔ | H1, D4 |
| H3 | Cyclone case studies (prefer events in the swath window) | ⛔ | H2, D5 |

---

## I. Eq. 1 partition (WP2.3)

**Status:** ⬜ · **Runs on:** observational data (I1); v2 data (I2) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| I1 | Observed: advective terms from drift, Θ as residual | ⛔ | C4, B4 |
| I2 | Model: advective and non-advective terms from `afxdyn`, `afxthd` and net ridging/rafting (ORCA025 now; other members after C6) | ⬜ | — |
| I3 | Compare over matched time windows and effective scale | ⛔ | I1, I2 |

---

## J. Synthesis (WP2.2–2.4)

**Status:** ⛔ · **Runs on:** v2 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| J1 | Localise model deficiencies by variable, region, season and scale | ⛔ | D–I |
| J2 | Update README Aim/Approach with results | ⛔ | J1 |

---

## K. Deployment design (WP3.1–3.2)

**Status:** ⛔ · **Runs on:** GLOB16 2019 run · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| K1 | Evaluate the GLOB16 2019 reference realisation against retrievals (MIZ focus) | ⛔ | A20, D |
| K2 | Lagrangian release experiments for candidate array geometries | ⛔ | K1, G6 |
| K3 | Array design and site recommendations for InSync Theme 2 | ⛔ | K2 |
