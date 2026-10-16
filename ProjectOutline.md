# SIDUS — Project context for RO2 and RO3 (workspace reference)

**Terminology used throughout**
- RO = Research Objective; WP = Work Package.
- *Advective* terms = the dynamic contributions to sea-ice concentration change
  (advection and divergence by ice drift).
- *Non-advective* terms = thermodynamic growth and melt, plus mechanical
  redistribution of ice area by ridging.
- MIZ = marginal ice zone.
- NEMO-SI³ = Nucleus for European Modelling of the Ocean, Sea Ice modelling
  Integrated Initiative (the sea-ice component).
- ERA5 = ECMWF Reanalysis v5 (atmospheric reanalysis, hourly).
- GLORYS12 = Global Ocean Reanalysis and Simulation at 1/12° (ocean reanalysis, daily).
- GLOB16 = the 1/16° model domain used as the finest hierarchy member.
- Antarctica InSync = international coordinated Antarctic field programme;
  Theme 2 is the relevant planning stream for RO3.

---

## 1. Problem outline

### 1.1 Dynamics versus thermodynamics in sea-ice change

Interpreting sea-ice variability requires separating **dynamics** (transport and
rearrangement of ice) from **thermodynamics** (growth and melt). At monthly-to-decadal
scales, wind-driven dynamics dominate observed change in some Antarctic sectors while
thermodynamics dominates in others. At **sub-daily timescales** — where synoptic
weather forcing acts and the ice responds — this balance is largely unstudied, because
of observational constraints and because sea-ice model fidelity at those scales is
unclear.

The local budget of sea-ice areal fraction (concentration) *A* under drift field **u**:

```
∂A/∂t = −u·∇A − A(∇·u) + Θ            (Eq. 1)
```

- `−u·∇A` : advection of concentration by ice drift (dynamic).
- `−A(∇·u)` : divergence/convergence of the drift field (dynamic).
- `Θ` : all non-advective tendencies — thermodynamic growth and melt, and mechanical
  redistribution of area by ridging where ice converges.

Different balances of these terms can produce the *same* change in ice coverage.
Distinguishing them is therefore necessary both to attribute observed change and to
judge whether a model reproduces it for the right reasons.

### 1.2 Why vorticity matters and why it is untested

The divergence in Eq. 1 is one component of the velocity-gradient tensor, which
decomposes as:

```
∇u = ε̇ + Ω                            (Eq. 2)
```

- `ε̇` : symmetric rate-of-deformation tensor — carries **divergence** and **shear**.
- `Ω` : antisymmetric spin tensor — carries **vorticity** (rotation).

Neither term changes *A* directly; they structure the drift field through which the
dynamic terms of Eq. 1 act.

Key asymmetry in how models treat them:

| Quantity | Status in a continuum sea-ice model |
|---|---|
| Divergence, shear (`ε̇`) | Governed **directly** by the rheology: internal stresses are computed from `ε̇` and the ice state alone. Calibrated against observations. |
| Vorticity (`Ω`) | **Deliberately excluded** from the rheology (ice rotating without deforming builds no internal stress). Simulated vorticity is therefore an **emergent** property of the full momentum balance. |

Consequences:
1. Simulated vorticity has never been calibrated or evaluated against observations,
   so its fidelity is unknown.
2. Because it emerges jointly from wind stress, ocean stress, drag formulation,
   internal stress and their numerical treatment, a departure from observations does
   **not by itself** identify which term is responsible. Any vorticity misfit must be
   tested against those resolvable terms before a physical interpretation is claimed.

### 1.3 The continuum assumption and resolution

Sea-ice models represent the ice field as a **continuum**, with rheologies developed
and calibrated at resolutions far coarser than the scales at which real ice deformation
localises. Whether that representation stays appropriate as grids refine is open.

- **Arctic**: intercomparisons have evaluated simulated deformation scaling and
  localised kinematic features against satellite observations, including rheologies
  built for small-scale deformation. But those evaluations carry **no per-retrieval
  observational uncertainty**, so observation–model disagreement cannot be separated
  from retrieval error.
- **Antarctic**: the gap is wider. No study has combined per-retrieval uncertainty,
  scale-matched satellite kinematics and a controlled model-resolution hierarchy to
  assess state consistency and process consistency together.
- Antarctic sea ice is typically thinner, younger and more heterogeneous, and can
  reorganise within a single synoptic event — a particularly stringent test of
  continuum rheologies.

### 1.4 Resulting knowledge gap

It is unknown whether a sea-ice model reproduces the observed Antarctic ice state
through the **correct balance of the terms in Eq. 1**, or at what **scales** its
continuum physics — the rheology through which **u** responds to forcing — can be
trusted.

