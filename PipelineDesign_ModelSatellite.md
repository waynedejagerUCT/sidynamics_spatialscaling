# Model–satellite comparability pipeline: design note (draft for review)

**Status:** draft, 2026-11-11; revised 2026-11-16 to the spatial-comparability outline (native grids, cell-corner tensor, tensor-aggregated scale ladder; §7, §11). For review before any pipeline code is written. **Scope of the current revision: spatial comparability.** Temporal matching (D2) is an open decision, to be discussed next. All numbers below come from
prototype runs on v2 data (July 2019 unless stated). Product-generation facts come from the OSI-455 ATBD/PUM and Lavergne et al. (2021) (L21); see `source material/DIGEST.md`. Prototype code is in the session scratchpad, not in
the repository; it moves into the modules in §9 once the design is approved.

## 1. Constraints carried into every choice

- Each comparison is made at one stated scale, defined by box size (ProjectOutline WP2.2; convention 1). Satellite vectors are never resampled: the model is brought to each product's native nodes, and coarser scales come from aggregating the gradient tensor (D1, D4).
- Only differences beyond retrieval uncertainty are interpreted (convention 2). Uncertainty is therefore propagated through regridding, coarsening and gradients (B3, C5).
- Vorticity is a first-order diagnostic with a strict attribution order: forcing, drag, internal stress, numerics, and only then missing physics (convention 4; F1–F5).
- The run is a forced hindcast. Synoptic, wind-driven features should match in phase; features the model generates itself need not.
- Model specifics: `sivelu`/`sivelv` are 3 h means (`cell_methods = time: mean (interval: 900 s)`) at U/V points in the i/j frame. Records are selected by `time_counter_bounds`. The domain is south of 40°S. ORCA05 carries halo columns (`interior_cols`). F-points use free slip (`fmask = 0` on land). `nn_nevp = 500`.

## 2. Product inventory (inspected)

**Observation set (decided):** OSI455_merged, OSI455_single (AMSR2) and S2S. The three products differ from one another and from the model in footprint, window, timing, coverage and error structure. Those differences are part of the project's methodological design and motive, not defects for the pipeline to remove. The pipeline therefore keeps each product as a separate stream with its own metadata, and comparability decisions are made as the project evolves. Where this note proposes a treatment (D1–D5), it is a starting default, not a final resolution.

OSI455_single shares the merged grid and variables. It differs in its true per-pixel `t0`/`t1`, in being satellite-only (no flags 22–25), and in coverage (2 Apr – 1 Nov 2019, October usable). Details: `source material/DIGEST.md`, consequence 6.

| | OSI455 (CDR v1.0) | OSI-SAF S2S (AMSR2) | NEMO-SI3 v2 |
|---|---|---|---|
| Path | `OSI455/south/merged/<YYYY>/<MM>/` | `S2S/2019/07/<DD>/` (DD = end-swath day) | `SEAICE_DYN_003_v2/<MEMBER>/` |
| Grid | EASE2 LAEA (EPSG:6932, WGS84), 144 × 144, 75 km | Polar stereographic, lat_ts −70°, Hughes ellipsoid, 131 × 125 subset, 62.5 km | ORCA C-grid; median e1t at 65°S: 94 / 47 / 23 / 12 km |
| Vector | `dX`, `dY` (km) as **projected-coordinate differences** along x/y (match the projected `lat1`/`lon1` end points to < 1 m) | `driftX`, `driftY` (km) along PS x/y; no end positions (end = inverse PS of x + driftX) | `sivelu`, `sivelv` (m s⁻¹), i/j frame, U/V points |
| Window | Per-pixel `t0`/`t1`; all **12:00 → 12:00 UTC**, 24.0 h, every pixel (Mar–Oct 2019); `time` = window end. This is by construction of the merged product: the real sensing times (about 8–16 UTC) are folded into the uncertainty through σ¹² (ATBD §3.6.2). The single-sensor files carry true `t0`/`t1` maps (PUM §4.2.2). The AMSR2 single-sensor files are now held for 2019 (see `source material/DIGEST.md`, consequence 6). | Swath start/end (in file name and attributes) plus per-pixel offsets `t0`/`t1` of a few minutes; 1.6–70.9 h, roughly uniform, median 29.7 h | 3 h means; files 18th to 18th, last file 18 Oct – 1 Nov |
| Uncertainty | `uncert_dX_and_dY` (1σ, km): median 2.6, p95 6.6; nominal vectors 2.6, wind-blended 5.8. It is a **validation look-up** by sensor, flag and season (SH winter AMSR: 2.8 / 5.3 / 8.3 km for flags 30 / 20 / 21), merged with inverse variance × 1.5. It carries no spatial covariance (ATBD §3.6, §5.3) | **None in the files.** Buoy validation (L21 Table 2, SH, 24 h): RMSE 1.4 / 1.6 km (dX / dY); about 0.5 km at 100 min rising to about 2 km at 52 h (L21 Fig. 5). Triplet closure (§6) gives 0.5–0.7 km for the matching error alone (lower bound) | — |
| Flags | Valid ≥ 20. Mar–Oct 2019 valid vectors: 30 nominal 66%, 25 blended with wind 19%, 22 interpolated 6%, 20 smaller window 5%, 21 corrected 1%, 23/24 wind-filled 0.5% | 0 nominal (2% of cells); 3 land, 4 no ice, 5 coast/MIZ, 7 no image, 10–17 rejected or corrected | `siconc > 0.15`; `beta_evp` |
| Coverage | Daily, 1990–2025 (Mar–Oct 2019: 245/245 days). **Only Apr–Sep is satellite-based**: March and October 2019 are the SH transition months, with 0% nominal and 76% / 95% wind-blended vectors (ATBD §5.2.2; verified) | 8907 pairs; 276 start and 248 end swaths; each end swath is paired with 29–43 starts; median 95 nominal vectors per pair | 18 Mar – 1 Nov 2019, all members local |

