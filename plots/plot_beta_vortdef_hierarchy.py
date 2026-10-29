#!/usr/bin/env python3
"""8-panel map (2 rows x 4 columns): solver convergence and rotation across the v1 hierarchy.
Row 1: aEVP beta (offline estimate from scripts/estimate_beta_evp.py, or NEMO's own beta_evp in v2).
Row 2: |vorticity| / total deformation.
Columns: ORCA2, ORCA1, ORCA05, ORCA025, one 3 h record each.
Usage: python plot_beta_vortdef_hierarchy.py [--time 2019-09-15T12:00] [--beta-source offline|model]
Run in env010. Writes a PNG only; no data are copied."""
import argparse, glob, os, sys, textwrap
import numpy as np, xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.path as mpath
from matplotlib.colors import LogNorm, ListedColormap, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import cartopy.crs as ccrs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from kinematics import DATA_ROOTS, ICE_MIN, DEF_FLOOR, load_grid, interior_cols, load_record, rotation_ratio, has_output
from estimate_beta_evp import beta_from

TIME = "2019-09-15T12:00"          # target time; the 3 h record whose interval contains it is used
BETA_SOURCE = "offline"            # "offline" (v1: from siconc/sithic/velocities) or "model" (v2: _icemod beta_evp)
VERSION = "v1"                     # data version: "v1" (nn_nevp = 100) or "v2" (nn_nevp = 500)
VERSION_LABELS = {"v1": "v1, nn_nevp = 100", "v2": "v2, nn_nevp = 500"}
MEMBERS = ["ORCA2", "ORCA1", "ORCA05", "ORCA025"]
BETA_LIM, BETA_LINES = (50, 1000), (100, 500)   # v1 and v2 nn_nevp
RATIO_LIM = (0.1, 10)
LAT_EDGE = -52.0                   # map edge; Sep 2019 ice reaches ~53.6S

# Colours (dataviz reference palette): sequential blue for beta; blue <-> grey <-> red diverging for the ratio.
INK, INK2 = "#0b0b0b", "#52514e"
LAND, WATER = "#8d8c87", "#d3d2cd"
LOW_DEF = "#eda100"                # below DEF_FLOOR; apart from both ramps and the greys
LINE_100, LINE_500 = "#0b0b0b", "#eb6834"
BETA_CMAP = LinearSegmentedColormap.from_list("seq_blue", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                                                           "#256abf", "#184f95", "#0d366b"])
RATIO_CMAP = LinearSegmentedColormap.from_list("div_blue_red", ["#0d366b", "#256abf", "#6da7ec", "#b7d3f6",
                                                                "#f0efec",
                                                                "#f4c3c0", "#ec8a88", "#e34948", "#9e2423"])
PROJ, GEO = ccrs.SouthPolarStereo(), ccrs.PlateCarree()


def find_record(member, when, root):
    """File and index of the 3 h record with bounds start <= when < end (files split 18th to 18th)."""
    for f in sorted(glob.glob(f"{root}/{member}/*_3h_icemod_*.nc")):
        with xr.open_dataset(f) as ds:
            b = ds.time_counter_bounds.values
            hit = np.nonzero((b[:, 0] <= when) & (when < b[:, 1]))[0]
            if hit.size:
                return f, int(hit[0]), b[hit[0]], ds.time_centered.values[hit[0]]
    raise SystemExit(f"{member}: no 3 h record contains {when}")


def mesh(g):
    """Projected F-point corners and the T-column slice they bound, handling the zonal wrap.
    ORCA05 carries two duplicate halo columns (0 and -1); the other trimmed grids are exactly periodic."""
    dom = g["dom"]
    lonf, latf = dom["glamf"].values, dom["gphif"].values
    cols = interior_cols(g)
    if cols != slice(None):
        lonf, latf = lonf[:, :-1], latf[:, :-1]
    else:
        cols = slice(None)
        lonf, latf = np.hstack([lonf[:, -1:], lonf]), np.hstack([latf[:, -1:], latf])
    xyf = PROJ.transform_points(GEO, lonf, latf)
    xyt = PROJ.transform_points(GEO, dom["glamt"].values[1:, cols], dom["gphit"].values[1:, cols])
    return xyf[..., 0], xyf[..., 1], xyt[..., 0], xyt[..., 1], (slice(1, None), cols)


def member_fields(member, rec, root, source):
    g = load_grid(member, root)
    f, t = rec
    with xr.open_dataset(f) as ds:
        a, h, u, v = load_record(ds, t)
        beta = beta_from(source, ds, t, a, h, u, v, g)
    ratio, total_def = rotation_ratio(u, v, g)
    ice = g["tmask"] & (np.nan_to_num(a) > ICE_MIN)
    return g, ice, beta, ratio, total_def


