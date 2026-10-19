# Scale-Dependent Sea-Ice Kinematics: NEMO vs. Satellite-Derived Drift

## Key documents

| File | Purpose |
|---|---|
| [`README.md`](README.md) | This document: project overview, approach, data locations, outstanding tasks and environment. |
| [`ROADMAP.md`](ROADMAP.md) | Analysis roadmap: sections, per-task status and blockers, and model rerun progress per member. Update as work completes. |
| [`ProjectOutline.md`](ProjectOutline.md) | The scientific goals and research objectives (RO2, RO3) for understanding the physical sea-ice system. Use it to inform analysis and diagnostic choices. |
| [`TechnicalScientificReference_SEAICE_DYN_003_v5.md`](TechnicalScientificReference_SEAICE_DYN_003_v5.md) | Complete technical and scientific reference for `SEAICE_DYN_003`: a forced standalone NEMO 5.0 + SI3 (SAS) Antarctic sea-ice hindcast run on UCT's HPC cluster across several resolutions, on domains trimmed to 40°S. It covers the cluster environment, build, domain preparation, forcing, interpolation weights, run configuration, verification and results, with the reasoning behind each scientific choice. Use it to interrogate how the model data were generated. |

## Aim

This project establishes whether, and at what spatial scales, a sea-ice model
reproduces the observed Antarctic sea-ice state and the balance of processes that
drives it. A NEMO-SI3 resolution hierarchy (2° to 1/16°), run standalone under
fixed ERA5 and GLORYS12 forcing, is compared with satellite-derived drift at a
common effective scale. Every consistency statement names that scale, and only
differences beyond satellite retrieval uncertainty are treated as model
deficiencies.

Two kinematic tests are applied across the hierarchy:

- **Deformation** (divergence and shear) directly tests the model's rheology.
- **Vorticity**, which the rheology excludes and which emerges from the full
  momentum balance, is a first-order diagnostic. It has not been evaluated
  against observations before. A vorticity misfit is attributed to missing
  rotational physics only after forcing, drag, internal-stress and numerical
  causes have been ruled out.

Lagrangian and Eulerian diagnostics, together with storm case studies, show where
model and observations agree and where they diverge. Advective and non-advective
contributions to concentration change are also compared, to test whether the
model gets the right state for the right reasons. The finest member, GLOB16,
additionally provides the reference field for designing *in situ* buoy
deployments.

## Approach

**Eulerian source data**

- NEMO SI3 (`SEAICE_DYN_003`) ice velocity fields at multiple grid resolutions. Hierarchical members include (coarse to fine):
  ORCA2, ORCA1, ORCA05, ORCA025, GLOB16.
- A satellite drift-retrieval product, to be incorporated as a parallel data source. Two satellite products being considered:
  OSISAF 455 daily average at 75 km spatial resolution (found in /home/waynedj/Data/seaicedrift/osisaf/24hr/south/merged)
  OSISAF S2S at 62.5 km spatial resolution (found in /home/waynedj/Data/seaicedrift/osisaf/swath)

**Lagrangian simulation**

