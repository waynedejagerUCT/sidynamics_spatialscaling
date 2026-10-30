# SEAICE_DYN_003 — NEMO 5.0 + SI3 (SAS), Antarctic-Only Trimmed Domains, Multi-Resolution

Complete recipe for reproducing SEAICE_DYN_003: a forced standalone sea-ice hindcast (SI3 with a
prescribed ocean surface) run on UCT's HPC cluster across a hierarchy of ORCA-family grids, on
domains truncated to 40°S. Covers the technical implementation — cluster environment, build, domain
preparation, forcing, interpolation weights, run configuration, verification — and the scientific
reasoning behind each choice. Self-contained: no other document is needed to rebuild the
configuration and regenerate the output.

**Scientific question.** Which sea-ice drift processes are resolved as a function of grid spacing.
Resolution is therefore the only quantity permitted to vary between members; every departure is
stated as an explicit caveat.

**Domain.** Each grid is truncated in j (south–north), retaining only rows south of 40°S. Full i
extent is kept, so east–west periodicity survives. The only structural departure from an ordinary
global standalone sea-ice configuration; physics, forcing, period and initial state are those of a
standard global run.

**Why the truncation is admissible.** Under SAS (Standalone Surface module) there is no prognostic
ocean — no wave propagation, no barotropic adjustment, no tracer advection into the domain.
Information reaches the interior only through ice advection and rheology, both local plus halo
exchange. Forcing at any retained point is a function of that point's coordinates and the unchanged
global source grids, so it is identical to what a global run delivers there. The northern wall is
confined to its own halo, ≥ 2 500 km from any sea ice. Verified empirically — see
[Gate T0](#gate-t0--trim-equivalence).

**Members.** ORCA2, ORCA1, ORCA05, ORCA025 form a clean ×2 ladder (2° → 1° → 0.5° → 0.25°).
GLOB16 (1/16°) is a stated-caveat extension member from a different grid family.

**Status (30 October 2026).**

| Member | Trimmed | Weights | v1 production | v1 verified | v2 production | v2 verified |
|---|---|---|---|---|---|---|
| ORCA2 | yes | yes | complete | passed | **complete** (job 1502542) | passed (both scripts); downloaded, MD5-verified; on external HDD |
| ORCA1 | yes | yes | complete | passed | **complete** (job 1502660) | passed (both scripts); downloaded, MD5-verified; on external HDD |
| ORCA05 | yes | **lost 30 Oct** (rebuild before any rerun) | complete | passed | **complete** (job 1503915; 1502968 OOM-killed) | passed (both scripts); downloaded, MD5-verified; on external HDD |
| ORCA025 | yes | yes | complete | passed | **complete** (job 1541973) | passed (both scripts); transfer running |
| GLOB16 | **lost 30 Oct** (rebuild) | **lost 30 Oct** (rebuild) | not run | — | not run | — |

**v1** (Sep 2026): four members ran the full 228-day period at `rn_Dt = 900 s` under
`srun --multi-prog`, 8 `_icemod` fields, `nn_nevp = 100`; output transferred to local storage and
verified byte-for-byte. v1 ORCA2–ORCA05 output has since moved to an external HDD (28 Oct); v1
ORCA025 stays local as the `nn_nevp = 100` member of the ORCA025 solver-sensitivity test.

**v2 regeneration** (from Oct 2026) reruns the same four members to add what the analysis needs and v1
lacks. Changes from v1:

- **21 more `_icemod` fields (29 total)** — area tendencies and ridging/rafting (Eq. 1 partition),
  momentum-balance terms, snow mass, native deformation, rheology state and `beta_evp`
  (§XIOS output).
- **`nn_nevp = 500`** (was 100) — aEVP convergence decision (§`namelist_ice_cfg`). The only change
  affecting the solution, so v2 is not bit-identical with v1.
- **`MY_SRC/icedyn_rdgrft.F90`** — fixes ridging diagnostics that SI3 never wrote (§Build).
  Diagnostics only.
- **`srun --mem=0`** — fixes the job-step memory cap that OOM-killed v2 ORCA05 (§Cluster environment).

For ORCA025 this was confirmed at namelist level (29 Oct): with comments and whitespace removed, the
v1 and v2 `namelist_cfg` files are identical and `namelist_ice_cfg` differs only in `nn_nevp`
(100 → 500), and both ran on the same 38 × (107 × 122) decomposition. A third ORCA025 run at
`nn_nevp = 2000`, otherwise identical to v2, is planned as a solver-sensitivity control
(100 / 500 / 2000; §Run statistics).

Validated by a 72-step ORCA2 run before production. v2 output is ~2.8× v1. ORCA2–ORCA05 were
downloaded, MD5-verified and cleared from scratch on 29 Oct (§Data transfer and archive), then
moved to an external HDD (re-verified, 30 Oct). ORCA025 completed and passed both verifications on
30 Oct; its transfer is running. The GLOB16 trimmed domain and weights, and the ORCA05 weights, were
lost on 30 Oct and must be rebuilt before use (§Directory layout). GLOB16 requires several departures from the common
recipe — see [GLOB16](#glob16-special-conditions).

---

## Contents

**Part I — Design**  [Pipeline](#pipeline) · [The controlled comparison](#the-controlled-comparison)
**Part II — Environment**  [Cluster](#cluster-environment) · [Build](#build)
**Part III — Inputs**  [Domain files and the trim](#domain-files-and-the-trim) · [Forcing](#forcing-unchanged-and-global) · [Interpolation weights](#interpolation-weights)
**Part IV — Run configuration**  [Timestep and CFL](#timestep-and-cfl) · [Run directories, namelists, XIOS](#run-directories-namelists-and-xios) · [Running production](#running-production)
**Part V — Results**  [Verification](#verification-protocol) · [Results as produced](#results-as-produced) · [Transfer and archive](#data-transfer-and-archive)
**Part VI — Reference**  [Source-verified facts](#source-verified-facts) · [Analysis inputs](#analysis-inputs) · [GLOB16](#glob16-special-conditions) · [Scripts](#scripts) · [Caveats](#scientific-caveats)

---

# Part I — Design

## Pipeline

Runs once per member; offline forcing steps are shared across all members.

```
        SHARED, BUILT ONCE                          PER MEMBER
   ┌──────────────────────────┐          ┌────────────────────────────────┐
   │ ERA5 download            │          │ source domain_cfg.nc            │
   │   → deaccumulate         │          │        ↓ audit_domain_cfg.py    │
   │   → time UNLIMITED       │          │        ↓ trim_domain_cfg.py     │
   │                          │          │ trimmed domain_cfg.nc (40°S)    │
   │ GLORYS surface forcing   │          │        ↓ build_weights.py        │
   │   → drown (30 passes)    │──────────┤ 3 weights files (SCRIP)         │
   │                          │          │        ↓ expand_weights.py       │
   │ GLORYS ice IC            │          │   (only where SCRIP skipped      │
   │   → zero-fill            │          │    destinations — §Weights)      │
   └──────────────────────────┘          │        ↓ setup_production.sh     │
                                         │ run directory + submit_run.sh    │
   ┌──────────────────────────┐          │        ↓ sbatch                  │
   │ NEMO 5.0 + SI3 + XIOS3   │──────────┤ 228-day production run           │
   │ one nemo.exe, all members│          │        ↓ verify_logs.sh          │
   └──────────────────────────┘          │        ↓ verify_production.py    │
                                         │ 31 output files, verified        │
                                         └────────────────────────────────┘
```

**Produced (v1):** four members × 31 netCDF files = 124 files, 60 GB, each member carrying 3 883
records across four streams over 2019-03-18 → 2019-11-01. **v2:** same file set, ~2.8× the volume;
all four ORCA members complete and verified (ORCA2–ORCA05 on an external HDD; ORCA025 transfer
running). **Remaining:** GLOB16.

## The controlled comparison

### Held identical across all members

| Item | Value |
|---|---|
| Trim latitude | **−40.0°**, same derived criterion at every member |
| Forcing data | Same ERA5 and GLORYS files, native global grids |
| Ice initial condition | Same GLORYS file, interpolated to each target at runtime |
| Run period | 2019-03-18 → 2019-11-01 (`nn_date0=20190318`, `nn_itend=21888`) |
| Ice timestep | `rDt_ice = 900 s` (`rn_Dt=900`, `nn_fsbc=1`) — ORCA2…ORCA025 |
| EOS, rheology, advection, ITD | `ln_eos80`, `ln_aEVP`, `rn_ecc`, `nn_nevp` (v1: 100, v2: 500), `ln_adv_Pra`, `jpl`, `nlay_i`, `nlay_s` |
| Lateral BC | `rn_ishlat = 2.` |
| Output frequency | 3-hourly ice, daily prescribed ocean, monthly scalars |
| NEMO build | Same `nemo.exe` — cpp keys and component set are grid-independent (v2: rebuilt with the `MY_SRC` ridging-diagnostics fix) |
| Northern wall | 2 rows, applied identically |
| Launcher | `srun --mpi=pmix --mem=0 --cpu-bind=none --multi-prog` (`--mem=0` from v2) |

### Necessarily varies with resolution

`domain_cfg.nc`; interpolation weights; MPI decomposition and rank count; wall clock; output volume.

### Varies, and is therefore a stated caveat

- **`rn_Dt` at GLOB16 only.** 900 s is CFL-inadmissible at its grid spacing (§Timestep).
  Resource-driven, carried as an explicit caveat on any GLOB16 result.
- **ERA5 held at 0.25° for every member**, so the finest members are forced by atmosphere coarser
  than their own grid. Deliberate: holding forcing resolution fixed means any change in resolved
  drift comes from the ice model's grid, not from better-resolved wind.

### Consequences of the trim

- **Domain integrals are hemispheric, not global.** `ibgvol_tot`/`ibgarea_tot` sum over the retained
  domain — Southern-Hemisphere quantities, not comparable with any global-domain figure.
- **Domains are not geometrically identical.** Each cut lands on its own nearest qualifying row;
  northernmost wet latitudes span −40.13° (GLOB16) to −43.21° (ORCA2). Irrelevant at ≥ 2 500 km from
  the ice, but a real difference in extent.
- **The wall's *effect* is resolution-dependent** — 2 rows is ~226 km at ORCA2, ~6 km at GLOB16. No
  ice approaches within 2 500 km, so it does not enter the diagnostics.

---

# Part II — Environment

## Cluster environment

**Access.** `ssh djgway001@hex.uct.ac.za` → head node `srvrochpc001`.

**SLURM.** `--account=oceanography --partition=ada`, QOS `normal`. Per-job limits `cpu=120,
node=6`; account limit `GrpTRES cpu=200`. `sinfo -o "%P %l %L"` reports `ada` as `infinite` and
`sacctmgr show qos` shows no `MaxWall` — **no walltime limit**. Scratch quota is the only reason to
segment a run.

**Nodes.** 100-series (`--constraint=large`): 48 cores, 375 GB usable, 7.8125 GB/core.

> **RAM-sizing trap.** `--ntasks=N` on a 48-core node allocates only `N × 7.8125` GB. Request the
> **full node** (`--constraint=large`, `--cpus-per-task=1`, omit `--mem`) even when launching fewer
> ranks. `setup_production.sh` does this; confirm `ReqMem = 375G` in `sacct`.

> **Step-level RAM trap (found 2026-10-18, v2 ORCA05).** The full-node *job* allocation does not reach
> the *job step*: without `--mem`, the `srun` step is given only the per-task default
> (`ntasks × 8000 MB`, e.g. `mem=144000M` for ORCA05's 18 tasks) and is OOM-killed above it, although
> the job holds 375 GB. **`srun` must carry `--mem=0`** so the step receives the whole job's memory.
> Confirm with `sacct -j <job>.0 --format=AllocTRES`. In practice the step receives **`mem=300G`**
> even with `--mem=0` (job holds 375 GB): **300 GB is the effective step ceiling**.

**Storage.** `/home` 10 GB, backed up. `/scratch/djgway001` 250 GB, **not backed up**.

**Per session:** `source /scratch/djgway001/NEMO/env_nemo.sh`

**Conda environments.** `nemo_analysis` (xarray, netCDF4 1.7.4, numpy 2.4.3, scipy, pandas,
matplotlib, cartopy, Parcels) · `cmems_download` · `era5_download`. NCO is not installed and is not
needed — all domain manipulation is pure Python via netCDF4.

**Versions.** NEMO 5.0 · XIOS3 trunk r2793 · netCDF-C 4.9.2 (parallel) + netCDF-F 4.6.1 ·
GCC 11.5.0 · OpenMPI 5.0.3 · HDF5 1.14.6 (MPI).

> `nemo_analysis` carries `libnetcdf 4.10.0` while NEMO is built against 4.9.2. The trim script
> writes in the source file's own format rather than defaulting to `NETCDF4`, removing any
> version-compatibility question.

### Operating conventions

1. **Verify against NEMO source, not documentation.** Grep `nemo_5.0/src/` for the actual `NAMELIST`
   statement before wiring any flag — several documented features are absent from this build.
2. Robustness and accuracy over speed, memory, convenience.
3. Every offline step gets a saved script and an on-disk check of its output.
4. Never assume output paths.
5. Head node: light operations only. All compute via `sbatch` or `sintx`.
6. **One conda environment per workflow.** Build and run: **no conda**, `env_nemo.sh` only — SCRIP
   and NEMO link against the module-provided `libnetcdff.so.7`, which conda shadows. Analysis,
   trimming, weights verification: `nemo_analysis`.
7. **New run directory:** symlink `nemo.exe` (the real `BLD/bin/` target, never the `EXP00` link),
   `xios_server.exe`, both reference namelists, `domain_cfg.nc`, ICs, weights; copy namelists and
   XMLs; `mkdir restart_files logs`. Then
   `find . -maxdepth 1 -type l ! -exec test -e {} \; -print` must return empty.
8. Symlinks, not copies, for shared inputs and executables. Always link the real target.
9. Paste `sbatch` on its own line; enable bracketed paste locally.
10. **Shell variables do not survive a new session or `sintx`.** Re-`export` paths — an unset
    variable silently expands to a wrong absolute path.

## Build

One executable serves every member: cpp keys and component set do not depend on the grid, and the
trim changes nothing about the build.

```bash
sintx
conda deactivate 2>/dev/null || true
source /scratch/djgway001/NEMO/env_nemo.sh
cd /scratch/djgway001/NEMO/nemo_5.0

./makenemo -n SEAICE_DYN_003 -m UCT_GCC -r ORCA2_SAS_ICE --add_key "key_xios3" -j 0
sed -i '/oasis_codes_id/d' cfgs/SEAICE_DYN_003/EXP00/iodef.xml
./makenemo -n SEAICE_DYN_003 -m UCT_GCC -r ORCA2_SAS_ICE -j 8
```

- **Components:** `OCE ICE NST SAS` (`cfgs/ref_cfgs.txt:8`). Do not force with `-d`.
- **cpp keys:** `key_si3 key_linssh key_vco_1d3d key_xios key_RK3 key_xios3`.
- `key_linssh` — `domzgr.F90:89` enforces XOR with `key_qco`. Correct here: no prognostic ocean, and
  the `sn_e3t` forcing slot is never read.
- `key_RK3` — shipped by the SAS reference; `rn_atfp` is unused but read unconditionally
  (`domain.F90:241`), so leave it set.
- The `oasis_codes_id` removal is required — XIOS3 aborts on that element.
- **`MY_SRC/icedyn_rdgrft.F90` (v2, 2026-10-18) — ridging diagnostics fix.** In the shipped source,
  `ice_dyn_rdgrft_init` sets `ll_diag_rdg` from `iom_use('lead_open' | 'rdg_*' | 'rft_*')`. That
  init runs before the XIOS context definition is closed, so `iom_use` returns `.FALSE.`, the flag
  stays `.FALSE.` for the whole run and the five fields are never sent (written as all-fill, 0 valid
  values). The copy sets `ll_diag_rdg = .TRUE.` unconditionally (it also gates allocation of the
  diagnostic arrays in `ice_dyn_rdgrft_alloc`, so re-evaluating per step is unsafe). Diagnostics only:
  no physics change. Rebuild with the second `makenemo` line above; **no conda environment may be
  active** (a stray `nemo_analysis` caused a link failure). Confirmed by the ORCA2 72-step v2
  validation: all five fields written; `lead_open` is legitimately zero there (filled from `opning`
  at ridging points, `icedyn_rdgrft.F90:1141`).

Tools, built once:

```bash
./maketools -m UCT_GCC -n WEIGHTS     # tools/WEIGHTS/BLD/bin/{scripgrid,scrip,scripshape}.exe
./maketools -m UCT_GCC -n DOMAINcfg   # needed only to build ORCA05
```

---

# Part III — Inputs

## Domain files and the trim

### Source files (as received, immutable)

`inputs/domain_cfgs/` — never modified. Since 29 Oct 2026 the `.nc` files are no longer on the
cluster; all five survive on an external HDD (the local `hpc_offload/` copy was lost on 30 Oct;
§Directory layout). Upload them before any re-trim. Audited by `audit_domain_cfg.py`; report at
`AUDIT_domain_cfgs_40S.txt` / `.json`.

| File | Grid | Provenance | Periodicity | Config identity | Cavities |
|---|---|---|---|---|---|
| `domain_cfg_ORCA2L31.nc` | 180×148×31 | NEMO 5.0 distribution (`ORCA_R2_zps_domcfg.nc`) | modern attrs | `ORCA`/2 | none |
| `domain_cfg_ORCA1L50.nc` | 360×291×50 | CMCC | legacy `jperio`=6 | `ORCA`/`ORCA_index` → `ORCA`/1 | none |
| `domain_cfg_ORCA05L75.nc` | 722×604×75 | **built in-house** from eORCA05 sources (IGE/CNRS) | legacy `jperio`=4 | none → `UNKNOWN`/−999 | none |
| `domain_cfg_ORCA025L75.nc` | 1440×1050×75 | CMCC | legacy `jperio`=4 | none → `UNKNOWN`/−999 | none |
| `domain_cfg_GLOB16L98.nc` | 5760×3962×98 | CMCC | legacy `jperio`=6 | `cn_cfg`/`nn_cfg` → `GLOB16`/6 | none |

- **Three storage conventions across five files.** Only ORCA2 carries modern periodicity attributes;
  the rest resolve through the legacy `jperio` fallback — hence the trim must write real
  `NFold`/`NFtype` rather than rely on any one convention (§Source-verified facts).
- **All five are cavity-free**, verified by counting `top_level > 1` rather than trusting the
  declared flag. Closes the sharpest version of the mask-comparability risk.
- **ORCA2 carries `strait_shlat`** (Gibraltar, Bab el Mandeb, Danish Straits — all NH, inert after
  trimming). Sliced for structural consistency only.
- **ORCA025 and ORCA1 are classic, not eORCA.** ORCA025's southernmost wet latitude is −78.6018°;
  its 1440×1050 shape comes from a CMCC `ncks` trim of overlap columns (`-d x,2,1441 -d y,1,1050`),
  recorded in `history`. ORCA1's `isf_draft`, `bathy_metry` and `mask_cs*` are `DOMAINcfg`
  boilerplate, not an eORCA signature.

### ORCA05 — built in-house from eORCA05 sources

No classic ORCA05 `domain_cfg.nc` was available.

**Source inputs** — `DOMAIN_cfg_build.tar` (IGE/CNRS, `eORCA05.L75` path in the original job
script). Zenodo: https://doi.org/10.5281/zenodo.14361713

- `eORCA05_coordinates.nc` (59 MB) — horizontal grid geometry
- `eORCA05_bathymetry_b0.2_closed_seas.nc` (8.7 MB) — carries `Bathymetry`, `Bathymetry_isf`,
  `isf_draft`, i.e. cavity geometry is present in the source

**Build.** `make_domain_cfg.exe` (single rank), using **this tree's own**
`namelist_ref`/`namelist_cfg` as the base — the supplied namelists are from a different tool version
and do not define the `cn_domcfg`/`cn_topo`/`cn_bath`/`cn_lon`/`cn_lat` variables this build's
`&namdom` (`domain.F90:164`) requires. Only `jpidta`/`jpjdta`/`Ni0glo`/`Nj0glo` (722/604) were
overridden; the vertical coefficients (`ppsur`, `ppa0`, `ppa1`, `ppa2`, `ppkth`, `ppkth2`, `ppacr`,
`ppacr2`, `ldbletanh`) matched the supplied namelist exactly, confirming the same L75 lineage.

- **`ln_isfcav = .false.`** — despite cavity geometry in the source, the produced file shows
  `top_level ∈ {0,1}` everywhere; zero cavity cells, confirmed empirically.
- **`ln_domclo = .true.`**, `nn_closea = 8`, geographic (lon/lat-keyed, not index-keyed) closed-sea
  definitions from this tree's reference `&namclo` — resolution-independent, so no mismatch risk
  against 722×604. NH lakes closed this way are removed by the 40°S trim anyway.
- **Output:** `domain_cfg.nc` (1.9 GB, `NETCDF3_64BIT_OFFSET`) plus `mesh_mask.nc` (hardcoded
  filename, `domwri.F90:69`). `ocean.output` terminated cleanly (`AAAAAAAA`) — confirmed before
  trusting the output.

**ORCA05 retains the eORCA southward extension**, `gphit` reaching **−85.79°** against classic
ORCA025's −78.6°. Two material consequences:

1. The 40°S cut retains a larger fraction of rows (42.2% vs 29.7–33.7%), so the saving from trimming
   is smaller.
2. **Southern rows extend beyond GLORYS's southern limit of −80.0°**, so SCRIP skips those
   destinations — requiring a post-processing step no other member needs (§Weights). Note
   `gphit[j].max()` for those rows reads about −78°; rows span a wide latitude range each, and it is
   `gphit.min()` that reaches −85.79°.

### Trim mechanism

Cut in j only, retaining all i so east–west periodicity survives. **Not** AGRIF nesting, **not** BDY
open boundaries — neither is needed and both add configuration surface.

Row index is **derived, never hardcoded**:

> `j_north = max{ j : max_i( gphit[j,:] ) ≤ −40.0 }`, taking the contiguous block from the southern
> edge.

Latitude is the fixed quantity, so the same invocation is correct at every resolution. Taking the
maximum over i rather than a mean guarantees no retained point lies north of the target.

**Zonal uniformity is verified, not assumed** — all five members returned a spread of exactly
0.000000° across the cut row, confirming a constant-j cut is a constant-latitude cut on these grids.

### What `trim_domain_cfg.py` does

1. **Slices every variable carrying the y dimension** (28–42 per file); the rest untouched.
2. **Writes `Iperio=1`, `Jperio=0`, `NFold=0`, `NFtype='-'` as global attributes.** Load-bearing:
   writing real `NFold`/`NFtype` is what disables the legacy fallback branch.
3. **Sets legacy `jperio` to 1** where present. Nothing reads it after step 2, but a generated file
   must not carry a contradictory value.
4. **Applies a 2-row northern land wall** — `top_level`, `bottom_level`, `mbku`, `mbkv`, `mbkf`
   zeroed. Previously-wet cells closed are recorded per member in `TRIM_LOG.txt`.
5. **Corrects `jpiglo`/`jpjglo`/`jpkglo` and `DOMAIN_size_*`.** NEMO ignores these, but several
   source files carried stale values.
6. **Writes `CfgName`/`CfgIndex`**, supplied explicitly where the source resolves to `UNKNOWN`;
   updates `ORCA_index` where present so both resolution routes agree.
7. **Records provenance** — `TrimScript`, `TrimDate`, `TrimSourceFile`, `TrimTargetLat`,
   `TrimCutRowLat`, `TrimRowsRetained`, `TrimRowsOriginal`, `TrimWallRows`, plus a history entry.

**Verification, every file, from disk.** The script re-opens the written file, re-resolves
dimensions, periodicity and identity **through the same logic NEMO uses**, then checks: no `gphit`
north of the target; zero wet cells in the wall rows; bitwise comparison of `gphit`, `glamt`, `e1t`,
`e2t`, `ff_t` against the source over retained rows. Non-zero exit on failure. All five:
**VERIFICATION PASSED**, 0 mismatches.

```bash
conda activate nemo_analysis
cd /scratch/djgway001/NEMO/inputs/domain_cfgs

python3 -u audit_domain_cfg.py domain_cfg_*.nc --target-lat -40.0 \
        --output AUDIT_domain_cfgs_40S.txt --json AUDIT_domain_cfgs_40S.json

python3 -u trim_domain_cfg.py domain_cfg_ORCA2L31.nc   ../ORCA2_ANT40S/domain_cfg.nc \
        --target-lat -40.0 --log ../ORCA2_ANT40S/TRIM_LOG.txt
python3 -u trim_domain_cfg.py domain_cfg_ORCA1L50.nc   ../ORCA1_ANT40S/domain_cfg.nc \
        --target-lat -40.0 --log ../ORCA1_ANT40S/TRIM_LOG.txt
python3 -u trim_domain_cfg.py domain_cfg_ORCA05L75.nc  ../ORCA05_ANT40S/domain_cfg.nc \
        --target-lat -40.0 --cfg-name ORCA --cfg-index 5 --log ../ORCA05_ANT40S/TRIM_LOG.txt
python3 -u trim_domain_cfg.py domain_cfg_ORCA025L75.nc ../ORCA025_ANT40S/domain_cfg.nc \
        --target-lat -40.0 --cfg-name ORCA --cfg-index 4 --log ../ORCA025_ANT40S/TRIM_LOG.txt
python3 -u trim_domain_cfg.py domain_cfg_GLOB16L98.nc  ../GLOB16_ANT40S/domain_cfg.nc \
        --target-lat -40.0 --log ../GLOB16_ANT40S/TRIM_LOG.txt      # ~10 min, use sintx
```

`--cfg-name`/`--cfg-index` are explicit for ORCA05 and ORCA025 because both resolve to
`UNKNOWN`/−999. The script refuses to overwrite an existing output.

> **Chunk inheritance.** Copying the source file's chunk layout forces read-modify-write on every
> slab (ORCA025: ~10 min). Letting the library choose its own chunking, plus copying variables whole
> below a 2 GB threshold, brings it to 25 s. GLOB16's 3-D variables stay above the threshold and
> keep the slab path — necessary, and ~10 min.

### Trimmed products

`inputs/<GRID>_ANT40S/domain_cfg.nc`, each with `TRIM_LOG.txt`.

| Member | Trimmed grid | Rows kept | Cut latitude | Northernmost wet | Surface-wet cells | Size |
|---|---|---|---|---|---|---|
| ORCA2 | 180×44×31 | 44 / 148 (29.7%) | −40.220644 | −43.205710 | 5 226 | 1.1 MB |
| ORCA1 | 360×88×50 | 88 / 291 (30.2%) | −40.220644 | −41.730512 | 21 486 | 3.1 MB |
| ORCA05 | 722×255×75 | 255 / 604 (42.2%) | −40.220644 | −40.979898 | 88 025 | ~340 MB |
| ORCA025 | 1440×354×75 | 354 / 1050 (33.7%) | −40.029484 | −40.411265 | 351 220 | 58 MB |
| GLOB16 | 5760×1179×98 | 1179 / 3962 (29.8%) | −40.029484 | −40.125131 | 5 250 546 | 779 MB |

**Cut latitudes pair three ways.** ORCA2, ORCA1 and ORCA05 land on exactly −40.220644°; ORCA025 and
GLOB16 on −40.029484°. Within the first group the finer grids' rows are an exact refinement of the
coarser, so qualifying rows coincide. The 0.19° offset between groups arises because nominal ratios
describe approximate resolution, not exact nesting — ORCA025 is an independent Mercator
construction, not a subdivision of ORCA1/ORCA05.

**Grid spacing within the retained domain** (from the audit):

| Member | e1t median @65°S | e1t min | e2t min |
|---|---|---|---|
| ORCA2 | 94.456 km | 47.096 km | 47.096 km |
| ORCA1 | 47.228 km | 23.573 km | 21.394 km |
| ORCA05 | 23.414 km | 11.497 km | 10.476 km |
| ORCA025 | 11.760 km | 5.800 km | 5.299 km |
| GLOB16 | 2.942 km | 1.399 km | 3.000 km |

## Forcing: unchanged and global

Three products, built once, shared by every member. Grid-independent by construction: they produce
files on the **source** grids, formatted for NEMO's runtime interpolation. A domain trim removes
target points; it cannot interact with an operation that has no spatial extent on the source.

| Product | Location | Content |
|---|---|---|
| GLORYS12 surface forcing | `inputs/GLORYS12/forcing_002/processed/` | 45 files, 20 GB, `thetao` `so` `uo` `vo` `zos` |
| ERA5 atmosphere | `inputs/ERA5/{raw,processed}/` | 9 variables × 9 months |
| Ice initial condition | `inputs/GLORYS12/glorys12_seaiceIC_20190318.nc` | `ati`, `hti`, `hts` |

*(`forcing_002` is a historical directory name, not a reference to another experiment.)*

**GLORYS identity:** `cmems_mod_glo_phy_my_0.083deg_P1D-m` — `_my_` = multi-year reanalysis. File
attributes are contradictory (`title` claims operational forecast); the catalogue and
`field_date = 2021-06-30` confirm the reanalysis.

| Source | Longitude | Latitude | Shape |
|---|---|---|---|
| ERA5 | 0 … 359.75 (0.25°) | +90 … −90 descending (0.25°) | 1440 × 721 |
| GLORYS12 | −180 … 179.9167 (1/12°) | **−80.0** … +90 ascending (1/12°) | 4320 × 2041 |

> **GLORYS stops at −80.0°S.** Any target extending further south has destination points with no
> source coverage. Of the five members only eORCA05-derived ORCA05 does (§Weights).

**Why the sources must stay global.** `fldread.F90:1200-1201` derives the source decomposition from
the **data file's own dimensions** at read time, and the weights hold **absolute source indices**. A
truncated source leaves `data_jpj` past the array bound, clamped at `fldread.F90:1402-1403` so it
truncates silently rather than aborting. Positively: the bilinear stencil for the northernmost
retained row samples source cells at and just north of 40°S, which exist because the source was never
cut. **No edge effect at the trim boundary.**

### NaN handling: drown the surface forcing, zero-fill the ice IC

Opposite treatments, because NaN means different things in each. Getting this wrong is silent — the
model runs, output looks plausible, and the error shows only as ice where none should exist.

| Product | NaN means | Treatment |
|---|---|---|
| `thetao`, `so`, `uo`, `vo`, `zos` | **Land only** — quantity genuinely undefined | **Drown**, 8-neighbour iterative fill, 30-pass bound |
| `ati`, `hti` | **No ice** (open ocean) *or* land | **Zero-fill**: `np.where(np.isnan(arr), 0.0, arr)` |

**Why drown the surface forcing.** With no `nn_lsm` on this path NEMO applies the weights blind — it
does not know where land is. A bilinear stencil for a coastal ocean point can reach a land cell, and
a NaN there propagates into the interpolated value. Drowning fills land with plausible neighbouring
ocean values so the arithmetic stays finite; NEMO masks land at runtime, so those values are never
used — they only have to *exist*. The 30-pass bound comes from source resolution (~9 km at 1/12°)
against ~250 km of required margin; the target grid never enters that argument.

**Why not drown the ice IC.** GLORYS ice fields carry `cell_methods = "area: mean where sea_ice"` —
averaged over the ice-covered fraction only, so where there is no ice the quantity is undefined and
the file stores NaN rather than zero. Verified against the raw source: **100% NaN in every latitude
band north of −60°**. Neighbour-averaging would propagate **pack concentrations** outward across the
global ocean, giving spurious thin ice at every latitude. Zero-fill is correct: physically right over
open ocean, harmless over land (masked at runtime), and every cell finite as the blind-weights rule
requires.

**Ice IC verification**, all must hold:

| Check | Expected |
|---|---|
| NaN count | 0 in `ati`, `hti`, `hts` |
| `ati` range | [0, 1] — clip after fill; GLORYS packing gives values marginally above 1 |
| `hti` range | ≥ 0; max 4.6312 m for 2019-03-18 |
| `ati`/`hti`, lat −60 to −40 | **exactly 0.000000**, mean and max |
| `ati`/`hti`, lat −40 to +40 | **exactly 0.000000**, mean and max |
| `ati`/`hti` cells > 0, per band | matches raw source valid-cell count to within ~2% |
| dimensions | `(latitude, longitude)` only — **no time dimension** |

The **−60 to −40 band** proves the fill is correct: that is where the ice edge sits and where a
smeared field would show first. Arctic ice at 40–90°N is genuine and is discarded at interpolation.

**ERA5 deaccumulation.** Pointwise scalar operation — `ssrd`/`strd` ÷ 3600, `tp`/`sf` × 1000/3600,
clamp ≥ 0. No spatial stencil, no differencing between records, no latitude dependence; same global
grid, cell for cell. `ln_prec_met = .false.` is paired with this offline conversion — `.true.` would
double-convert.

> **General rule.** A domain trim can only interact with an offline step applying a **spatial stencil
> on the source grid**, and then only if the source itself were trimmed. The GLORYS drown has such a
> stencil (hence the 30-pass argument); the ice-IC zero-fill and ERA5 deaccumulation have none.

## Interpolation weights

Three files per member, fifteen total. Built by `build_weights.py`, driving `scripgrid → scrip →
scripshape` once per source and copying the GLORYS result to a second filename.

| File | Source | Consumer block |
|---|---|---|
| `weights_bilin_era5_<grid>_ant40s.nc` | ERA5 0.25° global | `&namsbc_blk`, all nine fields |
| `weights_bilin_glorys_<grid>_ant40s_sas.nc` | GLORYS 1/12° global | `&namsbc_sas`, all five fields |
| `weights_bilin_glorys_<grid>_ant40s_ice.nc` | GLORYS 1/12° global | `&namini`, ice IC |

```bash
conda deactivate                                  # SCRIP needs module netCDF, not conda's
source /scratch/djgway001/NEMO/env_nemo.sh
cd /scratch/djgway001/NEMO/inputs/domain_cfgs
python3 -u build_weights.py --target ORCA05_ANT40S        # or --all
```

Writes into `inputs/<GRID>_ANT40S/weights/`, intermediates in `.work/`. Verification needs netCDF4 —
switch to `nemo_analysis` afterwards.

### Configuration constraints, all binding

- **Bilinear, not bicubic**, at every resolution. Bicubic smoothing and overshoot would corrupt the
  turning-angle diagnostic, and differently by resolution — manufacturing a spurious resolution
  signal.
- **T-point weights** everywhere — `fld_rot` hardcodes `'T'` (`fldread.F90:750-751`) regardless of
  which weights were built.
- **`ew_wrap = 0`** in `&shape_inputs`, matching `tools/WEIGHTS/namelist_bilin`. Consistent with the
  halo-free `domain_cfg` convention (`Ni0glo`/`Nj0glo` are inner dimensions; NEMO adds the halo at
  runtime). A wrong value produces a plausible file and shows as a meridional stripe near the date
  line in the first output, not a crash.
- **`method = 'regular'`** for both sources. SCRIP handles 0–360 and −180/180 longitude and either
  latitude ordering natively; no pre-rotation.
- **`scripgrid` requires the target present in its working directory as literally `coordinates.nc`**
  (stated in the reference namelist's comments); the `nemo_file` field alone is insufficient.
  `build_weights.py` symlinks the member's trimmed `domain_cfg.nc` to that name on every run.
- **The two GLORYS files are identical in content but need distinct filenames** — the fldread cache
  is keyed by filename (`fldread.F90:1078-1080`).
- **`cn_dir` prepends to the weights filename as well as the data root**, so each weights file must
  be reachable from its block's data directory, **not** the run directory. A weights file in the run
  directory but absent from the data directory gives `fld_weight : unable to read the file` and an
  immediate abort.

  | Block | `cn_dir` | Weights must be at |
  |---|---|---|
  | `&namsbc_blk` | `inputs/ERA5/` | `inputs/ERA5/` |
  | `&namsbc_sas` | `inputs/GLORYS12/forcing_002/processed/` | same |
  | `&namini` | `./` | the run directory |

- **The `_ant40s` token is load-bearing.** Weights are bound to the target grid; a weights file
  paired with a differently-trimmed domain fails *silently* — structured artefacts, not a crash.

### Unmapped destinations: required post-processing for ORCA05

SCRIP produces a link only for destinations it can enclose with a source stencil. Where the target
extends beyond the source's coverage those destinations are skipped, and **`scripshape` writes the
surviving links in link order rather than at destination position**. This matters because **NEMO
reads `src0k`/`wgt0k` positionally and never reads `dst0k`** (`fldread.F90:1196` and `:1206` are the
only reads) — entry (j,i) is applied to destination cell (j,i), so a compacted file misaligns forcing
across the *entire* domain, silently.

**Only ORCA05 is affected**, because eORCA05 reaches −85.79° while GLORYS12 stops at −80.0°. 19 122
of its 184 110 destinations were skipped (all land cells, rows j = 0…45), leaving 164 988 links
written compactly.

`expand_weights.py` repairs this — three requirements, each load-bearing:

1. **Scatter by `dst`**, so entry (j,i) again describes destination (j,i).
2. **Filled slots get `wgt = 0`** — the value read there is multiplied by zero and never used.
3. **Filled slots get a *valid and nearby* source index**, from the nearest mapped neighbour in array
   order. Valid because an out-of-range index corrupts the read; *nearby* because
   `fldread.F90:1215-1222` sizes each MPI rank's source read box from `MINVAL`/`MAXVAL` of its
   indices and allocates it — a distant filler inflates every affected rank's box.

```bash
conda activate nemo_analysis
cd /scratch/djgway001/NEMO/inputs/domain_cfgs
W=/scratch/djgway001/NEMO/inputs/ORCA05_ANT40S/weights
D=/scratch/djgway001/NEMO/inputs/ORCA05_ANT40S/domain_cfg.nc

python3 -u expand_weights.py $W/weights_bilin_glorys_orca05_ant40s_sas.nc.compacted \
                             $W/weights_bilin_glorys_orca05_ant40s_sas.nc --domain-cfg $D
cp $W/weights_bilin_glorys_orca05_ant40s_sas.nc $W/weights_bilin_glorys_orca05_ant40s_ice.nc

python3 -u expand_weights.py --verify-only $W/weights_bilin_glorys_orca05_ant40s_sas.nc --domain-cfg $D
python3 -u expand_weights.py --verify-only $W/weights_bilin_glorys_orca05_ant40s_ice.nc --domain-cfg $D
```

The compacted SCRIP originals are kept on disk renamed `*.nc.compacted_BROKEN`; only the expanded
files are used.

### Weights verification — what must be checked

The obvious checks are insufficient: a compacted file has four `src` and four `wgt` arrays, all
finite, correct dimensions, and a "no zero weights" test also passes because the affected cells are
land and zero is finite. **Three checks are required:**

| Check | Why |
|---|---|
| `dst0k[n] == n+1` for every slot, every k | Detects compaction — the decisive test |
| Every **wet** cell (trimmed `domain_cfg.nc`, `top_level > 0`) has non-zero total weight | Detects genuinely unforced ocean |
| Per-rank source-row span equals the span over mapped destinations only | Detects read-box inflation from far fillers |

All fifteen files as used for production: positional, every wet cell weighted, zero read-box
inflation. ORCA05's GLORYS pair carries 19 122 zero-weight land cells by construction; no other file
carries any.

---

# Part IV — Run configuration

## Timestep and CFL

`rDt_ice = nn_fsbc × rn_Dt` (`icestp.F90:374`). With `nn_fsbc = 1`, `rDt_ice = rn_Dt`.

### Decision: `rn_Dt = 900 s` for ORCA2, ORCA1, ORCA05, ORCA025

Uniform across the four, so **the timestep is not a covariate between them** and resolution remains
the only difference. Achievable because there is no walltime limit.

| | `rDt_ice = 900 s` |
|---|---|
| Steps per inertial period (~13 h at 65°S) | 52 |
| EVP relaxation (aEVP) | per-cell β, α from `rDt_ice` (`zdtevp = rDt_ice`, `icedyn_rhg_evp.F90:244`); no elastic timescale or sub-timestep |
| `nn_nevp` (ORCA2–ORCA025) | 500 iterations per `rDt_ice` |
| `MOD(rday, rDt_ice) = 0` | 96 steps/day — satisfied |
| `nn_itend`, 228 days | **21 888** |

**Why not 3600 s**, which CFL permits at the coarser members: CFL guarantees stability, not accuracy.
At 3600 s the inertial period is resolved by only 13 steps. Meandering and vorticity are explicit
diagnostics here and both depend on inertial-loop fidelity. 900 s is better physics at every member,
not merely a device for removing a confound. (Under aEVP there is no elastic timescale or EVP
sub-timestep to set: `rn_relast` is used only by standard EVP, and `nn_nevp` is purely an iteration
count — see `&namdyn_rhg` below.)

**Fixed forcing cadence does not make the timestep irrelevant.** ERA5 (hourly) and GLORYS (daily) are
identical files for every member, so a shorter timestep samples the same piecewise-linear interpolant
more finely rather than admitting new variability. But several timestep-dependent processes are
internal to SI3 and unaffected by forcing cadence: the aEVP relaxation parameters (β ∝ √rDt_ice),
inertial-motion representation, quadratic-drag response integrated over a linear interpolant, and
Prather advection error at differing Courant number.

**`nn_fsbc = 1`** is admissible because non-SBC steps are nearly free under SAS, not from any
alignment with the ERA5 record interval. At 900 s there are four SBC calls per hourly ERA5 record,
with `fld_read` interpolating linearly between record midpoints — correct and expected.

**Storage and memory are unaffected by the timestep** — output frequency is in *model* time, so a
shorter timestep computes more between records without writing more. Wall clock is the only resource
that grows, linearly with step count; under SAS there is no cheap-step/expensive-step structure
(`src/SAS/step.F90` contains only `sbc()`, `dia_wri()`, `stp_ctl()`, `day()` and IOM bookkeeping).

### Measured peak Antarctic ice speed

From each member's own `_icemod` output, cells with `siconc > 0.15` south of 40°S, 3-hourly mean
velocities:

| Member | Peak speed | Latitude | Date |
|---|---|---|---|
| ORCA2 | 1.4604 m/s | −69.50° | 2019-05-31 |
| ORCA1 | 1.3807 m/s | −69.83° | 2019-05-27 |
| ORCA05 | **1.8465 m/s** | −71.31° | 2019-05-27 |
| ORCA025 | 1.4927 m/s | −69.66° | 2019-04-02 |

All four peaks fall in austral autumn–winter storm season, not the cold-start transient. **The
maximum, 1.85 m/s, is the figure that must set any CFL limit for this configuration** — a short
spin-up gives a substantially lower value and must not be used.

> These are 3-hourly **means**; instantaneous peaks are higher, so a margin computed from them is
> optimistic rather than conservative.

### CFL limits at 1.85 m/s

Using **minimum** retained spacing, which is what CFL sees — a median-based limit would be optimistic
by more than a factor of two:

| Member | Min Δx | CFL limit @1.85 m/s | Margin at 900 s | Verdict |
|---|---|---|---|---|
| ORCA2 | 47.10 km | ~25 500 s | 28× | ample |
| ORCA1 | 21.39 km | ~11 600 s | 13× | ample |
| ORCA05 | 10.48 km | ~5 700 s | 6.3× | ample |
| ORCA025 | 5.30 km | ~2 900 s | 3.2× | adequate |
| **GLOB16** | **1.40 km** | **~757 s** | **0.84×** | **inadmissible** |

All four completed runs were stable at 900 s, consistent with their margins. **GLOB16 cannot run at
900 s** (§GLOB16).

## Run directories, namelists and XIOS

### Directory layout

```
/scratch/djgway001/NEMO/
├── env_nemo.sh
├── nemo_5.0/                         NEMO source + tools (WEIGHTS, DOMAINcfg)
├── xios/bin/xios_server.exe
├── inputs/
│   ├── domain_cfgs/                  AS-RECEIVED, immutable
│   │   ├── domain_cfg_{ORCA2L31,ORCA1L50,ORCA05L75,ORCA025L75,GLOB16L98}.nc
│   │   ├── audit_domain_cfg.py  trim_domain_cfg.py
│   │   ├── build_weights.py  expand_weights.py
│   │   └── AUDIT_domain_cfgs_40S.{txt,json}
│   ├── <GRID>_ANT40S/                DERIVED, one per member
│   │   ├── domain_cfg.nc  TRIM_LOG.txt
│   │   └── weights/weights_bilin_{era5,glorys_..._sas,glorys_..._ice}_<grid>_ant40s.nc
│   ├── GLORYS12/                     GRID-INDEPENDENT
│   └── ERA5/                         GRID-INDEPENDENT
└── experiments/SEAICE_DYN_003/
    ├── setup_production.sh           the generator
    ├── common/                       canonical templates; never run from here
    │   ├── namelist_cfg.template  namelist_ice_cfg.template
    │   ├── namelist_ref  namelist_ice_ref  *.xml  README.md
    ├── ORCA2/ ORCA1/ ORCA05/ ORCA025/ GLOB16/
    │   ├── namelist_cfg  namelist_ice_cfg  *.xml        (COPIES)
    │   ├── nemo.exe  xios_server.exe  domain_cfg.nc     (SYMLINKS)
    │   ├── weights  ICs                                 (SYMLINKS)
    │   ├── submit_run.sh  nemo_mpmd.conf
    │   └── restart_files/  logs/
    └── VALIDATION/
        ├── verify_logs.sh  verify_production.py
        └── T0_trim_equivalence/      global vs trimmed ORCA025
```

**Two rules that matter:**

1. **Namelists and XMLs are copies, never symlinks** — a symlinked namelist would have one member's
   edits clobber the others silently.
2. **`common/` is edited, members are regenerated** — edit the template and re-run
   `setup_production.sh` rather than hand-patching five directories.

**Moved off scratch (29 Oct 2026), then lost (30 Oct).** To make room for v2 ORCA025,
`inputs/GLOB16_ANT40S/` (2.6 GB), `inputs/ORCA05_ANT40S/` (2.6 GB) and the five as-received
`inputs/domain_cfgs/domain_cfg_*.nc` (5.5 GB) were moved to a local `~/Data/NEMO/hpc_offload/`, which
was accidentally deleted on 30 Oct with no backup. **Surviving:** all five as-received domains and
the 40°S trimmed domains of ORCA2, ORCA1 and ORCA05 on an external HDD; on the cluster, the 40°S
domains and weights of ORCA2, ORCA1 and ORCA025 (`inputs/<GRID>_ANT40S/`) and the `domain_cfgs/`
scripts, audit reports, `ORCA05_build/` and `ORCA05_weights_rebuild.log`. **Lost:** the GLOB16
trimmed domain (`GLOB16_ANT40S/domain_cfg.nc`, 816 803 227 B) and its `TRIM_LOG.txt`, the GLOB16
weights (ERA5, GLORYS SAS, GLORYS ice), and the ORCA05 weights (incl. `.work/`). **Rebuild before
use:** for GLOB16, upload GLOB16L98 from the HDD, re-run `trim_domain_cfg.py` (deterministic; expect
816 803 227 B) and rebuild the weights with `build_weights.py` into `inputs/GLOB16_ANT40S/`; for
ORCA05, only if it is ever rerun, rebuild with `build_weights.py` + `expand_weights.py` + the ORCA05
post-processing (§Unmapped destinations; `ORCA05_weights_rebuild.log`). Scratch is not backed up, so
copying `inputs/{ORCA2,ORCA1,ORCA025}_ANT40S/` to the HDD is recommended; `ORCA025_ANT40S/` must stay
on the cluster for the `nn_nevp = 2000` run.
`ERA5/` (`raw/` 51 GB: 10u, 10v, 2t, 2d, msl; `processed/` 38 GB: ssrd, strd, tp, sf) and
`GLORYS12/` (20 GB) are read by every run and cannot be trimmed.

### `setup_production.sh`

```bash
cd /scratch/djgway001/NEMO/experiments/SEAICE_DYN_003
./setup_production.sh --dry-run        # report the plan, write nothing
./setup_production.sh                  # generate all five members
./setup_production.sh --member ORCA2   # regenerate one
```

Copies namelists and XMLs from `common/`, substitutes the grid token, weights filenames and
`cn_exp`, symlinks shared inputs, writes `nemo_mpmd.conf` and `submit_run.sh`, creates
`restart_files/` and `logs/`.

**`common/` holds Gate T0 values, and that is correct.** Templates carry `rn_Dt = 3600.`,
`nn_itend = 72`, `nn_stocklist = 72`, `nn_rhg_chkcvg = 1`. Production values (`RN_DT=900.`,
`NN_ITEND=21888`, monthly `NN_STOCKLIST`, `chkcvg = 0`) are defined at the top of
`setup_production.sh` and substituted on generation. Since v2, `nn_nevp = 500` is set in
`namelist_ice_cfg.template` itself (not substituted), and the 29-field `_icemod` list lives in
`common/file_def_nemo-ice.xml`. **Verify the generated member directory, never the template.**

**Rank counts** from the script's `MEMBERS` table: ORCA2 4, ORCA1 8, ORCA05 16, ORCA025 38, GLOB16
38, plus 2 XIOS ranks each. The generator writes no explicit `jpni`/`jpnj` — automatic decomposition
was used for all four completed members and the layouts were sane (§Results).

**Closing message is out of date.** The script's final message ("~4.7 h", "run the 72-step
validation first") predates v2; ignore it. v2 ORCA025 was generated with `--member ORCA025` only and
checked in the generated directory: no broken symlinks; `ln_aEVP = .true.`, `nn_nevp = 500`,
`nn_rhg_chkcvg = 0`; `cn_exp = SEAICE_DYN_003_ORCA025`, `nn_itend = 21888`, `rn_Dt = 900.`, cold
start, monthly stocklist; 38 NEMO + 2 XIOS ranks; `orca025_ant40s` weights only; `split_freq = 1mo`
on all four `file_def` entries; launcher `srun --mpi=pmix --mem=0 --ntasks=40 --cpu-bind=none
--multi-prog nemo_mpmd.conf` in a full-node job (`--constraint=large`, `--ntasks=48`,
`--cpus-per-task=1`, no `--mem`).

`cn_exp = "SEAICE_DYN_003_<GRID>"`. The trim token is deliberately omitted — every member is
trimmed, so it carries no information and lengthens every filename.

**One run directory per member.** `ocean.output`, `time.step` and `layout.dat` are overwritten by
every run in that directory, including short validations. Run validations elsewhere or move their
output aside immediately.

> **Recorded exception (v2 ORCA05).** ORCA05's `namelist_cfg` was hand-edited (`! DIAGNOSTIC`) to
> `nn_stocklist = 21888` only. This changes the restart point, not the physics or output
> (`namelist_ice_cfg` and `file_def_nemo-ice.xml` are identical to ORCA1's). ORCA05's
> `namelist_cfg` is therefore the true record of that run. It has been held locally since 29 Oct
> (now on the external HDD). Regenerating ORCA05 also needs `inputs/ORCA05_ANT40S/` rebuilt: its
> weights were lost on 30 Oct (§Directory layout).

### `namelist_cfg`

Built from `cfgs/ORCA2_SAS_ICE/EXPREF/namelist_cfg`. The SAS reference retains 7 blocks and adds 5;
an orphan block aborts at init, so this must be empty:

```bash
diff <(grep -o '^&[a-z_]*' namelist_cfg.bak_sasref | sort) <(grep -o '^&[a-z_]*' namelist_cfg | sort)
```

Grid-dependent entries flagged `[PER-GRID]`.

**`&namrun`** — `cn_exp="SEAICE_DYN_003_<GRID>"`, `nn_date0=20190318`, `nn_it000=1`,
`nn_itend=21888`, `nn_leapy=1`, `ln_rstart=.false.`, `ln_rst_list=.true.`, `nn_stocklist` at monthly
boundaries (`1344, 4224, 7200, 10080, 13056, 16032, 18912, 21888, 0, 0`),
`cn_ocerst_indir/outdir="restart_files"` (relative; directory must exist).

> `ln_rst_list` under SAS writes only the first stocklist entry (§Source-verified facts). Immaterial
> for single-submission members; must be changed for GLOB16.

**`&namdom`** — **`rn_Dt=900.`**, `rn_atfp=0.1`, `ln_meshmask=.false.`

**`&namcfg`** — `ln_read_cfg=.true.`, `cn_domcfg="domain_cfg"`, `ln_closea=.false.` Only five
variables exist in this block in NEMO 5.0.

**`&namsbc`** — `nn_fsbc=1`, `ln_blk=.true.`, `nn_ice=2`, `ln_ice_embd=.false.`, `ln_traqsr=.false.`,
`ln_dm2dc=.false.`, `ln_ssr=.false.`, `ln_rnf=.false.`, `ln_apr_dyn=.false.`, `nn_fwb=0`. Set
explicitly, not inherited.

**`&namsbc_blk`** — `ln_ECMWF=.true.`; `ln_humi_dpt=.true.` only; `ln_tair_pot=.false.`;
**`ln_prec_met=.false.`** (precipitation converted offline; `.true.` double-converts); `rn_zqt=2.`,
`rn_zu=10.`; `ln_crt_fbk=.false.`; `ln_Cx_ice_cst=.true.` with `rn_Cd_ia=rn_Ce_ia=rn_Ch_ia=1.4e-3`;
`cn_dir='/scratch/djgway001/NEMO/inputs/ERA5/'`; roots `raw/era5_<tag>` and `processed/era5_<tag>`;
freq `1.`, `'monthly'`, `clim=.false.`, time-interp `.true.`; wind pair `'Uwnd'`/`'Vwnd'`; weights
**[PER-GRID]**.

> `ln_Cx_ice_cst=.true.` matters for the comparison: form-drag parameterisations are functions of the
> resolved ice state and would respond to resolution, confounding the drift signal with a
> drag-parameterisation signal.

**`&namsbc_sas`** — slot order verified at `sbcssm.F90:195`. `l_sasread=.true.`, `ln_3d_uve=.false.`,
`ln_read_frq=.false.`; `cn_dir='/scratch/djgway001/NEMO/inputs/GLORYS12/forcing_002/processed/'`;
`sn_usp`/`sn_vsp` paired `'Ucur'`/`'Vcur'`; `sn_tem`, `sn_sal`, `sn_ssh`; all five at 24 h,
`'monthly'`, weights **[PER-GRID]**. `sn_e3t`/`sn_frq`/`sn_ifr`/`sn_tic`/`sn_ial` = `'NOT USED'`. LSM
slot empty — the source is drowned.

**`&nameos`** — **`ln_eos80=.true.`, `ln_teos10=.false.`** The SAS reference ships TEOS-10 and must be
overridden. `eos_fzp` (`sbcssm.F90:129`) sets the freezing point governing ice formation, and GLORYS
supplies potential temperature and practical salinity; left at TEOS-10 the offset would interact with
resolution through the ice-edge representation. **Rule: all T/S inputs must be potential temperature
+ practical salinity.** NEMO echoes `ln_EOS80 = T` and `==>>> use of EOS-80 equation of state` — note
the capitalisation when grepping.

**`&namlbc`** — `rn_shlat=2.` Inert in SAS.

**`&namtile`, `&nammpp`, `&namctl`, `&namsto`** — present. `&nammpp` is where explicit `jpni`/`jpnj`
would go if automatic decomposition proved inadequate.

### `namelist_ice_cfg`

**`&nampar`** — `jpl=5`, `nlay_i=10`, `nlay_s=5`, `ln_virtual_itd=.false.`, `ln_icedyn=.true.`,
`ln_icethd=.true.`, `rn_amax_n=rn_amax_s=0.997`; `cn_icerst_in/out="restart_ice"`,
`cn_icerst_indir/outdir="restart_files"`. **These four restart variables belong here, not in
`&namini`.** `jpl=5` is held constant across members — category count interacts with the resolved
thickness distribution.

**`&namdyn`** — **`rn_ishlat=2.`** (no slip). SI3 builds its own `fimask`
(`icedyn_rhg_evp.F90:220-221`); declared in `NAMELIST/namdyn/` at `icedyn.F90:256`.

**`&namini`** — `nn_iceini_file=1`; `sn_hti/hts/ati` → ice IC + weights **[PER-GRID]**; other slots
`'NOT USED'`; **pond overrides `rn_apd_ini_s=rn_hpd_ini_s=rn_hld_ini_s=0.0`**; `cn_dir='./'`.

**`&namdyn_rhg`** — `ln_rhg_EVP=.true.`, **`ln_aEVP=.true.`**, `rn_ecc=2.0`, **`nn_nevp=500`**
(ORCA2–ORCA025, identical; v1 used 100; GLOB16 open), `rn_relast=0.333` (**unused**: read only in
the standard-EVP branch, `icedyn_rhg_evp.F90:236-238`, `IF(.NOT. ln_aEVP)`), `rn_creepl=2e-9`,
`nn_rhg_chkcvg=0` (set 1 for a short validation run at each new resolution).

**aEVP convergence.** Under aEVP the relaxation parameter is computed per cell each step
(`icedyn_rhg_evp.F90:446, 468`):

```
β = MAX(50, π·√(0.5·P/(Δ + rn_creepl) / (e1t·e2t) · rDt_ice / m)),   P = P*·vt_i·exp(−C(1−A))
```

With H79 strength (P ∝ vt_i) and m ≈ ρᵢ·vt_i, **ice thickness cancels**: β depends only on
concentration, deformation rate Δ and cell area. The residual after N iterations scales as
~exp(−N/β), so cells with β ≳ `nn_nevp` are not converged.

Offline estimate from v1 output (`scripts/estimate_beta_evp.py`; Δ on the C-grid from
`sivelu`/`sivelv`; 3 h mean velocities, no snow/pond mass). Share of ice cells (A > 0.15) with
β > 100, Sep 2019 (March is similar):

| Member | β > 100 | β > 300 | 99th pct / max |
|---|---|---|---|
| ORCA2 | 0.007% | 0% | 50 / 125 |
| ORCA1 | 0.37% | 0% | 57 / 252 |
| ORCA05 | 2.65% | 0.27% | 185 / 600 |
| ORCA025 | 8.07% | 1.60% | 375 / 1137 |

**The unconverged share grows with resolution** (β ∝ 1/√cell area), so a fixed `nn_nevp` would add a
resolution-dependent numerical error to exactly the diagnostics under study. `nn_nevp = 500` leaves
~96% of ORCA025 ice cells under ~5% residual; the poorly converged tail (~1–2%) is compact,
low-deformation ice, so deformation and vorticity extremes are well converged. **Caveat:** that tail
remains unconverged at ORCA025; it is documented per cell and step by the `beta_evp` output field.
GLOB16 β is roughly 4× ORCA025's (~2000 iterations for equal convergence); its `nn_nevp` is open.

**In-model `beta_evp` versus the offline estimate.** At the coarse members in-model β exceeded the
offline figure (ORCA2 max 666 vs ~125; ORCA1 Oct 99th percentile 113 vs 57), plausibly because
better-converged v2 ice deforms less in the compact pack. At **ORCA05 the two agree** (Sep: in-model
99th 190 / max 630 vs offline 185 / 600), so the offline estimate is not consistently biased in
either direction. Read the ORCA025 tail from its own `beta_evp`.

**ORCA05 v2 `beta_evp`** (ice cells, `siconc > 0.15`, all records per monthly file):

| File (18th → 18th) | β > 500 | 99th pct | max |
|---|---|---|---|
| Mar–Apr | 0.005% | 188 | 563 |
| Apr–May | 0.003% | 122 | 552 |
| May–Jun | 0.000% | 113 | 512 |
| Jun–Jul | 0.000% | 141 | 507 |
| Jul–Aug | 0.000% | 110 | 484 |
| Aug–Sep | 0.000% | 173 | 530 |
| Sep–Oct | 0.001% | 190 | 630 |
| Oct–Nov (to 1 Nov) | 0.020% | 276 | 664 |

**ORCA05 is effectively fully converged at `nn_nevp = 500`** (≤ 0.02% of ice cells above 500 in any
month). The tail is largest in the shoulder seasons and grows into late October.

**Measured cost.** v2 ran 1.56× (ORCA2), 1.57× (ORCA1) and **1.79× (ORCA05)** the v1 wall clock,
so the rheology was ~14% of v1 runtime at the two coarsest members and ~20% at ORCA05: **the share
grows with resolution.** ORCA025 estimate: ≈ 7–9 h (the earlier 16–20 h assumed 60–80%).

**`&namdyn_adv`** — **`ln_adv_Pra=.true.`, `ln_adv_UMx=.false.`** Load-bearing for a resolution study:
a diffusive scheme would smear the ice edge by an amount depending on grid spacing, manufacturing a
resolution signal in the diagnostic under investigation. *Cost:* the Prather moments **are** the
restart. `icedyn_adv.F90:157` enforces XOR.

### XIOS output

XML copied from `cfgs/SEAICE_DYN_003/EXP00/`, `oasis_codes_id` removed, both `file_def` files
rewritten. `field_def_nemo-{oce,ice}.xml` used as shipped.

**File IDs must match `fileN`** — `iom_update_file_name` runs only for `file0..file999`
(`iom.F90:2726-2738`); a descriptive ID silently skips token substitution.

| ID | Stream | Freq | Fields |
|---|---|---|---|
| `file21` | `_icemod` | 3 h | v1 (8): `siconc, sithic, sivelu, sivelv, utau_ai, vtau_ai, utau_oi, vtau_oi`; v2 adds 21 (29 total): `afxdyn, afxthd, rdg_loss, rdg_gain, rft_loss, rft_gain, lead_open, intstrx, intstry, corstrx, corstry, dssh_dx, dssh_dy, snwmass, icediv, iceshe, icedlt, icestr, normstr, sheastr, beta_evp` |
| `file22` | `_SBC_scalar` | monthly | 10 global ice-budget scalars |
| `file11` | `_grid_T` | daily | `ssu_m, ssv_m, sst_m, sss_m, ssh_m` |
| `file12` | `_sbcwind` | 3 h | `utau_oce, vtau_oce, wspd` |

All other file groups emptied. **A `field_ref` pointing at a variable that never receives data fails
silently** — the reference ships ~15 that do not exist under SAS. Every v2 field was confirmed to
receive data in the ORCA2 validation (the ridging/rafting group only after the `MY_SRC` fix).

**v2 field notes.**
- **Eq. 1 partition:** advective = `afxdyn` − (`rdg_gain` + `rft_gain` − `rdg_loss` − `rft_loss`);
  non-advective = `afxthd` + the same net ridging/rafting term, so ridging sits with the
  non-advective terms as the analysis requires.
- **`lead_open`** is filled from `opning` at ridging points only (`icedyn_rdgrft.F90:1141`) and was
  zero over ice in every month checked at ORCA2 and ORCA1. Kept for identical output across members;
  uninformative.
- **`beta_evp`** is 50 over open water and > 50 in ice; compare with `nn_nevp` to flag poorly
  converged cells.
- **`uice_cvg`** (solver convergence) is deliberately **not** output: it is written only when
  `nn_rhg_chkcvg > 0`, which is off in production.
- Ice + snow mass for the momentum balance = ρᵢ·`siconc`·`sithic` + `snwmass` (no ice-mass field
  exists).

- **`split_freq="1mo"` on every entry.** XIOS closes a file at each month boundary and closed files
  survive a kill, bounding loss from any interruption; also keeps filenames month-scoped, the
  granularity wanted for archiving and analysis.
- **Output frequency must not vary between members.** 3-hourly ice output resolves inertial motion
  (~13 h at 65°S).
- **Daily for the prescribed ocean:** GLORYS is a daily mean and `fld_read` interpolates linearly
  between record midpoints, so 3-hourly output would write eight samples of a straight line.
- **Why `_sbcwind` exists:** `utau_ai`/`vtau_ai` use **relative** wind (`U_wind − U_ice`). The classic
  Nansen turning angle is defined against **absolute** 10 m wind, which `utau_oce`/`vtau_oce`
  direction gives. The magnitude ratio needs wind *speed*, unrecoverable from `utau_ai` without
  inverting a stability-dependent bulk drag.
- **No output compression is possible in XIOS.** XIOS3 raises a hard `ERROR` for compression in
  parallel mode (`onetcdf4.cpp:527-529`), despite `compression_level` being a declared attribute.
  Offline `nccopy -d 1 -s` gives ~5× (measured on the v2 ORCA2 validation file); deferred unless
  storage requires it.
- **`_SBC_scalar` integrates the Southern Hemisphere only**, since that is the whole domain — no
  hemisphere masking needed.

**Filename pattern as produced.** With `name="@expname@_@freq@"` and `cn_exp =
"SEAICE_DYN_003_<GRID>"`:

```
SEAICE_DYN_003_ORCA025_3h_icemod_201905-201906.nc
└── experiment ──┘└ grid ┘└fq┘└stream┘└─ period ─┘
```

**The stream token precedes the period**, period is `YYYYMM-YYYYMM` at monthly split granularity. All
four identifiers present, so no renaming is required. **The monthly split counts from the run start,
not calendar months:** `_201903-201904` covers 18 Mar – 18 Apr (248 three-hourly records) and the last
file 18 Oct – 1 Nov (112). `split_freq_format` controls date granularity;
confirm any change against real output rather than assuming token syntax.

## Running production

### Segmentation is a storage decision, and only a storage decision

No walltime limit, so scratch quota is the only reason to segment. **All four ORCA members run
end-to-end in a single submission each.** Only GLOB16 requires segmentation.

| | ORCA2 | ORCA1 | ORCA05 | ORCA025 | Total |
|---|---|---|---|---|---|
| v1 output | 0.65 GB | 2.6 GB | 16 GB | 41 GB | 60 GB |
| v2 output | 1.8 GB | 7.1 GB | 41 GB | 113 GiB (121.4 GB) | ~163 GiB |

v2 members cannot all sit on scratch at once. After ORCA2–ORCA05 were downloaded and their output
deleted (29 Oct), together with `testing/orca2_ice_smoketest` (3.4 GB) and the inputs moved off
scratch (§Directory layout), the 250 GB quota held 115 GB (mostly ERA5 and GLORYS12), leaving
~135 GB: room for ORCA025 with ~18 GB to spare (228 GB used while ORCA025 v2 is held). Restarts
are negligible (ORCA025: 76 files, 7.6 MB, at step 1344 only). A later ORCA025 run at
`nn_nevp = 2000` (~121 GB) needs ORCA025 at 500 verified locally and cleared first. `quota -s` reports 0 and is unusable; measure with
`du -sh /scratch/djgway001`.

### Launch mechanism: `srun --multi-prog`

SLURM's own MPMD launcher, not `mpirun`, per cluster policy. `N` compute ranks plus 2 XIOS ranks
share one `MPI_COMM_WORLD`:

```
0-(N-1)   ./nemo.exe
N-(N+1)   ./xios_server.exe
```

```bash
srun --mpi=pmix --mem=0 --ntasks=$((N+2)) --cpu-bind=none --multi-prog nemo_mpmd.conf
```

- **`--mem=0` is required (v2 onward).** Without it the step's memory is the per-task default, not the
  job's 375 GB (see the step-level RAM trap above). `setup_production.sh` (backup
  `setup_production.sh.bak_stepmem`) writes it on both `srun` lines: the dry-run echo (line 297) and
  the launch (line 308). A `diff` against the backup confirms these are the only changes.
  v1 never hit the limit (peak 43 GB); v2 ORCA05 did (job 1502968: an XIOS server reached 113 GB
  against a 144 GB step limit during start-up → `OUT_OF_MEMORY`). With `--mem=0` the step receives
  300 GB.
- **`--cpu-bind=none` is required, not optional.** Without it the job step's cpuset is scoped to the
  `--ntasks` request and the inherited default binding tries to bind outside it, failing immediately
  with `CPU binding outside of job step allocation`. The job's own allocation is unaffected — `sacct`
  confirms the full 48 CPUs and 375 GB.
- **Requires the `pmix` plugin** — `srun --mpi=list` must show `pmix_*`; confirmed here as `pmix_v5`,
  matching OpenMPI 5.0.3.
- `setup_production.sh` writes both `nemo_mpmd.conf` and the `srun` line.
- **Identifying the launcher afterwards:** `srun --multi-prog` appears in `sacct` as one numbered job
  step carrying all `N+2` tasks. `verify_logs.sh` checks this — evidence from the scheduler rather
  than the submitted script.

### Dry run: mandatory, every member, every submission

Rewrites namelists and writes the sbatch script without submitting, so the exact configuration can be
read before any node time is spent. Costs no queue wait.

```bash
cd /scratch/djgway001/NEMO/experiments/SEAICE_DYN_003/<GRID>
./submit_run.sh --dry-run
```

| Check | Expected |
|---|---|
| `cn_exp` | `SEAICE_DYN_003_<GRID>` |
| `nn_it000` / `nn_itend` | `1` / `21888` |
| `ln_rstart` / `nn_rstctl` | `.false.` / `0` for a cold start |
| `nn_stocklist` | monthly points |
| `rn_Dt` | `900.` (ORCA members) |
| weights filenames | this member's, with the `_ant40s` token |
| `split_freq` | `1mo` on all four `file_def` entries |
| launcher line | `srun --mpi=pmix --mem=0 --ntasks=<N+2> --cpu-bind=none --multi-prog nemo_mpmd.conf` |
| dangling symlinks | none |

```bash
sbatch submit_run.sh          # namelists ALREADY written by the dry run; do not re-run the
                              # wrapper, it would overwrite the pre-edit backup
squeue -u djgway001
```

### Watching a run start

A configuration fault aborts within seconds or minutes:

```bash
tail -f ocean.output          # humidity sanity test; both vector pairs rotated;
                              # configuration resolving to ORCA/<n>, not UNKNOWN
head -n 8 layout.dat          # decomposition
cat time.step                 # must be advancing
sstat -j <job>.0 --format=MaxRSS   # step memory; sacct -j <job>.0 --format=AllocTRES for the ceiling
```

Also watch `du -sh /scratch/djgway001` during the run: scratch margin is small (§Segmentation).

`fld_weight : unable to read the file` appears within seconds. A stall at low `time.step` with no
error is the `dia_mlr_init` deadlock (§GLOB16) — kill rather than wait.

### Hard constraints

- **MPI rank count identical across all segments of a member** — restarts are per-rank. May differ
  between members.
- **Request the full node** — `--constraint=large`, `--cpus-per-task=1`, omit `--mem` on the job.
- **Give the step the node's memory** — `srun --mem=0`; otherwise the step is capped at `ntasks × 8000 MB`.
- **XIOS server mode** (`using_server=true`), floor of 2 servers.
- **`split_freq="1mo"` on every `file_def` entry**, every member.
- **No output compression.**

---

# Part V — Results

## Verification protocol

### Gate T0 — trim equivalence

Matched pair: global ORCA025 and trimmed ORCA025, same build, same session, same rank count (38
compute + 2 XIOS), **domain file and its weights the only difference**. 72 steps each, differencing
`sivelu`, `sivelv`, `siconc`, `sithic` over retained rows.

**Bit-identical output is not achievable and is not the test.** The runs decompose different row
counts (1050 vs 354) across 38 ranks, so partial sums accumulate in a different order. Floating-point
addition is not associative, so they differ in the last representable digit from the first operation
onward, and over 72 steps of nonlinear EVP iteration that seed amplifies at ice-edge cells. Two
things are diagnostic, and both must hold:

- **Divergence must start at zero.** If the configurations are equivalent the first output record is
  identical; a non-zero difference at record 0 is a configuration fault no chaotic-amplification
  argument can explain away.
- **Integrated quantities must agree.** Per-cell chaos averages out; domain totals are what the
  science reports.

**Record 0, ice-covered cells:**

| Field | max abs diff | mean abs diff |
|---|---|---|
| `siconc` | **0.000e+00** | 0.000e+00 |
| `sivelu` | **0.000e+00** | 0.000e+00 |
| `sivelv` | **0.000e+00** | 0.000e+00 |
| `sithic` | 7.015e-05 | 4.620e-09 |

**Growth from that zero** — mean abs diff over ice-covered cells (upper rows), and relative
difference of domain integrals over the retained interior, j = 0…343 (lower rows):

| Record | 0 | 1 | 2 | 4 | 8 | 15 | 23 |
|---|---|---|---|---|---|---|---|
| `siconc` | 0 | 9e-8 | 8e-7 | 8e-6 | 4e-5 | 9e-5 | — |
| `sivelu` | 0 | 5e-9 | 3e-7 | 2e-6 | 2e-5 | 3e-5 | — |
| `sivelv` | 0 | 3e-8 | 8e-7 | 2e-6 | 2e-5 | 3e-5 | — |
| total ice area | 0.0e+00 | — | — | 8.4e-07 | 4.8e-06 | 2.2e-06 | 8.1e-06 |
| total ice volume | 3.0e-06 | — | — | 2.6e-05 | 5.5e-05 | 3.4e-05 | 9.6e-05 |

Agreement to ~6 significant figures in area, ~5 in volume, **oscillating rather than trending** —
bounded numerical noise. Wall rows (j = 352…353): max abs diff exactly 0.000e+00 in all four fields.

**Conclusion: the 40°S truncation is inert.** The trimmed domain reproduces the global domain's
Antarctic sea-ice state to within floating-point noise from the different MPI decomposition — the
closest agreement achievable between two domains of different extent.

### Post-run verification, every member

Two scripts in `VALIDATION/`, run before any output is transferred.

**`verify_logs.sh <GRID> <JOBID>`** — head-node safe (grep and `sacct` only):

- `time.step` = 21888; `AAAAAAAA` at the end of `ocean.output`
- no `E R R O R`, abort, misspelled-variable or NaN lines
- key parameters **as NEMO read them**, not as the namelist claims: `rn_Dt`, `rDt_ice`, `nn_itend`,
  `nn_fsbc`, `ln_aEVP`, `ln_adv_Pra`, `rn_ishlat`, `nn_nevp`
- configuration identity resolves (`cn_cfg = ORCA`, `nn_cfg = <n>`), not `UNKNOWN`/−999
- both vector pairs rotated: `(u10, v10)` and `(uo, vo)`
- launcher confirmed from `sacct` step task counts
- restart file counts per stocklist point; output inventory per stream
- **any file predating the job's start** — stale output from an earlier run in the directory

**`verify_production.py --grid <GRID> --ncompute <N> --outdir <dir> --restartdir <dir>`** — under
`sintx` with `nemo_analysis`:

- every file opens; time axis complete, uniformly spaced, contiguous across month splits; first and
  last records centred correctly
- no non-finite values over surface-wet cells, mask from the **trimmed** `domain_cfg.nc`
- `siconc ∈ [0,1]`, `sithic ≥ 0` as hard bounds; loose physical ranges elsewhere as warnings
- `_SBC_scalar` volume / area / mean-thickness table
- peak Antarctic ice speed where `siconc > 0.15`
- every restart file read variable by variable, not merely opened

Non-zero exit on any failure. `verify_production.py` writes `VERIFY_PRODUCTION_<GRID>.txt` into the
member directory; **`verify_logs.sh` prints to the terminal only**, so save it with
`verify_logs.sh <GRID> <JOBID> | tee VERIFY_LOGS_<GRID>.txt`. (v1 reports and v2 ORCA025 were saved;
v2 ORCA2–ORCA05 were not, and their results are recorded in §Run statistics.) At ORCA025,
`verify_production.py` runs as an sbatch job (`verify_production_<GRID>.sh`; 6:07 and 113.5 GiB
batch MaxRSS at ORCA025); the wrapper must `tee` the report into the member directory, as the
ORCA025 wrapper wrote it only to `logs/verify_production_<jobid>.out`.

**Expected non-failures:**

- `sst_m` minimum around −2.55 °C trips a soft warning — this is the GLORYS seawater freezing point
  and is correct.
- A single `W A R N I N G` block in `ocean.output` at some members is benign.
- XIOS `Unexpected request for buffer` (`.err`) and `zoom_axis is deprecated` (`.out`) are normal
  XIOS3 chatter.
- The restart check reports a single stocklist point (§Source-verified facts, `ln_rst_list`).

### Local verification after transfer

Opening a file proves the header survived, not the payload. **v2 uses checksums:** an MD5 list of
every regular file in the member directory is made on the cluster (`./<file>` paths; symlinks such as
`domain_cfg.nc`, `nemo.exe` and the weights are not regular files and are excluded), copied to
`~/Data/NEMO/SEAICE_DYN_003_v2/v2_md5_<GRID>.txt`, and checked locally:

```bash
cd ~/Data/NEMO/SEAICE_DYN_003_v2/<GRID> && md5sum -c --quiet ../v2_md5_<GRID>.txt
```

v2 ORCA2, ORCA1 and ORCA05 each passed for all 67 files: 31 output `.nc` plus 36 run-record files
(namelists, XMLs, `ocean.output`, `time.step`, `output.namelist.*`, `logs/<jobid>.*`,
`xios_server_*`, timing files, `VERIFY_PRODUCTION_<GRID>.txt`, `PROVENANCE.md`). The local
`domain_cfg_<GRID>_ANT40S.nc` was checked separately: MD5-identical to the cluster `domain_cfg.nc`
target the run used.

v1 was checked by total byte counts against the cluster, plus local record-count and
time-contiguity checks:

```bash
for G in ORCA2 ORCA1 ORCA05 ORCA025; do
  echo "$G $(cat $G/SEAICE_DYN_003_${G}_*.nc | wc -c)"
done
```

## Results as produced

### Run statistics — `srun` launcher, `rn_Dt = 900`

**v1** (8 `_icemod` fields, `nn_nevp = 100`):

| Member | Ranks | Per-rank `jpi`×`jpj` | Elapsed | s/step | MaxRSS | Output |
|---|---|---|---|---|---|---|
| ORCA2 | 4 | 49 × 48 | 35:53 | 0.098 | 14.3 GB | 653 MB |
| ORCA1 | 8 | 49 × 92 | 56:25 | 0.155 | 13.8 GB | 2.6 GB |
| ORCA05 | 16 | 149 × 68 | 2:01:12 | 0.332 | 39.2 GB | 16 GB |
| ORCA025 | 38 | 107 × 122 | 3:53:36 | 0.640 | 43.3 GB | 41 GB |

All four: `time.step = 21888`, `AAAAAAAA`, no errors, 31 output files, both verification scripts
**0 FAIL**.

Automatic decomposition gave 4×1 (ORCA2), 8×1 (ORCA1), 5×4 minus 4 land-only (ORCA05), 14×3 minus 4
land-only (ORCA025). No explicit `jpni`/`jpnj` needed.

- **Memory scales with grid size under this launcher** — 14 → 14 → 39 → 43 GB across a 64× range in
  grid points, comfortably inside a single 375 GB node (v1). Makes GLOB16 single-node operation
  plausible but unconfirmed.
- **Wall clock is super-linear in points per rank** (1 980 → 3 960 → 11 507 → 13 415 points/rank
  giving 0.098 → 0.155 → 0.332 → 0.640 s/step) — per-step overhead dominates at small sizes.
  Initialisation costs minutes, a fixed addition to every figure.

**v2 (29 `_icemod` fields, `nn_nevp = 500`).** XIOS server memory grows with the number of output
fields (~26 in v1 → ~47 in v2 across all streams) and dominates the peak.

| Member | Job | Elapsed | vs v1 | MaxRSS (step) | Output |
|---|---|---|---|---|---|
| ORCA2 | 1502542 | 55:50 | 1.56× | 19.7 GB | 1.8 GB |
| ORCA1 | 1502660 | 1:28:31 | 1.57× | 13.2 GB | 7.1 GB |
| ORCA05 | 1503915 | 3:36:31 | 1.79× | 36.9 GB (task 0, a NEMO rank) | 41 GB |
| ORCA025 | 1541973 | 7:24:53 | 1.90× | 51.0 GiB | 113.1 GiB (121 444 783 127 B) |

ORCA05's first attempt (1502968) was OOM-killed at start-up by the step-level RAM trap (113 GB on one
XIOS server vs a 144 GB step limit); fixed with `srun --mem=0`. **XIOS is not the steady-state
memory consumer:** the XIOS server memory reports show 8 KB buffers per client (32 KB in total at
ORCA2, 64 KB at ORCA1, ~96 KB at ORCA05), and v2 ORCA05 peaked at 36.9 GB on a NEMO rank, close to
v1's 39 GB. The 113 GB was an artefact of the 144 GB cap or a start-up transient. v2 ORCA025 peaked
at 51.0 GiB (53 466 036 KiB) against the 300 GB step ceiling. MaxRSS values are `sacct` KiB; the
"GB" figures in both tables are GiB.

All four completed v2 members passed `verify_logs.sh` and `verify_production.py`, plus a field-level
check of the 29 `_icemod` variables and `beta_evp` at each. v2 ORCA2–ORCA05 restarts were deleted
after verification; ORCA025's are deleted with its output once the local MD5 check passes.

**v2 ORCA025 verification (job 1541973; `verify_production.py` job 1543487).** `verify_logs.sh`:
0 FAIL — `time.step` 21888, `AAAAAAAA`, no ERROR/NaN; as read by NEMO `nn_nevp = 500`,
`ln_aEVP = T`, `rn_ishlat = 2`, `rDt_ice = 900`, `nn_itend = 21888`, `cn_cfg` ORCA/4, both vector
pairs rotated; 38 + 2 ranks; decomposition 38 × (107 × 122), identical to v1; expected non-failures
only (1 `W A R N I N G` block, XIOS chatter, single restart point at step 1344 with 38 + 38 files);
no stale files. `verify_production.py`: 0 FAIL, 2 WARN — time axes complete and contiguous
(`_icemod`/`_sbcwind` 1824 × 3 h, `_grid_T` 228, `_SBC_scalar` 7); all 29 `_icemod` fields; no
non-finite values; WARN `sst_m` minimum −2.551 °C (GLORYS freezing point, benign); WARN peak ice speed
1.4927 m/s at −69.66°, 2019-04-02 10:30 (identical to v1 ORCA025; relevant to the GLOB16 CFL only).
Also noted: `beta_evp` wet-cell maximum 6790 (ORCA05 v2 monthly maxima 484–664), so the monthly share
of ice cells above 500 and the 99th percentile are to be computed after download; `sithic` maximum
29.09 m (v1 28.76 m; coastal pile-up); `lead_open` non-zero somewhere at ORCA025 (max 1.8e-4),
unlike the other members — check whether over ice.

**ORCA025 solver-sensitivity resources (100 / 500 / 2000).**

| `nn_nevp` | Run | Elapsed | s/step | × v1 | Step MaxRSS | Output (31 files) | Restarts |
|---|---|---|---|---|---|---|---|
| 100 | v1, job 1349225 | 3:53:36 | 0.640 | 1.00 | 43.3 GiB | 43 337 903 919 B | — |
| 500 | v2, job 1541973 | 7:24:53 | 1.22 | 1.90 | 51.0 GiB | 121 444 783 127 B | 7.6 MB |
| 2000 | projected | ~20.5 h | ~3.4 | ~5.3 | ~51 GiB | ~121 GB | ~8 MB |

With v2 = v1 × (1 + 4r), r ≈ 0.225: the rheology costs ≈ 22.5% of v1 runtime per 100 iterations at
ORCA025 (14% at ORCA2/ORCA1, 20% at ORCA05; it rises with resolution). The 2000 run is then
v1 × (1 + 19r) ≈ 20.5 h. Iteration cost is fixed because `nn_rhg_chkcvg = 0` (no early exit). The
43.3 → 51.0 GiB rise comes from v2's extra output fields, not from iterations, so the 2000 run should
peak near 51 GiB; output volume does not depend on `nn_nevp`. **Recommended set-up:** a full-season
cold start, identical to v2 ORCA025 except `nn_nevp`, in its own run directory with its own `cn_exp`
(e.g. `ORCA025_NEVP2000` / `SEAICE_DYN_003_ORCA025_NEVP2000`) so the v2 run records are not
overwritten, and without editing `common/namelist_ice_cfg.template`. A shorter window cannot start
from a v2 restart, since SAS writes only step 1344 (§`ln_rst_list`).

### Output inventory

31 files per member (v1 and v2): 8 × `_icemod`, 8 × `_sbcwind`, 8 × `_grid_T`, 7 × `_SBC_scalar`.
The scalar stream has 7 because the run starts 18 March, so there is no complete March month.
Records: 1 824 + 1 824 + 228 + 7 = **3 883**.

| Member | Total bytes, v1 (31 files) | Total bytes, v2 (31 files) |
|---|---|---|
| ORCA2 | 677 333 511 | 1 894 295 279 |
| ORCA1 | 2 697 144 623 | 7 554 518 551 |
| ORCA05 | 15 654 970 287 | 43 867 059 095 |
| ORCA025 | 43 337 903 919 | 121 444 783 127 |

### Conservation diagnostics — the primary cross-member result

*v1 figures. v2 differs only through `nn_nevp`; recompute from v2 once all members are complete.*

`ibgvol_tot` (km³) and `ibgarea_tot` (km²), units confirmed from file metadata, integrated over the
Southern Hemisphere domain. Mean thickness is their ratio.

**Mean ice thickness (m), by record centre:**

| Record centre | ORCA2 | ORCA1 | ORCA05 | ORCA025 |
|---|---|---|---|---|
| 2019-04-02 | 3.535 | 0.888 | 0.896 | 0.858 |
| 2019-05-03 | 4.680 | 0.819 | 0.863 | 0.812 |
| 2019-06-02 | 5.651 | 0.845 | 0.900 | 0.853 |
| 2019-07-03 | 6.182 | 0.977 | 1.024 | 0.976 |
| 2019-08-02 | 6.444 | 1.068 | 1.115 | 1.069 |
| 2019-09-02 | 6.231 | 1.065 | 1.116 | 1.074 |
| 2019-10-03 | **5.908** | **1.093** | **1.143** | **1.099** |

**Final record (2019-10-03):**

| Member | Volume (km³) | Area (km²) | Mean thickness (m) |
|---|---|---|---|
| ORCA2 | 49 109 | 8 312 350 | 5.908 |
| ORCA1 | 15 433 | 14 123 442 | 1.093 |
| ORCA05 | 16 884 | 14 770 534 | 1.143 |
| ORCA025 | 15 973 | 14 538 222 | 1.099 |

**Interpretation.**

- **ORCA1, ORCA05 and ORCA025 have converged.** Across an 8× change in minimum grid spacing
  (21.4 → 5.3 km) they agree within 9% on volume, 5% on area, 5% on mean thickness, with no monotonic
  trend. All three reproduce the same seasonal shape: thickness dipping in May during rapid areal
  expansion, then rising through winter.
- **All three are physically realistic.** September–October area 14.1–14.8 × 10⁶ km² and volume
  15–17 × 10³ km³ sit within observed Antarctic maxima of roughly 14–15 × 10⁶ km² and
  15–20 × 10³ km³; mean thickness ~1.1 m against an observed ~1 m. Good for a standalone SI3 run
  cold-started six months earlier.
- **ORCA2 is below the resolution floor this configuration requires.** Final area 57% of ORCA1's
  while carrying 3.2× the volume → ~5.9 m mean thickness. With 44 rows south of 40°S and 47 km
  minimum spacing it cannot resolve the ice edge, the marginal ice zone or coastal boundary layers,
  so ice thickens in place rather than advecting outward. **An informative endpoint — where the
  model stops being physically meaningful at this configuration — not a configuration defect**;
  the convergence of the three finer members is what establishes this.
- **The prescribed ocean is not the cause.** `sst_m` and `sss_m` ranges are unremarkable at every
  member, with no cold or fresh bias that would drive runaway growth via the freezing-point path.
- **Monotonic growth through autumn and winter is expected.** Each `_SBC_scalar` record is a monthly
  mean centred mid-month — the final one on 3 October, not the 1 November end date — so the
  September maximum falls inside the last record's averaging window rather than after it.

## Data transfer and archive

Compute nodes are unreachable from outside the cluster, so transfers are **pulled from the local
machine** using the head node as source host.

Throughput via `djgway001@hex.uct.ac.za` is ~4.4–4.8 MB/s (~20 min per 5 GB; ~6.8 h for ORCA025 v2).
v1 was pulled file set by file set:

```bash
cd ~/Data/NEMO/SEAICE_DYN_003_v1
mkdir -p ORCA2 ORCA1 ORCA05 ORCA025
R=djgway001@hex.uct.ac.za
E=/scratch/djgway001/NEMO/experiments/SEAICE_DYN_003
I=/scratch/djgway001/NEMO/inputs

for G in ORCA2 ORCA1 ORCA05 ORCA025; do
  scp "$R:$E/$G/SEAICE_DYN_003_${G}_*.nc"  $G/
  scp "$R:$I/${G}_ANT40S/domain_cfg.nc"    $G/domain_cfg_${G}_ANT40S.nc
  scp "$R:$E/$G/VERIFY_LOGS_$G.txt"        $G/
  scp "$R:$E/$G/VERIFY_PRODUCTION_$G.txt"  $G/
  scp "$R:$E/$G/namelist_cfg"              $G/
  scp "$R:$E/$G/namelist_ice_cfg"          $G/
  scp "$R:$E/$G/ocean.output"              $G/
  scp "$R:$E/$G/layout.dat"                $G/
done
```

**v2** is pulled as every regular file in the member directory (output plus all run records, the
same set as the MD5 list; §Local verification after transfer), plus the trimmed `domain_cfg.nc`
renamed to `domain_cfg_<GRID>_ANT40S.nc`. Watch that the run records come across: for ORCA2–ORCA05
they were missed on the first pass and fetched separately. ORCA025 uses `rsync -rt --partial`
(symlinks skipped) against a list made on a compute node
(`/scratch/djgway001/NEMO/experiments/SEAICE_DYN_003/v2_md5_ORCA025.txt`: 74 regular files = 31
output + 43 run records, including `VERIFY_LOGS`, `VERIFY_PRODUCTION`, the verify wrapper and its
logs, and `registry.bin`; `restart_files/` excluded). Its trimmed domain should match MD5
`7e1b052d43f3ac473441a9551b6f485e` (60 566 167 B).

**Data locations (30 Oct 2026).**

```
~/Data/NEMO/
├── SEAICE_DYN_003_v1/      ORCA025 (A17's nn_nevp = 100 member), SEAICE_DYN_003_runrecords.tgz
└── SEAICE_DYN_003_v2/      ORCA025 (transfer running), v2_md5_<GRID>.txt
External HDD:               v1 and v2 ORCA2, ORCA1, ORCA05 (v2 re-verified by MD5 after the move);
                            five as-received domain_cfg files; 40°S domains of ORCA2, ORCA1, ORCA05
```

The three ORCA025 solver-test settings total ~283 GB uncompressed (41 + 121 + ~121), more than the
251 GB local disk: lossless compression (`nccopy -d 1 -s`, ~5× measured, applied locally after the
MD5 check) or analysis from the HDD must be chosen before the 2000 run is downloaded.

**The trimmed `domain_cfg.nc` must accompany every member's output** — neither stream carries cell
areas, so it is required for any area-weighted quantity, and it must be the *trimmed* file.

**Verify locally before deleting anything remote** — record counts, time contiguity, total byte
counts against §Results (v2: MD5 lists). Scratch is not backed up, so the local copy plus an
external backup is the only durable record. On the cluster, v2 ORCA2–ORCA05 configs and logs were
kept after their output was deleted.

---

# Part VI — Reference

## Source-verified facts

Confirmed by reading `nemo_5.0/src/`. Re-verify only if the NEMO version changes.

### `domain_cfg` — how the grid is actually read (`domain.F90:568-654`)

```fortran
idvar = iom_varid( inum, 'e3t_0', kdimsz = idimsz )   ! use e3t_0, that must exist
kpi = idimsz(1)   ;   kpj = idimsz(2)   ;   kpk = idimsz(3)
```

**Global dimensions come from the SHAPE of `e3t_0`.** Scalar `jpiglo`/`jpjglo`/`jpkglo` are **never
read**. Values are the inner dimensions `Ni0glo`/`Nj0glo`; the halo is added at runtime, so there is
no halo arithmetic in the trim.

```fortran
CALL iom_getatt( inum, 'Iperio', iatt )   ;   ldIperio = iatt == 1   ! -999 if not found -> .false.
CALL iom_getatt( inum, 'Jperio', iatt )   ;   ldJperio = iatt == 1
CALL iom_getatt( inum,  'NFold', iatt )   ;   ldNFold  = iatt == 1
CALL iom_getatt( inum, 'NFtype', catt )
```

**Periodicity is four global attributes**, defaulting to false / `'-'` when absent. The legacy
`jperio` fallback fires only when **both** `NFold` and `NFtype` are absent **and** a `jperio` variable
exists. **Writing a real `NFold`/`NFtype` pair is what disables it — overwriting `jperio` alone would
not.**

**Configuration identity** comes from `CfgName`/`CfgIndex`, falling back to `ORCA`/`ORCA_index`, then
`cn_cfg`/`nn_cfg`. Absent all three → `UNKNOWN`/−999, cosmetic only.

**`ln_use_jattr` does not exist in NEMO 5.0.** `&namcfg` accepts exactly five variables
(`ln_read_cfg`, `cn_domcfg`, `ln_closea`, `ln_write_cfg`, `cn_domcfg_out`), identical across all six
`nemogcm.F90` variants. No `open_ocean_jstart` consumer in `src/`; setting it aborts at init as a
misspelled variable.

### The ocean vertical dimension is inert under SAS + SI3

- `src/SAS/step.F90` contains no `jpk`/`jpkm1` reference.
- `src/ICE/*.F90` contains none either, excluding ice-internal counters (`nlay_i`, `nlay_s`, `jpl`).
- The only `jpk`-dimensioned allocation in the SAS surface path (`sbcssm.F90:296-297`) sits inside
  `IF( nfld_3d > 0 )` at `:290`, and `nfld_3d = 0` under `ln_3d_uve=.false.` (`:262`).

**Consequences:** the L31/L50/L75/L98 mismatch is **not** a comparability issue; trimming `jpk` would
save no memory; the vertical is a structural dimension in the domain file only. What this does *not*
resolve: `bottom_level` still sets `tmask(:,:,1)`, which sets `fimask`
(`icedyn_rhg_evp.F90:220-221`), which shapes coastal ice deformation.

### Weights hold ABSOLUTE source indices

```fortran
! fldread.F90:1151, 1200-1201
id = iom_varid( sd%num, sd%clvar, ddims )          ! source dims from the DATA file
data_jpi = 1 + MOD(isrc,  ddims(1))
data_jpj = 1 +     isrc / ddims(1)
```

Bound to the exact source grid built against; decomposition uses the **data file's** dimensions at
read time. Source windows are per MPI rank (`:1215-1226`) from `MINVAL`/`MAXVAL` of that rank's
indices; `recn` is clamped against `ddims` at `:1402-1403`, so a subset source truncates rather than
aborting cleanly. **Download forcing on the grid the weights were built for.**

**NEMO reads only `src01..04` (`:1196`) and `wgt01..04` (`:1206`); `dst0k` is never read.** Entry
(j,i) applies to destination cell (j,i) — why a compacted weights file misaligns the whole domain.

Cache is **keyed by filename** (`fldread.F90:1078-1080`). `cn_dir` prepends to the data root, the
weights filename and the LSM name.

### Vector rotation

`fld_rot` pairs off `vcomp(1:1)=='U'` (`fldread.F90:730-736`); geographic E/N components are rotated
onto the model i/j frame at read time — **no offline rotation needed**.

```fortran
! fldread.F90:750-751
CALL rot_rep( dta_u(:,:,jk), dta_v(:,:,jk), 'T', 'en->i', utmp(:,:) )
```

Grid point **hardcoded to `'T'`**. `ssu_m`/`ssv_m` are assigned with no staggering interpolation
(`sbcssm.F90:109-110`), leaving a half-cell offset that **scales with grid spacing** (~47 km at
ORCA2, ~5.9 km at ORCA025, ~1.5 km at GLOB16) — a genuine resolution-dependent effect when
interpreting the ocean-drag term at coarse resolution.

### `ln_rst_list` does not advance under SAS

`rst_opn` sets `nrst_lst = 1` and `nitrst = nn_stocklist(1)` once at `nit000`
(`OCE/IOM/restart.F90:83-85`). `nrst_lst` is incremented only at `restart.F90:209`, inside
`rst_write`, reached from the ocean stepping path and **never from `SAS/step.F90`**. So `nitrst`
stays pinned at the first entry and **exactly one restart point is ever written**, regardless of how
many `nn_stocklist` values are supplied. Confirmed empirically: all four production runs produced
restarts at step 1344 only.

- **Single-submission members: immaterial** — no resume required, restarts deleted after the run.
- **GLOB16: blocking** — set `ln_rst_list = .false.`, which makes `nitrst = nitend`
  (`restart.F90:87`).

### Other

- **Monthly-split forcing files must contain the COMPLETE calendar month.** `fldread.F90:869` computes
  record count from month length, never from the file. A partial monthly file maps record N to day N
  — silent date offset, no warning. NEMO never reads the netCDF time coordinate for forcing.
- **Dimension arithmetic** (`iom.F90:1280-1283`): forcing `time` must be UNLIMITED; forcing `depth`
  must be squeezed; initial conditions must have **no** singleton `time`.
- **Restart naming:** `cn_*rst_in` takes the **bare root** — `iom_open` appends `_<rank>.nc`. The
  four-digit suffix is the MPI rank, not a date.
- **`sn_*` root must NOT end in `_`** — NEMO supplies the `_y` itself (`fldread.F90:1600-1601`); a
  trailing underscore gives a double underscore → file not found → field silently zero.
- **Blind-weights rule:** with no `nn_lsm`, every source cell a stencil can reach must hold a finite
  value. Verify NaN = 0 on the file itself.
- **`stp_ctl` NaN at kt=1 is the INITIAL CONDITION**, not the forcing.
- **`cn_domcfg` absent** → NEMO silently builds an idealised GYRE domain.
- **Two `sbcssm.F90` files exist**; `makenemo` links SAS last, so the SAS version wins. All line
  references above are to `src/SAS/sbcssm.F90`.
- **`utau`/`vtau` are dead under SAS** (only `dynatf_qco.F90`, never called by `SAS/step.F90`).
- **`wndm` vs `wspd`:** the variable is `wndm`, the field id is `wspd` (`sbcmod.F90:636`).

### Operational (environment, not NEMO)

- **`set -u` + `source ~/.bashrc` in a SLURM script fails instantly.** Sourcing `env_nemo.sh` is safe.
- **SCRIP and NEMO require the module-provided netCDF**, not conda's — an active conda environment
  gives `error while loading shared libraries: libnetcdff.so.7`.
- **XIOS XML comments must not contain `--`.**
- **Python stdout is block-buffered when redirected** — use `python -u`.
- **`!` inside double quotes triggers bash history expansion** — single-quote `grep` patterns.
- **scp must be pulled from the laptop** using `hex.uct.ac.za` as source host.
- **`ocean.output`, `time.step`, `layout.dat` are overwritten by every run in the directory.**

## Analysis inputs

Per member: `~/Data/NEMO/SEAICE_DYN_003_v1/<GRID>/` (v1) or `~/Data/NEMO/SEAICE_DYN_003_v2/<GRID>/`
(v2) — 31 output files plus the **trimmed** `domain_cfg_<GRID>_ANT40S.nc` (v2 also carries the run
records).

| Stream | Freq | Records | Variables |
|---|---|---|---|
| `_icemod` | 3 h | 1 824 | v1: `siconc`, `sithic`, `sivelu`, `sivelv`, `utau_ai`, `vtau_ai`, `utau_oi`, `vtau_oi`; v2: + 21 fields (§XIOS output) |
| `_sbcwind` | 3 h | 1 824 | `utau_oce`, `vtau_oce`, `wspd` |
| `_grid_T` | 1 d | 228 | `ssu_m`, `ssv_m`, `sst_m`, `sss_m`, `ssh_m` |
| `_SBC_scalar` | 1 mo | 7 | 10 ice-budget scalars (**Southern Hemisphere only**) |
| `domain_cfg.nc` | static | — | `e1t`, `e2t`, `top_level`, `bottom_level`, `glamt`, `gphit`, `nav_lon`, `nav_lat`; also the U/V/F metrics and positions (`e1u`, `e2u`, `e1v`, `e2v`, `e1f`, `e2f`, `glamu/v/f`, `gphiu/v/f`, `ff_f`, `ff_t`) |

**Field → diagnostic mapping:**

- Lagrangian seeding / drift: `sivelu`, `sivelv` (model i/j frame). **Values are on the native
  C-grid U and V points, not T points.** `icewri.F90:134-135` writes the raw `u_ice`/`v_ice` arrays
  without interpolation; `field_def_nemo-ice.xml` only *labels* them `grid_T_2D`, so the files carry
  T-point `nav_lon`/`nav_lat`. Confirmed in ORCA2 output: every ice-covered T cell with land to its
  east has `sivelu = 0` (U-point land mask). Position them with `glamu`/`gphiu` and
  `glamv`/`gphiv` from `domain_cfg`, and compute divergence (T) and vorticity (F) with the C-grid
  metrics (`e1u`, `e2v`, `e1f`, `e2f`, …). The rheology force-balance terms (`intstrx`, `corstrx`,
  `dssh_dx`, …) are likewise U/V-point arrays.
- Relative-velocity decomposition: `sivelu`/`sivelv` minus `ssu_m`/`ssv_m`. The prescribed ocean
  fields are post-interpolation, post-rotation, time-interpolated and land-masked — what the ice
  actually felt. They differ between members despite an identical source, because the interpolation
  differs; that is part of what the comparison measures.
- Turning angle, stress-based (physically causal): ice velocity vs `utau_ai`/`vtau_ai`.
- Turning angle, wind-based (Nansen, observationally comparable): ice velocity vs
  `utau_oce`/`vtau_oce`. The difference between the two is itself a diagnostic.
- Magnitude ratio: `|u_ice| / wspd`.

**Cross-member analysis.** Velocities are on each member's own curvilinear grid in its own i/j frame.
Comparing drift requires regridding to a common target or working in geographic coordinates — via
`glamu/gphiu` and `glamv/gphiv` for velocities and force terms (not the T-point `nav_lon`/`nav_lat`
the files carry), and rotating i/j components to east/north. Seeding positions must be identical across members for trajectory comparison to
mean anything — **seeding in geographic coordinates and letting each member interpolate is the
cleaner choice.**

**Hemisphere masking is not needed** — the domain is already Southern-Hemisphere-only, so a `lat < 0`
filter carried over from a global configuration is redundant, and its absence is correct by
construction.

**Cross-member drift diagnostics are interpretable for ORCA1, ORCA05 and ORCA025.** ORCA2 is a
resolution-floor endpoint, not a fourth point on a convergence curve.

## GLOB16: special conditions

GLOB16 (5760 × 1179 × 98 trimmed, 6 791 040 grid points, 13.3× ORCA025) cannot use the common recipe
unchanged. Each departure must be recorded as a caveat on any GLOB16 result.

### 1. Timestep must be reduced

At 1.40 km minimum spacing and the measured peak of 1.85 m/s, the CFL limit is ~757 s. **`rn_Dt = 900`
is inadmissible** — margin 0.84×, below unity.

| `rn_Dt` | Margin @1.85 m/s | `nn_itend` for 228 d | Steps/day | `MOD(rday, rDt_ice) = 0`? |
|---|---|---|---|---|
| 900 s | 0.84× | 21 888 | 96 | yes — **but unstable** |
| 600 s | 1.26× | 32 832 | 144 | yes |
| 450 s | 1.68× | 43 776 | 192 | yes |
| 300 s | 2.52× | 65 664 | 288 | yes |

Choice pending. Two considerations pull opposite ways: measured peaks are 3-hourly means, so
instantaneous peaks are higher and argue for more margin than the table shows; and wall clock scales
linearly with step count, so halving the timestep doubles an already long run.

**This breaks timestep uniformity across the hierarchy.** GLOB16 results carry an explicit caveat
that `rn_Dt` differs from the four ORCA members, making timestep a covariate between GLOB16 and the
rest. A two-timestep sensitivity test at ORCA025 would bound that covariate and is the recommended
way to quantify the caveat; not needed for the ORCA members themselves, which share a timestep.

### 2. Storage — segmentation is mandatory

- **Volume:** output scales linearly with grid points (v1: 0.65 GB at 7 920 points → 41 GB at
  509 760). GLOB16 (6 791 040 points) projects to ~545 GB for v1 fields and **~1.5 TB for v2**,
  independent of timestep (output frequency is in model time); ~300–500 GB if compressed offline.
- **Against the quota:** far beyond the 250 GB scratch quota, of which inputs already take
  ~110 GB (Oct 2026; ERA5 89 GB and GLORYS12 20 GB). No scheduling arrangement makes it fit. The
  GLOB16 trimmed domain and weights were lost on 30 Oct and must be rebuilt first (§Directory layout).
- **Consequence:** GLOB16 must run in segments with an archive cycle — run a segment, verify,
  transfer off the cluster, delete, continue — stopping gracefully at a measured free-space threshold
  rather than at a full filesystem. Each segment needs room for its output plus two restarts
  (§3). All ORCA output must be cleared from scratch first.
- **Undecided:** the segment driver and where GLOB16 output is stored.

### 3. Restarts — `ln_rst_list` must be turned off

Each segment resumes from the previous segment's restart, and `ln_rst_list = .true.` writes only
the first stocklist entry under SAS. **Set `ln_rst_list = .false.`** — `restart.F90:87` then sets
`nitrst = nitend`, writing exactly one restart at each segment end, which is what the next segment consumes.

- **MPI rank count identical across all segments** — restarts are per-rank.
- **`nn_it000` must be continuous.** Under `nn_rstctl = 2` NEMO checks against the restart and aborts
  on mismatch, so the segment table is self-validating.
- **Never delete a restart until the next segment has read it** — the one irreversible mistake
  available here.
- **Verify the restart chain at the first segment boundary:** mean ice speed at the start of segment 2
  within ~1% of the end of segment 1, not back near a from-rest value, with record centring exactly
  adjacent and no gap or overlap.
- Restart volume at GLOB16 is substantial (~49 GB per point, scaling from measured members, dominated
  by the Prather moments) and must be counted in the free-space threshold.

### 4. Launch mechanics may need modification

- **Rank count and XIOS servers.** The floor of 2 servers was sized for ~39 clients at ORCA025; more
  are likely needed at GLOB16's volume. Set in `iodef.xml` and the `nemo_mpmd.conf` rank ranges,
  which `setup_production.sh` generates from the compute rank count.
- **Multi-node is currently blocked** — a deadlock at `dia_mlr_init` during XIOS context setup,
  producing zero-byte `.err` files. Documented upstream fix is `transport_protocol = p2p` in
  `iodef.xml` (XIOS3 r2793 has the feature); untested here. Must be resolved first if single-node
  proves insufficient.
- **Single-node memory looks feasible but is unconfirmed.** MaxRSS (v1: 14 → 14 → 39 → 43 GB; v2
  ORCA05 37 GB) is dominated by NEMO ranks, not XIOS, so v2's extra fields add little. GLOB16 is
  13.3× ORCA025, well beyond the measured range, against a 300 GB effective step ceiling;
  `srun --mem=0` is mandatory. Record MaxRSS from the first segment before committing to the full
  sequence.
- **`nn_nevp` is open.** β is roughly 4× ORCA025's, so ~2000 iterations would match ORCA025's
  convergence; the template's 500 is a placeholder until decided.
- **Set an explicit `--time`.** With no partition cap and a known deadlock mode, an unbounded job that
  hangs consumes the allocation indefinitely and blocks other work under `GrpTRES cpu=200`. Roughly
  2× the estimate as a dead-man switch; costs nothing on normal completion.

### 5. Verification — unchanged in kind, changed in parameters

Both scripts apply as they stand, but `nn_itend` and expected record counts change with the chosen
timestep, and the restart check should be run with expected restart points supplied once
`ln_rst_list = .false.` makes them predictable.

## Scripts

| Script | Location | Purpose |
|---|---|---|
| `audit_domain_cfg.py` | `inputs/domain_cfgs/` | Read-only audit of source domain files: dimensions, periodicity storage, config identity, cavity cells, grid spacing, latitude extents |
| `trim_domain_cfg.py` | `inputs/domain_cfgs/` | Trim to 40°S, correct metadata, apply the northern wall, verify from disk |
| `build_weights.py` | `inputs/domain_cfgs/` | Drive SCRIP per target × source; `--verify-only` checks a built set |
| `expand_weights.py` | `inputs/domain_cfgs/` | Rewrite a compacted SCRIP weights file into positional form; `--verify-only` checks positionality, wet-cell coverage, read-box span |
| `setup_production.sh` | `experiments/SEAICE_DYN_003/` | Generate all five member run directories from `common/` |
| `submit_run.sh` | generated, per member | Dry run and sbatch script for one member |
| `verify_logs.sh` | `.../VALIDATION/` | Post-run log, accounting, launcher, restart and inventory checks |
| `verify_production.py` | `.../VALIDATION/` | Post-run netCDF integrity, physical-range, scalar-table, peak-speed checks |
| `setup_t0_equivalence.sh` | `experiments/SEAICE_DYN_003/` | Build the Gate T0 global/trimmed run pair |
| `compare_t0_equivalence.py` | `.../VALIDATION/T0_trim_equivalence/` | Gate T0 field comparison |
| `make_glorys_sas_download.py`, `make_glorys_sas_preprocess.py` | `inputs/GLORYS12/` | GLORYS surface forcing: download and drown |
| `make_glorys_ice_ic_002.py` | `inputs/GLORYS12/` | Ice initial condition (zero-fill, **not** drowned) |
| `make_era5_{download,deaccumulate,unlimited,symlinks}_002.py` | `inputs/ERA5/` | ERA5 atmosphere pipeline |
| `make_domain_cfg.exe` (`tools/DOMAINcfg`) | `inputs/domain_cfgs/ORCA05_build/` | Build ORCA05 from eORCA05 coordinates and bathymetry |

*The `_002` and `forcing_002` tokens are historical naming only — these are the current, working
products for this experiment.*

## Scientific caveats

To be carried into any write-up. Each is argued in full in the section named.

- **ORCA2 is below the resolution floor** (§Results) — 5.9 m mean thickness against ~1.1 m, 57% of
  their area. An informative endpoint, not a fourth point on a convergence curve.
- **GLOB16 is not a fifth rung of the ladder.** ORCA2 → ORCA1 → ORCA05 → ORCA025 is a clean ×2
  sequence in one grid family; GLOB16 is ×4 from ORCA025 and from a different family (CMCC
  forecasting). An extension member.
- **GLOB16 runs at a different `rn_Dt`** (§Timestep) — timestep is a covariate between it and the
  rest, driven by stability and resource constraints rather than choice.
- **Bathymetry lineage is undocumented** for ORCA1, ORCA025 and GLOB16 (received as finished files);
  ORCA05's is documented but IGE/CNRS, different again from CMCC's three. All five are cavity-free,
  closing the sharpest version of the risk, but a coastline difference driven by *provenance* rather
  than *resolution* cannot be separated post hoc.
- **ORCA05 is eORCA-derived**, the only such member, extending beyond the GLORYS −80.0° limit — hence
  the weights post-processing (§Weights). No ocean information is lost, but the asymmetry belongs in
  the record.
- **Northernmost wet latitudes differ by ~3°** (−40.13° to −43.21°), driven by ORCA2's coarse rows.
  Physically irrelevant; recorded for completeness.
- **`rn_ishlat = 2.` has a resolution-dependent *effect*** — the coastal boundary layer spans fewer
  cells at coarse resolution. Part of the resolution signal rather than a confound, but worth
  discussing; a free-slip test at one resolution would bound it.
- **Landfast ice is off** — masks unavailable. Landfast parameterisation is strongly
  resolution-sensitive, so enabling it at some members only would be a serious confound.
- **ERA5 held at 0.25° for every member** — a stated limit on what "resolved drift" can mean at the
  finest resolutions.
- **The half-cell staggering offset in `ssu_m`/`ssv_m`** scales with grid spacing (~47 km at ORCA2 to
  ~1.5 km at GLOB16) — relevant when interpreting the ocean-drag term at coarse resolution.
- **`ln_ice_embd = .false.`** (levitating ice) — chosen for cold-start robustness; worth re-examining
  for an ocean-stress diagnostic.
- **Domain integrals are Southern-Hemisphere quantities**, not comparable with any global-domain
  figure.
- **aEVP is not fully converged everywhere** (§`namelist_ice_cfg`). At `nn_nevp = 500` a small,
  resolution-dependent tail of compact low-deformation ice (largest at ORCA025) has β > `nn_nevp`;
  documented per cell by `beta_evp`, which should be used to mask or flag cells before attributing a
  deformation or vorticity misfit.
