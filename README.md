# Scale-Dependent Sea-Ice Kinematics: NEMO vs. Satellite-Derived Drift

## Key documents

| File | Purpose |
|---|---|
| [`README.md`](README.md) | This document: project overview, approach, repository layout, data locations, usage and environment. |
| [`ROADMAP.md`](ROADMAP.md) | Analysis roadmap: per-task status and blockers, and model run progress per member. Update as work completes. |
| [`ProjectOutline.md`](ProjectOutline.md) | The scientific goals and research objectives (RO2, RO3). Use it to inform analysis and diagnostic choices. |
| [`TechnicalScientificReference_SEAICE_DYN_003_v5.md`](TechnicalScientificReference_SEAICE_DYN_003_v5.md) | How the `SEAICE_DYN_003` model output was generated: configuration, set-up, compute environment and the reason for each scientific choice. |

## Aim

This project establishes whether, and at what spatial scales, a sea-ice model
reproduces the observed Antarctic sea-ice state and the balance of processes that
drives it. A NEMO-SI3 resolution hierarchy (2° to 1/4° run; 1/16° planned), run
standalone under fixed ERA5 and GLORYS12 forcing, is compared with satellite-derived
drift at a common effective scale. Every consistency statement names that scale, and
only differences beyond satellite retrieval uncertainty are treated as model
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

- NEMO SI3 (`SEAICE_DYN_003`) ice velocity fields at multiple grid resolutions,
  coarse to fine: ORCA2, ORCA1, ORCA05, ORCA025, GLOB16.
