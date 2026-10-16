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
- Internal-stress force (not yet in model output; see Outstanding tasks)

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
├── scripts/          NEMO domain configuration utilities:
│   ├── audit_domain_cfg.py   Read-only audit of domain_cfg files for inclusion
│   │                         in the SEAICE_DYN_003 resolution hierarchy.
│   └── trim_domain_cfg.py    Trims a domain_cfg file to a southern band below a
│                             target latitude (for the standalone SI3 setup).
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
(`domain_cfg_<RES>_*.nc`, e.g. `domain_cfg_ORCA025_ANT40S.nc`).

> **Status:** GLOB16 resolution member output is pending. To be included in Kinematics analysis later

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
> fixed by changing the model output configuration, and adding outputs afterwards
> means running the simulations again.

**Model output (requires changes to the run configuration)**

- **No ice-area tendency diagnostics.** `_icemod` holds only `siconc`, `sithic`,
  `sivelu`/`sivelv` and the air–ice and ocean–ice stresses. The WP2.3 partition
  needs SI3's own dynamic and thermodynamic area tendencies, with ridging grouped
  with the non-advective terms. These outputs need enabling.
- **No internal-stress term.** Step 2 of the vorticity attribution sequence needs
  the internal-stress force. Without it, the term must be estimated as the
  residual of the momentum balance, which adds error. Output it directly.
- **Simulation period.** The current hierarchy covers Mar–Nov 2019, whereas the
  WP3.1 reference realisation is the 2022 season. Decide whether the hierarchy
  is also run for 2022.
- **Numerical control experiments.** Decide the solver settings to vary at fixed
  resolution (WP2.1) before production runs.

**Satellite data**

- **Swath coverage.** OSISAF S2S, the primary comparison product (WP2.2), is
  currently held only for 13–31 Jul 2019. Decide whether to acquire more.
- **Retrieval uncertainty.** Per-retrieval uncertainties (RO1 inputs) must be
  carried through to every derived diagnostic, since gradients amplify error.

**Diagnostics**

- **Time matching.** Model trajectories (3-hourly) must be subsampled to the
  satellite timestep before comparing time-sensitive metrics such as the
  meandering index.

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
