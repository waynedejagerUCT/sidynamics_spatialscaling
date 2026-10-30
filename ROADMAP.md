# Roadmap: SEAICE_DYN_003 scale-dependent kinematics

Living document. Update task status as work completes. Scientific goals: [ProjectOutline.md](ProjectOutline.md). Model setup: [TechnicalScientificReference_SEAICE_DYN_003_v5.md](TechnicalScientificReference_SEAICE_DYN_003_v5.md).

**Last updated:** 2026-10-30

**Status key:** ✅ done · 🟡 in progress · ⬜ not started (unblocked) · ⛔ blocked (see *Blocked by*)

**Data versions**
- **v1:** ORCA2–ORCA025, 18 Mar – 31 Oct 2019, 8 `_icemod` fields. Local: `~/Data/NEMO/SEAICE_DYN_003_v1/`. ORCA2, ORCA1 and ORCA05 v1 output was moved to an external HDD on 2026-10-28 to save space; **ORCA025 v1 stays local** for A17.
- **v2:** rerun with 29 `_icemod` fields (v1 fields + partition, momentum balance, snow mass, native deformation, rheology state, `beta_evp`) and `nn_nevp = 500` (ORCA2–ORCA025; v1 used 100). ORCA2, ORCA1 and ORCA05 are on the external HDD (moved from `~/Data/NEMO/SEAICE_DYN_003_v2/` and re-verified by MD5, 2026-10-30); ORCA025 (job 1541973, completed and verified on the HPC 2026-10-30) is being transferred to `~/Data/NEMO/SEAICE_DYN_003_v2/ORCA025/`. Scripts read `DATA_ROOTS` in `scripts/kinematics.py`, which point at the local directories, so ORCA2–05 show as "not held locally" unless a root is pointed at the HDD. The old path `~/Data/NEMO/SEAICE_DYN_003/` no longer exists.
- **ORCA025 solver test (A17):** ORCA025 at `nn_nevp` = 100 (v1), 500 (v2) and 2000 (v2 configuration). ORCA025 v1 is therefore kept locally.

## Section overview

| # | Section | Status | Can start now? | Blocked by |
|---|---|---|---|---|
| A | Model reruns (WP2.1) | 🟡 | Yes | — |
| B | Observational data holdings | 🟡 | Yes | — |
| C | Shared foundations | 🟡 | Yes | — |
| D | Velocity-gradient diagnostics | 🟡 | Partly | C |
| E | Scaling with averaging scale | ⛔ | No | D |
| F | Vorticity attribution | ⛔ | No | D; A (v2) for momentum terms; A17 (ORCA025 100/500/2000) for the numerical test |
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

| Member | v1 (2019, 8 fields) | v2 config generated | v2 72-step validation | v2 production | v2 archived locally | `nn_nevp` | 2022 run |
|---|---|---|---|---|---|---|---|
| ORCA2 | ✅ local | ✅ (29 fields, `nn_nevp = 500`; regenerated for production) | ✅ | ✅ job 1502542 (55:50; 1.8 GB) | ✅ MD5-verified 2026-10-29; on external HDD (re-verified 2026-10-30) | 500 | ⛔ A10 |
| ORCA1 | ✅ local | ✅ | — (covered by ORCA2) | ✅ job 1502660 (1:28:31; 7.1 GB) | ✅ MD5-verified 2026-10-29; on external HDD (re-verified 2026-10-30) | 500 | ⛔ A10 |
| ORCA05 | ✅ local | ✅ (A7 link verified) | — (covered by ORCA2) | ✅ job 1503915 (3:36:31; 41 GB; `namelist_cfg` hand-edited, see A6) | ✅ MD5-verified 2026-10-29; on external HDD (re-verified 2026-10-30) | 500 | ⛔ A10 |
| ORCA025 | ✅ local (keep: A17 `nn_nevp = 100` member) | ✅ 2026-10-29 (`--member ORCA025` only) | — (covered by ORCA2) | ✅ job 1541973 (7:24:53; 51.0 GiB; 121 444 783 127 B; both verifications passed) | 🟡 transfer running (MD5 check pending) | 500 | ⛔ A10 |
| ORCA025 (`nn_nevp = 2000`, A17; third setting after 100 and 500) | — | ⬜ (own run directory, A17) | — (covered by ORCA2) | ⛔ ORCA025 v2 verified locally and cleared from scratch (A4) | ⛔ | 2000 | — |
| GLOB16 | ⛔ pending | ⬜ | ⛔ A3 | ⛔ A4, A11, A19 | ⛔ A5 | open (A11) | ⛔ A10, A11 (WP3 reference) |

