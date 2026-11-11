# Roadmap: SEAICE_DYN_003 scale-dependent kinematics

Living document: what is done and what is left. Scientific goals: [ProjectOutline.md](ProjectOutline.md). How the data were generated (configuration, set-up, compute environment, scientific choices): [TechnicalScientificReference_SEAICE_DYN_003_v5.md](TechnicalScientificReference_SEAICE_DYN_003_v5.md) ("tech ref").

**Last updated:** 2026-11-09 · All simulation and analysis use the 2019 season (18 Mar – 31 Oct); no 2022 runs planned.

**Status key:** ✅ done · 🟡 in progress · ⬜ not started (unblocked) · ⛔ blocked (see *Blocked by*)

**Data versions** (locations: README §Data; configuration: tech ref §1)
- **v1:** ORCA2–ORCA025, 2019 season; 8 `_icemod` fields; `nn_nevp = 100`; ORCA025 local, rest on external HDD.
- **v2:** ORCA2–ORCA025 rerun; 29 `_icemod` fields; `nn_nevp = 500`; ORCA025 local, all members on HDD.
- **ORCA025_NEVP2000:** ORCA025 only, v2 configuration with `nn_nevp = 2000`; third A16 setting, not a new version; local under v2.

## Section overview

| # | Section | Status | Can start now? | Blocked by |
|---|---|---|---|---|
| A | Model reruns (WP2.1) | 🟡 | Yes | — |
| B | Observational data holdings | 🟡 | Yes | — |
| C | Shared foundations | 🟡 | Yes | — |
| D | Velocity-gradient diagnostics | 🟡 | Partly | C |
| E | Scaling with averaging scale | ⛔ | No | D |
| F | Vorticity attribution | ⛔ | No | D; A16 for the numerical test |
| G | Lagrangian analysis | ⬜ | Partly | C |
| H | Storm composites and case studies | ⛔ | No | D, E |
| I | Eq. 1 partition | ⛔ | Obs side partly | C, B4 |
| J | Synthesis | ⛔ | No | D–I |
| K | WP3 deployment design | ⛔ | No | A (GLOB16 2019 run), G |

Sections C, D, E, G and the observed side of I can run on v1 data; v2 adds momentum-balance, native-deformation and partition fields.

---

## A. Model reruns (WP2.1)

**Status:** 🟡 · **Runs on:** produces v2 data · HPC

### Rerun status per member

| Member | v1 (8 fields) | v2 config | v2 validation | v2 production | v2 archived | `nn_nevp` |
|---|---|---|---|---|---|---|
| ORCA2 | ✅ | ✅ | ✅ | ✅ | ✅ HDD | 500 |
| ORCA1 | ✅ | ✅ | — (via ORCA2) | ✅ | ✅ HDD | 500 |
| ORCA05 | ✅ | ✅ (hand-edited, A6) | — (via ORCA2) | ✅ | ✅ HDD | 500 |
| ORCA025 | ✅ (A16 100 setting) | ✅ | — (via ORCA2) | ✅ | ✅ local + HDD | 500 |
| ORCA025_NEVP2000 | — | ✅ (hand-copy exception, A16) | — | ✅ | ✅ local | 2000 |
| GLOB16 | ⛔ | ⬜ | ⛔ A3 | ⛔ A4, A10 | ⛔ A5 | open (A10) |

All v1 and v2 archives MD5-verified; run statistics and verification: tech ref §11, §12.

### Tasks

| ID | Task | Status | Blocked by |
|---|---|---|---|
| A1 | Map required outputs to SI3 field IDs | ✅ | — |
| A2 | Add 21 `_icemod` fields (29 total, incl. `beta_evp`) | ✅ | — |
| A3 | ORCA2 72-step validation of the v2 set-up; all 29 fields written after the ridging fix (A13) | ✅ | — |
| A4 | Storage on scratch and locally; compression not needed; local disk 393 GB holds all three ORCA025 settings; 2000-run HPC clean-up done (scratch 118 GB); `GLOB16_ANT40S` backed up to HDD; recommended: copy HPC `{ORCA2,ORCA1,ORCA025}_ANT40S` inputs to HDD; data layout: README §Data | 🟡 | — |
| A5 | Decide where GLOB16 output is stored (~1.5 TB; 250 GB scratch); GLOB16 inputs in place (A18) | ⛔ | A4 |
| A6 | v2 production ORCA2 → ORCA025: all complete, verified and archived; ORCA05 `namelist_cfg` hand-edited (restart point only); details: tech ref §9.2, §12 | ✅ | — |
| A7 | ORCA05 ice-weights link checked and resolved | ✅ | — |
| A8 | General solver-variant runs dropped; replaced by A16 | ✅ superseded | — |
| A9 | aEVP decision: keep aEVP; `nn_nevp = 500` for ORCA2–ORCA025; `rn_relast` unused under aEVP; details: tech ref §9.4 | ✅ | — |
| A10 | GLOB16 run design; informed by A16; `rn_Dt`: 900 s inadmissible (CFL ~757 s); choose 600, 450 or 300 s (`nn_itend` 32 832 / 43 776 / 65 664), a stated caveat, boundable by a two-timestep ORCA025 test; segments (~1.5 TB): `ln_rst_list = .false.`, same rank count, continuous `nn_it000`, keep each restart (~49 GB) until read, check drift continuity at the first boundary; `nn_nevp` ~2000; memory: one node (300 GB step) unconfirmed, record first-segment MaxRSS; multi-node blocked by `dia_mlr_init` deadlock (try `transport_protocol = p2p`); likely more than 2 XIOS servers; set `--time` ~2× estimate | ⬜ | — |
| A11 | Technical reference updated for v2 and the 2000 run | ✅ | — |
| A12 | Apply `nn_nevp = 500` via the common template | ✅ | — |
| A13 | Ridging-diagnostics source fix; `nemo.exe` rebuilt | ✅ | — |
| A14 | `srun --mem=0` fix for job-step memory; effective step ceiling 300 GB | ✅ | — |
| A15 | ORCA025 XIOS memory risk assessed: low; no change needed | ✅ | — |
| A16 | ORCA025 solver test, `nn_nevp` 100 / 500 / 2000: all three runs done, verified and local; 2000 run: 20.9 h; first results: rotation-dominated share within ~2 points across settings; ζ and deformation differ from 2000 by ≤ 8% of the field; largest differences outside high-β ice; open: full comparison binned by β; rules for future variants: `cn_exp` ≤ 29 characters, pass `--domain` to `verify_production.py`; details: tech ref §1, §9.2, §12 | 🟡 | — |
| A17 | Delete leftovers not needed for analysis or reruns (local and HPC); closed 2026-11-09: 2000-run output and restarts, backups and empty directories removed; scratch 228 → 118 GB; run directories kept | ✅ | — |
| A18 | Rebuild lost GLOB16 trimmed domain and weights; done 2026-11-09: re-trim identical to the original, all three weights files pass the full check, backed up to HDD; ORCA05 weights still lost (rebuild only if ORCA05 is rerun); details: tech ref §5.4, §7.4 | ✅ | — |

