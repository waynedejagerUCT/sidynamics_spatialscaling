# Source material digest: how the satellite drift products were generated

These are the authoritative sources for product-generation details. Check them before relying on file attributes or general knowledge. Section and table numbers point into the PDFs in this folder.

- **ATBD**: *OSI-455 Algorithm Theoretical Basis Document* v1.0 (Aug 2022), SAF/OSI/CDOP3/MET/SCI/MA/417.
- **PUM**: *OSI-455 Product User Manual* v1.0 (Aug 2022), SAF/OSI/CDOP3/MET/TEC/MA/418.
- **L21**: Lavergne et al. (2021), *The Cryosphere* 15, 3681–3698, doi:10.5194/tc-15-3681-2021 (S2S).

The validation report (OSI-455 VALR, SAF/OSI/CDOP3/MET/SCI/RP/419) is cited by both OSI documents but is not held.

## OSI-455 (daily drift CDR v1, 1991–2020; held files 1990–2025, post-2020 = ICDR)

**Imagery (ATBD §2.1, §2.4; PUM §2.2)**
- Sensors: SSM/I and SSMIS use the near-90 GHz channels (13 × 14 km iFoV); AMSR-E and AMSR2 use 36.5 GHz (7 × 12 km); both polarisations in each case.
- Daily maps cover 00–24 UTC. Each is weighted by a hat function in time (W = 1 at 12 UTC, 0 at 00 and 24 UTC) to reduce motion blur. Footprints are spread over a 3 × 3 cell Gaussian neighbourhood on a 12.5 km EASE2 grid.
- A mean sensing-time map is built in the same way.
- A Laplacian filter is then applied (a 5 × 5 stencil: ring at ±1 cell minus ring at ±2). Only ice pixels enter, using the ice mask from the OSI-450/430-b SIC CDR.

**Tracking (ATBD §3; PUM §3.2.5)**
- Method: CMCC (continuous maximum cross-correlation, optimised with Nelder–Mead) on the start and end Laplacian images. The V and H polarisation correlations are summed.
- Tracking points are every 6th pixel of the 12.5 km grid, i.e. the 75 km EASE2 product grid.
- **The nominal block is about a 137.5 km diameter disk** (11 × 11 pixels minus 3 cells at each corner, 109 px). The reduced block is 62.5 km square (5 × 5), used near the coast, the ice edge or missing data (flag 20).
- **Blocks at neighbouring 75 km nodes overlap.**
- A block must lie wholly over closed ice in both the start and end masks, and contain no missing pixels.
- Search radius: v_max = 0.45 m s⁻¹ × 24 h.
- QC: each vector is compared with the mean of its 8 neighbours (neighbours with correlation < 0.5 are excluded from the mean). If it differs by more than Δmax = 10 km, it is re-optimised within 10 km of the neighbour mean (flag 21) or rejected (flag 13). Vectors with correlation < 0.3 are rejected (flag 11).

**Vectors and time (PUM §4.2, §4.6; ATBD §1.6)**
- `dX` and `dY` (km) are differences in the EASE2 grid x and y coordinates (the CF definition). EASE2 is LAEA on WGS84 (EPSG:6932); the SH grid is 144 × 144 at 75 km. `lat1`/`lon1` give the end positions.
- In the single-sensor files, `t0`/`t1` are mean sensing-time maps, typically 8–16 UTC, so durations run about 21–27 h. **In the merged (multi-oi) files we hold, `t0`/`t1` are exactly 12 UTC**: the timing mismatch is folded into the uncertainty through σ¹².
- The file time coordinate is the window end.
- Filename: `ice_drift_sh_ease2-750_cdr-v1p0[-<source>]_24h-<YYYYMMDD>1200.nc`. No source tag means multi-oi.

**Uncertainty (ATBD §3.6, §4.5, §5.3)**
- **Uncertainty is not propagated per vector.** It is a validation look-up by sensor, flag, hemisphere and season. SH winter values (km, 1σ for each of dX and dY):

  | Sensor | flag 30 | flag 20 | flag 21 |
  |---|---|---|---|
  | AMSRs | 2.8 | 5.3 | 8.3 |
  | SSM/IS | 3.6 | 6.2 | 8.7 |

- In transition months the value ramps towards 10 km.
- Timing correction when the 12 UTC approximation is used: σ¹² = 0.015 δt² − 0.005 δt + σ (δt in hours).
- Merged product: inverse-variance merge of 2–4 sensors, σ = 1.5 · (Σ σ⁻²)^−½. The merge **ignores error correlation between neighbouring vectors and between sensors**.
- Interpolated vectors (flag 22) use Gaussian weights with σ = 200 km out to 300 km, and take interpolated uncertainties.