- Satellite drift retrievals: OSISAF 455 daily drift (75 km) and OSISAF S2S
  swath-to-swath drift (62.5 km); locations under [Data](#data).

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
├── preprocessing/    (empty; planned) reading, regridding and preparing NEMO and
│                     satellite velocity fields ahead of Lagrangian simulation.
├── scripts/          NEMO configuration utilities and shared analysis code:
│   ├── audit_domain_cfg.py   Read-only audit of domain_cfg files for inclusion
│   │                         in the SEAICE_DYN_003 resolution hierarchy.
│   ├── trim_domain_cfg.py    Trims a domain_cfg file to a southern band below a
│   │                         target latitude (for the standalone SI3 setup).
│   ├── build_weights.py      Builds bilinear ERA5 and GLORYS interpolation weights
│   │                         for a trimmed domain with NEMO's SCRIP tools.
│   ├── expand_weights.py     Rewrites compacted SCRIP weights in positional form;
│   │                         --verify-only is the full weights check.
│   ├── estimate_beta_evp.py  Offline estimate of the aEVP relaxation parameter
│   │                         from model output, to check nn_nevp convergence.
│   │                         Also importable: beta_offline, and beta_from to
│   │                         switch between offline β and NEMO's beta_evp (v2).
│   └── kinematics.py         Shared C-grid code: domain_cfg loading, strain
│                             rates, vorticity (ζ² averaged F→T), |ζ|/total
│                             deformation, halo handling, ice/deformation thresholds.
├── plots/            Plotting scripts and the figures they write (.png):
│   ├── plot_beta_vortdef_hierarchy.py    8-panel map (ORCA2–ORCA025) of β and
│   │                                     |ζ|/total deformation at one 3 h record.
│   ├── plot_beta_rotation_timeseries.py  Season time series of % ice converged
│   │                                     (β ≤ nn_nevp) and % rotation-dominated.
│   ├── plot_orca025_nevp_timeseries.py   ORCA025 solver test: the same series for
│   │                                     nn_nevp = 100 / 500 / 2000.
│   ├── plot_orca025_nevp_vorticity_maps.py    ORCA025 solver test: signed
│   │                                     vorticity maps (3 dates × 3 settings) and
│   │                                     differences from 2000 with β contours.
│   ├── plot_orca025_nevp_deformation_maps.py  Total-deformation counterpart of
│   │                                     the vorticity maps, same scales.
│   └── vp_loops_vs_evp_nudging.html      Interactive explainer: VP nested loops vs
│                                         EVP subcycles nudging towards balance.
└── misc/             Exploratory scripts (compute_monthly_mean.py: OSISAF 455
                      monthly means; dataset_exploring.py).
```

## Usage

Run scripts in the `env010` environment (see [Environment](#environment)) from the
repository root; figures are written to `plots/` by default (`--out-dir` to change).

```bash
conda activate env010
```

```bash
python plots/plot_beta_vortdef_hierarchy.py --time 2019-09-15T12:00 --beta-source offline
```

```bash
python plots/plot_beta_rotation_timeseries.py --source offline --weight count
```

```bash
python plots/plot_orca025_nevp_timeseries.py --weight count --residual 0.05
```

```bash
python plots/plot_orca025_nevp_vorticity_maps.py --times 2019-09-01T12:00 2019-10-01T12:00 2019-10-30T12:00
```

```bash
python plots/plot_orca025_nevp_deformation_maps.py --times 2019-09-01T12:00 2019-10-01T12:00 2019-10-30T12:00
```

The two time-series scripts cache per-record results as CSV in
`~/Data/intermediate/SEAICE_DYN_003/` (`beta_rotation_ts_offline.csv`,
`orca025_nevp_ts.csv`) and reuse them unless `--recompute` is given; members not
held locally are then read from the cache only.

## Data

All datasets live outside this repository under `~/Data/`. This is deliberate:
the same holdings are shared by several other projects. Raw dataset `.nc` files
must never be committed or pushed to GitHub unless explicitly requested (`*.nc`
is excluded in `.gitignore`).

### NEMO

| Version | Members | `_icemod` fields | `nn_nevp` | Held |
|---|---|---|---|---|
| v1 | ORCA2–ORCA025 | 8 | 100 | ORCA025 local; all on external HDD |
| v2 | ORCA2–ORCA025 | 29 | 500 | ORCA025 local; all on external HDD |
| v2 `ORCA025_NEVP2000` | ORCA025 | 29 | 2000 | local; external HDD |

`ORCA025_NEVP2000` is not a new version: it is v2 ORCA025 with only `nn_nevp`
changed, the third setting of the ORCA025 solver test (100 = v1, 500 = v2,
2000 = `v2/ORCA025_NEVP2000`).

```
~/Data/NEMO/
├── SEAICE_DYN_003_v1/
│   ├── ORCA025/                  v1 ORCA025 (nn_nevp = 100)
│   └── SEAICE_DYN_003_runrecords.tgz
└── SEAICE_DYN_003_v2/
    ├── ORCA025/                  v2 ORCA025 (nn_nevp = 500)
    ├── ORCA025_NEVP2000/         ORCA025 at nn_nevp = 2000
    ├── ORCA2/ ORCA1/ ORCA05/     empty (held on the external HDD)
    ├── v2_md5_<RES>.txt          MD5 lists made on the HPC
    └── md5_ORCA025_NEVP2000.txt

External HDD: all v1 and v2 output (incl. ORCA025_NEVP2000); all domain_cfg files,
as received (global) and 40°S trimmed; GLOB16_ANT40S/ inputs (with weights).
HPC: member run directories (configurations, logs) kept; output .nc files removed.
```

Each member directory holds its NEMO output (`_icemod`, `_grid_T`, `_sbcwind`,
`_SBC_scalar`) and its trimmed domain file (`domain_cfg_<RES>_ANT40S.nc`, needed for
cell metrics). v2 members also hold their run records (namelists, XMLs,
`ocean.output`, logs, timing files, verification reports, `PROVENANCE.md`).
Restart files are not kept. Monthly files are split from the run start
(18 Mar 2019), so `_201903-201904` covers 18 Mar – 18 Apr. Scripts select a
version through `DATA_ROOTS` in `scripts/kinematics.py`, which points at the local
directories, so v2 ORCA2–ORCA05 show as "not held locally" unless a root is pointed
at the HDD. Variant runs are read with
`load_grid(member, root, run_dir="ORCA025_NEVP2000")`.

### Satellite drift (OSISAF)

```
~/Data/seaicedrift/osisaf/
├── 24hr/south/merged/        OSISAF 455 daily drift, 75 km (EASE2 grid)
│   ├── <YYYY>/<MM>/          Daily files, 1990–2025
│   └── monthly_mean/         Derived monthly means (sh_monthly_mean_<YYYY>_<MM>.nc)
└── swath/                    OSISAF S2S swath-to-swath drift, 62.5 km
    └── <YYYY>/<MM>/<DD>/     Per-swath-pair files (AMSR2); currently 13–31 Jul 2019 only
```

## Open gaps and decisions

Status and blockers for every task are in [`ROADMAP.md`](ROADMAP.md). The items
below are unresolved choices that shape the analysis.

> **GLOB16 configuration must be settled before its production run** (`ROADMAP.md`
> A5, A10): changing it afterwards means running the simulation again.

**Observational data**

- **Swath coverage:** OSISAF S2S, the primary comparison product (WP2.2), is held
  only for 13–31 Jul 2019; decide whether to acquire more (B2).
- **Concentration product:** none held; needed for the observed Eq. 1 partition
  and the state comparison (B4).
- **Buoys:** AWI 2019 buoys are held; check their coverage against the model
  period (B5).
- **Retrieval uncertainty:** per-retrieval uncertainties (RO1 inputs) must be
  carried through every derived diagnostic, since gradients amplify error (B3, C5).

**Diagnostics**

- **Time matching:** model trajectories (3-hourly) must be subsampled to the
  satellite timestep before comparing time-sensitive metrics such as the
  meandering index (C3, G5).
- **Convergence masking:** flag or mask cells where `beta_evp` exceeds `nn_nevp`
  before attributing a vorticity or deformation misfit; the ORCA025
  100/500/2000 test covers what masking cannot, chiefly rotation-dominated ice
  (F4, F6).

## Environment

Analysis is carried out in the conda environment **`env010`** (Python 3.11.14).

```bash
conda activate env010
```

Full package list: `conda list -n env010`.

Project status: see [`ROADMAP.md`](ROADMAP.md).