Notes:
- `OSI455/south/merged/2019/` also holds a yearly aggregate file (30 Mar – 25 Dec). It is byte-identical in content to the daily files, so readers must glob `<MM>/*.nc` only.
- **About 20% of valid OSI455 vectors in Mar–Oct 2019 (flags 23–25) are wholly or partly from a wind-drift model**, almost all of them in March and October. That model is an ERA5 free-drift model, u = A·U₁₀ + U_wg, with monthly A and θ maps (ATBD §4). It shares NEMO's forcing, so these vectors must be excluded. Otherwise both the forced model and the free-drift null get credit from the wind. In practice, OSI455 comparisons cover **April–September** only.
- Each OSI455 vector is the CMCC displacement of a **~137.5 km disk pattern** (62.5 km square for flag 20), centred on 75 km nodes. Neighbouring windows overlap, and a neighbour-consistency QC (Δmax = 10 km) is applied on top (ATBD §3.2, §3.5). Errors are therefore spatially correlated by construction.
- Source documents for these facts: `source material/DIGEST.md`.
- The two products have different projections and ellipsoids but the same orientation (south-polar, lon₀ = 0). Their x/y axes therefore point the same way everywhere.
- The `dX`/`dY` values are LAEA projected lengths, not true lengths. Against displacements rebuilt from the start and end positions they differ by up to ±3.3% in magnitude and ±1.9° in direction. Because the distortion is anisotropic, about 2ε of the shear leaks into the vorticity.

## 3. C6: v2 ORCA2–ORCA05 readable (done)

The v2 ORCA2, ORCA1 and ORCA05 output is already local under `SEAICE_DYN_003_v2/`. All 35 `.nc` files per member match the HPC MD5 lists, and `load_grid`, `has_output` and `interior_cols` work for every member. v1 and `ORCA025_NEVP2000` are now on the HDD only, which matters for F6. README §Data and ROADMAP are updated to match.

## 4. Operator tests (D2)

The test fields are defined analytically on the sphere, centred at 65°S, 30°W. Truth comes from Stokes integrals on 1 km circles.

- **Route A** is the native C-grid route (`kinematics.vorticity_f`, `strain_components`).
- **Route B** is the comparison-grid route: U/V → T, then the polar frame, then a conservative box mean onto EASE2 nodes, then Green's theorem on the dual quads.
- **Route O** samples the field at the OSI455 nodes, block-averages and applies Green's theorem, as an observation would.

