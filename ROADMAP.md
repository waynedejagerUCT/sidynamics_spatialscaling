# Roadmap: SEAICE_DYN_003 scale-dependent kinematics

Living document. Update task status as work completes. Scientific goals: [ProjectOutline.md](ProjectOutline.md). Model setup: [TechnicalScientificReference_SEAICE_DYN_003_v5.md](TechnicalScientificReference_SEAICE_DYN_003_v5.md).

**Last updated:** 2026-10-16

**Status key:** ✅ done · 🟡 in progress · ⬜ not started (unblocked) · ⛔ blocked (see *Blocked by*)

**Data versions**
- **v1:** current local output. ORCA2–ORCA025, 18 Mar – 31 Oct 2019, 8 `_icemod` fields.
- **v2:** rerun with 28 `_icemod` fields: v1 fields + partition, momentum balance, snow mass, native deformation, rheology state.

## Section overview

| # | Section | Status | Can start now? | Blocked by |
|---|---|---|---|---|
| A | Model reruns (WP2.1) | 🟡 | Yes | — |
| B | Observational data holdings | 🟡 | Yes | — |
| C | Shared foundations | ⬜ | Yes | — |
| D | Velocity-gradient diagnostics | ⬜ | Partly | C |
| E | Scaling with averaging scale | ⛔ | No | D |
| F | Vorticity attribution | ⛔ | No | D; A (v2) for momentum terms |
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

| Member | v1 (2019, 8 fields) | v2 config generated | v2 72-step validation | v2 production | v2 archived locally | Solver variants | 2022 run |
|---|---|---|---|---|---|---|---|
| ORCA2 | ✅ local | ✅ | ⬜ | ⛔ A4 | ⛔ | ⛔ A8 | ⛔ A10 |
| ORCA1 | ✅ local | ⬜ | ⛔ A3 | ⛔ A4 | ⛔ | — | ⛔ A10 |
| ORCA05 | ✅ local | ⬜ | ⛔ A3 | ⛔ A4 | ⛔ | — | ⛔ A10 |
| ORCA025 | ✅ local | ⬜ | ⛔ A3 | ⛔ A4 | ⛔ | ⛔ A8 (target member) | ⛔ A10 |
| GLOB16 | ⛔ pending | ⬜ | ⛔ A3 | ⛔ A4, A11 | ⛔ A5 | — | ⛔ A10, A11 (WP3 reference) |

v1 output was removed from the HPC on 2026-10-16. Local copies are kept, and run records are in `~/Data/NEMO/SEAICE_DYN_003/SEAICE_DYN_003_runrecords.tgz`.

### Tasks

| ID | Task | Status | Blocked by |
|---|---|---|---|
| A1 | Map required outputs to SI3 field IDs; check `iom_put` calls and grids | ✅ | — |
| A2 | Add 20 fields to `common/file_def_nemo-ice.xml` (`_icemod`); regenerate ORCA2 (28 fields confirmed) | ✅ | — |
| A3 | ORCA2 72-step validation: new fields present and non-zero over ice | ⬜ | — |
| A4 | Measure `nccopy -d 1 -s` compression on A3 output; decide storage (local 136 GB free; v2 ORCA2–025 ≈ 170 GB uncompressed) | ⛔ | A3 |
| A5 | Decide where GLOB16 is stored (≈ 1.5 TB uncompressed v2; 250 GB scratch quota) | ⛔ | A4 |
| A6 | Production v2 runs, cheapest first: ORCA2 → ORCA1 → ORCA05 → ORCA025 | ⛔ | A3, A4 |
| A7 | Check ORCA05 ice-weights filename (`weights_bilinglorys_…`, missing underscore) | ⬜ | — |
| A8 | Add `--variant` option to `setup_production.sh` (ctl / nevp300 / evp; `uice_cvg` per variant) | ⬜ | — |
| A9 | Check whether `rn_relast` is used under adaptive EVP | ⬜ | — |
| A10 | Decide whether the full hierarchy also runs 2022 | ⬜ | — |
| A11 | GLOB16: segment driver and memory decision | ⬜ | — |
| A12 | Update the technical reference with v2 outputs | ⛔ | A6 |

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
| C1 | NEMO reader: C-grid positions (`glamu/v/f`, `gphiu/v/f`), masks, metrics from `domain_cfg_<RES>_ANT40S.nc` | ⬜ | — |
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

**Status:** ⛔ · **Runs on:** v1 data (F1–F2); v2 data and solver-variant runs (F3–F4) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| F1 | Step 1: locate vorticity misfits beyond retrieval uncertainty | ⛔ | D4 |
| F2 | Step 2a: test against curl of air–ice and ocean–ice stress, and ocean-current vorticity (v1 fields) | ⛔ | F1 |
| F3 | Step 2b: test against internal stress, Coriolis and tilt (`intstrx`, `corstrx`, `dssh_dx`) | ⛔ | F1, A6 |
| F4 | Step 2c: numerical contribution from solver variants | ⛔ | F1, A8 + variant runs |
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