**Seasons and wind drift (ATBD §1.6.3, §4, §5; PUM §2.3–2.4)**
- SH seasons: winter Apr–Sep (satellite only); autumn = **March** and spring = **October** (satellite and wind blended, flag 25); summer Nov–Feb (wind only).
- Wind drift is a free-drift model, u = A·U₁₀ + U_wg. A is complex: |A| is somewhat above 2% in the SH and the turning angle θ is about +20°. U_wg is a geostrophic current.
- Monthly parameter maps were fitted to AMSR-E/AMSR2 drift and ERA5 10 m wind for 2002–2020. The ERA5 wind is averaged 12–12 UTC on the 75 km grid. In winter, the wind field fills only whole missing days (flags 23 and 24).
- Validation (PUM §2.6): multi-oi RMSE about 4.0 km in the SH year-round, with a small negative bias in the SH winter at high speeds.

**Verified in the held 2019 merged files:** March and October have 0% nominal vectors (76% and 95% flag 25). April–September are 72–89% flag 30 and 4–12% flag 22.

## S2S (L21; held: AMSR2, Weddell Sea, start swaths from 13 Jul, end swaths 15–31 Jul 2019)

- The held files are the published research subset, doi:10.21343/0asd-6t60. It was chosen for its "sharp spatial gradients and rotation patterns caused by low pressure systems".
- A matching daily-map (DM) subset at 62.5 km exists, doi:10.21343/yfj4-2528. It is **not held**.
- **Processing:** the same CMCC chain as OSI SAF (both polarisations, QC that corrects outlier vectors) on AMSR2 36.5 GHz. Each swath is gridded on its own, with no daily averaging, and paired with the overlapping earlier swaths. Vectors sit on a 62.5 km polar-stereographic grid.
- **Ice mask:** OSI-430-b SIC > 40%. Sub-windows are "e.g. 11 × 11 image pixels". The image pixel size is not stated, so the S2S window size is not documented.
- **Durations:** the paper pairs each swath with all swaths in the preceding 48 h (about 100 min to 48 h). Our files contain intervals up to about 71 h; that discrepancy is unexplained.
- **Time:** start and end are swath timestamps. Per-pixel offsets in `t0`/`t1` are given relative to the swath start and end times.
- **Accuracy (SH, 24 ± 2 h, Jun–Aug 2016 Weddell buoys):**

  | | bias dX / dY (km) | RMSE dX / dY (km) |
  |---|---|---|
  | S2S | −0.04 / +0.20 | 1.36 / 1.62 |
  | DM | −0.29 / +0.46 | 2.29 / 2.91 |

- RMSE grows with duration, from about 0.5 km at 100 min to about 2 km at 52 h. The SH statistics are noisier than the NH.
- **Geolocation:** S2S is more sensitive to geolocation error than DM. With an along-track offset, the bias has a 24 h cycle. It is largest near 12 and 36 h (swaths flying in opposite directions) and smallest near 0, 24 and 48 h (parallel swaths). A weak version of this cycle is visible in the SH validation.
- **No per-vector uncertainty field.** Use the duration-dependent validation RMSE above.
- **Resolution:** the accuracy stalls once image resolution reaches about 6 km. A 31.25 km vector grid did not improve the validation statistics.

## Consequences for this project (cross-reference: PipelineDesign_ModelSatellite.md)

1. Use the OSI-455 merged product for model evaluation **in April–September only**. March and October are wind-blended.
2. An OSI-455 vector is the displacement of a ~137.5 km disk pattern (62.5 km for flag 20), smoothed further by the neighbour QC. It is not a point value. Neighbouring errors are correlated by construction, which matches the spectral evidence. A model "observation operator" should average over that disk.
3. The stated OSI-455 uncertainty is a validation look-up value, not a per-vector error, and carries no spatial covariance. Noise floors therefore need an explicit correlation model.
4. Wind-derived OSI-455 vectors (flags 23–25) are an ERA5 free-drift model, the same forcing NEMO uses. Exclude them.
5. Keep sub-daily S2S pairs, which are the point of the method; ~12 h pairs are the primary sub-daily class. Treat the duration- and geometry-dependent geolocation bias as an uncertainty term: estimate it from triplets and propagate it, rather than excluding pairs. Use the RMSE-versus-duration curve as the interim random part.
6. The single-sensor OSI-455 AMSR2 files carry true `t0`/`t1` maps, which allow exact time matching. **Held for 2019** (`OSI455/south/single_sensor/2019/<MM>/`, SH only). Checked against the held files:
   - Same 144 × 144 EASE2 grid as the merged files, and the same variables.
   - Satellite-only: no wind flags (23–25) and no interpolation (22).
   - Vectors run from 2 Apr to 1 Nov 2019.
     - April is sparse: 330–710 vectors per day, against 2000–2600 in Jul–Oct.
     - **October is fully satellite-derived** (about 90% flag 30), unlike the merged October, which is 95% flag 25. Its uncertainty is ramped up: median 8.6 km for flag 30.
     - 1 Nov carries uncertainty 100 km and is unusable.
   - Uncertainty, Apr–Sep: exactly 2.9 / 5.3 / 8.3 km for flags 30 / 20 / 21. This is the AMSR row of the ATBD look-up table; the file stores 2.9 km where the table gives 2.8.
   - Durations are 22–26.5 h (5th–95th percentile). `t0` and `t1` fall at about 8–15 UTC, at the same hour of day.
   - Compared with merged, July, nominal in both: correlation 0.97, RMS difference 2.3 km per component, bias under 0.1 km.