| Test | Route A (ORCA025 native) | Route B, L = 75 / 150 / 300 km | Route O, same L |
|---|---|---|---|
| Solid-body rotation ζ/truth | 1.0006 | 1.0009 / 1.0011 / 1.0015 | 1.0010 / 1.0012 / 1.0016 |
| Pure divergence | 0.9989 | 0.9990 / 0.9985 / 0.9975 | same to 1e-4 |
| Pure shear, pure tension | total deformation exact; shear and tension mix by the i/j-to-polar angle, as expected | 1.0002–1.0013 | same |
| Cross-talk (e.g. ζ from pure shear) | < 1e-3 | < 2e-3 | < 2e-3 |
| Gaussian vortex peak (a = 150 km) | 0.999 | 0.86 / 0.65 / 0.20 | 0.89 / 0.67 / 0.20 |
| Route B vs ideal (exact velocities, same filter) | — | ≤ 0.3% rms | — |
| Route O vs route B (point sampling vs area mean), a ≥ 150 km | — | 2–4% rms | |
| Coast (rotation field at the Weddell coast) | ζ_F correct off land; **`vorticity_t` −29% in the first coastal T row** (zeros on land F-points) | corner-node coverage ≥ 0.9: < 1%; 0.75–0.9: −3%; < 0.5: −22% to −26% | |
| ORCA05 seam | F column −1 is wrong (sign flipped, since the halo duplicates); everything inside `interior_cols` is correct | 1.000–1.003 | |

These tests predate the revised design. Route O at L = 75 km is the native-rung operator. Routes A and B remain useful as references, but the revised chain (native cell-corner tensor, then tensor aggregation) needs the extra verification listed in §11.

**Conclusions:**
1. The two routes agree to better than 0.25% on resolved fields, so method differences cannot masquerade as model–observation differences.
2. Attenuation at scale L is large: a vortex of radius a = L keeps only about 60–65% of its peak. Every magnitude must therefore be quoted "at L", and model and observations must go through the identical filter. Point sampling (O) and area means (B) differ by only 1–4%.
3. The first prototype assigned whole model cells to boxes by their centres. That gave a 1.4% bias and spurious coverage drop-outs, so any model-to-box assignment must be conservative (overlap-weighted). In the revised design this applies to the fractional S2S weights and to the optional tracking-window average (D1).

## 5. Effective resolution

The estimator is coherence and gain between datasets that share the forcing, plus spectral roll-off. All fields are daily (12:00–12:00 UTC) means from July 2019, remapped conservatively to a common EASE2 grid. λ is wavelength, and L ≈ λ/2 is the node spacing whose Nyquist wavelength is λ.

| Dataset | Evidence | Effective λ | As grid spacings |
|---|---|---|---|
| ORCA025 | KE spectrum about k⁻² down to ~100 km, then steepening to ~k⁻⁴; ORCA05 matches it to ~90 km | ~90–100 km | ~8Δx (forcing-limited?) |
| ORCA05 | vs ORCA025: coherence ≥ 0.9 and gain ≥ 0.7 for λ ≥ 90 km | ~90 km | ~4Δx |
| ORCA1 | coherence ≥ 0.5 at λ ≥ 104 km; gain ≥ 0.5 at λ ≥ 190 km | ~200 km | ~4Δx |
| ORCA2 | coherence ≤ 0.8 even at 1500 km; gain ≥ 0.5 only at λ ≥ 540 km (few segments; ice-extent mismatch) | ~500 km | ~5Δx |
| OSI455 daily | vs S2S (partly independent: same CMCC chain and AMSR2 36.5 GHz is one of the OSI455 inputs; matched 24 h windows): coherence 0.14 / 0.27 / 0.35 / 0.67 at 148 / 237 / 300 / 428 km | **a bound, not the resolution**: resolved to at least ~350–400 km; to be re-estimated | ≤ ~5Δx |
| S2S (~24 h) | vs OSI455 as above; vs ORCA025: coherence ≤ 0.1 below 240 km at every interval (3–72 h) | as for OSI455: a bound at 24 h, to be re-estimated per duration class | ≤ ~6Δx |

**The satellite figures are bounds, not resolutions.** Coherence between two products falls when *either* one's noise grows. A drop at 350–400 km therefore says only that the pair shares signal down to that wavelength. Each product on its own may resolve finer scales. The figure also mixes in temporal mismatch (merged OSI455 at nominal 12 UTC against swath-timed S2S).

**Re-estimation (planned, not yet run):**
- A three-cornered hat per wavenumber on matched windows: ORCA025, OSI455_single and S2S. With three datasets whose errors are mutually independent, the three pairwise cross-spectra separate each one's noise spectrum. Effective resolution is then the wavelength where a product's signal-to-noise ratio falls to 1.
  - OSI455_single and S2S are both AMSR2 and CMCC, so their errors may be partly correlated. That would inflate their apparent coherence, which the hat assumes away; S2S triplet closure (§6) gives an independent check on S2S noise.
  - OSI455_merged contains OSI455_single, so the two are never used as an independent pair.
- Spectral roll-off of each product against its implied white-noise level (§6), per flag class.
- The 137.5 km tracking disk and the neighbour QC (DIGEST, consequence 2) put a physical floor on OSI455's effective resolution of order 140–280 km (one to two window widths, where a disk filter's response falls to about half). The re-estimate should be consistent with that floor.

