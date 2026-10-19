#!/usr/bin/env python3
"""Offline estimate of aEVP beta from v1 output, to test whether nn_nevp suffices.
beta formula: icedyn_rhg_evp.F90:446,468 (NEMO 5.0), with zdtevp = rDt_ice (line 244).
Usage: python estimate_beta_evp.py ORCA025 201908-201909
Upward-biased (3 h mean velocities -> smaller Delta; no snow mass), so a conservative test."""
import glob, sys
import numpy as np, xarray as xr

RHOI = 917.0                       # kg/m3            # confirmed (phycst.F90)
PSTAR, CRHG = 2.0e4, 20.0          # H79 strength     # confirmed
CREEPL, ECC = 2.0e-9, 2.0          # from tech reference
DT, NEVP = 900.0, 100              # zdtevp = rDt_ice # confirmed; NEVP = v1 value (v2: 500)
MMIN = 1.0                         # kg/m2 floor      # confirmed (zmmin)

member, period = sys.argv[1], sys.argv[2]
root = f"/home/waynedj/Data/NEMO/SEAICE_DYN_003/{member}"
dom = xr.open_dataset(glob.glob(f"{root}/domain_cfg_{member}_ANT40S.nc")[0]).squeeze()
g = {k: dom[k].values.astype("f8") for k in ("e1t", "e2t", "e1u", "e2u", "e1v", "e2v", "e1f", "e2f")}
tmask = dom["top_level"].values > 0
e1e2t = g["e1t"] * g["e2t"]

ip = lambda a, s: np.roll(a, s, axis=1)                    # zonally periodic shift in i
def jp(a, s):                                              # non-periodic shift in j
    out = np.zeros_like(a)
    if s > 0: out[s:] = a[:-s]
    else:     out[:s] = a[-s:]
    return out
fmask = tmask * ip(tmask, -1) * jp(tmask, -1) * jp(ip(tmask, -1), -1)

def delta(u, v):
    div = (g["e2u"] * u - ip(g["e2u"] * u, 1) + g["e1v"] * v - jp(g["e1v"] * v, 1)) / e1e2t
    ten = ((u / g["e2u"] - ip(u / g["e2u"], 1)) * g["e2t"]**2
           - (v / g["e1v"] - jp(v / g["e1v"], 1)) * g["e1t"]**2) / e1e2t
    shr = ((jp(u / g["e1u"], -1) - u / g["e1u"]) * g["e1f"]**2
           + (ip(v / g["e2v"], -1) - v / g["e2v"]) * g["e2f"]**2) / (g["e1f"] * g["e2f"]) * fmask
    s2 = 0.25 * (shr**2 + ip(shr**2, 1) + jp(shr**2, 1) + jp(ip(shr**2, 1), 1))
    return np.sqrt(div**2 + (ten**2 + s2) / ECC**2)

ds = xr.open_dataset(glob.glob(f"{root}/*_3h_icemod_{period}.nc")[0])
vals = []
for t in range(ds.sizes["time_counter"]):
    a = ds.siconc[t].values.astype("f8"); h = ds.sithic[t].values.astype("f8")
    u = np.nan_to_num(ds.sivelu[t].values.astype("f8")); v = np.nan_to_num(ds.sivelv[t].values.astype("f8"))
    vti = np.nan_to_num(a * h)
    P = PSTAR * vti * np.exp(-CRHG * (1.0 - np.nan_to_num(a)))
    m = np.maximum(RHOI * vti, MMIN)
    beta = np.maximum(50.0, np.pi * np.sqrt(0.5 * P / (delta(u, v) + CREEPL) / e1e2t * DT / m))
    vals.append(beta[tmask & (np.nan_to_num(a) > 0.15)])
b = np.concatenate(vals)

print(f"{member} {period}: n={b.size:,} ice-cell samples")
print("  beta percentiles 50/90/99/max:", np.percentile(b, [50, 90, 99]).round(0), round(b.max()))
for n in (NEVP, 300, 500):
    print(f"  fraction beta > {n}: {(b > n).mean():.3%}")
