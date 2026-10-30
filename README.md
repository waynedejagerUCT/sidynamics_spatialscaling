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
├── scripts/          NEMO configuration utilities and shared analysis code:
│   ├── audit_domain_cfg.py   Read-only audit of domain_cfg files for inclusion
│   │                         in the SEAICE_DYN_003 resolution hierarchy.
│   ├── trim_domain_cfg.py    Trims a domain_cfg file to a southern band below a
│   │                         target latitude (for the standalone SI3 setup).
│   ├── estimate_beta_evp.py  Offline estimate of the aEVP relaxation parameter
│   │                         from model output, to check nn_nevp convergence.
│   │                         Also importable: beta_offline, and beta_from to
│   │                         switch between offline β and NEMO's beta_evp (v2).
│   └── kinematics.py         Shared C-grid code: domain_cfg loading, strain
│                             rates, vorticity (ζ² averaged F→T), |ζ|/total
│                             deformation, halo handling, ice/deformation thresholds.
├── plots/            Figures and plotting scripts for diagnostics and results:
│   ├── plot_beta_vortdef_hierarchy.py    8-panel map (ORCA2–ORCA025) of β and
│   │                                     |ζ|/total deformation at one 3 h record.
│   └── plot_beta_rotation_timeseries.py  Season time series of % ice converged
│                                         (β ≤ nn_nevp) and % rotation-dominated;
│                                         per-record results cached as CSV under
│                                         ~/Data/intermediate/SEAICE_DYN_003/.
└── misc/             Supporting scripts, notes, and other project material.
```

## Data

All datasets live outside this repository under `~/Data/`. This is deliberate:
the same holdings are shared by several other projects. Raw dataset `.nc` files
must never be committed or pushed to GitHub unless explicitly requested (`*.nc`
is excluded in `.gitignore`).

### NEMO

NEMO output is held by data version, locally and on an external HDD:

```
~/Data/NEMO/
├── SEAICE_DYN_003_v1/            v1: 8 _icemod fields, nn_nevp = 100
│   ├── ORCA025/                  only v1 member held locally (ORCA025 solver test)
│   ├── ORCA2/ ORCA1/ ORCA05/     empty: output on the external HDD since 2026-10-28
│   └── SEAICE_DYN_003_runrecords.tgz
└── SEAICE_DYN_003_v2/            v2: 29 _icemod fields, nn_nevp = 500
    ├── ORCA025/                  output + run records + domain_cfg, MD5-verified 2026-10-30
    ├── ORCA2/ ORCA1/ ORCA05/     empty: on the external HDD since 2026-10-30
    └── v2_md5_<RES>.txt          HPC-made MD5 lists used for the checks

External HDD: v1 and v2 ORCA2, ORCA1, ORCA05 (v2 re-verified by MD5 after the
move); the five as-received domain_cfg files; 40°S trimmed domains of ORCA2,
ORCA1 and ORCA05.
```

Each member directory holds that configuration's NEMO output (`_icemod`,
`_grid_T`, `_sbcwind` files) and its own domain file
(`domain_cfg_<RES>_ANT40S.nc`). v2 members also hold their run records
(namelists, XMLs, `ocean.output`, logs, timing files, `VERIFY_LOGS_<RES>.txt` where
saved, `VERIFY_PRODUCTION_<RES>.txt`, `PROVENANCE.md`). Monthly files are split from
the run start (18 Mar 2019), so `_201903-201904` covers 18 Mar – 18 Apr. The old
path `~/Data/NEMO/SEAICE_DYN_003/` no longer exists; scripts select a version
through `DATA_ROOTS` in `scripts/kinematics.py`, which points at the local
directories, so ORCA2–ORCA05 show as "not held locally" unless a root is pointed
at the HDD.

> **Status (2026-10-30):** v2 ORCA025 (job 1541973) is archived locally in
> `SEAICE_DYN_003_v2/ORCA025/`, MD5-verified (74 files), and cleared from HPC
> scratch. The ORCA025 `nn_nevp = 2000` run (job 1544646) is running; ~47 GB is
> free locally against its ~121 GB output, so a storage decision (compression
> or HDD-based analysis) is needed before it is downloaded. v1 ORCA025 stays local as the `nn_nevp = 100`
> member of the ORCA025 solver test. `~/Data/NEMO/hpc_offload/` was accidentally
> deleted on 2026-10-30: the GLOB16 trimmed domain and weights and the ORCA05
> weights must be rebuilt before they are next needed (see `ROADMAP.md` A19).
> GLOB16 output is pending.

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

- **v2 production:** all four ORCA members complete and verified (runtime
  1.56–1.90× v1, rising with resolution; ORCA025 7:24:53, 51.0 GiB peak,
  121 444 783 127 B). ORCA2–ORCA05 are MD5-verified on the external HDD and
  ORCA025 locally; all four have been cleared from scratch.
- **Storage:** v2 output is ~2.8× v1; compression deferred (5× measured with
  `nccopy`). Scratch is back to 115 of 250 GB after ORCA025 was cleared; the
  `nn_nevp = 2000` run takes it to ~236 GB (restarts are only ~8 MB). Locally ~47
  GB is free, and the three ORCA025 solver-test settings total ~283 GB
  uncompressed, more than the 251 GB disk: decide between lossless compression and
  HDD-based analysis before the 2000 run finishes. `hpc_offload/` was lost on 2026-10-30; the
  GLOB16 trimmed domain and weights must be rebuilt before the GLOB16 run, and
  the ORCA05 weights before any ORCA05 rerun. Copying the HPC
  `inputs/{ORCA2,ORCA1,ORCA025}_ANT40S/` to the HDD is recommended. Transfers use
  `djgway001@hex.uct.ac.za` at ~4.4–4.8 MB/s.
- **ORCA025 solver-sensitivity test:** ORCA025 is compared at `nn_nevp` = 100
  (v1), 500 (v2) and 2000 (`ORCA025_NEVP2000`, the v2 configuration with only
  `nn_nevp` changed; the third setting of this test, not a new data version). `beta_evp` masking alone is weakest for vorticity, because
  rotation-dominated, low-deformation ice has the highest β. The three settings show
  whether the numerical contribution is small and shrinking with iteration count, and
  inform GLOB16's `nn_nevp`. v1 and v2 ORCA025 namelists differ only in `nn_nevp`
  (checked 2026-10-29) and share the same decomposition. The 500 run is done, so 100
  vs 500 can start. The 2000 run was generated by a documented hand-copy exception
  (`setup_production.sh` has no `--variant`) and submitted as job 1544646 on
  2026-10-30: a full-season cold start, projected ~20.5 h.
- **GLOB16:** `nn_nevp` (β ≈ 4× ORCA025; ~2000 iterations for equal convergence),
  segment driver, memory (300 GB effective step ceiling), and storage (~1.5 TB uncompressed
  vs a 250 GB scratch quota). Inputs must also be rebuilt before the production run,
  since both were lost on 2026-10-30 (`ROADMAP.md` A19): generate the 40°S domain by
  re-trimming the full GLOB16L98 domain (held on the external HDD) with
  `trim_domain_cfg.py`, then regenerate the ERA5, GLORYS SAS and GLORYS ice weights
  with `build_weights.py`.
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
  before attributing a vorticity or deformation misfit. ORCA05 is effectively
  fully converged at 500 (≤ 0.02% of ice cells above it); ORCA025, the finest
  member, is expected to have the largest tail. The ORCA025 100/500/2000 test checks what masking can't
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
