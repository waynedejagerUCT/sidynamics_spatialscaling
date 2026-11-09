#!/usr/bin/env python3
"""Signed relative vorticity maps for the ORCA025 solver-sensitivity test (A16). Writes two figures:
1. orca025_nevp_vorticity_maps.png (3 x 3): rows = three 3 h records through spring 2019 (start of September,
   start of October, late October), columns = nn_nevp 100 (v1), 500 (v2), 2000 (v2/ORCA025_NEVP2000).
2. orca025_nevp_vorticity_diff.png (3 x 2): the same rows, columns = 100 - 2000 and 500 - 2000, with the
   less-converged run's beta contoured (offline beta for 100, NEMO beta_evp for 500).
The rows were chosen because the convergence share at nn_nevp = 500 falls from ~95% to ~79% over that span.
Vorticity is plotted on its native F-points (no averaging to T), ice only. Blue = negative (clockwise,
cyclonic in the Southern Hemisphere), red = positive; discrete colour scales symmetric about zero.
Usage: python plot_orca025_nevp_vorticity_maps.py [--times 2019-09-01T12:00 2019-10-01T12:00 2019-10-30T12:00]
Run in env010."""
import argparse, os, sys, textwrap
import numpy as np, pandas as pd, xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, HERE)
from kinematics import ICE_MIN, load_grid, interior_cols, load_record, vorticity_f, strain_components, ip, jp
from estimate_beta_evp import beta_offline
from plot_beta_vortdef_hierarchy import (find_record, mesh, add_background, style_map, panel_note,
                                         RATIO_CMAP, INK, INK2, PROJ, GEO)
from plot_orca025_nevp_timeseries import RUNS, CACHE, GRID_NAME

TIMES = ["2019-09-01T12:00", "2019-10-01T12:00", "2019-10-30T12:00"]   # each picks the 3 h record containing it
UNIT = 1e-6                        # s-1 per colour-bar unit
VORT_LIM, VORT_STEP = 5.0, 0.25    # vorticity: +-5e-6 s-1 in 0.25e-6 bins (caps the ice edge, shows the interior)
DIFF_LIM, DIFF_STEP = 0.5, 0.05    # difference vs 2000: +-0.5e-6 s-1 in 0.05e-6 bins (~99th percentile of |diff|)
REF = 2000                         # reference (best-converged) setting for the difference maps
RESIDUAL = 0.05                    # beta contour at nn_nevp / ln(1/RESIDUAL), where reachable (beta >= 50)


def discrete(lim, step):
    """Discrete diverging colour map and norm, symmetric about zero, with zero on a bin boundary."""
    levels = np.round(np.arange(-lim, lim + step / 2, step), 6)
    n = len(levels) - 1
    cols = RATIO_CMAP(np.linspace(0, 1, n + 2))
    cmap = ListedColormap(cols[1:-1]).with_extremes(under=cols[0], over=cols[-1])
    return cmap, BoundaryNorm(levels, n), levels


def f_mesh(g):
    """Projected T-point corners for F-point cells. F(j,i) sits inside T(j..j+1, i..i+1); i wraps.
    Returns corner x, y and the F-row slice they bound (ORCA025 has no duplicate halo columns)."""
    if interior_cols(g) != slice(None):
        raise SystemExit("f_mesh assumes an exactly periodic grid (no halo columns)")
    dom = g["dom"]
    lon, lat = dom["glamt"].values, dom["gphit"].values
    lon, lat = np.hstack([lon, lon[:, :1]]), np.hstack([lat, lat[:, :1]])
    xy = PROJ.transform_points(GEO, lon, lat)
    return xy[..., 0], xy[..., 1], slice(0, lon.shape[0] - 1)


def conv_share(cache, nevp, when):
    """% of ice converged to a 5% residual for the cached record nearest `when` (model beta where output)."""
    d = cache[cache.nevp == nevp]
    r = d.iloc[(d.time - when).abs().argmin()]
    src = "model" if pd.notna(r.get("n_conv_model_r05")) else "offline"
    return 100 * r[f"n_conv_{src}_r05"] / r.n_ice


def load_panel(nevp, when, g):
    """zeta at F, total deformation at T, concentration at T and F, beta at T (model where output, else
    offline), record bounds."""
    run = RUNS[nevp]
    f, t, bounds, _ = find_record(run["dir"], when, run["root"])
    with xr.open_dataset(f) as ds:
        a, h, u, v = load_record(ds, t)
        beta = ds.beta_evp[t].values.astype("f8") if "beta_evp" in ds else beta_offline(a, h, u, v, g)
        src = "NEMO beta_evp" if "beta_evp" in ds else "offline β"
    an = np.nan_to_num(a)
    a_f = 0.25 * (an + ip(an, -1) + jp(an, -1) + jp(ip(an, -1), -1))
    div, ten, s2 = strain_components(u, v, g)
    return dict(zeta=vorticity_f(u, v, g), defo=np.sqrt(div**2 + ten**2 + s2), a=an, a_f=a_f, beta=beta,
                beta_src=src, bounds=bounds)