Synthetic ice parcels are seeded and advected through each velocity field using
[OceanParcels](https://oceanparcels.org/) or [OpenDrift](https://opendrift.github.io/).

**Diagnostics**

Each diagnostic is computed for every hierarchy member and satellite product,
compared at a stated common effective scale, and carries the satellite
retrieval uncertainty through so that only significant differences are
interpreted.

*Eulerian (gridded drift fields)*

- Drift speed and direction, and ice concentration (state consistency)
- Divergence, shear and total deformation (tests the rheology)
- Vorticity, and the ratio of vorticity to total deformation
- Change in deformation and vorticity with averaging scale
- Eq. 1 partition: advection term, divergence term and residual Θ, with ridging
  grouped with the non-advective terms

*Lagrangian (simulated parcel trajectories)*

- Advection pathways
- Single-parcel and pair dispersion
- Deformation and rotation from parcel triangles (the quantities a buoy array
  measures)
- Meandering index, with model trajectories subsampled to the satellite timestep
- Cumulative distance travelled
- Zones of drift retention (also informs buoy deployment design)

*Attribution (for vorticity and deformation misfits)*

- Curl of air–ice and ocean–ice stress
- Ocean surface current vorticity
- Internal-stress, Coriolis and sea-surface tilt forces (v2 output)

*Synoptic events*

- Storm composites and cyclone case studies of vorticity and deformation

**Synthesis**

For each diagnostic, identify the effective scale at which a feature (e.g.
synoptic-scale vorticity, small-scale divergence, retention zones) becomes
resolved or is lost across the hierarchy.

## Repository structure

```
.
├── preprocessing/   Scripts for reading, regridding, and preparing NEMO and
│                     satellite velocity fields ahead of Lagrangian simulation.
├── scripts/          NEMO configuration utilities:
│   ├── audit_domain_cfg.py   Read-only audit of domain_cfg files for inclusion
│   │                         in the SEAICE_DYN_003 resolution hierarchy.
│   ├── trim_domain_cfg.py    Trims a domain_cfg file to a southern band below a
│   │                         target latitude (for the standalone SI3 setup).
│   └── estimate_beta_evp.py  Offline estimate of the aEVP relaxation parameter
│                             from model output, to check nn_nevp convergence.
├── plots/            Figures and plotting scripts for diagnostics and results.
└── misc/             Supporting scripts, notes, and other project material.
```

## Data

All datasets live outside this repository under `~/Data/`. This is deliberate:
the same holdings are shared by several other projects. Raw dataset `.nc` files
must never be committed or pushed to GitHub unless explicitly requested (`*.nc`
is excluded in `.gitignore`).

### NEMO

NEMO output is expected locally under:

```
~/Data/NEMO/SEAICE_DYN_003/
├── ORCA2/
├── ORCA1/
├── ORCA05/
├── ORCA025/
└── GLOB16/
```

Each resolution subdirectory is populated post-run with that configuration's NEMO
output (`_icemod`, `_grid_T`, `_sbcwind` files) and its own domain file
(`domain_cfg_<RES>_*.nc`, e.g. `domain_cfg_ORCA025_ANT40S.nc`). Monthly files are
split from the run start (18 Mar 2019), so `_201903-201904` covers 18 Mar – 18 Apr.

> **Status:** the local files are **v1** (8 `_icemod` fields, `nn_nevp = 100`).
> **v2** (29 `_icemod` fields, `nn_nevp = 500`) is being produced on the HPC and
> held there until scratch is full, then downloaded; where it will sit locally
> (replacing v1 or alongside) is undecided, except that ORCA025 v1 is kept as the
> `nn_nevp = 100` member of the ORCA025 solver test. GLOB16 output is pending.

### Satellite drift (OSISAF)

Southern Hemisphere OSISAF sea-ice drift products are expected locally under:

```
~/Data/seaicedrift/osisaf/
├── 24hr/south/merged/        OSISAF 455 daily drift, 75 km (EASE2 grid)
│   ├── <YYYY>/<MM>/          Daily files, 1990–2025
│   └── monthly_mean/         Derived monthly means (sh_monthly_mean_<YYYY>_<MM>.nc)
└── swath/                    OSISAF S2S swath-to-swath drift, 62.5 km
    └── <YYYY>/<MM>/<DD>/     Per-swath-pair files (AMSR2); currently 13–31 Jul 2019 only
```


## Outstanding tasks, gaps and decisions

Task-level status and blockers are tracked in [`ROADMAP.md`](ROADMAP.md).

> **These must be considered before the GLOB16 production run.** Some can only be
> fixed by changing the model configuration, and changing it afterwards means
> running the simulations again.

**Resolved for v2 (configured in `common/` on the HPC; validated on ORCA2)**

- **Ice-area tendencies and ridging:** `afxdyn`, `afxthd`, `rdg_*`, `rft_*` and
  `lead_open` added to `_icemod`, enough to split the model's area change as Eq. 1
  requires, with ridging on the non-advective side.
- **Momentum balance:** internal stress, Coriolis, sea-surface tilt and snow mass
  added; no residual estimate needed.
- **Solver:** adaptive EVP kept; `nn_nevp = 500` for ORCA2–ORCA025 (v1: 100);
  `rn_relast` is unused under aEVP. Convergence documented per cell by `beta_evp`,
  plus one targeted solver-sensitivity test at ORCA025 (see below).
- **Velocity grid:** `sivelu`/`sivelv` and the force-balance terms are native
  U/V-point values, labelled as T-point fields in the files.
- **Ridging diagnostics source fix:** SI3 never wrote the ridging/rafting fields
  (flag set before XIOS was ready); fixed in `MY_SRC/icedyn_rdgrft.F90`
  (diagnostics only) and `nemo.exe` rebuilt.
- **Job-step memory:** `srun` now carries `--mem=0`; without it the step was capped
  at `ntasks × 8000 MB` and v2 ORCA05 was OOM-killed at start-up.

**Model runs: still open**

- **v2 production:** ORCA2, ORCA1 and ORCA05 complete and verified (runtime
  1.56–1.79× v1, rising with resolution). ORCA025 (est. 7–9 h) is on hold for
  scratch space.
- **Storage:** v2 output is ~2.8× v1 (~175 GB uncompressed for ORCA2–ORCA025);
  compression deferred (5× measured with `nccopy`). After clean-up, scratch has
  ~72 GB free, so ORCA025 (~105–118 GB plus restarts) needs ORCA2–ORCA05 (~50 GB)
  downloaded and cleared first. Locally,
  136 GB is free, enough only if v1 is replaced, except ORCA025 v1, which is kept
  for the solver test. The ORCA025 `nn_nevp = 2000` run adds ~118 GB (full season).
- **ORCA025 solver-sensitivity test:** ORCA025 is compared at `nn_nevp` = 100
  (v1), 500 (v2) and 2000 (an extra run, v2 configuration), after ORCA025 at 500
  completes. `beta_evp` masking alone is weakest for vorticity, because
  rotation-dominated, low-deformation ice has the highest β. The three settings show
  whether the numerical contribution is small and shrinking with iteration count, and
  inform GLOB16's `nn_nevp`. The run period for 2000 (full season or a window) is
  undecided.
- **GLOB16:** `nn_nevp` (β ≈ 4× ORCA025; ~2000 iterations for equal convergence),
  segment driver, memory (300 GB effective step ceiling), and storage (~1.5 TB uncompressed
  vs a 250 GB scratch quota).
- **Simulation period:** the hierarchy covers 18 Mar – 31 Oct 2019, whereas the
  WP3.1 reference realisation is the 2022 season. Decide whether the hierarchy
  also runs 2022.

**Observational data**

- **Swath coverage:** OSISAF S2S, the primary comparison product (WP2.2), is held
  only for 13–31 Jul 2019. Decide whether to acquire more.
- **Concentration product:** none held locally; needed for the observed Eq. 1
  partition and the state comparison.
- **Buoys:** AWI 2019 buoys are held; check their coverage against the model period.
- **Retrieval uncertainty:** per-retrieval uncertainties (RO1 inputs) must be
  carried through to every derived diagnostic, since gradients amplify error.

**Diagnostics**

- **Time matching:** model trajectories (3-hourly) must be subsampled to the
  satellite timestep before comparing time-sensitive metrics such as the
  meandering index.
- **Convergence masking:** flag or mask cells where `beta_evp` exceeds `nn_nevp`
  before attributing a vorticity or deformation misfit. In-model β is about 2×
  the offline v1 estimate, so the poorly converged tail at ORCA025 may be larger
  than first estimated. The ORCA025 100/500/2000 test checks what masking can't
  catch, chiefly rotation-dominated ice.

## Environment

Analysis is carried out in the conda environment **`env010`** (Python 3.11.14).

To activate:

```bash
conda activate env010
```

Full package list: `conda list -n env010`.

## Status

This project is under active development. This README will be updated as the
codebase, data holdings, and results evolve.