Observations against your rule of thumb (4–8Δx):
- The rule holds for the models.
- ORCA025 is no better resolved than ORCA05 above ~90 km. This is consistent with the ERA5 (0.25°) forcing setting the smallest forced scales. If so, the hierarchy gains little from refinement beyond ORCA05 in the forced part of the field. That is a result worth testing, not just a pipeline detail.
- **For daily OSI455, narrow-band coherence with S2S falls below 0.5 at about 350–400 km wavelength.** This bounds the shared signal; it is not an observational limit, and it no longer sets the finest comparison scale. The ladder starts at the native grids (D1), and significance at each rung comes from the noise floor (§6). Cell-wise vorticity at L = 150 km still correlates at r = 0.81 with ORCA025 (§6), because ζ at L integrates wavelengths of a few L.
- At 150–300 km, OSI455 carries 3–5× more power than ORCA025 but no coherence with it. Its small-scale variance is mostly retrieval error.
- For 44–72 h pairs, S2S small-scale power falls below the model's (ratio 0.6–0.9), yet coherence stays near zero. At those scales the model and observations disagree in phase, beyond what noise explains. This is a candidate finding for F1, not a pipeline artefact; model–model coherence on the same pipeline is 0.96.

## 6. Noise floors

Vorticity noise (1σ, s⁻¹) from Monte Carlo through route O, for 24 h displacement noise of 2.6 km (the OSI455 median stated σ):

| L (km) | white | correlated, L_c = 75 km | correlated, L_c = 150 km |
|---|---|---|---|
| 75 | 5.7e-7 | 3.5e-7 | 1.9e-7 |
| 150 | 1.4e-7 | 2.2e-7 | 1.6e-7 |
| 225 | 6.3e-8 | 1.4e-7 | 1.3e-7 |
| 300 | 3.4e-8 | 9.0e-8 | 1.1e-7 |
| 450 | 1.6e-8 | 4.4e-8 | 6.7e-8 |
| 600 | 0.9e-8 | 2.6e-8 | 4.1e-8 |

Divergence noise is the same. The white case matches the analytic √2 σ_u /(n L) for an n × n block, with σ_u = σ_d/T.

- **The OSI455 errors are not white at the stated σ.** At 150–300 km the observed velocity spectrum is 2–6× *below* the white-noise spectrum implied by `uncert_dX_and_dY`. The stated errors must therefore be spatially correlated (overlapping CMCC windows and neighbour filtering), or overstated at small scales. The incoherent excess over the model implies about 1 km/day white-equivalent at 150 km. Correlation slows the fall of the noise floor with L: at L = 225–300 km the floor is 2–3× the white value.
- **Signal at L** (July, daily, OSI455 flags {20, 30} against ORCA025, Eulerian 12–12 UTC, route B and route O):

  | L (km) | cells | ζ rms OSI455 | ζ rms ORCA025 | r | share \|ζ_OSI\| > 2σ, white | share, corr. 150 km |
  |---|---|---|---|---|---|---|
  | 75 | 44 912 | 7.1e-7 | 6.6e-7 | 0.55 | 11% | 50% |
  | 150 | 8 293 | 5.0e-7 | 5.0e-7 | 0.81 | 51% | 47% |
  | 225 | 2 595 | 4.3e-7 | 4.3e-7 | 0.90 | 74% | 49% |
  | 300 | 1 044 | 3.8e-7 | 3.7e-7 | 0.94 | 84% | 52% |

  Vorticity at L is dominated by wavelengths of a few L. This is why the cell-wise correlation is high even where the narrow-band velocity coherence in §5 is low. The model already matches the observed rms closely at these scales, so the free-drift null (§8) is the test that decides whether this is ice-dynamics skill or forcing skill.
- **S2S:** the triplet-closure residual d_AC − (d_AB + d_BC) gives a per-vector matching σ of 0.46 km (robust) to 0.71 km (rms). Geolocation errors cancel in the closure, so this is a lower bound. Buoy validation gives the total: SH RMSE 1.4–1.6 km at 24 h, about 2 km at 52 h (L21). Use that as the interim S2S σ. Because displacement error grows more slowly than T, a 48 h pair has a velocity noise floor about 1.5–2× lower than a 24 h pair.

**Recommendation:** propagate a correlated-error Monte Carlo with σ from the product and L_c bracketed at 75 and 150 km (L_c is an open decision, §11). Report significance under the more conservative case. When RO1 covariances arrive (B3), they replace the bracket.

