"""C-grid kinematics shared by scripts/ and plots/: grid loading, strain rates, vorticity, rotation ratio.
sivelu/sivelv are native U/V-point values, although the files label them as T-point fields."""
import glob
import numpy as np, xarray as xr

DATA_ROOT = "/home/waynedj/Data/NEMO/SEAICE_DYN_003"
ICE_MIN = 0.15                     # siconc threshold for ice cells
DEF_FLOOR = 1e-8                   # s-1; rotation ratio not evaluated below this total deformation

ip = lambda a, s: np.roll(a, s, axis=1)                    # zonally periodic shift in i
def jp(a, s):                                              # non-periodic shift in j
    out = np.zeros_like(a)
    if s > 0: out[s:] = a[:-s]
    else:     out[:s] = a[-s:]
    return out

def load_grid(member, root=DATA_ROOT):
    """C-grid metrics and masks from domain_cfg_<member>_ANT40S.nc."""
    dom = xr.open_dataset(glob.glob(f"{root}/{member}/domain_cfg_{member}_ANT40S.nc")[0]).squeeze()
    g = {k: dom[k].values.astype("f8") for k in ("e1t", "e2t", "e1u", "e2u", "e1v", "e2v", "e1f", "e2f")}
    g["tmask"] = dom["top_level"].values > 0
    g["fmask"] = g["tmask"] * ip(g["tmask"], -1) * jp(g["tmask"], -1) * jp(ip(g["tmask"], -1), -1)
    g["e1e2t"] = g["e1t"] * g["e2t"]
    g["dom"] = dom
    return g

def interior_cols(g):
    """T-column slice without duplicate zonal halo columns (ORCA05 carries two; the other trimmed grids none)."""
    lon = g["dom"]["glamt"].values
    return slice(1, lon.shape[1] - 1) if np.allclose(lon[:, 0], lon[:, -2]) else slice(None)

def load_record(ds, t):
    """siconc, sithic, sivelu, sivelv for record t of an _icemod dataset (velocities NaN -> 0)."""
    a, h = ds.siconc[t].values.astype("f8"), ds.sithic[t].values.astype("f8")
    u = np.nan_to_num(ds.sivelu[t].values.astype("f8"))
    v = np.nan_to_num(ds.sivelv[t].values.astype("f8"))
    return a, h, u, v

def strain_components(u, v, g):
    """Divergence and tension at T; shear at F with shear**2 averaged to T. All s-1 (s-2 for shear**2)."""
    div = (g["e2u"] * u - ip(g["e2u"] * u, 1) + g["e1v"] * v - jp(g["e1v"] * v, 1)) / g["e1e2t"]
    ten = ((u / g["e2u"] - ip(u / g["e2u"], 1)) * g["e2t"]**2
           - (v / g["e1v"] - jp(v / g["e1v"], 1)) * g["e1t"]**2) / g["e1e2t"]
    shr = ((jp(u / g["e1u"], -1) - u / g["e1u"]) * g["e1f"]**2
           + (ip(v / g["e2v"], -1) - v / g["e2v"]) * g["e2f"]**2) / (g["e1f"] * g["e2f"]) * g["fmask"]
    s2 = 0.25 * (shr**2 + ip(shr**2, 1) + jp(shr**2, 1) + jp(ip(shr**2, 1), 1))
    return div, ten, s2

def vorticity_t(u, v, g):
    """|Relative vorticity| at T-points: F-point zeta (circulation form, fmask = 0 on land), zeta**2 averaged
    F->T like shear**2 in strain_components, so grid-scale sign changes don't cancel."""
    zeta = ((ip(g["e2v"] * v, -1) - g["e2v"] * v)
            - (jp(g["e1u"] * u, -1) - g["e1u"] * u)) / (g["e1f"] * g["e2f"]) * g["fmask"]
    z2 = zeta**2
    return np.sqrt(0.25 * (z2 + ip(z2, 1) + jp(z2, 1) + jp(ip(z2, 1), 1)))

def rotation_ratio(u, v, g):
    """|zeta| / total deformation and total deformation = sqrt(div**2 + ten**2 + shear**2).
    Total deformation is not the rheology Delta (no 1/e**2)."""
    div, ten, s2 = strain_components(u, v, g)
    total_def = np.sqrt(div**2 + ten**2 + s2)
    return vorticity_t(u, v, g) / np.where(total_def > 0, total_def, np.nan), total_def