---

## B. Observational data holdings

**Status:** 🟡 · **Runs on:** observational data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| B1 | OSISAF 455 daily, 75 km, 1990–2025 (`~/Data/seaicedrift/osisaf/24hr/south/merged`) | ✅ held | — |
| B2 | OSISAF S2S swath, 62.5 km: only 13–31 Jul 2019 held; decide whether to extend to the full season | ⬜ | — |
| B3 | Per-retrieval uncertainty: RO1 products pending; interim: OSISAF native uncertainty | ⬜ | — |
| B4 | Sea-ice concentration product for Eq. 1 and state comparison: none held yet | ⬜ | — |
| B5 | Drifting-buoy reference (AWI 2019 in `~/Data/insitu/AWIbuoys`; ISVP): check coverage against the model period | ⬜ | — |

---

## C. Shared foundations

**Status:** 🟡 · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| C1 | NEMO reader: grid, masks, record loading and v1/v2 switch done (`scripts/kinematics.py`); open: shared multi-file time-series reader; U/V positions for G1; code: `scripts/kinematics.py` | 🟡 | — |
| C2 | OSISAF 455 and swath readers (grids, time windows, uncertainty, flags) | ⬜ | — |
| C3 | Time matching: integrate 3 h model velocity over each satellite displacement window | ⬜ | C1, C2 |
| C4 | Regridding and coarsening to a common effective scale | ⬜ | C1, C2 |
| C5 | Uncertainty propagation through coarsening and gradients | ⬜ | C2, B3 (interim OK) |

---

## D. Velocity-gradient diagnostics (divergence, shear, total deformation, vorticity)

**Status:** 🟡 · **Runs on:** v1 data (D1–D5); v2 data (D6) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| D1 | C-grid operators (divergence, shear, total deformation, vorticity) implemented (`scripts/kinematics.py`); open: coastal free-slip bias (`fmask = 0` on land F-points) | 🟡 | — |
| D2 | Synthetic-field tests (solid-body rotation, pure divergence); also coastal boundary, ORCA05 halo seam, grid-scale noise | ⬜ | — |
| D3 | First complete case: ORCA025 vs OSISAF 455, Mar–Oct 2019, at common scale | ⬜ | D2, C3–C5 |
| D4 | Extend to all members; vorticity/deformation ratio; significance masks | ⬜ | D3 |
| D5 | Swath comparison (Jul 2019 window) | ⬜ | D4, B2 |
| D6 | Check offline operators against native `icediv`/`iceshe` | ⬜ | — |

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
| F0 | v1 preview of F4 (no observations): convergence falls and rotation dominance rises with resolution; rotation-dominated ice is the least converged; supports A16; figures: `plots/plot_beta_vortdef_hierarchy.py`, `plots/plot_beta_rotation_timeseries.py` | ✅ | — |
| F1 | Step 1: locate vorticity misfits beyond retrieval uncertainty | ⛔ | D4 |
| F2 | Step 2a: test against curl of air–ice and ocean–ice stress, and ocean-current vorticity | ⛔ | F1 |
| F3 | Step 2b: test against internal stress, Coriolis and tilt | ⛔ | F1 |
| F4 | Step 2c: numerical contribution from `beta_evp` maps and the A16 100/500/2000 sequence; numerics excluded if the misfit exceeds the 500–2000 difference and that difference shrinks with N | ⛔ | F1, A16 |
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
| I2 | Model: advective and non-advective terms from `afxdyn`, `afxthd` and net ridging/rafting | ⬜ | — |
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

**Status:** ⛔ · **Runs on:** GLOB16 2019 run · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| K1 | Evaluate the GLOB16 2019 reference realisation against retrievals (MIZ focus) | ⛔ | A10 + GLOB16 2019 run, D |
| K2 | Lagrangian release experiments for candidate array geometries | ⛔ | K1, G6 |
| K3 | Array design and site recommendations for InSync Theme 2 | ⛔ | K2 |