v1 output was removed from the HPC on 2026-10-16. v1 run records are in `~/Data/NEMO/SEAICE_DYN_003_v1/SEAICE_DYN_003_runrecords.tgz`; ORCA2–05 v1 output is on an external HDD (moved 2026-10-28); ORCA025 v1 stays local. v2 ORCA2–05 were checked against HPC-made MD5 lists of every regular file in the member directory (`~/Data/NEMO/SEAICE_DYN_003_v2/v2_md5_<RES>.txt`), then moved to the external HDD and re-checked there (all OK, 2026-10-30). ORCA025's list is `/scratch/djgway001/NEMO/experiments/SEAICE_DYN_003/v2_md5_ORCA025.txt` (74 regular files: 31 output + 43 run records; `restart_files/` excluded).

### Tasks

| ID | Task | Status | Blocked by |
|---|---|---|---|
| A1 | Map required outputs to SI3 field IDs; check `iom_put` calls and grids | ✅ | — |
| A2 | Add 21 fields to `common/file_def_nemo-ice.xml` (`_icemod`, 29 total), incl. `beta_evp` (+~3.7 GB ORCA025 uncompressed) | ✅ | — |
| A3 | ORCA2 72-step validation: 29 fields present, new ones non-zero over ice; `nn_nevp = 500` read by NEMO. Run 1 (job 1501899): 24/29 ok, `NN_NEVP=500` read; ridging/rafting fields never written (A14). Run 2 (job 1502021, 1:14, rebuilt `nemo.exe`): all 29 fields written; ridging ~1e-9 s⁻¹, rafting ~0, `lead_open` zero (filled by source; plausible after 18 h; kept). Output deleted; ORCA2 regenerated with production values | ✅ | — |
| A4 | Storage: **compression deferred** (measured `nccopy -d 1 -s` 5.0× on ORCA2 validation). **HPC:** v2 output held on scratch until verified locally, then deleted (output + restarts; configs and logs kept). `quota -s` reports 0 (unusable) → measure with `du -sh /scratch/djgway001`. **2026-10-29 clean-up:** deleted the output of ORCA2, ORCA1 and ORCA05 (1.8 + 7.1 + 41 GB) after MD5-verified download, and `testing/orca2_ice_smoketest` (3.4 GB); moved `inputs/GLOB16_ANT40S/` (2.6 GB), `inputs/ORCA05_ANT40S/` (2.6 GB) and the five as-received `inputs/domain_cfgs/domain_cfg_*.nc` (5.5 GB) to local `~/Data/NEMO/hpc_offload/` → 115 of 250 GB used. **2026-10-30: `hpc_offload/` accidentally deleted (no backup).** Surviving on the external HDD: all five as-received domains (ORCA2L31, ORCA1L50, ORCA05L75, ORCA025L75, GLOB16L98) and the 40°S trimmed domains of ORCA2, ORCA1 and ORCA05 (byte sizes still to confirm against the pre-deletion sizes — full: 4 271 355 / 10 239 960 / 1 922 280 500 / 217 865 371 / 3 392 886 068 B; 40°S: ORCA2 1 051 645, ORCA1 3 159 099, ORCA05 811 562 104 B). On the HPC: 40°S domains and weights for ORCA2, ORCA1 and ORCA025 (`inputs/<GRID>_ANT40S/`), and the `domain_cfgs/` scripts, audit reports, `ORCA05_build/` and `ORCA05_weights_rebuild.log`; the ORCA025 40°S domain is also local (v1 ORCA025; v2 copy arriving). **Lost:** the GLOB16 40°S domain (`GLOB16_ANT40S/domain_cfg.nc`, 816 803 227 B) and `TRIM_LOG.txt`, the GLOB16 weights (ERA5, GLORYS SAS, GLORYS ice), and the ORCA05 weights (incl. `.work/`); rebuild in A19. The top-level `~/Data/NEMO/{GLOB16L98,ORCA025L75,ORCA1L50}_domain_cfg.nc` seen on 2026-10-29 are also gone; the full domains survive on the HDD. Only an empty `hpc_offload/ORCA05_ANT40S/weights/.work/` skeleton with two dangling symlinks into scratch remains locally (A18). **Recommended (not yet done):** copy the HPC `inputs/{ORCA2,ORCA1,ORCA025}_ANT40S/` folders (domains + weights) to the HDD, since scratch is not backed up; `ORCA025_ANT40S/` must stay on the HPC for the 2000 run. **Not trimmable:** ERA5 `raw/` (51 GB: 10u, 10v, 2t, 2d, msl) and `processed/` (38 GB: ssrd, strd, tp, sf) are both read by the model; `GLORYS12/` is 20 GB. **Scratch now (2026-10-30):** 228 of 250 GB used (~22 GB free) with ORCA025 v2 output still held; after its verified deletion, ~115 GB used / ~135 GB free, enough for the 2000 run (~121 GB output; restarts ~8 MB). **Transfers:** `djgway001@hex.uct.ac.za`, 4.4–4.8 MB/s; ORCA025 v2 (121 444 783 127 B) running with `rsync -rt --partial` (symlinks skipped), ETA ~6.8 h from 2026-10-30. **Local:** v1 ORCA025 (41 GB, A17's `nn_nevp = 100` member) and run records in `SEAICE_DYN_003_v1/`; v2 ORCA025 arriving in `SEAICE_DYN_003_v2/`; v1 and v2 ORCA2–05 on the external HDD. 147 GB free before the ORCA025 download (251 GB disk) against ~121.5 GB needed. **Structural limit:** the three A17 ORCA025 settings total ~283 GB uncompressed (41 + 121 + ~121), more than the 251 GB disk. Decide before downloading the 2000 run: lossless compression (`nccopy -d 1 -s`, ~5× measured; compress locally after the MD5 check) or HDD-based analysis | 🟡 | — |
| A5 | Decide where GLOB16 is stored (≈ 1.5 TB uncompressed v2; 250 GB scratch quota). GLOB16 inputs must be rebuilt first (A19): the trimmed domain and weights were lost with `hpc_offload/` on 2026-10-30 | ⛔ | A4 |
| A6 | Production v2 runs, cheapest first: ORCA2 → ORCA1 → ORCA05 → ORCA025 (ORCA025 ≈ 7–9 h at `nn_nevp = 500`, from ORCA05). ORCA2 ✅ 2026-10-18 (job 1502542): `verify_logs.sh` all PASS except stale validation restarts (step 72; delete); 55:50 vs v1 35:53 (1.56×) → rheology ≈ 14% of v1 runtime at ORCA2; MaxRSS 19.7 GB (v1 14.3); 1.8 GB (2.8× v1); all 29 fields written. In-model `beta_evp` max 666 (Oct), 0.0018% of ice cells > 500 — above the offline v1 estimate (max ~125), so the offline estimate may be biased **low** (better-converged v2 → lower Δ in compact ice → higher β); recheck the ORCA025 tail from its v2 `beta_evp`. ORCA1 ✅ (job 1502660): `verify_logs.sh` 0 FAIL; 1:28:31 vs v1 56:25 (1.57×, rheology ≈ 14% of v1 runtime, same as ORCA2); MaxRSS 13.2 GB; 7.1 GB; 29 fields ok; `beta_evp` Oct 99th 113 (offline v1 Sep estimate 57), max 857, 0.0004% > 500 — offline estimate again ~2× low. Revised estimates: ORCA05 ≈ 3–3.5 h, ORCA025 ≈ 6–8 h if rheology share stays ~14–20% (was 16–20 h). ORCA05 ✅ (job 1503915; 1502968 OOM-killed, A15): `verify_logs.sh` all PASS; 3:36:31 vs v1 2:01:12 (**1.79×** → rheology ≈ 20% of v1 runtime; share grows with resolution) → ORCA025 ≈ 7–9 h; MaxRSS 36.9 GB on task 0 (a NEMO rank; v1 39 GB); 41 GB, 31 files, 29 fields all written; `beta_evp`: ≤ 0.02% of ice cells > 500 in every month (max 0.020% in the Oct–Nov file), 99th 110–276, max 484–664 → **effectively fully converged at 500**; in-model and offline β agree at ORCA05 (Sep 99th 190 vs 185), so the ~2× low bias seen at ORCA2/ORCA1 does not carry over. **Hand edit:** ORCA05 `namelist_cfg` carries `nn_stocklist = 21888` only (`! DIAGNOSTIC`) — restart point only, no physics/output change (`namelist_ice_cfg`, `file_def_nemo-ice.xml` identical to ORCA1). Breaks the regenerate-don't-hand-patch rule: keep ORCA05's `namelist_cfg` as the true record (now held locally, 2026-10-29). Any ORCA05 rerun also needs `inputs/ORCA05_ANT40S/` restored (A4). `verify_production.py` passed for ORCA2, ORCA1, ORCA05 (v2); their restarts then deleted. `setup_production.sh` (modified 2026-10-19 09:36) confirmed to differ from `.bak_stepmem` only by `--mem=0` on its two `srun` lines (297 dry-run echo, 308 launch), so it is clean for generating ORCA025. `lead_open` zero over ice in every month checked (kept for consistency across members; uninformative). **Downloads (2026-10-29):** ORCA2, ORCA1 and ORCA05 v2 MD5-verified against HPC lists of every regular file: 67 files per member (31 output `.nc` + 36 run-record files: namelists, XMLs, `ocean.output`, `time.step`, `output.namelist.*`, `logs/<jobid>.*`, `xios_server_*`, timing files, `VERIFY_PRODUCTION_<RES>.txt`, `PROVENANCE.md`; the run records were missed at first and fetched separately). Each local `domain_cfg_<RES>_ANT40S.nc` is MD5-identical to the HPC `domain_cfg.nc` used in the run. No `VERIFY_LOGS_<RES>.txt` exists for v2 ORCA2–05: `verify_logs.sh` printed to the terminal only. **ORCA025 ✅ (2026-10-30):** generated with `./setup_production.sh --member ORCA025` only and checked (no broken symlinks; `ln_aEVP = .true.`, `nn_nevp = 500`, `nn_rhg_chkcvg = 0`; `cn_exp = SEAICE_DYN_003_ORCA025`, `nn_itend = 21888`, `rn_Dt = 900.`, cold start, monthly stocklist; 38 NEMO + 2 XIOS ranks; `orca025_ant40s` weights only; `split_freq = 1mo` on all four `file_def` entries; `srun --mpi=pmix --mem=0 --ntasks=40 --cpu-bind=none --multi-prog nemo_mpmd.conf` in a full-node job). `setup_production.sh`'s closing message ("~4.7 h", "run the 72-step validation first") is out of date; ignore it. Job 1541973: COMPLETED 0:0, started 2026-10-29 09:56:56, **7:24:53** (1.90× v1's 3:53:36), 1.22 s/step (v1 0.640); step MaxRSS 53 466 036 KiB = **51.0 GiB** (v1 43.3 GiB) vs the 300 GB step ceiling; rheology ≈ 22.5% of v1 runtime per 100 iterations (14% ORCA2/ORCA1, 20% ORCA05: rises with resolution). `verify_logs.sh ORCA025 1541973`: **0 FAIL**, saved with `tee` as `VERIFY_LOGS_ORCA025.txt` — `time.step` 21888, `AAAAAAAA`, no ERROR/NaN; as read by NEMO `nn_nevp = 500`, `ln_aEVP = T`, `rn_ishlat = 2`, `rDt_ice = 900`, `nn_itend = 21888`, `cn_cfg` ORCA/4, both vector pairs rotated; 38 + 2 ranks; decomposition 38 × (107 × 122), identical to v1 ORCA025 (not a confound for A17); expected non-failures only (1 W A R N I N G block, XIOS buffer/zoom_axis chatter, single restart point at step 1344 with 38 + 38 files); no stale files. `verify_production.py`, job 1543487 (sbatch wrapper `ORCA025/verify_production_ORCA025.sh`): COMPLETED 0:0, 6:07, batch MaxRSS 113.5 GiB; **0 FAIL, 2 WARN**. The wrapper wrote the report only to `logs/verify_production_1543487.out`, copied to `VERIFY_PRODUCTION_ORCA025.txt`; future wrappers should `tee` the report into the member directory. Time axes complete and contiguous (`_icemod`/`_sbcwind` 1824 × 3 h, `_grid_T` 228, `_SBC_scalar` 7); all 29 `_icemod` fields present; 0 non-finite values. WARN `sst_m` min −2.551 °C (benign, GLORYS freezing point); WARN peak ice speed 1.4927 m/s at −69.66°, 2019-04-02 10:30 (GLOB16 CFL note only; identical to v1 ORCA025). Other notes: `beta_evp` wet-cell max 6790 (ORCA05 v2 monthly max 484–664) — compute the monthly share of ice cells > 500 and the 99th percentile locally after download; `sithic` max 29.09 m (v1 28.76 m; coastal pile-up, consistent with v1); `lead_open` non-zero somewhere at ORCA025 (max 1.8e-4), unlike the other members — check whether over ice. Output: 31 files, **121 444 783 127 B** (113.1 GiB) = 2.80× v1 (43 337 903 919 B). Restarts: 7.6 MB apparent (76 files at step 1344, ~98 KB each); the earlier "~4 GB restarts" estimate was wrong. **Remaining:** transfer and local `md5sum -c` (expect all OK; 31 output files, 121 444 783 127 B; local domain MD5 `7e1b052d43f3ac473441a9551b6f485e`, 60 566 167 B, matching HPC `inputs/ORCA025_ANT40S/domain_cfg.nc`); fetch `v2_md5_ORCA025.txt` and `domain_cfg_ORCA025_ANT40S.nc`; only then delete ORCA025 output + restarts from scratch (keep configs/logs) | ✅ | — |
| A7 | ORCA05 ice-weights name: correctly spelt `weights_bilin_glorys_orca05_ant40s_ice.nc` exists in `inputs/ORCA05_ANT40S/weights/`; no misspelt file (v1 link target `weights_bilinglorys_…` likely a stale link or paste artefact). After regenerating ORCA05, confirm the link resolves (`ls -lL`). `*.compacted_BROKEN` leftovers there can be deleted. Verified 2026-10-18: regenerated ORCA05 link resolves (17.7 MB); ORCA05 v2 ran on it (job 1503915). `*.compacted_BROKEN` files deleted 2026-10-19 | ✅ | — |
| A8 | ~~Solver variant runs (`--variant`)~~ dropped as a general sweep; replaced by one targeted three-setting test at ORCA025 (A17: `nn_nevp` 100/500/2000) alongside `beta_evp` maps (F4) | ✅ superseded by A17 | — |
| A9 | `rn_relast` under aEVP: unused (standard-EVP branch only, `icedyn_rhg_evp.F90:236-238`); `nn_nevp` is an iteration count. Offline β estimate (`scripts/estimate_beta_evp.py`) → decision: keep aEVP, `nn_nevp = 500` for ORCA2–ORCA025, `nn_rhg_chkcvg = 0` | ✅ | — |
| A10 | Decide whether the full hierarchy also runs 2022 | ⬜ | — |
| A11 | GLOB16: segment driver, memory decision, and `nn_nevp` (β ≈ 4× ORCA025; ~2000 iterations for equal convergence). The A17 convergence trend (100/500/2000 at ORCA025) informs the choice. Requires the rebuilt GLOB16 inputs (A19) | ⬜ | A19 (before production) |
| A12 | Update the technical reference with v2 outputs. **2026-10-29:** status table, v2 byte totals (ORCA2–05), MD5 transfer check, local data layout, scratch clean-up, ORCA025 generation checks and submission, `verify_logs.sh` saved with `tee`, and v1/v2 ORCA025 namelist equivalence. **2026-10-30:** ORCA025 v2 run statistics, verification results and byte total; A17 resource table; `hpc_offload/` loss and the GLOB16/ORCA05 rebuild requirements. **Remaining:** the ORCA025 local MD5 result after transfer | 🟡 | ORCA025 transfer |
| A13 | Apply `nn_nevp = 500` via `common/namelist_ice_cfg.template`; regenerate ORCA2 (29 fields, `nn_nevp = 500`) | ✅ | — |
| A15 | `srun` step memory: step got only `ntasks × 8000 MB` (ORCA05: 144 GB) despite full-node job; an XIOS server needed 113 GB (v2 has ~47 output fields vs ~26) → `OUT_OF_MEMORY` (job 1502968). Fix: `srun --mpi=pmix --mem=0 …` on both `srun` lines of `setup_production.sh` (backup `.bak_stepmem`); ORCA05 cleaned, regenerated, resubmitted (job 1503875). Confirmed by ORCA05 job 1503915 (completed). Note the step receives `mem=300G` even with `--mem=0` (job holds 375 GB): **300 GB is the effective step ceiling**. Recorded in technical reference | ✅ | — |
| A16 | ORCA025 XIOS memory risk: **low.** XIOS server memory reports show 8 KB buffers per client (32 KB total at ORCA2, 64 KB ORCA1, ~96 KB ORCA05), so XIOS is not the steady-state consumer; the 113 GB in job 1502968 was an artefact of the 144 GB step cap or a start-up transient. ORCA05 v2 peaked at 36.9 GB on a NEMO rank. Expected ORCA025 peak ~45–60 GB vs the 300 GB step ceiling. No XIOS change; watch `sstat` for the first 15 min of ORCA025 | ✅ | — |
| A14 | Ridging diagnostics fix: `ll_diag_rdg` set in `ice_dyn_rdgrft_init` via `iom_use()` before XIOS closedef → always `.FALSE.`. `MY_SRC/icedyn_rdgrft.F90` sets it `.TRUE.` (diagnostics only); `nemo.exe` rebuilt 2026-10-18 12:25. Confirmed in A3 run 2; recorded in technical reference build section | ✅ | — |
| A17 | **Three-setting solver-sensitivity test at ORCA025 (WP2.1 numerical control), committed 2026-10-19.** Compare ORCA025 at `nn_nevp` = **100** (v1, held locally), **500** (v2 production, A6; ✅ job 1541973) and **2000** (new run, v2 configuration otherwise identical to the 500 run). Three settings show the convergence trend: is the 500→2000 change smaller than the 100→500 change, and does it shrink at a rate that fits ~exp(−N/β)? One pair alone can't show that. **Compare:** vorticity, deformation, the vorticity/deformation ratio, drift, concentration and thickness, binned by β. Use in-model `beta_evp` for 500 and 2000, and the offline estimate (`scripts/estimate_beta_evp.py`) for 100, since v1 has no `beta_evp` field. Comparisons that include 100 are limited to the 8 v1 fields. **Why:** `beta_evp` masking alone is weakest for vorticity. β rises as Δ falls, so rotation-dominated, low-deformation ice is the least converged, and masking it would remove the cases the vorticity test needs. Masking also misses non-local effects of unconverged stress on later ice state. This test measures the numerical sensitivity directly at the finest completed member, and informs GLOB16 `nn_nevp` (A11). **Preconditions:** (i) keep ORCA025 v1 locally even if other v1 members are replaced (A4); (ii) confirm from the run records (`SEAICE_DYN_003_runrecords.tgz` vs v2 namelists) that v1 and v2 ORCA025 differ physically only in `nn_nevp`. The v2 changes to output fields, the ridging-diagnostic source fix and `srun --mem=0` should not affect the solution. **(ii) met at namelist level, 2026-10-29:** with comments and whitespace removed, v1 and v2 ORCA025 `namelist_cfg` are identical and `namelist_ice_cfg` differs only in `nn_nevp` (100 → 500); v1 files in `~/Data/NEMO/SEAICE_DYN_003_v1/ORCA025/`. The rebuilt `nemo.exe` carries only the diagnostics-only ridging fix. **Status (2026-10-30):** the 500 run is done; 100 vs 500 is unblocked once its transfer is MD5-verified locally. The 2000 run is not yet generated. **Resources (ORCA025):** `nn_nevp` 100 — v1 job 1349225, 3:53:36, 0.640 s/step, 1.00× v1, step MaxRSS 43.3 GiB, 43 337 903 919 B; 500 — v2 job 1541973, 7:24:53, 1.22 s/step, 1.90×, 51.0 GiB, 121 444 783 127 B, restarts 7.6 MB; 2000 (projected) — ~20.5 h, ~3.4 s/step, ~5.3×, ~51 GiB, ~121 GB, restarts ~8 MB. Projection: v2 = v1 × (1 + 4r) gives r ≈ 0.225 (rheology ≈ 22.5% of v1 runtime per 100 iterations); 2000 = v1 × (1 + 19r) ≈ 20.5 h. Iteration cost is fixed because `nn_rhg_chkcvg = 0` (no early exit). The 43.3 → 51.0 GiB rise comes from v2's extra output fields, not iterations, so 2000 ≈ 51 GiB; output volume does not depend on `nn_nevp`. **2000 run plan (recommended):** full-season cold start (18 Mar – 31 Oct), identical to v2 ORCA025 except `nn_nevp`. A shorter window can't start from a v2 restart, since SAS writes only step 1344. Use its own run directory and `cn_exp` (e.g. `ORCA025_NEVP2000` / `SEAICE_DYN_003_ORCA025_NEVP2000`) so the v2 ORCA025 run records are not overwritten; do not edit `common/namelist_ice_cfg.template`. Pending: check whether `setup_production.sh` supports `--variant`; otherwise use a documented hand-copy exception. It can be generated and checked now, but submitted only after ORCA025 v2 is verified locally and cleared from scratch (A4). Local storage for all three settings exceeds the disk (A4) | 🟡 | ORCA025 v2 transfer (100 vs 500); scratch clearance (2000 run) |
| A18 | **Clean-up candidates (marked 2026-10-29; confirm with `ls`/`du` before deleting).** Rule: delete only what is neither needed for analysis nor useful for a rerun. **Local:** the empty `SEAICE_DYN_003_v1/{ORCA2,ORCA1,ORCA05}/` directories (0 B; placeholders for the external-HDD copies, removable) and the empty `SEAICE_DYN_003_v2/<RES>/restart_files/` directories (0 B). **HPC:** the `experiments/SEAICE_DYN_003/{ORCA2,ORCA1,ORCA05}/` run directories (configs, logs, symlinks; their run records are now MD5-verified locally, and a rerun regenerates the directory with `setup_production.sh`); `setup_production.sh.bak_stepmem` (superseded backup; it differs only by `--mem=0`, recorded in A15). **Keep:** all run records held locally (~6 MB per member: provenance), including v1 `ORCA025/VERIFY_LOGS_ORCA025.txt` (the only saved log check of A17's `nn_nevp = 100` member: confirms `nn_nevp = 100`, `rn_ishlat = 2`, decomposition, MaxRSS 43.3 GiB — sacct K = KiB; earlier quoted here as 45.4 GB); `inputs/` on the HPC (ERA5, GLORYS12, ORCA2/ORCA1/ORCA025 `_ANT40S/`; needed for ORCA025, the A17 2000 run and any 2022 runs); `common/`, `setup_production.sh` and `VALIDATION/` scripts. **Added 2026-10-30:** locally, the empty `~/Data/NEMO/hpc_offload/` skeleton (two dangling symlinks into scratch, no data) and the now-empty `SEAICE_DYN_003_v2/{ORCA2,ORCA1,ORCA05}/` directories (contents on the HDD); optional HPC tidy-ups `inputs/domain_cfgs/*.bak*`, `__pycache__/` and `VALIDATION/*.bak_*` — first check that the repo's `scripts/audit_domain_cfg.py` and `trim_domain_cfg.py` match the HPC versions. **Expected saving: negligible** (MB): the space is in model output and forcing, both still needed | ⬜ | — |
| A19 | **Rebuild lost GLOB16 inputs (prerequisite to A11; not urgent — GLOB16 production is scheduled much later for resource reasons).** Before the GLOB16 production run: upload GLOB16L98 from the HDD; re-run `trim_domain_cfg.py` (deterministic; expect 816 803 227 B); rebuild the weights (ERA5, GLORYS SAS, GLORYS ice) with `build_weights.py` into `inputs/GLOB16_ANT40S/`. ORCA05 weights: rebuild only if ORCA05 is ever rerun (`build_weights.py` + `expand_weights.py` + ORCA05 post-processing; see `ORCA05_weights_rebuild.log`) | ⬜ | — |

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

**Status:** 🟡 · **Runs on:** v1 data · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| C1 | NEMO reader (note: monthly files split from the run start, e.g. `_201903-201904` = 18 Mar–18 Apr, 248 records; not calendar months): C-grid positions (`glamu/v/f`, `gphiu/v/f`), masks, metrics from `domain_cfg_<RES>_ANT40S.nc`. **Done (2026-10-20, `scripts/kinematics.py`):** metrics and T/F masks (`load_grid`), one-record loader with `sivelu`/`sivelv` as native U/V (`load_record`), halo detection (`interior_cols`), and a v1/v2 data switch (`DATA_ROOTS`, `has_output`; scripts skip members not held locally). ORCA05 carries two duplicate zonal halo columns (722 = 720 + 2); ORCA2, ORCA1 and ORCA025 are exactly periodic. Record selection by `time_counter_bounds` exists only in `plots/plot_beta_vortdef_hierarchy.py` (`find_record`). **Remaining:** a shared multi-file time-series reader, and U/V positions for G1 | 🟡 | — |
| C2 | OSISAF 455 and swath readers (grids, time windows, uncertainty, flags) | ⬜ | — |
| C3 | Time matching: integrate 3 h model velocity over each satellite displacement window (24 h / swath pair) | ⬜ | C1, C2 |
| C4 | Regridding and coarsening to common effective scale (explicit scale parameter) | ⬜ | C1, C2 |
| C5 | Uncertainty propagation through coarsening and gradients | ⬜ | C2, B3 (interim OK) |

---

## D. Velocity-gradient diagnostics (divergence, shear, total deformation, vorticity)

**Status:** 🟡 · **Runs on:** v1 data (D1–D5); v2 data (D6) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| D1 | C-grid operators: divergence (T), vorticity (F), shear, total deformation. **Implemented (2026-10-20, `scripts/kinematics.py`):** divergence and tension at T; shear and ζ at F (ζ in circulation form with `e1u`, `e2v`, `e1f`, `e2f`), both averaged to T as the mean of the square (signed ζ averaging cancelled grid-scale sign changes and biased the ratio low); total deformation √(div² + ten² + shear²); \|ζ\|/total deformation (`rotation_ratio`). The rheology Δ (1/e² scaling) stays in `estimate_beta_evp.py`. **Open:** `fmask = 0` on land F-points imposes free slip, so coast-adjacent ratios are biased low; compare with SI3's `rn_ishlat` treatment in D2 | 🟡 | — |
| D2 | Synthetic-field tests (solid-body rotation, pure divergence) on trimmed ORCA grids. Also check: coastal boundary treatment (D1 open item), the ORCA05 halo seam, and whether grid-scale speckle in the ORCA05/ORCA025 pack ratio is physical or 2Δx noise | ⬜ | — (D1 implemented) |
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

**Status:** ⛔ · **Runs on:** v1 data (F1–F2); v2 data (F3–F4) · local

| ID | Task | Status | Blocked by |
|---|---|---|---|
| F0 | **v1 preview of F4 (no observations).** Offline β and \|ζ\|/total deformation across ORCA2–ORCA025. Outputs: `plots/plot_beta_vortdef_hierarchy.py` (8-panel map, 2019-09-15 12:00–15:00) and `plots/plot_beta_rotation_timeseries.py` (every 3 h record, 18 Mar – 31 Oct; cache `~/Data/intermediate/SEAICE_DYN_003/beta_rotation_ts_offline.csv`). Season means, ORCA2/1/05/025: % ice with β ≤ 100 = 100.0 / 99.7 / 97.8 / 92.8; % rotation-dominated (ratio > 1, total deformation ≥ 1e-8 s⁻¹) = 32.5 / 37.6 / 42.5 / 45.4. ORCA025 convergence falls from mid-October to ~65% (ORCA05 ~86%), as rotation dominance rises in every member. Rotation-dominated, low-deformation ice sits where β is highest, supporting A17. Offline β runs ~2× low against in-model β, so these shares are optimistic. Caveat: `estimate_beta_evp.py` statistics for ORCA05 include the two halo columns (behaviour kept unchanged); the plot scripts exclude them. Since v1 ORCA2–05 moved to an external HDD (2026-10-28), the v1 time series is reproducible only from its cache, and the v1 map now shows ORCA025 alone; v2 equivalents run with `--version v2` / `--source model` | ✅ | — |
| F1 | Step 1: locate vorticity misfits beyond retrieval uncertainty | ⛔ | D4 |
| F2 | Step 2a: test against curl of air–ice and ocean–ice stress, and ocean-current vorticity (v1 fields) | ⛔ | F1 |
| F3 | Step 2b: test against internal stress, Coriolis and tilt (`intstrx`, `corstrx`, `dssh_dx`) | ⛔ | F1, A6 |
| F4 | Step 2c: numerical contribution, using two pieces of evidence: (i) `beta_evp` maps, binning misfits by β/`nn_nevp` and flagging cells with β ≳ `nn_nevp`; (ii) the ORCA025 `nn_nevp` 100/500/2000 sequence (A17), compared with the misfit. If the misfit is larger than the 500–2000 difference and that difference is shrinking with N, numerics are excluded at ORCA025 | ⛔ | F1, A6, A17 |
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
