#!/usr/bin/env python3
"""Total-deformation counterpart of plot_orca025_nevp_vorticity_maps.py for the ORCA025 solver test (A17).
Writes two figures with the same rows, columns, units and bin widths as the vorticity pair, for side-by-side
comparison of how vorticity and deformation respond to nn_nevp:
1. orca025_nevp_deformation_maps.png (3 x 3): total deformation at nn_nevp 100 (v1), 500 (v2), 2000.
2. orca025_nevp_deformation_diff.png (3 x 2): 100 - 2000 and 500 - 2000, with the less-converged run's beta
   contoured (offline beta for 100, NEMO beta_evp for 500).
Total deformation = sqrt(div**2 + tension**2 + shear**2) at T-points (shear**2 averaged F -> T), computed from
sivelu/sivelv with the same operators for all three runs (v1 has no native icediv/iceshe output).
Usage: python plot_orca025_nevp_deformation_maps.py [--times 2019-09-01T12:00 2019-10-01T12:00 2019-10-30T12:00]
Run in env010."""
import argparse, os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap, LinearSegmentedColormap
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, HERE)
from kinematics import ICE_MIN, load_grid
from plot_beta_vortdef_hierarchy import mesh, add_background, style_map, panel_note, INK, PROJ
from plot_orca025_nevp_timeseries import RUNS, CACHE, GRID_NAME
from plot_orca025_nevp_vorticity_maps import (TIMES, UNIT, VORT_LIM, VORT_STEP, DIFF_LIM, DIFF_STEP, REF, RESIDUAL,
                                              discrete, conv_share, load_panel, row_label, caption_text)

DEF_LIM, DEF_STEP = VORT_LIM, VORT_STEP   # same cap and bins as vorticity: 0..5e-6 s-1 in 0.25e-6 bins
# Sequential orange (dataviz: a second sequential context takes the next categorical hue), so deformation is not
# confused with the blue = negative of the vorticity maps.
DEF_CMAP = LinearSegmentedColormap.from_list("seq_orange", ["#fbe3d6", "#f7c0a1", "#f2976b", "#eb6834",
                                                            "#c4501f", "#8f3a16", "#5e260e"])