def row_label(ax, bounds):
    t0, t1 = (str(x)[:16].replace("T", " ") for x in bounds)
    ax.text(-0.08, 0.5, f"{pd.Timestamp(t0):%-d %b %Y}\n{t0[11:]}–{t1[11:]} UTC", transform=ax.transAxes,
            rotation=90, ha="center", va="center", fontsize=12, color=INK)


def caption_text(fig, text, width):
    fig.text(0.07, 0.02, "\n".join(textwrap.wrap(text, width)), fontsize=8.8, color=INK2, va="bottom",
             linespacing=1.5)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--times", nargs=3, default=TIMES, help="three target times (rows)")
    p.add_argument("--out-dir", default=HERE)
    args = p.parse_args()
    whens = [np.datetime64(t) for t in args.times]
    cache = pd.read_csv(CACHE, parse_dates=["time"]) if os.path.exists(CACHE) else None

    g = load_grid(GRID_NAME, RUNS[100]["root"], RUNS[100]["dir"])   # the three runs share one trimmed domain
    xf, yf, xt, yt, sl = mesh(g)                                     # T-cell corners and T centres
    xc, yc, fsl = f_mesh(g)
    fmask = g["fmask"].astype(bool)
    P = {(r, n): load_panel(n, w, g) for r, w in enumerate(whens) for n in RUNS}

    # ---- Figure 1: vorticity, 3 x 3 ----
    cmap, norm, levels = discrete(VORT_LIM, VORT_STEP)
    fig, axes = plt.subplots(3, 3, figsize=(13, 14.2), subplot_kw={"projection": PROJ})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.9, bottom=0.175, wspace=0.04, hspace=0.12)
    for r in range(3):
        for k, nevp in enumerate(RUNS):
            ax, d = axes[r, k], P[r, nevp]
            ice_f = fmask & (d["a_f"] > ICE_MIN)
            add_background(ax, xf, yf, g["tmask"][sl], (g["tmask"] & (d["a"] > ICE_MIN))[sl])
            qm = ax.pcolormesh(xc, yc, np.ma.masked_array(d["zeta"] / UNIT, ~ice_f)[fsl], cmap=cmap, norm=norm,
                               transform=PROJ, rasterized=True)
            style_map(ax)
            if r == 0:
                ax.set_title(f"nn_nevp = {RUNS[nevp]['label']}", fontsize=13, color=INK, pad=8)
            if cache is not None:
                panel_note(ax, f"converged (residual ≤ 5%): {conv_share(cache, nevp, whens[r]):.1f}% of ice")
        row_label(axes[r, 0], P[r, 100]["bounds"])
    cax = fig.add_axes([0.2, 0.13, 0.6, 0.014])
    cb = fig.colorbar(qm, cax=cax, orientation="horizontal", extend="both", ticks=levels[::4])
    cb.set_label("relative vorticity ζ (10⁻⁶ s⁻¹)   ·   blue: negative, clockwise, cyclonic (SH)   ·   "
                 "red: positive, anticyclonic (SH)", color=INK, fontsize=10)
    fig.suptitle("ORCA025 sea-ice relative vorticity at nn_nevp = 100, 500 and 2000, spring 2019",
                 x=0.07, ha="left", y=0.965, fontsize=15, color=INK)
    caption_text(fig, f"ζ = ∂v/∂x − ∂u/∂y on the native F-points (circulation form with e1u, e2v, e1f, e2f), from 3 h "
                 "mean sivelu/sivelv; zero on land F-points (free slip), so coast-adjacent values are suppressed. Ice "
                 f"only: F-points whose four surrounding cells average siconc > {ICE_MIN}; dark grey land, light grey "
                 f"open water. Discrete colour scale, {VORT_STEP:g} × 10⁻⁶ s⁻¹ bins, symmetric about zero (zero is "
                 f"the blue/red boundary), capped at ±{VORT_LIM:g} × 10⁻⁶ s⁻¹ to show the pack interior; the ice "
                 "edge saturates. Convergence share from plot_orca025_nevp_timeseries.py: ice cells with aEVP residual "
                 "≤ 5% (offline β for 100, NEMO beta_evp for 500 and 2000); 0% is unreachable at nn_nevp = 100 "
                 "because β ≥ 50.", 165)
    out1 = os.path.join(args.out_dir, "orca025_nevp_vorticity_maps.png")
    fig.savefig(out1, dpi=200, facecolor="#ffffff")
    plt.close(fig)

    # ---- Figure 2: differences against 2000, 3 x 2, with beta of the less-converged run ----
    cmap, norm, levels = discrete(DIFF_LIM, DIFF_STEP)
    others = [n for n in RUNS if n != REF]
    fig, axes = plt.subplots(3, 2, figsize=(10.2, 14.2), subplot_kw={"projection": PROJ})
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.185, wspace=0.04, hspace=0.16)
    for r in range(3):
        ref = P[r, REF]
        for k, nevp in enumerate(others):
            ax, d = axes[r, k], P[r, nevp]
            ice_f = fmask & (d["a_f"] > ICE_MIN) & (ref["a_f"] > ICE_MIN)
            ice_t = g["tmask"] & (d["a"] > ICE_MIN)
            diff = d["zeta"] - ref["zeta"]
            add_background(ax, xf, yf, g["tmask"][sl], ice_t[sl])
            qm = ax.pcolormesh(xc, yc, np.ma.masked_array(diff / UNIT, ~ice_f)[fsl], cmap=cmap, norm=norm,
                               transform=PROJ, rasterized=True)
            b = np.ma.masked_array(d["beta"], ~ice_t)[sl]
            lv5 = nevp / np.log(1 / RESIDUAL)
            ax.contour(xt, yt, b, levels=[nevp], colors=INK, linewidths=0.6, transform=PROJ)
            if lv5 >= 50:
                ax.contour(xt, yt, b, levels=[lv5], colors=INK, linewidths=0.6, linestyles=[(0, (2.5, 1.5))],
                           transform=PROJ)
            style_map(ax)
            if r == 0:
                ax.set_title(f"nn_nevp {RUNS[nevp]['label']} − {RUNS[REF]['label']}", fontsize=13, color=INK, pad=8)
            rms = np.sqrt(np.mean(diff[ice_f] ** 2)) / UNIT
            rms_ref = np.sqrt(np.mean(ref["zeta"][ice_f] ** 2)) / UNIT
            bt = np.nan_to_num(d["beta"])
            beta_f = 0.25 * (bt + ip(bt, -1) + jp(bt, -1) + jp(ip(bt, -1), -1))   # beta at F
            thr = lv5 if lv5 >= 50 else nevp                                         # innermost contour drawn
            hi = ice_f & (beta_f > thr)
            rin = np.sqrt(np.mean(diff[hi] ** 2)) / UNIT if hi.any() else np.nan
            rout = np.sqrt(np.mean(diff[ice_f & ~hi] ** 2)) / UNIT
            panel_note(ax, f"RMS difference {rms:.2f} ({100 * rms / rms_ref:.0f}% of RMS ζ at {REF})\n"
                           f"β > {thr:.0f} ({100 * hi.sum() / ice_f.sum():.1f}% of ice): {rin:.2f}  ·  elsewhere: {rout:.2f}")
        row_label(axes[r, 0], P[r, REF]["bounds"])
    cax = fig.add_axes([0.15, 0.135, 0.7, 0.014])
    cb = fig.colorbar(qm, cax=cax, orientation="horizontal", extend="both", ticks=levels[::2])
    cb.set_label("ζ difference from nn_nevp = 2000 (10⁻⁶ s⁻¹)   ·   blue: more cyclonic   ·   red: more anticyclonic",
                 color=INK, fontsize=10)
    fig.legend(handles=[Line2D([], [], color=INK, lw=0.8, label="β = nn_nevp (residual e⁻¹ ≈ 37%)"),
                        Line2D([], [], color=INK, lw=0.8, ls=(0, (2.5, 1.5)),
                               label=f"β = nn_nevp / {np.log(1 / RESIDUAL):.2f} (residual {100 * RESIDUAL:.0f}%)")],
               loc="upper right", bbox_to_anchor=(0.98, 0.955), ncol=1, frameon=False, fontsize=9.5)
    fig.suptitle("ORCA025 vorticity: difference from nn_nevp = 2000", x=0.09, ha="left", y=0.965,
                 fontsize=15, color=INK)
    caption_text(fig, "Difference in F-point relative vorticity (as in orca025_nevp_vorticity_maps.png) between each "
                 "less-converged run and nn_nevp = 2000, over F-points that are ice in both runs. Discrete colour scale, "
                 f"{DIFF_STEP:g} × 10⁻⁶ s⁻¹ bins, symmetric about zero, capped at ±{DIFF_LIM:g} × 10⁻⁶ s⁻¹ (about the "
                 "99th percentile of |difference|). Contours: β of the less-converged run at T-points over ice — offline "
                 "estimate for 100 (no beta_evp output), NEMO beta_evp (3 h mean) for 500. Inside the solid line the "
                 "residual after nn_nevp iterations, ~exp(−nn_nevp/β), exceeds ~37%; inside the dashed line it "
                 f"exceeds {100 * RESIDUAL:.0f}% (not drawn for 100: β ≥ 50 everywhere, so the whole ice cover "
                 f"exceeds {100 * np.exp(-2):.1f}%). RMS values (10⁻⁶ s⁻¹) are over the same ice points, and split by β "
                 "of the less-converged run averaged to F-points: inside versus outside the innermost contour drawn "
                 "(β > 100 for 100, β > 167 for 500).", 130)
    out2 = os.path.join(args.out_dir, "orca025_nevp_vorticity_diff.png")
    fig.savefig(out2, dpi=200, facecolor="#ffffff")
    print(out1); print(out2)


if __name__ == "__main__":
    main()