**Per rung and per product route.** The Monte Carlo runs through each product's own route: native cell-corner tensor, then tensor aggregation. It gives a noise floor at every rung, including the native 62.5 km (S2S) and 75 km (OSI455) rungs. The L = 75 rows above approximate the OSI455 native rung, where noise is largest (~11–50% of cells above 2σ).

The floor serves two purposes:
- **Significance:** a cell differs significantly where |X_obs − X_model| > 2σ_X.
- **Noise-bias correction:** squared quantities are biased upward by noise, so E[X̂²] = X² + σ_X². Variances, rms and Okubo–Weiss terms are corrected by subtracting the Monte Carlo noise variance. Magnitudes (total deformation, |ζ|) are corrected statistically, on the squared quantity before the root, and never cell by cell. The correction is largest at the native rungs.

## 7. Decisions

### D1. Spatial coarsening and comparison scale

**Revised 2026-11-16. Scale is defined by box size.** This replaces the earlier recommendation of a primary L = 225 km with 150 km as the finest admissible scale.

**Physical vectors.** Every observed vector is a physical start and end point on the Earth (OSI455 `lat`/`lon` → `lat1`/`lon1`; S2S start node → inverse-projected end). No product's map projection enters the result (D3).

**Native grids, never resampled.** Each satellite product stays on its own grid: OSI455_merged and OSI455_single on 75 km EASE2, S2S on 62.5 km polar stereographic.

**Model at the product's nodes.** Each ORCA member is sampled at each product's native nodes, separately for each product. The model therefore exists once per product grid, not on one shared base grid.
- Sampling is interpolation of the polar-frame model velocity (U/V → T, D3) to the node positions. The interpolation stencil uses ocean points only; nodes whose stencil touches land are masked (D5).
- **Aliasing caveat:** point-sampling ORCA025 or ORCA05 at 62.5–75 km folds the model's sub-node variance into the native rung. The observations, by contrast, are smoothed by the tracking window. This inflates the model's native-rung variance ratio. ORCA2 (~94 km) is the opposite case: sampling at 62.5 km interpolates it, and it is flagged as resolution-limited.
- **Optional observation operator (open, §11):** before sampling, average the model over the CMCC tracking window at each OSI455 node: a 137.5 km disk, or a 62.5 km square for flag 20 (ATBD §3.2). Model and observation then share the retrieval's spatial filter. This option directly controls the aliasing above. It cannot be matched for S2S, whose image pixel size, and hence window size, is undocumented (L21 §2.3).

**The scale ladder.**

| Rung | Cells | Products | Comparisons |
|---|---|---|---|
| Native 62.5 km | S2S dual cells | S2S | model vs S2S, null vs S2S |
| Native 75 km | OSI455 dual cells | OSI455_merged, OSI455_single | model vs each product, null vs each product |
| 150 / 225 / 300 km | EASE2 boxes of 2 × 2 / 3 × 3 / 4 × 4 OSI455 cells | all | the above, plus product vs product |
| 450 / 600 km (optional, §11) | 6 × 6 / 8 × 8 | all | as above |

- The two native rungs are separate scales and are never compared with each other directly.
- Coarser rungs use the same EASE2 boxes for every product and model, so all datasets meet on identical cells.
- **Aggregate the tensor, never magnitudes** (D4). Box values are area-weighted means of the native-cell tensors. For OSI455, the cells tile the boxes exactly. S2S cells do not tile EASE2 boxes, so they enter with fractional-overlap area weights.
- **Coverage:** a box is kept if the valid native-cell area reaches a threshold (open, §11; the earlier default of 75% is the starting value). For product vs product, the threshold applies to the joint mask (D5).
- **Resolution-limited flag:** every member is run at every rung. Results below a member's effective resolution are flagged, not dropped: ORCA1 below 150 km, ORCA2 below 300 km (§5).
- Since the hierarchy comparison below the observational noise floor is model against model, it needs no observations.

### D2. Temporal matching

**Open decision, to be discussed next.** The analysis below stands as input to that discussion; its recommendation is not yet adopted.

Options: (a) the Eulerian mean of 3 h records over the window; (b) Lagrangian integration of parcels seeded at the observation start positions over the exact window.

