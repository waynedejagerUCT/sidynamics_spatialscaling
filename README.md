# Scale-Dependent Sea-Ice Kinematics: NEMO vs. Satellite-Derived Drift

## Aim

This project determines which dynamical processes in Antarctic sea-ice drift are
resolved as a function of spatial scale. Lagrangian trajectory diagnostics computed
from model output are compared against satellite-derived drift at matched
resolutions, in order to identify where model and observational representations of
sea-ice kinematics agree, and where they diverge.

## Approach

**Eulerian source data**

- NEMO SI3 (`SEAICE_DYN_002`) ice velocity fields at multiple grid resolutions:
  ORCA2, ORCA1, ORCA05, ORCA025, ORCA12.
- A satellite drift-retrieval product, to be incorporated as a parallel data source.

**Lagrangian simulation**

Synthetic ice parcels are seeded and advected through each velocity field using
[OceanParcels](https://oceanparcels.org/) or [OpenDrift](https://opendrift.github.io/).

**Diagnostics**

For each trajectory set, computed and compared across resolution and source:

- Advection pathways
- Divergence
- Vorticity
- Meandering index
- Cumulative distance travelled
- Zones of drift retention

**Synthesis**

Identification of the spatial scale at which specific dynamical features (e.g.
small-scale divergence, retention zones) become resolved or lost, and
characterisation of how model and satellite representations diverge.

## Repository structure

```
.
├── preprocessing/   Scripts for reading, regridding, and preparing NEMO and
│                     satellite velocity fields ahead of Lagrangian simulation.
├── plots/            Figures and plotting scripts for diagnostics and results.
└── misc/             Supporting scripts, notes, and other project material.
```

## Data

NEMO output is not stored in this repository. It is expected locally under:

```
~/Data/NEMO/SEAICE_DYN_002/
├── ORCA2/
├── ORCA1/
├── ORCA05/
├── ORCA025/
└── ORCA12/
```

Each resolution subdirectory is populated post-run with that configuration's NEMO
output (`_icemod`, `_grid_T`, `_sbcwind` files) and `domain_cfg.nc`.

> **Status:** ORCA025 is currently populated from `SEAICE_DYN_002`
> (segment-by-segment archival in progress). Other resolutions are pending.

Satellite drift data and retrieval-algorithm output will be added as a parallel
source once incorporated, likely under a sibling directory (e.g. `SATELLITE/` or
per-product subfolders).

### NEMO output files

Each monthly segment produces up to four NetCDF files, named
`SEAICE_DYN_002_<freq>_<startdate>_<enddate>_<stream>.nc`. Dates change per
segment; file structure and variables do not.

#### `..._3h_..._icemod.nc` — sea-ice state and momentum (3-hourly)

Grid: 1440×1050 (ORCA025), `time_counter` at 3 h steps. **Primary file for the
drift analysis** — `sivelu`/`sivelv` are what feed the Lagrangian simulator.

| Variable | Description | Units |
|---|---|---|
| `siconc` | Ice concentration | fraction, 0–1 |
| `sithic` | Ice thickness | m |
| `sivelu`, `sivelv` | Ice velocity, i/j components on the model grid | m/s |
| `utau_ai`, `vtau_ai` | Air → ice stress (relative to ice motion) | N/m² |
| `utau_oi`, `vtau_oi` | Ocean → ice stress | N/m² |

#### `..._1d_..._grid_T.nc` — prescribed ocean surface (daily)

Same grid, `time_counter` at 1-day steps. Daily because the source (GLORYS) is
itself a daily mean — no sub-daily signal exists to sample. Use `ssu_m`/`ssv_m`
for the ocean-driven component of relative-velocity diagnostics.

| Variable | Description | Units |
|---|---|---|
| `ssu_m`, `ssv_m` | Ocean surface current, interpolated onto the model grid and felt by the ice | m/s |
| `sst_m`, `sss_m` | Sea surface temperature, salinity | °C, psu |
| `ssh_m` | Sea surface height | m |

#### `..._3h_..._sbcwind.nc` — atmospheric wind forcing (3-hourly)

Added from segment 1 onward for the turning-angle diagnostic.

| Variable | Description | Units |
|---|---|---|
| `utau_oce`, `vtau_oce` | Open-ocean wind stress; with current-feedback disabled, direction is the absolute 10 m wind direction (unlike `utau_ai`, which is relative) | N/m² |
| `wspd` | 10 m wind speed magnitude | m/s |

#### `..._1mo_..._SBC_scalar.nc` — monthly scalar diagnostics

Monthly, only for segments spanning a full calendar month (not segment 1). Ten
scalar time series (total ice volume, area, salt/heat content, and their drifts)
— a conservation check, not intended for the drift analysis itself.

#### `domain_cfg.nc` — static grid geometry (once-off)

Copied once, shared across all segments. Needed alongside the output files for
anything beyond raw velocity fields — cell-area weighting, masking land, or
converting grid indices to lon/lat for Lagrangian seeding.

| Variable | Description |
|---|---|
| `e1t`, `e2t` | Grid cell dimensions (m); needed for any area-weighted quantity (total ice area, flux calculations) |
| `tmask` | Land/ocean mask |
| `nav_lon`, `nav_lat` | Cell-centre coordinates |

Also carries vertical grid info (z = 75 levels) — irrelevant here since SI3 fields
are 2D, but present because it's the same file NEMO uses for the full ocean
configuration.

## Environment

Analysis is carried out in the conda environment **`env010`** (Python 3.11.14).
Key packages, grouped by role in the pipeline:

| Role | Package(s) | Version |
|---|---|---|
| NetCDF I/O | `xarray`, `netcdf4`, `h5netcdf`, `cf_xarray` | 2026.1.0, 1.7.4, 1.8.1, 0.10.11 |
| Lagrangian simulation | `parcels`, `opendrift` | 3.1.4, 1.14.10 |
| Trajectory analysis | `trajan` | 0.8.0 |
| Regridding | `xesmf`, `esmf`/`esmpy` | 0.9.2, 8.9.1 |
| Grid-aware diagnostics (divergence, vorticity) | `xgcm` | 0.10.1 |
| Geospatial / satellite | `pyresample`, `cartopy`, `pyproj`, `shapely` | 1.35.0, 0.25.0, 3.7.2, 2.1.2 |
| Numerics | `numpy`, `scipy`, `pandas`, `numba` | 2.3.5, 1.17.0, 3.0.0, 0.63.1 |
| Parallel / out-of-core | `dask`, `distributed`, `mpi4py` | 2026.1.2, 2026.1.2, 4.1.2 |
| Plotting | `matplotlib-base`, `bokeh` | 3.10.8, 3.8.2 |
| Interactive use | `jupyter`, `ipykernel`, `ipython` | —, 7.2.0, 9.10.0 |

To activate:

```bash
conda activate env010
```

Full package list: `conda list -n env010`.

> **Maintenance:** this table reflects the environment as of the last README
> update. When a package is added to `env010` for this project, note it here
> the next time the README is revised.

## Status

This project is under active development. This README will be updated as the
codebase, data holdings, and results evolve.