def sequential(lim, step):
    levels = np.round(np.arange(0, lim + step / 2, step), 6)
    n = len(levels) - 1
    cols = DEF_CMAP(np.linspace(0, 1, n + 1))
    return ListedColormap(cols[:-1]).with_extremes(over=cols[-1]), BoundaryNorm(levels, n), levels


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--times", nargs=3, default=TIMES, help="three target times (rows)")
    p.add_argument("--out-dir", default=HERE)
    args = p.parse_args()
    whens = [np.datetime64(t) for t in args.times]
    cache = pd.read_csv(CACHE, parse_dates=["time"]) if os.path.exists(CACHE) else None

    g = load_grid(GRID_NAME, RUNS[100]["root"], RUNS[100]["dir"])
    xf, yf, xt, yt, sl = mesh(g)
    P = {(r, n): load_panel(n, w, g) for r, w in enumerate(whens) for n in RUNS}

    # ---- Figure 1: total deformation, 3 x 3 ----
    cmap, norm, levels = sequential(DEF_LIM, DEF_STEP)
    fig, axes = plt.subplots(3, 3, figsize=(13, 14.2), subplot_kw={"projection": PROJ})
    fig.subplots_adjust(left=0.07, right=0.98, top=0.9, bottom=0.175, wspace=0.04, hspace=0.12)
    for r in range(3):
        for k, nevp in enumerate(RUNS):
            ax, d = axes[r, k], P[r, nevp]
            ice_t = g["tmask"] & (d["a"] > ICE_MIN)
            add_background(ax, xf, yf, g["tmask"][sl], ice_t[sl])
            qm = ax.pcolormesh(xf, yf, np.ma.masked_array(d["defo"] / UNIT, ~ice_t)[sl], cmap=cmap, norm=norm,
                               transform=PROJ, rasterized=True)
            style_map(ax)
            if r == 0:
                ax.set_title(f"nn_nevp = {RUNS[nevp]['label']}", fontsize=13, color=INK, pad=8)
            if cache is not None:
                panel_note(ax, f"converged (residual ≤ 5%): {conv_share(cache, nevp, whens[r]):.1f}% of ice")
        row_label(axes[r, 0], P[r, 100]["bounds"])
    cax = fig.add_axes([0.2, 0.13, 0.6, 0.014])
    cb = fig.colorbar(qm, cax=cax, orientation="horizontal", extend="max", ticks=levels[::4])
    cb.set_label("total deformation √(div² + tension² + shear²) (10⁻⁶ s⁻¹)", color=INK, fontsize=10)
    fig.suptitle("ORCA025 sea-ice total deformation at nn_nevp = 100, 500 and 2000, spring 2019",
                 x=0.07, ha="left", y=0.965, fontsize=15, color=INK)
    caption_text(fig, "Total deformation = √(div² + tension² + shear²) at T-points from 3 h mean sivelu/sivelv, the "
                 "same C-grid operators for all three runs (shear² averaged F→T; shear zero on land F-points). Not the "
                 f"rheology Δ, which divides tension and shear by e². Ice only (siconc > {ICE_MIN}); dark grey land, "
                 f"light grey open water. Discrete colour scale, {DEF_STEP:g} × 10⁻⁶ s⁻¹ bins from 0, capped at "
                 f"{DEF_LIM:g} × 10⁻⁶ s⁻¹ — the same units, bin width and cap as orca025_nevp_vorticity_maps.png, so "
                 "the two figures compare directly. Convergence share as in the vorticity figure.", 165)
    out1 = os.path.join(args.out_dir, "orca025_nevp_deformation_maps.png")
    fig.savefig(out1, dpi=200, facecolor="#ffffff")
    plt.close(fig)

    # ---- Figure 2: differences against 2000, 3 x 2, with beta of the less-converged run ----
    cmap, norm, levels = discrete(DIFF_LIM, DIFF_STEP)
    others = [n for n in RUNS if n != REF]
    fig, axes = plt.subplots(3, 2, figsize=(10.2, 14.2), subplot_kw={"projection": PROJ})
    fig.subplots_adjust(left=0.09, right=0.98, top=0.9, bottom=0.185, wspace=0.04, hspace=0.16)
    stats = []
    for r in range(3):
        ref = P[r, REF]
        for k, nevp in enumerate(others):
            ax, d = axes[r, k], P[r, nevp]
            ice_t = g["tmask"] & (d["a"] > ICE_MIN) & (ref["a"] > ICE_MIN)
            diff = d["defo"] - ref["defo"]
            add_background(ax, xf, yf, g["tmask"][sl], ice_t[sl])
            qm = ax.pcolormesh(xf, yf, np.ma.masked_array(diff / UNIT, ~ice_t)[sl], cmap=cmap, norm=norm,
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
            rms = lambda x, m: np.sqrt(np.mean(x[m] ** 2)) / UNIT if m.any() else np.nan
            thr = lv5 if lv5 >= 50 else nevp
            hi = ice_t & (np.nan_to_num(d["beta"]) > thr)
            r_all, r_ref = rms(diff, ice_t), rms(ref["defo"], ice_t)
            panel_note(ax, f"RMS difference {r_all:.2f} ({100 * r_all / r_ref:.0f}% of RMS deformation at {REF})\n"
                           f"β > {thr:.0f} ({100 * hi.sum() / ice_t.sum():.1f}% of ice): {rms(diff, hi):.2f}  ·  "
                           f"elsewhere: {rms(diff, ice_t & ~hi):.2f}")
            stats.append((str(whens[r])[:10], nevp, r_all, r_ref, rms(diff, hi), rms(ref["defo"], hi),
                          rms(diff, ice_t & ~hi), rms(ref["defo"], ice_t & ~hi),
                          np.mean(diff[ice_t]) / UNIT))
        row_label(axes[r, 0], P[r, REF]["bounds"])
    cax = fig.add_axes([0.15, 0.135, 0.7, 0.014])
    cb = fig.colorbar(qm, cax=cax, orientation="horizontal", extend="both", ticks=levels[::2])
    cb.set_label("deformation difference from nn_nevp = 2000 (10⁻⁶ s⁻¹)   ·   blue: less deforming   ·   "
                 "red: more deforming", color=INK, fontsize=10)
    fig.legend(handles=[Line2D([], [], color=INK, lw=0.8, label="β = nn_nevp (residual e⁻¹ ≈ 37%)"),
                        Line2D([], [], color=INK, lw=0.8, ls=(0, (2.5, 1.5)),
                               label=f"β = nn_nevp / {np.log(1 / RESIDUAL):.2f} (residual {100 * RESIDUAL:.0f}%)")],
               loc="upper right", bbox_to_anchor=(0.98, 0.955), ncol=1, frameon=False, fontsize=9.5)
    fig.suptitle("ORCA025 total deformation: difference from nn_nevp = 2000", x=0.09, ha="left", y=0.965,
                 fontsize=15, color=INK)
    caption_text(fig, "Difference in T-point total deformation (as in orca025_nevp_deformation_maps.png) between each "
                 "less-converged run and nn_nevp = 2000, over cells that are ice in both runs. Discrete colour scale, "
                 f"{DIFF_STEP:g} × 10⁻⁶ s⁻¹ bins, symmetric about zero, capped at ±{DIFF_LIM:g} × 10⁻⁶ s⁻¹ — the same "
                 "scale as orca025_nevp_vorticity_diff.png. Contours: β of the less-converged run over ice — offline "
                 "estimate for 100, NEMO beta_evp (3 h mean) for 500; inside the solid line the residual after nn_nevp "
                 f"iterations, ~exp(−nn_nevp/β), exceeds ~37%, inside the dashed line {100 * RESIDUAL:.0f}% (not drawn "
                 "for 100: β ≥ 50 everywhere). RMS values (10⁻⁶ s⁻¹) over the same ice cells, split inside versus "
                 "outside the innermost contour drawn (β > 100 for 100, β > 167 for 500).", 130)
    out2 = os.path.join(args.out_dir, "orca025_nevp_deformation_diff.png")
    fig.savefig(out2, dpi=200, facecolor="#ffffff")
    print(out1); print(out2)
    print("date nevp | rms diff, rms def(2000) | inside: diff, def | outside: diff, def | mean diff")
    for s_ in stats:
        print(s_[0], s_[1], "|", " ".join(f"{x:.2f}" for x in s_[2:]))


if __name__ == "__main__":
    main()
