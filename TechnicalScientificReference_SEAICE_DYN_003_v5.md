# SEAICE_DYN_003 — technical reference

NEMO 5.0 + SI3 standalone (SAS) Antarctic sea-ice hindcast; ORCA-family grids trimmed to 40°S; UCT HPC.

**Scope:** configuration, set-up and compute environment used to generate the v1 and v2 output, and
the reason for each scientific choice. Status, data locations and analysis: `README.md`, `ROADMAP.md`.

**Contents**
1. [Experiment and datasets](#1-experiment-and-datasets)
2. [Design of the comparison](#2-design-of-the-comparison)
3. [Compute environment](#3-compute-environment)
4. [Build](#4-build)
5. [Domain files](#5-domain-files)
6. [Forcing and initial condition](#6-forcing-and-initial-condition)
7. [Interpolation weights](#7-interpolation-weights)
8. [Timestep](#8-timestep)
9. [Run configuration](#9-run-configuration)
10. [Job submission](#10-job-submission)
11. [Verification](#11-verification)
12. [Production runs](#12-production-runs)
13. [NEMO 5.0 source facts](#13-nemo-50-source-facts)
14. [Scripts](#14-scripts)

---

## 1. Experiment and datasets

- **Question:** which sea-ice drift processes are resolved as a function of grid spacing → resolution
  is the only quantity varied between members; each departure is a stated caveat (§2).
- **Model:** forced standalone SI3 with a prescribed ocean surface (SAS); no prognostic ocean.
- **Period:** 2019-03-18 → 2019-11-01 (228 days); cold start.
- **Domain:** each grid truncated in j to the rows south of 40°S; full i extent (east–west periodicity
  kept). Otherwise physics, forcing, period and initial state of a standard global run.
- **Members:** ORCA2, ORCA1, ORCA05, ORCA025 — a ×2 ladder (2° → 0.25°) in one grid family.
  GLOB16 (1/16°, CMCC, different grid family): extension member; inputs built (§5, §7), not run.

**Datasets**

| Dataset | Members | `_icemod` fields | `nn_nevp` | `nemo.exe` | Launcher |
|---|---|---|---|---|---|
| v1 | ORCA2–ORCA025 | 8 | 100 | shipped SI3 source | `srun` without `--mem=0` |
| v2 | ORCA2–ORCA025 | 29 | 500 | + `MY_SRC/icedyn_rdgrft.F90` (§4) | `srun --mem=0` (§10) |
| v2 `ORCA025_NEVP2000` | ORCA025 | 29 | 2000 | as v2 | as v2 |

- **v1 → v2:** 21 extra `_icemod` fields (§9.5); `nn_nevp` 100 → 500 (§9.4), the only change
  affecting the solution; ridging-diagnostics fix (diagnostics only); `srun --mem=0` (memory only).
  ORCA025 v1 and v2 namelists identical apart from `nn_nevp`; same decomposition.
- **`ORCA025_NEVP2000`:** v2 ORCA025 with only `nn_nevp` and `cn_exp` changed (§9.2). Third setting of
  the ORCA025 solver test (100 / 500 / 2000). Reason: masking by `beta_evp` alone would remove the
  compact, low-deformation, rotation-dominated ice the vorticity analysis needs; three settings show
  whether the numerical contribution shrinks as ~exp(−N/β). Not a new data version.

**Pipeline**

```
        SHARED, BUILT ONCE                          PER MEMBER
   ┌──────────────────────────┐          ┌────────────────────────────────┐
   │ ERA5 download            │          │ source domain_cfg.nc            │
   │   → deaccumulate         │          │        ↓ audit_domain_cfg.py    │
   │   → time UNLIMITED       │          │        ↓ trim_domain_cfg.py     │
   │                          │          │ trimmed domain_cfg.nc (40°S)    │
   │ GLORYS surface forcing   │          │        ↓ build_weights.py       │
   │   → drown (30 passes)    │──────────┤ 3 weights files (SCRIP)         │
   │                          │          │        ↓ expand_weights.py      │
   │ GLORYS ice IC            │          │          (ORCA05 only, §7.3)    │
   │   → zero-fill            │          │        ↓ setup_production.sh    │
   └──────────────────────────┘          │ run directory + submit_run.sh   │
                                         │        ↓ sbatch                 │
   ┌──────────────────────────┐          │ 228-day production run          │
   │ NEMO 5.0 + SI3 + XIOS3   │──────────┤        ↓ verify_logs.sh         │
   │ one nemo.exe, all members│          │        ↓ verify_production.py   │
   └──────────────────────────┘          │ 31 output files                 │
                                         └────────────────────────────────┘
```

---

## 2. Design of the comparison

### 2.1 Held identical across members

| Item | Value |
|---|---|
| Trim latitude | −40.0°, same derived criterion (§5.3) |
| Forcing | same ERA5 and GLORYS files on their native global grids |
| Ice initial condition | same GLORYS file, interpolated to each grid at runtime |
| Run period | `nn_date0=20190318`, `nn_itend=21888` |
| Timestep | `rn_Dt=900`, `nn_fsbc=1` → `rDt_ice = 900 s` |
| Physics | `ln_eos80`, `ln_aEVP`, `rn_ecc`, `nn_nevp` (per dataset), `ln_adv_Pra`, `jpl`, `nlay_i`, `nlay_s`, `rn_ishlat=2.`, constant ice drag |
| Output | 3-hourly ice and wind stress, daily prescribed ocean, monthly scalars |
| Build | one `nemo.exe` per dataset |
| Northern wall | 2 land rows |
| Launcher | `srun --multi-prog`, same flags (§10) |

### 2.2 Varies with resolution

`domain_cfg.nc`; interpolation weights; MPI rank count and decomposition; wall clock; output volume.

### 2.3 Choices and caveats

- **Trim admissible.** Under SAS no wave propagation, barotropic adjustment or tracer advection;
  information enters only through ice advection and rheology (local + halo). Forcing at a retained
  point depends only on its coordinates and the unchanged global source → identical to a global run.
  Northern wall ≥ 2 500 km from any ice. Confirmed by Gate T0 (§11.1).
- **Trim consequences.** Domain integrals (`_SBC_scalar`: `ibgvol_tot`, `ibgarea_tot`) are
  Southern-Hemisphere totals, not global. Northernmost wet latitude differs by member (−40.13° GLOB16
  to −43.21° ORCA2). Wall width is resolution-dependent (~226 km ORCA2, ~6 km GLOB16), far from ice.
- **ERA5 at 0.25° for every member.** Drift changes come from the ice grid, not better-resolved wind;
  limits what "resolved drift" means at the finest members.
- **Bilinear weights, not bicubic.** Bicubic smoothing/overshoot would differ by resolution and
  corrupt turning angles.
- **Constant ice–atmosphere drag (`ln_Cx_ice_cst`).** Form-drag schemes respond to the resolved ice
  state → would confound the resolution signal.
- **Prather advection.** A diffusive scheme smears the ice edge by a grid-dependent amount.
- **No-slip coast (`rn_ishlat=2.`).** Coastal boundary layer spans fewer cells at coarse resolution —
  part of the resolution signal.
- **Landfast ice off.** No masks available; landfast schemes are strongly resolution-sensitive.
- **Levitating ice (`ln_ice_embd=.false.`).** Cold-start robustness.
- **Bathymetry lineage.** Undocumented for ORCA1, ORCA025, GLOB16 (CMCC finished files); ORCA05
  IGE/CNRS (§5.2). All five cavity-free; provenance-driven coastline differences cannot be separated
  from resolution.
- **ORCA05 is eORCA-derived.** Extends south of the GLORYS −80° limit → weights post-processing
  (§7.3); affected cells are all land.
- **Ocean velocity staggering.** `ssu_m`/`ssv_m` assigned at T without interpolation
  (`sbcssm.F90:109-110`); half-cell offset ~47 km (ORCA2) to ~5.9 km (ORCA025) in the ocean-drag term.
- **aEVP not converged everywhere.** At `nn_nevp=500` a small, resolution-dependent tail of compact,
  low-deformation ice has β > `nn_nevp` (§9.4); flagged per cell by `beta_evp`.

---

## 3. Compute environment

| Item | Value |
|---|---|
| Cluster | UCT HPC, `hex.uct.ac.za` (head node `srvrochpc001`), user `djgway001` |
| SLURM | `--account=oceanography`, `--partition=ada`, QOS `normal`; per job `cpu=120, node=6`; account `GrpTRES cpu=200`; no walltime limit |
| Nodes | 100-series (`--constraint=large`): 48 cores, 375 GB, 7.8125 GB/core |
| Storage | `/scratch/djgway001` 250 GB, not backed up (inputs, runs); `/home` 10 GB |
| Software | NEMO 5.0; XIOS3 trunk r2793; GCC 11.5.0; OpenMPI 5.0.3 (PMIx `pmix_v5`); HDF5 1.14.6 (MPI); netCDF-C 4.9.2 (parallel); netCDF-Fortran 4.6.1 |

**Environments**
- Build, SCRIP weights, runs: modules via `/scratch/djgway001/NEMO/env_nemo.sh`; **no conda active**
  (conda's netCDF shadows the module `libnetcdff.so.7`).
- Domain audit and trim, weights verification, output verification: conda `nemo_analysis` (netCDF4
  1.7.4, numpy 2.4.3, xarray, scipy, pandas). The trim writes in the source file's own netCDF format,
  so the conda `libnetcdf` version does not matter. No NCO.
- Forcing downloads: conda `cmems_download` (GLORYS), `era5_download` (ERA5).
- Compute through `sbatch` or `sintx`; head node for light work only.

---

## 4. Build

One `nemo.exe` for all members: cpp keys and components are grid-independent.

| Item | Value |
|---|---|
| Configuration | `SEAICE_DYN_003` from reference `ORCA2_SAS_ICE`; arch `UCT_GCC`; added key `key_xios3` |
| Components | `OCE ICE NST SAS` (`cfgs/ref_cfgs.txt`; not forced with `-d`) |
| cpp keys | `key_si3 key_linssh key_vco_1d3d key_xios key_RK3 key_xios3` |
| `EXP00/iodef.xml` | `oasis_codes_id` element removed (XIOS3 aborts on it) |
| Tools | `WEIGHTS` (`scripgrid`, `scrip`, `scripshape`); `DOMAINcfg` (ORCA05 only) |

- `key_linssh`: XOR with `key_qco` (`domzgr.F90:89`); valid — no prognostic ocean, `sn_e3t` never read.
- `key_RK3`: from the SAS reference; `rn_atfp` unused but read unconditionally (`domain.F90:241`).
- **`MY_SRC/icedyn_rdgrft.F90` (v2):** `ll_diag_rdg = .TRUE.` unconditionally. Reason: the shipped
  `ice_dyn_rdgrft_init` sets it from `iom_use('lead_open' | 'rdg_*' | 'rft_*')` before the XIOS context
  is closed → always `.FALSE.` → those five fields never written. The flag also gates allocation in
  `ice_dyn_rdgrft_alloc`, so it is not re-evaluated per step. Diagnostics only; no physics change.

---

## 5. Domain files

### 5.1 Source files (as received, never modified)

| File | Grid | Provenance | Periodicity stored as | Identity resolves to | Cavities |
|---|---|---|---|---|---|
| `domain_cfg_ORCA2L31.nc` | 180×148×31 | NEMO 5.0 distribution (`ORCA_R2_zps_domcfg.nc`) | modern attributes | `ORCA`/2 | none |
| `domain_cfg_ORCA1L50.nc` | 360×291×50 | CMCC | legacy `jperio=6` | `ORCA`/1 (via `ORCA_index`) | none |
| `domain_cfg_ORCA05L75.nc` | 722×604×75 | built in-house (§5.2) | legacy `jperio=4` | `UNKNOWN`/−999 | none |
| `domain_cfg_ORCA025L75.nc` | 1440×1050×75 | CMCC | legacy `jperio=4` | `UNKNOWN`/−999 | none |
| `domain_cfg_GLOB16L98.nc` | 5760×3962×98 | CMCC | legacy `jperio=6` | `GLOB16`/6 (via `cn_cfg`/`nn_cfg`) | none |

- Three periodicity conventions → the trim writes explicit `NFold`/`NFtype` (§13.1).
- Cavity-free by count (`top_level > 1` = 0), not by the declared flag.
- ORCA2 `strait_shlat` (NH straits): sliced only; inert after the trim.
- ORCA1 and ORCA025 are classic ORCA, not eORCA. ORCA025's 1440×1050 shape is a CMCC `ncks` trim of
  overlap columns (in `history`); southernmost wet latitude −78.60°.
- Audited with `audit_domain_cfg.py` (target −40.0°) → `AUDIT_domain_cfgs_40S.{txt,json}`.

### 5.2 ORCA05 build

- No classic ORCA05 `domain_cfg` available → built with `DOMAINcfg` `make_domain_cfg.exe` (one rank).
- **Sources:** `DOMAIN_cfg_build.tar` (IGE/CNRS eORCA05.L75; https://doi.org/10.5281/zenodo.14361713):
  `eORCA05_coordinates.nc`, `eORCA05_bathymetry_b0.2_closed_seas.nc`.
- **Namelists:** this NEMO tree's `namelist_ref`/`namelist_cfg` (the supplied ones lack the
  `cn_domcfg`, `cn_topo`, `cn_bath`, `cn_lon`, `cn_lat` variables `&namdom` requires, `domain.F90:164`).
  Overrides: `jpidta`/`jpjdta`/`Ni0glo`/`Nj0glo` = 722/604 only. Vertical coefficients (`ppsur`,
  `ppa0–2`, `ppkth`, `ppkth2`, `ppacr`, `ppacr2`, `ldbletanh`) match the supplied namelist (same L75).
- `ln_isfcav=.false.` (result: `top_level ∈ {0,1}`); `ln_domclo=.true.`, `nn_closea=8`, geographic
  closed-sea definitions from the reference `&namclo` (NH only; removed by the trim).
- Output: `domain_cfg.nc` (`NETCDF3_64BIT_OFFSET`) and `mesh_mask.nc`.
- Keeps the eORCA southward extension (`gphit` min −85.79°, vs −78.6° ORCA025) → larger retained
  fraction (42.2%) and southern rows beyond GLORYS coverage (§7.3).

### 5.3 Trim

- **Cut in j only**, all i kept; not AGRIF, not BDY (neither needed).
- **Row derived, never hardcoded:** `j_north = max{ j : max_i gphit[j,:] ≤ −40.0 }`, contiguous block
  from the southern edge. Max over i → no retained point north of the target. Cut-row zonal spread
  0.000000° at all five (constant j = constant latitude).
- **`trim_domain_cfg.py` steps:**
  1. Slice every y-dimensioned variable.
  2. Global attributes `Iperio=1`, `Jperio=0`, `NFold=0`, `NFtype='-'`; legacy `jperio` → 1 where
     present. A real `NFold`/`NFtype` pair is what disables NEMO's legacy fallback.
  3. 2-row northern land wall: `top_level`, `bottom_level`, `mbku`, `mbkv`, `mbkf` = 0.
  4. Correct `jpiglo`/`jpjglo`/`jpkglo` and `DOMAIN_size_*` (unread by NEMO; stale in sources).
  5. `CfgName`/`CfgIndex`: explicit `ORCA`/5 (ORCA05) and `ORCA`/4 (ORCA025); `ORCA_index` updated
     where present.
  6. Carry every source global attribute except `history` (rebuilt with the trim entry). Required:
     `domzgr.F90:115` reads the `VertCoord` attribute when no `ln_zco`/`ln_zps`/`ln_sco` variable
     exists (ORCA2: `VertCoord="zps"`).
  7. Provenance attributes `Trim*`.
  - Library-default chunking; source compression settings kept.
- **Verification (from disk, NEMO's resolution logic):** no `gphit` north of the target; no wet wall
  cells; `gphit`, `glamt`, `e1t`, `e2t`, `ff_t` bitwise equal to the source; no global attribute lost.
  All five passed.

### 5.4 Trimmed products

`inputs/<GRID>_ANT40S/domain_cfg.nc`, with `TRIM_LOG.txt`.

| Member | Trimmed grid | Rows kept | Cut latitude | Northernmost wet | Surface-wet cells |
|---|---|---|---|---|---|
| ORCA2 | 180×44×31 | 44 / 148 | −40.220644 | −43.205710 | 5 226 |
| ORCA1 | 360×88×50 | 88 / 291 | −40.220644 | −41.730512 | 21 486 |
| ORCA05 | 722×255×75 | 255 / 604 | −40.220644 | −40.979898 | 88 025 |
| ORCA025 | 1440×354×75 | 354 / 1050 | −40.029484 | −40.411265 | 351 220 |
| GLOB16 | 5760×1179×98 | 1179 / 3962 | −40.029484 | −40.125131 | 5 250 546 |

- Cut latitudes pair: ORCA2/1/05 rows are exact refinements of each other; ORCA025 and GLOB16 are
  independent constructions.
- ORCA05's 722 columns = 720 + 2 duplicate zonal halo columns; the others are exactly periodic.
- Each member's output is paired with its trimmed `domain_cfg` (cell metrics and positions; the
  output carries none).

---

## 6. Forcing and initial condition

Built once, shared by every member, kept on the source grids; NEMO interpolates at runtime.

| Product | Location | Content |
|---|---|---|
| GLORYS12 surface ocean | `inputs/GLORYS12/forcing_002/processed/` | `thetao`, `so`, `uo`, `vo`, `zos`; daily; 45 monthly files |
| ERA5 atmosphere | `inputs/ERA5/{raw,processed}/` | hourly; `raw/`: 10u, 10v, 2t, 2d, msl; `processed/`: ssrd, strd, tp, sf; monthly files |
| Ice initial condition | `inputs/GLORYS12/glorys12_seaiceIC_20190318.nc` | `ati`, `hti`, `hts` |

| Source | Longitude | Latitude | Shape |
|---|---|---|---|
| ERA5 | 0 … 359.75 (0.25°) | +90 … −90, descending | 1440 × 721 |
| GLORYS12 | −180 … 179.9167 (1/12°) | −80.0 … +90, ascending | 4320 × 2041 |

- **GLORYS product:** `cmems_mod_glo_phy_my_0.083deg_P1D-m` (multi-year reanalysis; the file `title`
  wrongly says forecast).
- **Sources stay global:** weights hold absolute source indices and NEMO takes the source shape from
  the data file (§13.2); the northernmost retained row's stencil samples north of 40°S → no edge
  effect at the trim boundary.
- `_002`, `forcing_002`: historical names only.

**NaN treatment** — opposite treatments, because NaN means different things.

| Field | NaN means | Treatment | Reason |
|---|---|---|---|
| `thetao`, `so`, `uo`, `vo`, `zos` | land | **drown**: 8-neighbour iterative fill, 30 passes | no `nn_lsm` → weights applied blind; a NaN anywhere in a stencil propagates. Filled land values are masked at runtime. 30 passes: ~9 km source cells vs ~250 km margin |
| `ati`, `hti` | no ice (`cell_methods = "area: mean where sea_ice"`) or land | **zero-fill**; clip `ati` to [0, 1] | drowning would spread pack concentrations across open ocean |

- Ice IC: no time dimension; verified no NaN, `ati` ∈ [0, 1], zero ice between −60° and +40° (Arctic
  ice is genuine and discarded at interpolation).
- **ERA5 deaccumulation:** pointwise — `ssrd`/`strd` ÷ 3600; `tp`/`sf` × 1000/3600; clamp ≥ 0. Paired
  with `ln_prec_met=.false.` (`.true.` would convert twice). Time dimension UNLIMITED.
- File-format rules: §13.2.

---

## 7. Interpolation weights

| File | Source | Used by |
|---|---|---|
| `weights_bilin_era5_<grid>_ant40s.nc` | ERA5 | `&namsbc_blk`, all nine fields |
| `weights_bilin_glorys_<grid>_ant40s_sas.nc` | GLORYS12 | `&namsbc_sas`, all five fields |
| `weights_bilin_glorys_<grid>_ant40s_ice.nc` | GLORYS12 | `&namini`, ice IC |

Built by `build_weights.py` (module environment): `scripgrid → scrip → scripshape` per source; the
GLORYS result copied to the second name. Output: `inputs/<GRID>_ANT40S/weights/`.

### 7.1 Settings (all binding)

- Bilinear (§2.3); T-point (`fld_rot` hardcodes `'T'`, `fldread.F90:750-751`).
- `ew_wrap = 0` in `&shape_inputs` (as `tools/WEIGHTS/namelist_bilin`; halo-free `domain_cfg`).
- `method = 'regular'` for both sources (SCRIP handles either longitude convention and latitude order).
- `scripgrid` needs the target as `coordinates.nc` in its working directory (`build_weights.py` links
  the trimmed `domain_cfg.nc`).
- Two GLORYS files, identical content, distinct names (`fldread` cache keyed by filename).
- `_ant40s` token: weights are bound to the trimmed grid; a mismatched pair fails silently.

### 7.2 Placement

`cn_dir` prepends to the weights filename as well as the data root:

| Block | `cn_dir` | Weights location |
|---|---|---|
| `&namsbc_blk` | `inputs/ERA5/` | `inputs/ERA5/` (symlink) |
| `&namsbc_sas` | `inputs/GLORYS12/forcing_002/processed/` | same (symlink) |
| `&namini` | `./` | run directory (symlink) |

### 7.3 ORCA05 post-processing

- SCRIP skips destinations outside source coverage, and `scripshape` writes the remaining links in
  link order (compacted). NEMO reads `src0k`/`wgt0k` positionally and never `dst0k` → a compacted file
  misaligns forcing across the whole domain.
- ORCA05 only (eORCA05 reaches −85.79°; GLORYS stops at −80.0°): 19 122 of 184 110 destinations
  skipped, all land (j = 0–45). ERA5 weights unaffected.
- `expand_weights.py` on the GLORYS SAS file, then copied to `_ice`:
  1. scatter by `dst`, so entry (j,i) is destination (j,i);
  2. filled slots `wgt = 0`;
  3. filled slots take the nearest mapped neighbour's source index — valid, and nearby so per-rank
     source read boxes (from `MINVAL`/`MAXVAL` of indices, `fldread.F90:1215-1222`) are not inflated.

### 7.4 Verification

- `expand_weights.py --verify-only` (full check): positional (`dst0k[n] = n+1`); every wet cell has
  non-zero total weight; no read-box inflation. (`build_weights.py --verify-only`: shape and
  finiteness only.)
- All files passed. ORCA05 GLORYS pair: 19 122 zero-weight land cells by construction; none elsewhere.
  GLOB16 needs no expand step (southern limit −78.41°).

---

## 8. Timestep

`rDt_ice = nn_fsbc × rn_Dt` (`icestp.F90:374`); `nn_fsbc = 1` → **`rDt_ice = rn_Dt = 900 s`** for all
four ORCA members; 96 steps/day (`MOD(rday, rDt_ice) = 0`); `nn_itend = 21888` (228 days).

**Reasons**
- Uniform → timestep is not a covariate between members.
- 52 steps per inertial period (~13 h at 65°S); 3600 s (CFL-admissible at coarse members) gives 13.
  Inertial loops, meandering and vorticity are target diagnostics.
- SI3-internal timestep dependence regardless of forcing cadence: aEVP α/β (β ∝ √rDt_ice), inertial
  motion, quadratic drag, Prather Courant number.
- Affordable: no walltime limit; output volume and memory independent of timestep (output frequency
  in model time).
- `nn_fsbc = 1`: non-SBC steps nearly free under SAS; 4 SBC calls per hourly ERA5 record, linear
  interpolation between record midpoints.

**CFL check** — minimum retained spacing; peak ice speed 1.85 m/s (largest 3-hourly-mean speed over
the four v1 members, ORCA05, 2019-05-27; instantaneous peaks are higher, so margins are optimistic).

| Member | Median e1t at 65°S | Min spacing | CFL limit | Margin at 900 s |
|---|---|---|---|---|
| ORCA2 | 94.5 km | 47.10 km | ~25 500 s | 28× |
| ORCA1 | 47.2 km | 21.39 km | ~11 600 s | 13× |
| ORCA05 | 23.4 km | 10.48 km | ~5 700 s | 6.3× |
| ORCA025 | 11.8 km | 5.30 km | ~2 900 s | 3.2× |
| GLOB16 | 2.9 km | 1.40 km | ~757 s | 0.84× (900 s inadmissible) |

---

## 9. Run configuration

### 9.1 Directory layout

```
/scratch/djgway001/NEMO/
├── env_nemo.sh
├── nemo_5.0/                         NEMO source, BLD, tools (WEIGHTS, DOMAINcfg)
├── xios/bin/xios_server.exe
├── inputs/
│   ├── domain_cfgs/                  as-received domains (§5.1), scripts, audit reports, ORCA05_build/
│   ├── <GRID>_ANT40S/                domain_cfg.nc, TRIM_LOG.txt, weights/
│   ├── GLORYS12/
│   └── ERA5/
└── experiments/SEAICE_DYN_003/
    ├── setup_production.sh
    ├── common/                       templates: namelist_cfg.template, namelist_ice_cfg.template,
    │                                 namelist_ref, namelist_ice_ref, *.xml
    ├── <GRID>/                       one per member (and ORCA025_NEVP2000)
    │   ├── namelist_cfg  namelist_ice_cfg  *.xml        copies
    │   ├── nemo.exe  xios_server.exe  domain_cfg.nc     symlinks
    │   ├── weights, ice IC                              symlinks
    │   ├── submit_run.sh  nemo_mpmd.conf
    │   └── restart_files/  logs/
    └── VALIDATION/                   verify_logs.sh, verify_production.py, T0_trim_equivalence/
```

- Namelists and XMLs are copies (a symlink would let one member's edits change the others); shared
  inputs and executables are symlinks to real targets (`nemo.exe` → `BLD/bin/`, not the `EXP00` link).
- Edit `common/`, then regenerate members.

### 9.2 `setup_production.sh`

- Generates each member directory from `common/`: copies namelists and XMLs; substitutes grid token,
  weights names and `cn_exp`; makes the symlinks; writes `nemo_mpmd.conf` and `submit_run.sh`; creates
  `restart_files/` and `logs/`.
- **Templates hold Gate T0 values** (`rn_Dt=3600.`, `nn_itend=72`, `nn_stocklist=72`,
  `nn_rhg_chkcvg=1`); production values from the script header are substituted: `rn_Dt=900.`,
  `nn_itend=21888`, monthly `nn_stocklist`, `nn_rhg_chkcvg=0`.
- v2: `nn_nevp = 500` set in `namelist_ice_cfg.template` (not substituted); 29-field `_icemod` list in
  `common/file_def_nemo-ice.xml`.
- **Ranks** (`MEMBERS` table): ORCA2 4, ORCA1 8, ORCA05 16, ORCA025 38, each + 2 XIOS. Automatic
  decomposition (no `jpni`/`jpnj`).
- `cn_exp = "SEAICE_DYN_003_<GRID>"` (no trim token: every member is trimmed).
- One run directory per member (`ocean.output`, `time.step`, `layout.dat` are overwritten by each run).

**Exceptions (v2)**
- **ORCA05:** `namelist_cfg` hand-edited to `nn_stocklist = 21888` only (restart point; no effect on
  physics or output). The member's saved `namelist_cfg` is the record.
- **`ORCA025_NEVP2000`:** the script has no variant option → ORCA025 member generated, directory
  renamed, then hand-edited (recorded in `NEVP2000_EXCEPTION.txt`): `nn_nevp = 2000`;
  `cn_exp = "SEAICE_DYN_003_ORCA025_NEVP2000"`; `submit_run.sh` paths and job name. Everything else
  identical to v2 ORCA025. This `cn_exp` exceeds the 29-character limit for ice restart names (§13.3).

### 9.3 `namelist_cfg`

Base: `cfgs/ORCA2_SAS_ICE/EXPREF/namelist_cfg`. Block set must match the SAS reference (an orphan
block aborts at init). `[PER-GRID]` = substituted per member.

- **`&namrun`** — `cn_exp="SEAICE_DYN_003_<GRID>"` `[PER-GRID]`, `nn_date0=20190318`, `nn_it000=1`,
  `nn_itend=21888`, `nn_leapy=1`, `ln_rstart=.false.`, `ln_rst_list=.true.`,
  `nn_stocklist=1344,4224,7200,10080,13056,16032,18912,21888,0,0` (monthly; only the first is written
  under SAS, §13.3), `cn_ocerst_indir/outdir="restart_files"`.
- **`&namdom`** — `rn_Dt=900.`, `rn_atfp=0.1`, `ln_meshmask=.false.`
- **`&namcfg`** — `ln_read_cfg=.true.`, `cn_domcfg="domain_cfg"`, `ln_closea=.false.`
- **`&namsbc`** — `nn_fsbc=1`, `ln_blk=.true.`, `nn_ice=2`, `ln_ice_embd=.false.`, `ln_traqsr=.false.`,
  `ln_dm2dc=.false.`, `ln_ssr=.false.`, `ln_rnf=.false.`, `ln_apr_dyn=.false.`, `nn_fwb=0` (all
  explicit).
- **`&namsbc_blk`** — `ln_ECMWF=.true.`; `ln_humi_dpt=.true.`; `ln_tair_pot=.false.`;
  `ln_prec_met=.false.` (§6); `rn_zqt=2.`, `rn_zu=10.`; `ln_crt_fbk=.false.`; `ln_Cx_ice_cst=.true.`,
  `rn_Cd_ia=rn_Ce_ia=rn_Ch_ia=1.4e-3` (§2.3); `cn_dir='/scratch/djgway001/NEMO/inputs/ERA5/'`; roots
  `raw/era5_<tag>`, `processed/era5_<tag>`; freq `1.`, `'monthly'`, `clim=.false.`, time interpolation
  `.true.`; wind pair `'Uwnd'`/`'Vwnd'`; weights `[PER-GRID]`.
- **`&namsbc_sas`** — `l_sasread=.true.`, `ln_3d_uve=.false.`, `ln_read_frq=.false.`;
  `cn_dir='/scratch/djgway001/NEMO/inputs/GLORYS12/forcing_002/processed/'`; `sn_usp`/`sn_vsp` paired
  `'Ucur'`/`'Vcur'`, `sn_tem`, `sn_sal`, `sn_ssh`: 24 h, `'monthly'`, weights `[PER-GRID]`;
  `sn_e3t`/`sn_frq`/`sn_ifr`/`sn_tic`/`sn_ial` = `'NOT USED'`; no LSM (source drowned). Slot order:
  `sbcssm.F90:195`.
- **`&nameos`** — `ln_eos80=.true.`, `ln_teos10=.false.` (SAS reference ships TEOS-10). Reason: the
  freezing point (`eos_fzp`, `sbcssm.F90:129`) must match GLORYS potential temperature and practical
  salinity; a TEOS-10 offset would interact with resolution through the ice edge.
- **`&namlbc`** — `rn_shlat=2.` (inert under SAS).
- **`&namtile`, `&nammpp`, `&namctl`, `&namsto`** — reference values.

### 9.4 `namelist_ice_cfg`

- **`&nampar`** — `jpl=5`, `nlay_i=10`, `nlay_s=5`, `ln_virtual_itd=.false.`, `ln_icedyn=.true.`,
  `ln_icethd=.true.`, `rn_amax_n=rn_amax_s=0.997`; `cn_icerst_in/out="restart_ice"`,
  `cn_icerst_indir/outdir="restart_files"` (restart variables belong here, not in `&namini`).
  `jpl` fixed across members (category count interacts with the resolved thickness distribution).
- **`&namdyn`** — `rn_ishlat=2.` (no slip; SI3 builds its own `fimask`, `icedyn_rhg_evp.F90:220-221`).
- **`&namini`** — `nn_iceini_file=1`; `sn_hti`/`sn_hts`/`sn_ati` → ice IC, weights `[PER-GRID]`; other
  slots `'NOT USED'`; `rn_apd_ini_s=rn_hpd_ini_s=rn_hld_ini_s=0.0` (no ponds); `cn_dir='./'`.
- **`&namdyn_rhg`** — `ln_rhg_EVP=.true.`, `ln_aEVP=.true.`, `rn_ecc=2.0`, `nn_nevp=500` (v1: 100),
  `rn_relast=0.333` (unused under aEVP, `icedyn_rhg_evp.F90:236-238`), `rn_creepl=2e-9`,
  `nn_rhg_chkcvg=0`.
- **`&namdyn_adv`** — `ln_adv_Pra=.true.`, `ln_adv_UMx=.false.` (§2.3; XOR enforced,
  `icedyn_adv.F90:157`; Prather moments are part of the restart).

**aEVP and the choice of `nn_nevp`**
- Per-cell relaxation (`icedyn_rhg_evp.F90:446, 468`):
  `β = MAX(50, π·√(0.5·P/(Δ + rn_creepl) / (e1t·e2t) · rDt_ice / m))`, `P = P*·vt_i·exp(−C(1−A))`.
  With P ∝ vt_i and m ≈ ρᵢ·vt_i, thickness cancels: β depends on concentration, deformation rate Δ and
  cell area (β ∝ 1/√area). `nn_nevp` is an iteration count only (no elastic timescale under aEVP);
  residual after N iterations ~exp(−N/β).
- Unconverged share grows with resolution. Offline estimate from v1 (`scripts/estimate_beta_evp.py`,
  Sep 2019, ice cells): β > 100 in 0.007% (ORCA2), 0.37% (ORCA1), 2.65% (ORCA05), 8.07% (ORCA025) of
  ice → `nn_nevp=100` adds resolution-dependent numerical error to the target diagnostics.
- **`nn_nevp = 500` (v2):** ~96% of ORCA025 ice under ~5% residual; the remaining tail is compact,
  low-deformation ice, flagged per cell by `beta_evp`. Cost: v2/v1 wall clock 1.56× (ORCA2) to 1.90×
  (ORCA025), no early exit (`nn_rhg_chkcvg=0`).

### 9.5 XIOS output

- XML from `cfgs/SEAICE_DYN_003/EXP00/` (`oasis_codes_id` removed); both `file_def` files rewritten;
  `field_def_nemo-{oce,ice}.xml` as shipped; all other file groups empty. No `--` inside XML comments.
- File IDs must be `fileN` (token substitution only for `file0..file999`, `iom.F90:2726-2738`).

| ID | Stream | Freq | Fields |
|---|---|---|---|
| `file21` | `_icemod` | 3 h | v1 (8): `siconc, sithic, sivelu, sivelv, utau_ai, vtau_ai, utau_oi, vtau_oi`; v2 adds 21: `afxdyn, afxthd, rdg_loss, rdg_gain, rft_loss, rft_gain, lead_open, intstrx, intstry, corstrx, corstry, dssh_dx, dssh_dy, snwmass, icediv, iceshe, icedlt, icestr, normstr, sheastr, beta_evp` |
| `file22` | `_SBC_scalar` | monthly | 10 ice-budget scalars (domain = Southern Hemisphere) |
| `file11` | `_grid_T` | daily | `ssu_m, ssv_m, sst_m, sss_m, ssh_m` |
| `file12` | `_sbcwind` | 3 h | `utau_oce, vtau_oce, wspd` |

- **v2 fields, purpose:** area-change partition (`afxdyn`, `afxthd`, ridging/rafting gains and losses,
  `lead_open`); momentum balance (`intstr*`, `corstr*`, `dssh_d*`, `snwmass`; ice + snow mass =
  ρᵢ·`siconc`·`sithic` + `snwmass`); native deformation and rheology state (`icediv`, `iceshe`,
  `icedlt`, `icestr`, `normstr`, `sheastr`); convergence (`beta_evp`; 50 over open water).
- `uice_cvg` not output (written only when `nn_rhg_chkcvg > 0`).
- Every `field_ref` must receive data under SAS (the reference ships ~15 that do not; failure is
  silent).
- **Frequencies, same for all members:** 3-hourly ice (resolves the ~13 h inertial period); daily ocean
  (GLORYS is daily; 3-hourly output would repeat a linear interpolant).
- **`_sbcwind`:** `utau_ai` uses relative wind; the Nansen turning angle needs absolute 10 m wind
  direction (`utau_oce`/`vtau_oce`) and speed (`wspd`).
- **`split_freq="1mo"` on every file:** closed files survive a kill; month-scoped files. Months count
  from the run start: `_201903-201904` = 18 Mar – 18 Apr (248 3-hourly records); last file 18 Oct –
  1 Nov (112).
- **No compression:** XIOS3 raises an error for compression in parallel mode (`onetcdf4.cpp:527-529`).
- **Filenames** (`name="@expname@_@freq@"`): `SEAICE_DYN_003_<GRID>_3h_icemod_YYYYMM-YYYYMM.nc`.
- **Grid positions:** `sivelu`, `intstrx`, `corstrx`, `dssh_dx`, … are on C-grid U points and the
  `…v`/`…y` fields on V points (`icewri.F90:134-135`, written without interpolation), although
  labelled `grid_T_2D` with T-point `nav_lon`/`nav_lat`.

---

## 10. Job submission

`submit_run.sh` (written by `setup_production.sh`):

| Setting | Value | Reason |
|---|---|---|
| `#SBATCH` | `--account=oceanography --partition=ada --constraint=large --ntasks=48 --cpus-per-task=1`, no `--mem`, no `--time` | full node and its 375 GB (`--ntasks=N` alone allocates N × 7.8125 GB) |
| Launcher | `srun --mpi=pmix --mem=0 --ntasks=<N+2> --cpu-bind=none --multi-prog nemo_mpmd.conf` | SLURM MPMD launcher (cluster policy: `srun`, not `mpirun`) |
| `nemo_mpmd.conf` | ranks 0…N−1 `./nemo.exe`; N…N+1 `./xios_server.exe` | one `MPI_COMM_WORLD`; XIOS server mode, 2 servers |
| `--mem=0` (v2) | step receives the job's memory (effective ceiling 300 GB) | without it the step gets the per-task default, `ntasks × 8000 MB` |
| `--cpu-bind=none` | required | the default binding falls outside the step's cpuset → immediate failure |

- One submission per member (no walltime limit). Rank count must stay the same across any resubmission
  (restarts are per rank).
- `submit_run.sh --dry-run` writes the namelists and batch script without submitting; check the
  generated values against §9 before `sbatch`.

---

## 11. Verification

### 11.1 Gate T0 — trim equivalence

- Global vs trimmed ORCA025: same build, 38 + 2 ranks; only the domain file and its weights differ;
  72 steps at template values.
- Pass criteria: identical first record; domain integrals agree. (Bit-identity is impossible: different
  row counts per rank change the summation order.)
- **Passed:** first record identical in `siconc`, `sivelu`, `sivelv`; ice area and volume integrals
  agree to ~1e-5 (relative) without trend; wall rows identical → the trim is inert.

### 11.2 Before production

- ORCA2 72-step validation of the v2 set-up (`nn_rhg_chkcvg=1`): all 29 `_icemod` fields written.

### 11.3 After each run

- `verify_logs.sh`: completion, errors, parameters as read by NEMO, configuration identity, vector
  rotation, launcher (from `sacct`), restarts, output inventory, stale files.
- `verify_production.py`: every file and time axis complete and contiguous, finite over wet cells,
  physical ranges, `_SBC_scalar` table, peak ice speed, restarts readable.
- **All v1 and v2 members passed both.** `ORCA025_NEVP2000`: passed apart from the restart-name check
  (truncated ice restart names, §13.3).
- Benign by design: `sst_m` minimum ≈ −2.55 °C (GLORYS freezing point); one `W A R N I N G` block in
  `ocean.output`; XIOS buffer and `zoom_axis` messages; a single restart point (§13.3).

---

## 12. Production runs

**v1** (`nn_nevp = 100`, 8 fields)

| Member | Ranks (decomposition) | Per-rank `jpi`×`jpj` | Elapsed | s/step | Step MaxRSS | Output |
|---|---|---|---|---|---|---|
| ORCA2 | 4 (4×1) | 49×48 | 35:53 | 0.098 | 14.3 GiB | 0.63 GiB |
| ORCA1 | 8 (8×1) | 49×92 | 56:25 | 0.155 | 13.8 GiB | 2.51 GiB |
| ORCA05 | 16 (5×4 − 4 land) | 149×68 | 2:01:12 | 0.332 | 39.2 GiB | 14.6 GiB |
| ORCA025 | 38 (14×3 − 4 land) | 107×122 | 3:53:36 | 0.640 | 43.3 GiB | 40.4 GiB |

**v2** (29 fields; same decompositions)

| Member | `nn_nevp` | Elapsed | s/step | × v1 | Step MaxRSS | Output |
|---|---|---|---|---|---|---|
| ORCA2 | 500 | 55:50 | 0.153 | 1.56 | 19.7 GiB | 1.76 GiB |
| ORCA1 | 500 | 1:28:31 | 0.243 | 1.57 | 13.2 GiB | 7.04 GiB |
| ORCA05 | 500 | 3:36:31 | 0.594 | 1.79 | 36.9 GiB | 40.9 GiB |
| ORCA025 | 500 | 7:24:53 | 1.22 | 1.90 | 51.0 GiB | 113.1 GiB |
| `ORCA025_NEVP2000` | 2000 | 20:52:16 | 3.43 | 5.36 | 41.1 GiB | 113.1 GiB |

- Elapsed includes initialisation; MaxRSS from `sacct` (largest task in the step).
- **Output per member:** 31 files — 8 `_icemod`, 8 `_sbcwind`, 8 `_grid_T`, 7 `_SBC_scalar` (no complete
  March month); 1 824 + 1 824 + 228 + 7 = 3 883 records.
- Restarts: one point, step 1344 (§13.3); not part of the datasets.

---

## 13. NEMO 5.0 source facts

From `nemo_5.0/src/`; these set the configuration rules above.

### 13.1 Domain file

- Global dimensions = shape of `e3t_0` (`domain.F90:568-654`); `jpiglo`/`jpjglo`/`jpkglo` never read.
  Inner dimensions (`Ni0glo`/`Nj0glo`); halo added at runtime.
- Periodicity = global attributes `Iperio`, `Jperio`, `NFold`, `NFtype` (absent → false/`'-'`). Legacy
  `jperio` used only if both `NFold` and `NFtype` are absent and `jperio` exists.
- Identity: `CfgName`/`CfgIndex` → `ORCA`/`ORCA_index` → `cn_cfg`/`nn_cfg` → `UNKNOWN`/−999
  (cosmetic).
- `&namcfg` has five variables only (`ln_read_cfg`, `cn_domcfg`, `ln_closea`, `ln_write_cfg`,
  `cn_domcfg_out`); no `ln_use_jattr`. `cn_domcfg` absent → idealised GYRE domain built silently.
- Ocean vertical dimension inert under SAS + SI3 (no `jpk` use in `SAS/step.F90` or `src/ICE`; the
  only `jpk` allocation in `sbcssm.F90` needs `nfld_3d > 0`) → different level counts (L31–L98) do not
  affect comparability. `bottom_level` still sets `tmask(:,:,1)` → `fimask` → coastal ice deformation.

### 13.2 Forcing

- Weights hold absolute source indices; source shape taken from the data file
  (`fldread.F90:1151, 1200-1201`); out-of-range reads clamped silently (`:1402-1403`) → forcing must be
  on the grid the weights were built for.
- Only `src01..04` (`:1196`) and `wgt01..04` (`:1206`) are read; `dst0k` never.
- `fldread` cache keyed by filename (`:1078-1080`); `cn_dir` prepends to the data root, weights name
  and LSM name.
- Vector pairs (`vcomp` starting `'U'`) rotated from east/north to model i/j at read
  (`fldread.F90:730-751`, grid point hardcoded `'T'`) → no offline rotation.
- Monthly files must hold the complete calendar month: record count from month length
  (`fldread.F90:869`), time coordinate never read.
- Forcing `time` UNLIMITED; forcing `depth` squeezed; initial conditions without a singleton `time`
  (`iom.F90:1280-1283`).
- `sn_*` roots must not end in `_` (NEMO adds `_y…`, `fldread.F90:1600-1601`).
- No `nn_lsm` → every source cell a stencil reaches must be finite.
- Two `sbcssm.F90` exist; the SAS version is linked. Line numbers here refer to `src/SAS/sbcssm.F90`.
- `utau`/`vtau` unused under SAS; wind speed variable `wndm` = field id `wspd` (`sbcmod.F90:636`).

### 13.3 Restarts

- `ln_rst_list` does not advance under SAS: `nrst_lst` is incremented only in `rst_write`
  (`OCE/IOM/restart.F90:209`), never reached from `SAS/step.F90` → only the first `nn_stocklist` entry
  is written. `ln_rst_list=.false.` writes at `nitend` (`restart.F90:87`).
- `cn_*rst_in` takes the bare root; `_<rank>.nc` appended (four-digit suffix = MPI rank).
- Ice restart name held in `CHARACTER(len=50)` (`icerst.F90:52,71`) = `cn_exp` + 21 characters →
  `cn_exp` ≤ 29 characters, else names are truncated.

---

## 14. Scripts

| Script | Location | Purpose |
|---|---|---|
| `audit_domain_cfg.py` | `inputs/domain_cfgs/` | Read-only audit of source domains: dimensions, periodicity, identity, cavities, spacing, latitude extents |
| `trim_domain_cfg.py` | `inputs/domain_cfgs/` | Trim to 40°S, set metadata, add the wall, verify from disk (§5.3) |
| `build_weights.py` | `inputs/domain_cfgs/` | SCRIP weights per target and source; `--verify-only <TARGET>` (target name, e.g. `GLOB16_ANT40S`) checks shape and finiteness |
| `expand_weights.py` | `inputs/domain_cfgs/` | Positional rewrite of compacted weights (§7.3); `--verify-only` is the full check |
| `make_domain_cfg.exe` (`tools/DOMAINcfg`) | `inputs/domain_cfgs/ORCA05_build/` | ORCA05 domain from eORCA05 sources (§5.2) |
| `make_glorys_sas_download.py`, `make_glorys_sas_preprocess.py` | `inputs/GLORYS12/` | GLORYS surface forcing: download, drown |
| `make_glorys_ice_ic_002.py` | `inputs/GLORYS12/` | Ice initial condition (zero-fill) |
| `make_era5_{download,deaccumulate,unlimited,symlinks}_002.py` | `inputs/ERA5/` | ERA5 pipeline |
| `setup_production.sh` | `experiments/SEAICE_DYN_003/` | Generate member run directories from `common/` (§9.2) |
| `submit_run.sh` | per member (generated) | Dry run and batch script (§10) |
| `setup_t0_equivalence.sh` | `experiments/SEAICE_DYN_003/` | Gate T0 run pair |
| `compare_t0_equivalence.py` | `VALIDATION/T0_trim_equivalence/` | Gate T0 comparison |
| `verify_logs.sh` | `VALIDATION/` | Post-run log and accounting checks |
| `verify_production.py` | `VALIDATION/` | Post-run output checks; variant runs need `--domain` |

The four domain and weights scripts are also in the repository's `scripts/`, identical to the cluster
copies.