### 1.5 Dependency on RO1 (context only)

RO1 produces per-retrieval satellite uncertainty estimates, an unconstrained-accuracy
map, and observational trajectory analysis. RO2 and RO3 consume these:
- RO2 uses the observed uncertainties to decide **which model–observation differences
  are significant**.
- RO3 uses the unconstrained-accuracy map and trajectory analysis as design inputs.
RO1's own derivation is out of scope here.

---

## 2. Research objectives in scope

### RO2 — Establish whether, and at what scales, a sea-ice model reproduces the observed Antarctic sea-ice state and advective/non-advective process balance

Approach: a **model resolution hierarchy under fixed forcing** is confronted with
observations at **matched effective scale**, testing whether the model's continuum
representation of the ice remains appropriate as the grid refines.

Two complementary tests:
- **Deformation (`ε̇`)** tests the modelled constitutive behaviour comparatively
  directly.
- **Emergent vorticity (`Ω`)** supplies an independent test of the complete dynamical
  balance, once forcing and numerical effects have been excluded.

Process test: the observed distinction between advective and non-advective
contributions to ice change is compared against the model's own process-balance
diagnostics, with RO1's observed uncertainties determining which differences are
significant.

**Success criteria**
- State consistency quantified.
- Observed process partition delivered with confidence statements.
- Model process deficiencies localised by region, season and scale.

### RO3 — Deliver a model-guided design for the independent *in situ* test of the uncertainty framework

Rationale: RO1's uncertainty estimates derive from the observing system itself.
Scarce, logistics-bound Antarctic *in situ* measurements are their only fully
independent test.

RO3 converts RO1's unconstrained-accuracy map and trajectory analysis — evaluated in a
high-resolution reference realisation taken from RO2 — into **array-geometry and
deployment-site recommendations**, deliverable mid-project within the planning cycles
of Antarctica InSync (Theme 2).

Logical loop across the project: RO1 derives the uncertainties, RO2 exploits them,
RO3 designs the measurements that would independently test them.

**Success criterion**
- Deployment-design framework and site recommendations delivered to InSync planning —
  of value to the campaign independent of the project's other outputs.

---

## 3. Implementation (methodology by work package)

### WP2 — Sea-ice state consistency and process balance across scales (RO2)

#### WP2.1 Hierarchy configuration and control simulations

- **Model**: NEMO-SI³ configured in **standalone** (sea-ice only) mode for a
  circumpolar Antarctic domain.
- **Grid hierarchy**: a hierarchy of ORCA grids forced at the atmosphere and ocean
  boundaries, with resolutions spanning **2° to 1/16°**. This runs from climate-class
  configurations, in which sea-ice kinematics are wholly parameterised, to the finest
  resolution that the forcing still informs.
  - **The 1/16° member is the GLOB16 domain, which replaces ORCA12 as the finest
    hierarchy member.**
- **Forcing**: ERA5 (hourly) constrains the atmosphere at synoptic scale; GLORYS12
  (daily) constrains the ocean at mesoscale. Forcing is held fixed across the
  hierarchy.
- **Scale bracketing**: the satellite drift retrieval's effective scale (62.5 km or
  75 km product resolutions) falls *inside* the hierarchy range, so the model is
  constrained from both the coarse and fine sides.
- **Why standalone**: deliberate — it controls the external forcing and isolates the
  sea-ice model response.
- **Numerical control experiments**: the rheology solver's convergence behaviour
  changes with grid spacing, so **solver settings are varied at fixed resolution** to
  confirm the numerical contribution is small relative to the physical signal. These
  runs are the reference for attributing (or excluding) numerical causes of misfit in
  WP2.2.

#### WP2.2 State consistency evaluation across scales

- **Variables compared**: simulated drift, concentration and derived kinematics versus
  the satellite **swath** retrievals.
- **Scale matching**: comparison at a **common effective scale**, coarsening whichever
  of observation and model is finer, so that every consistency statement is explicit
  about the scale it applies to.
- **Significance rule**:
  - differences **within** satellite retrieval uncertainty → unresolvable, no claim
    made;
  - differences **beyond** retrieval uncertainty → localise model deficiency by
    variable, region, season and scale.
- **Independent reference**: drifting-buoy trajectories give a sparse but independent
  reference against which both observations and model are judged.
- **Lagrangian analysis**: applied to observed and simulated drift at **each**
  resolution, to compare how pathways and dispersion are represented across the
  hierarchy.