- **Recommendation: (b) as the standard**, with (a) kept as a diagnostic.
- The measured difference for daily OSI455 windows (ORCA025, July, RK2 through the 3 h means, then box-averaged):

  | L (km) | velocity difference | ζ difference | ζ rms |
  |---|---|---|---|
  | 75 | 0.49 km/day | 6.9e-8 (10%) | 7.0e-7 |
  | 150 | 0.32 km/day | 1.6e-8 (3%) | 5.4e-7 |
  | 225 | 0.27 km/day | 9e-9 (2%) | 4.6e-7 |
  | 300 | 0.23 km/day | 6e-9 (1.5%) | 3.9e-7 |

  For daily windows at L ≥ 150 km the difference is about 10× below the noise floor, so the choice does not affect daily results. It grows roughly as T², so it matters for 48–72 h S2S pairs and for trajectories. I still recommend Lagrangian as the single standard (with the RGI implementation it takes ~1 min per day per member), which avoids two code paths.
- For S2S, overlap weighting of the 3 h records is already prototyped (weights = overlap seconds).
- **Keep the sub-daily S2S pairs.** Sub-daily resolution with exact swath timestamps is the reason for using S2S. Duration-dependent geolocation bias is a term in the uncertainty budget, not a reason to exclude pairs.
- **Primary sub-daily class: ~12 h pairs (about 8–16 h).** They resolve sub-daily motion with precise timestamps and have a large overlap area. The geolocation bias between swath pairs of the same geometry should be systematic, so it can be estimated and propagated rather than treated as random.
- Analyse each duration class (~12, ~24, ~36, ~48 h, plus shorter pairs where useful) as its own sub-product, with a duration-dependent uncertainty: the L21 RMSE curve plus a geolocation-bias term (next bullet).
- **Estimating the geolocation-bias term from the data.** In a triplet A→B→C where A and C fly in the same direction and B in the opposite one, the mean of d_AB − d_BC over many triplets is about 2 × (e_B − e_A), because the motion difference averages to zero. Here e_A and e_B are the geolocation offsets of each swath. This gives the along-track offset between ascending and descending passes. The ~12 h pair bias is then propagated through the Monte Carlo as a correlated (whole-swath) error, alongside the random matching error from triplet closure (§6).
- **Caveat on geometry:** L21 (§4.5, Fig. 8) attributes the ~12 and ~36 h separations to swaths flying in nearly opposite directions (θr ≈ 180°), where an along-track offset gives the largest drift error. Your note describes these pairs as near-orthogonal. The relative heading at each latitude can be checked from the swath geometry before the bias model is fixed.
- **Model-side limits** (not reasons to exclude): windows shorter than 3 h cannot be resolved by 3 h-mean output (the overlap weights still apply), and at 3–9 h the velocity noise floor is about 2–4× the 24 h value (L21 RMSE ≈ 0.5–1 km over a much shorter T), so statistical rather than point-by-point skill is expected there.
- Pairs beyond 52 h lie outside L21's validated range, and L21's processing stopped at 48 h. The 60–71 h pairs in our files are unexplained, so flag them and keep them out of primary results until their origin is clear.

### D3. Vector frame

Options: (a) east/north; (b) EASE2 x/y projected components; (c) the **polar grid frame**: the orthonormal physical basis aligned with the south-polar x/y axes, i.e. east/north rotated by the longitude.

- **Recommendation: (c), in physical units (m s⁻¹ or m).**
- It is a single smooth basis for averaging over boxes. Option (a) rotates 10° across a 300 km box at 75°S.
- It shares its orientation with both satellite grids.
- The rotation is exactly the longitude. The convergence angle you were worried about is only singular at the pole, which carries no ice in the Southern Hemisphere.
- Observation vectors are rebuilt from the start and end positions (OSI455 `lat1`/`lon1`; S2S end points by inverse projection), never from `dX`/`dY` directly, because of the anisotropic LAEA error in §2.
- Model: average U/V to T, then project onto the local i/j axis vectors taken from the `domain_cfg` positions (verified in §4).

### D4. Operator: cell-corner tensor, then tensor aggregation

