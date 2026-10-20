#!/usr/bin/env python3
"""Offline estimate of aEVP beta from v1 output, to test whether nn_nevp suffices.
beta formula: icedyn_rhg_evp.F90:446,468 (NEMO 5.0), with zdtevp = rDt_ice (line 244).
Usage: python estimate_beta_evp.py ORCA025 201908-201909
Upward-biased (3 h mean velocities -> smaller Delta; no snow mass), so a conservative test.
Importable: delta, beta_offline and beta_from are shared with plots/; grid operators live in kinematics.py."""
import glob, os, sys
import numpy as np, xarray as xr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kinematics import DATA_ROOT, load_grid, strain_components   # C-grid operators (shared)

RHOI = 917.0                       # kg/m3            # confirmed (phycst.F90)
PSTAR, CRHG = 2.0e4, 20.0          # H79 strength     # confirmed
CREEPL, ECC = 2.0e-9, 2.0          # from tech reference
DT, NEVP = 900.0, 100              # zdtevp = rDt_ice # confirmed; NEVP = v1 value (v2: 500)
MMIN = 1.0                         # kg/m2 floor      # confirmed (zmmin)

def delta(u, v, g):
    """Rheology Delta (tension and shear scaled by 1/e**2)."""
    div, ten, s2 = strain_components(u, v, g)
    return np.sqrt(div**2 + (ten**2 + s2) / ECC**2)

def beta_offline(a, h, u, v, g):
    """Per-cell aEVP beta from one record of siconc, sithic, sivelu, sivelv (NaNs allowed)."""
    u = np.nan_to_num(u); v = np.nan_to_num(v)
    vti = np.nan_to_num(a * h)
    P = PSTAR * vti * np.exp(-CRHG * (1.0 - np.nan_to_num(a)))
    m = np.maximum(RHOI * vti, MMIN)
    return np.maximum(50.0, np.pi * np.sqrt(0.5 * P / (delta(u, v, g) + CREEPL) / g["e1e2t"] * DT / m))

def beta_from(source, ds, t, a, h, u, v, g):
    """beta for record t: "offline" from the fields above, "model" from NEMO's beta_evp (v2 _icemod only)."""
    if source == "model":
        if "beta_evp" not in ds:
            raise SystemExit("beta_evp not in this _icemod file (v1?); use the offline source")
        return ds.beta_evp[t].values.astype("f8")
    return beta_offline(a, h, u, v, g)

if __name__ == "__main__":
    member, period = sys.argv[1], sys.argv[2]
    g = load_grid(member)
    ds = xr.open_dataset(glob.glob(f"{DATA_ROOT}/{member}/*_3h_icemod_{period}.nc")[0])
    vals = []
    for t in range(ds.sizes["time_counter"]):
        a = ds.siconc[t].values.astype("f8")
        beta = beta_offline(a, ds.sithic[t].values.astype("f8"),
                            ds.sivelu[t].values.astype("f8"), ds.sivelv[t].values.astype("f8"), g)
        vals.append(beta[g["tmask"] & (np.nan_to_num(a) > 0.15)])
    b = np.concatenate(vals)

    print(f"{member} {period}: n={b.size:,} ice-cell samples")
    print("  beta percentiles 50/90/99/max:", np.percentile(b, [50, 90, 99]).round(0), round(b.max()))
    for n in (NEVP, 300, 500):
        print(f"  fraction beta > {n}: {(b > n).mean():.3%}")