- **Vorticity as a first-order diagnostic**: scaling research has concentrated almost
  entirely on `ε̇`; the rotational component is understudied and has been addressed
  directly only by the applicant's Antarctic satellite retrievals. SIDUS treats
  **vorticity as a diagnostic across the hierarchy**, assessing for the first time its
  importance relative to `ε̇` across scales.
- **Attribution sequence for a vorticity misfit** (strict order):
  1. Identify where simulated vorticity departs from observation **beyond retrieval
     uncertainty**.
  2. Test the misfit against the resolvable parts of the momentum balance — forcing,
     drag, internal-stress gradients, and their numerical treatment (from WP2.1).
  3. Only a **residual surviving those tests** would support the hypothesis that the
     classical continuum assumption omits rotational physics. That hypothesis sharpens
     as the grid refines toward the scales at which deformation localises, where the
     continuum representation is least likely to remain appropriate.

#### WP2.3 Partition confrontation, observed versus simulated

- **Observed partition**: follows the applicant's published decomposition — the
  advective terms of Eq. 1 are evaluated from retrieved drift, and the **residual
  estimates Θ**.
- **Simulated partition**: the model computes the same partition through its **native
  tendency diagnostics**, with the mechanical redistribution (ridging) tendency grouped
  with the non-advective tendencies, so that both sides partition Eq. 1 **identically**
  into advective and non-advective contributions.
- **Comparison**: the two partitions are compared integrated over **matched time
  windows and matched effective scale**.
- **Why this test is necessary**: it tests whether the model produces sea-ice change
  through the observed *balance of processes* — a test that state-level comparison
  cannot perform, because compensating errors between dynamic and thermodynamic
  processes can yield a correct state for the wrong reasons.

#### WP2.4 Synoptic response and cyclone case analysis

- The kinematic response of the ice to synoptic forcing provides the **high-signal**
  test.
- **Storm-composite** and **case-study** analysis examines whether cyclone-induced
  vorticity and deformation are reproduced by the model's rheology under
  high-frequency forcing.

---

### WP3 — Model-guided validation deployment design (RO3)

Framing: RO2's vorticity test requires independent measurement to close, and in the
Antarctic such measurement is scarce. WP3 turns that constraint into a **design
question** — where instruments should be released, and in what configuration, so that
the returned measurements could test both claims (the uncertainty framework and the
vorticity finding).

#### WP3.1 Reference realisation and regime evaluation

- **Need**: designing a deployment requires a **gap-free** field to sample from, whose
  accuracy is **known rather than assumed**.
- **Source**: the **finest member of the WP2.1 hierarchy (GLOB16, 1/16°)**, run over
  the **2022 season**, serves as WP3's **reference realisation**.
- **Why 2022**: a record-low summer with an unusually extensive and mobile marginal ice
  zone (MIZ), coincident with WP1's analysis window.
- **Evaluation**: the reference realisation is evaluated against the swath and/or daily
  retrievals, so the design inherits a documented account of **where the reference field
  is trustworthy**.
- **Stress-test regime**: the MIZ.

#### WP3.2 Provisional array-geometry optimisation

- **Constraint**: ice-tethered instruments are uncontrollable once deployed. The only
  design variables are **release location, timing and configuration**.
- **Candidate geometries**: cluster spacing, unit count, staggered release.
- **Method**: candidate geometries are evaluated by **Lagrangian release experiments in
  the reference realisation**, scored against *process constraint* — relative
  displacement between units measures **strain rate** and **rotation** directly, and
  rotation measured *in situ* is a fully independent check on RO2's vorticity finding.
- **Output**: a provisional array design plus site recommendations, delivered into
  Antarctica InSync Theme 2 planning and the South African expedition programme, where
  it can be refined against real logistics.

---

## 4. Implementation notes for the AI workspace

- **Scope**: WP2 and WP3 only. WP1 (observational uncertainty derivation) is handled
  elsewhere; treat RO1 products (per-retrieval uncertainty, unconstrained-accuracy map,
  observational trajectory analysis) as **inputs**.
- **Non-negotiable analysis conventions**:
  1. Every observation–model consistency statement must be **scale-explicit** (state
     the common effective scale used).
  2. No model deficiency may be claimed for differences **within** retrieval
     uncertainty.
  3. Both sides of the Eq. 1 partition must group ridging with non-advective terms, so
     the comparison is like-for-like.
  4. A vorticity misfit is not attributed to missing rotational physics until forcing,
     drag, internal-stress gradient and numerical explanations have been excluded.
- **Model configuration substitution**: GLOB16 (1/16°) is the finest hierarchy member
  and the WP3.1 reference realisation, replacing ORCA12 wherever the original project
  text referred to it.