**Agreed:** one chain and one operator, applied identically to every dataset (each product and each member sampled at that product's nodes).

**Native operator.** The cells are the dual quads formed by 2 × 2 adjacent native nodes (75 km for OSI455, 62.5 km for S2S). The tensor on each cell comes from the velocities at its four corner nodes, via Green's theorem on the sphere:
- each cell is projected gnomonically onto its own tangent plane;
- each corner vector is projected into the centre frame;
- the line integrals use trapezoidal edges.

It returns the full velocity-gradient tensor (∮u n dl), not just ζ and divergence. It works unchanged on triangles, so it also serves the parcel triangles (G6), buoy arrays (K2) and the S2S inversion product.

**Coarser scales come from aggregating the tensor.** A box value is the area-weighted mean of the native-cell tensors inside it, with fractional weights for S2S (D1). For contiguous, fully valid OSI455 cells, the interior edge integrals cancel. The aggregate then equals Green's theorem on the box boundary, up to the small per-cell tangent-plane differences; §11 checks this. Velocities are never averaged first, and magnitudes are never averaged.

**Derived quantities**, computed at each scale from the aggregated tensor ∇u = [[u_x, u_y], [v_x, v_y]] in the cell-centre polar frame:

| Quantity | Definition | Frame-invariant |
|---|---|---|
| Vorticity ζ | v_x − u_y | yes |
| Divergence δ | u_x + v_y | yes |
| Normal strain (tension) σ_n | u_x − v_y | no |
| Shear strain σ_s | u_y + v_x | no |
| Total deformation D | √(σ_n² + σ_s²); maximum shear = D/2 | yes |
| Okubo–Weiss W | σ_n² + σ_s² − ζ² (W < 0 means rotation dominates) | yes |

- σ_n and σ_s are reported in the polar frame (D3). That frame is common to every product, so components can still be compared, but only invariants enter scale-dependence statements.
- ζ and deformation are therefore derived from the same tensor at the same scale, which keeps them consistent with each other.
- Squared quantities (D², W, variances) are corrected for noise bias at each scale (§6).

The native C-grid operators stay for D6 and for the model-only hierarchy work. Do not use `vorticity_t` at coastal T cells.

### D5. Masking

**Revised 2026-11-16: one shared mask.** Model and observation are compared only where both are valid. A native cell enters only if all four corner nodes pass every test below, for the model *and* the product. A box at a coarser rung inherits the valid native-cell area and applies the coverage threshold (D1). Product-vs-product boxes use the joint mask of both products and the model.

Node-level tests:
- **Observations:** OSI455_merged flags {20, 30}, **April–September only**; 21 and 22 kept in a separate tag for sensitivity tests; 23–25 excluded. OSI455_single flags {20, 30}, April–October (October carries its ramped-up uncertainty, 1 Nov excluded); 21 tagged as for merged. S2S flag 0, which already excludes coast and MIZ (flag 5) and requires SIC > 40% (L21 §2.3).
- **Model:** `siconc > 0.15` at the node, and an interpolation stencil wholly over ocean.
- **Coast:** the four-corner rule gives at least one cell of buffer from land, matching the coverage ≥ 0.9 criterion from the coastal test (§4). Removal of coastal artefacts is verified in §11.
- No pole hole is needed in the Southern Hemisphere. Swath edges are handled by the S2S flags.
- The model is sampled only at observation-valid nodes and windows.
- `beta_evp > 500` is carried as a coverage fraction per box and used for stratification, not for masking. In July, ORCA025 cells with β > 500 cover only 0.3% of the ice area, so masking them would change nothing; the misfit is instead stratified by β coverage for F4.

## 8. Other components

- **Uncertainty (C5):** Monte Carlo of 200 draws per window with the correlated error model (§6), run through the native cell-corner tensor and the tensor aggregation, per product route and rung. Stored per cell as σ for each tensor component and derived quantity (ζ, δ, D, W), plus the noise variance used for bias correction. A cell is significant where |X_obs − X_model| > 2σ_X.
- **Free-drift null:** u = α R(θ) U₁₀.
  - Wind direction comes from `utau_oce`/`vtau_oce` (i/j, absolute wind direction) and speed from `wspd` in each member's `_sbcwind`. That is ERA5 on the model grid, so no new data are needed.
  - α and θ are fitted by complex regression against OSI455 nominal vectors in a training month (not July) or taken from the literature (α ≈ 2%, θ ≈ 20–30° to the left in the Southern Hemisphere).
  - The null runs through the same pipeline, at native ORCA025 resolution.
  - Optional variant: add the GLORYS surface current. That needs the ocean forcing files, so tell me whether they are held.
- **Comparison matrix (every rung):**
  - each ORCA member against each product;
  - product against product, at 150 km and coarser only, on the joint mask;
  - the free-drift null against each product, as the baseline.
- **Skill:**
  - **Pattern agreement (correlation) and amplitude agreement (noise-corrected variance ratio) are reported separately**, never merged into one score;
  - point by point: RMS and the significant-misfit fraction at matched windows;
  - statistical: PDFs of ζ, D, W and |ζ|/D; rms against box size (E1); and the rotation-dominated fraction (W < 0);
  - each reported per rung, member and product, with the null alongside, and with resolution-limited results flagged (D1).
- **Lagrangian:** observed trajectories from chained daily OSI455 vectors (nominal flags only), reseeded every 5 days. The accumulated error grows as about σ√n, roughly 6 km after 5 days. Model parcels are seeded at identical positions and times.
- **Intermediates:** under `~/Data/intermediate/SEAICE_DYN_003/comparison/`.
  - Level 1: per product and window, observation vectors in the polar frame, start and end times, σ, flags, mask and positions.
  - Level 2: per product, member and window, the model sampled at that product's native nodes (velocity and displacement, ice and β coverage, the window).
  - Level 3: per product, member and window, the native-cell tensor and the aggregated tensors at each rung, with valid-area fractions and Monte Carlo σ.
  - Attributes record the processing parameters, the git hash and the source files.

## 9. Module layout (proposed)

| Module | Content |
|---|---|
| `scripts/kinematics.py` (extend) | `find_record`, moved from the plot script; `records_in_window` (overlap weights); `model_axes`; `uv_to_polar` |
| `scripts/sphere_ops.py` (new) | sphere geometry, polar frame, gnomonic cells, `green_tensor` on polygons, derived invariants (ζ, δ, σ_n, σ_s, D, W) |
| `scripts/satdrift.py` (new) | readers for OSI455_merged, OSI455_single and S2S, each returning standard vectors (positions, per-pixel window, σ, flags, product tag); S2S triplet noise |
| `scripts/comparison_grid.py` (new) | native node and dual-cell definitions per product; model sampling at nodes (ocean-only stencil; optional tracking-window average); EASE2 box ladder; tensor aggregation with area and fractional-overlap weights; shared and joint masks; coverage |
| `scripts/advect.py` (new) | window-integrated Lagrangian displacement (RK2 on 3 h means); later OceanParcels for G |
| `scripts/uncertainty.py` (new) | correlated-noise Monte Carlo |
| `preprocessing/build_obs_intermediates.py` | Level 1 files, one stream per product (OSI455_merged, OSI455_single, S2S) |
| `preprocessing/build_model_intermediates.py` | Level 2 files per member and window (Lagrangian and Eulerian) |
| `preprocessing/build_free_drift.py` | null-model velocities, processed as a "member" |
| `tests/test_operators.py` | D2 tests (§4) plus the §11 verification items, as a runnable check |
| `plots/plot_comparison_testcase.py` | test-case figures (dataviz skill) |

## 10. One-month test case (after approval)

ORCA025 against OSI455_merged, OSI455_single and S2S, July 2019 (the S2S window), with:
- the native rungs plus 150, 225 and 300 km;
- temporal matching as decided in D2 (open);
- the §7 shared masks and the correlated-noise Monte Carlo;
- the free-drift null.

Outputs:
- ζ and D maps for one storm day;
- correlation and variance ratio against box size, per product;
- the significant-misfit fraction;
- PDFs of ζ, D and W;
- the rotation-dominated fraction and the β-flag share.

## 11. Verification and open decisions

**Verification that may be needed before analysis** (extends §4):
1. **Synthetic fields on the sphere:** the cell-corner operator on OSI455 and S2S dual cells reproduces the analytic tensor (rotation, divergence, shear, tension, Gaussian vortex). Route O at L = 75 km (§4) already covers most of this for OSI455.
2. **Frame and projection invariance:**
   - ζ, δ, D and W are unchanged when the same physical vectors are expressed in east/north, polar or projected frames;
   - they are unchanged whether S2S end points come from `driftX`/`driftY` via the inverse projection or from an independent reconstruction;
   - results from `dX`/`dY` differ by the expected 2ε leakage (§2), which confirms that the rebuild from end points is needed.
3. **Consistency of tensor aggregation across scales:**
   - for OSI455, the aggregated tensor equals Green's theorem on the box boundary, to the tangent-plane tolerance;
   - for S2S with fractional weights, the departure from the box-boundary integral is quantified on linear and vortex fields;
   - the aggregate of a linear field is exact at every rung.
4. **Coastal artefacts:** on a rotation field at the Weddell and Ross coasts, the shared mask (four-corner rule plus ocean-only model stencil) removes the −22% to −29% coastal bias (§4) at the native rungs and in partly covered boxes.

**Open decisions:**
- Temporal matching (D2), to be discussed next.
- Whether to apply the OSI455 tracking-window average to the model (D1).
- The coverage threshold for aggregated boxes (D1); starting value 75%.
- Whether to include the 450 and 600 km rungs.
- The error correlation length L_c (§6); currently bracketed at 75 and 150 km.