def add_background(ax, xf, yf, ocean, ice):
    bg = np.ma.masked_array(np.where(ocean, 1, 0), mask=ice)   # 0 land, 1 open water
    ax.pcolormesh(xf, yf, bg, cmap=ListedColormap([LAND, WATER]), vmin=0, vmax=1,
                  transform=PROJ, rasterized=True)


def style_map(ax):
    ax.set_extent([-180, 180, -90, LAT_EDGE], GEO)
    ax.set_facecolor(LAND)                             # south of the grid's southern row
    theta = np.linspace(0, 2 * np.pi, 200)
    ax.set_boundary(mpath.Path(np.c_[np.sin(theta), np.cos(theta)] * 0.5 + 0.5), transform=ax.transAxes)
    ax.gridlines(color="#ffffff", linewidth=0.4, alpha=0.6, ylocs=[-80, -70, -60])
    ax.spines["geo"].set_edgecolor(INK2); ax.spines["geo"].set_linewidth(0.6)


def panel_note(ax, text):
    ax.text(0.5, -0.04, text, transform=ax.transAxes, ha="center", va="top", fontsize=8.5, color=INK2)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--time", default=TIME, help="target time, e.g. 2019-09-15T12:00")
    p.add_argument("--beta-source", choices=("offline", "model"), default=BETA_SOURCE)
    p.add_argument("--version", choices=tuple(DATA_ROOTS), default=VERSION, help="data version (sets root and label)")
    p.add_argument("--label", default=None, help="override the data version label used in row 1 and the title")
    p.add_argument("--data-root", default=None, help="override the data root for --version")
    p.add_argument("--deform-floor", type=float, default=DEF_FLOOR, help="s-1")
    p.add_argument("--out-dir", default=HERE)
    args = p.parse_args()
    args.data_root = args.data_root or DATA_ROOTS[args.version]
    args.label = args.label or VERSION_LABELS[args.version]
    when = np.datetime64(args.time)

    recs = {m: find_record(m, when, args.data_root) for m in MEMBERS if has_output(m, args.data_root)}
    if not recs:
        raise SystemExit(f"no member output under {args.data_root}")
    for m in MEMBERS:
        if m not in recs:
            print(f"{m}: no output under {args.data_root}; panel left empty")
    bounds, centre = next(iter(recs.values()))[2:4]
    if any(r[3] != centre for r in recs.values()):
        raise SystemExit("record times differ between members")
    t0, t1 = (str(x)[:16].replace("T", " ") for x in bounds)

    fig, axes = plt.subplots(2, 4, figsize=(16, 9.6), subplot_kw={"projection": PROJ})
    fig.subplots_adjust(left=0.045, right=0.9, top=0.88, bottom=0.17, wspace=0.06, hspace=0.2)
    beta_norm, ratio_norm = LogNorm(*BETA_LIM), LogNorm(*RATIO_LIM)

    for k, m in enumerate(MEMBERS):
        if m not in recs:
            for row in (0, 1):
                style_map(axes[row, k])
                axes[row, k].set_facecolor("#ffffff")
                axes[row, k].text(0.5, 0.5, "not held locally", transform=axes[row, k].transAxes,
                                  ha="center", va="center", fontsize=10, color=INK2)
            axes[0, k].set_title(m, fontsize=13, color=INK, pad=6)
            continue
        g, ice, beta, ratio, total_def = member_fields(m, recs[m][:2], args.data_root, args.beta_source)
        xf, yf, xt, yt, sl = mesh(g)
        ice_s, beta_s, ratio_s, def_s = ice[sl], beta[sl], ratio[sl], total_def[sl]

        # Row 1: beta
        ax = axes[0, k]
        add_background(ax, xf, yf, g["tmask"][sl], ice_s)
        bq = ax.pcolormesh(xf, yf, np.ma.masked_array(beta_s, ~ice_s), cmap=BETA_CMAP, norm=beta_norm,
                           transform=PROJ, rasterized=True)
        ax.contour(xt, yt, np.ma.masked_array(beta_s, ~ice_s), levels=list(BETA_LINES),
                   colors=[LINE_100, LINE_500], linewidths=[0.6, 0.9], transform=PROJ)
        style_map(ax)
        ax.set_title(m, fontsize=13, color=INK, pad=6)
        n_ice = ice_s.sum()
        panel_note(ax, f"β > 100: {(beta_s[ice_s] > 100).mean():.2%} of {n_ice:,} ice cells")

        # Row 2: |zeta| / total deformation
        ax = axes[1, k]
        add_background(ax, xf, yf, g["tmask"][sl], ice_s)
        low = ice_s & ~(def_s >= args.deform_floor)
        ok = ice_s & ~low
        rq = ax.pcolormesh(xf, yf, np.ma.masked_array(ratio_s, ~ok), cmap=RATIO_CMAP, norm=ratio_norm,
                           transform=PROJ, rasterized=True)
        ax.pcolormesh(xf, yf, np.ma.masked_array(np.ones_like(ratio_s), ~low), cmap=ListedColormap([LOW_DEF]),
                      transform=PROJ, rasterized=True)
        style_map(ax)
        panel_note(ax, f"ratio > 1: {(ratio_s[ok] > 1).mean():.1%} · below floor: {low.sum() / n_ice:.1%} of ice cells")

    for row, text in enumerate((f"Offline β estimate ({args.label})" if args.beta_source == "offline"
                                else f"NEMO beta_evp ({args.label})",
                                "|ζ| / total deformation")):
        axes[row, 0].text(-0.07, 0.5, text, transform=axes[row, 0].transAxes, rotation=90,
                          ha="center", va="center", fontsize=12, color=INK)

    cax = fig.add_axes([0.915, axes[0, 3].get_position().y0 + 0.02, 0.012, axes[0, 3].get_position().height - 0.04])
    cb = fig.colorbar(bq, cax=cax, extend="max")
    cb.set_ticks([50, 100, 200, 500, 1000]); cb.set_ticklabels(["50", "100", "200", "500", "1000"])
    cb.set_label("β (aEVP relaxation)", color=INK)
    cb.ax.axhline(100, color=LINE_100, lw=1.2); cb.ax.axhline(500, color=LINE_500, lw=1.6)

    cax = fig.add_axes([0.915, axes[1, 3].get_position().y0 + 0.02, 0.012, axes[1, 3].get_position().height - 0.04])
    cb = fig.colorbar(rq, cax=cax, extend="both")
    cb.set_ticks([0.1, 0.3, 1, 3, 10]); cb.set_ticklabels(["0.1", "0.3", "1", "3", "10"])
    cb.set_label("|ζ| / total deformation\n< 1 deformation-, > 1 rotation-dominated", color=INK)
    cb.ax.axhline(1, color=INK, lw=1.2)

    fig.legend(handles=[Line2D([], [], color=LINE_100, lw=1.2, label="β = 100 (v1 nn_nevp)"),
                        Line2D([], [], color=LINE_500, lw=1.6, label="β = 500 (v2 nn_nevp)")],
               loc="upper right", bbox_to_anchor=(0.9, 0.955), ncol=2, frameon=False, fontsize=9.5)
    fig.legend(handles=[Patch(facecolor=LOW_DEF, label=f"total deformation < {args.deform_floor:.0e} s⁻¹ (ratio not shown)")],
               loc="lower right", bbox_to_anchor=(0.9, axes[1, 3].get_position().y1 + 0.005), frameon=False, fontsize=9.5)
    fig.suptitle(f"Solver convergence and rotation across the hierarchy ({args.label})\n"
                 f"3 h mean {t0} to {t1[11:]} (centred {str(centre)[11:16]})",
                 x=0.045, ha="left", y=0.975, fontsize=14, color=INK)

    beta_note = ("Offline β from scripts/estimate_beta_evp.py (3 h mean velocities, no snow mass; in-model v2 β "
                 "has run ~2x this estimate at ORCA2/ORCA1)." if args.beta_source == "offline"
                 else "β from NEMO's beta_evp field in _icemod.")
    caption = (f"Ice cells only (siconc > {ICE_MIN}); dark grey land, light grey open water. {beta_note} "
               "β ≳ nn_nevp marks cells where aEVP is not converged.\n"
               "ζ = ∂v/∂x − ∂u/∂y at F-points (circulation form with e1u, e2v, e1f, e2f; zero on land F-points); "
               "|ζ| = √(ζ² averaged F→T), matching shear. Total deformation = √(div² + tension² + shear²), shear² averaged F→T as in "
               "estimate_beta_evp.py;\nnot the rheology Δ, which divides tension and shear by e². "
               f"Yellow: ice cells with total deformation below {args.deform_floor:.0e} s⁻¹ "
               f"({args.deform_floor * 86400:.2g} d⁻¹), ratio not shown. "
               "ORCA05's two duplicate halo columns are excluded.")
    caption = "\n".join(textwrap.wrap(caption.replace("\n", " "), 205))
    fig.text(0.045, 0.035, caption, fontsize=8.5, color=INK2, va="bottom", ha="left", linespacing=1.5)

    stamp = str(centre)[:16].replace("-", "").replace(":", "")
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, f"beta_vortdef_{args.version}_{args.beta_source}_{stamp}.png")
    fig.savefig(out, dpi=200, facecolor="#ffffff")
    print(out)


if __name__ == "__main__":
    main()
