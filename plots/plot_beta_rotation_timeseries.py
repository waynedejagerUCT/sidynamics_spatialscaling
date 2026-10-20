#!/usr/bin/env python3
"""Two-panel time series: solver convergence and rotation dominance through the season, across the hierarchy.
Upper: % of ice cells with beta <= nn_nevp / CONV_DIVISOR. Lower: % of ice cells with |zeta| / total deformation > 1.
Every 3 h record of every member, 18 Mar - 31 Oct 2019. Per-record results are cached as CSV under
~/Data/intermediate/SEAICE_DYN_003/ and re-read on later runs (--recompute forces a fresh pass).
Usage: python plot_beta_rotation_timeseries.py [--source offline|model] [--weight count|area] [--recompute]
Run in env010."""
import argparse, glob, os, sys, textwrap, time
import numpy as np, pandas as pd, xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.transforms import blended_transform_factory

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
from kinematics import DATA_ROOT, ICE_MIN, DEF_FLOOR, load_grid, interior_cols, load_record, rotation_ratio
from estimate_beta_evp import beta_from

CONV_DIVISOR = 1.0                 # converged: beta <= nn_nevp / CONV_DIVISOR (residual ~ exp(-CONV_DIVISOR))
SOURCE = "offline"                 # "offline" (v1, beta from fields) or "model" (v2, NEMO beta_evp)
SOURCES = {"offline": {"nevp": 100, "label": "v1, nn_nevp = 100, offline β"},
           "model":   {"nevp": 500, "label": "v2, nn_nevp = 500, NEMO beta_evp"}}
WEIGHT = "count"                   # "count" (cells) or "area" (e1t*e2t)
MEMBERS = ["ORCA2", "ORCA1", "ORCA05", "ORCA025"]
CACHE_DIR = os.path.expanduser("~/Data/intermediate/SEAICE_DYN_003")
ROLL = 8                           # records per day
SEASONS = [("Autumn", "2019-03-18", "2019-06-01"), ("Winter", "2019-06-01", "2019-09-01"),
           ("Spring", "2019-09-01", "2019-11-01")]

# Colours (dataviz reference palette): categorical slots 1-4 in fixed order, one per member.
COLORS = dict(zip(MEMBERS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]))
INK, INK2, MUTED, GRID, WINTER = "#0b0b0b", "#52514e", "#8d8c87", "#e4e3df", "#f3f2ef"


def compute_member(member, root, source, nevp):
    """One row per 3 h record: ice-cell counts/areas, converged and rotation-dominated subsets."""
    g = load_grid(member, root)
    cols = interior_cols(g)
    area = (g["e1e2t"] / 1e6)[:, cols]                         # km2
    ocean = g["tmask"][:, cols]
    rows = []
    for f in sorted(glob.glob(f"{root}/{member}/*_3h_icemod_*.nc")):
        with xr.open_dataset(f) as ds:
            times = ds.time_counter.values
            for t in range(ds.sizes["time_counter"]):
                a, h, u, v = load_record(ds, t)
                beta = beta_from(source, ds, t, a, h, u, v, g)[:, cols]
                ratio, total_def = (x[:, cols] for x in rotation_ratio(u, v, g))
                ice = ocean & (np.nan_to_num(a[:, cols]) > ICE_MIN)
                conv = ice & (beta <= nevp / CONV_DIVISOR)
                valid = ice & (total_def >= DEF_FLOOR)
                rot = valid & (ratio > 1)
                rows.append(dict(time=times[t], member=member,
                                 n_ice=int(ice.sum()), area_ice=area[ice].sum(),
                                 n_conv=int(conv.sum()), area_conv=area[conv].sum(),
                                 n_valid=int(valid.sum()), area_valid=area[valid].sum(),
                                 n_rot=int(rot.sum()), area_rot=area[rot].sum()))
    df = pd.DataFrame(rows).drop_duplicates("time").sort_values("time")
    df["pct_conv_count"] = 100 * df.n_conv / df.n_ice
    df["pct_conv_area"] = 100 * df.area_conv / df.area_ice
    df["pct_rot_count"] = 100 * df.n_rot / df.n_valid
    df["pct_rot_area"] = 100 * df.area_rot / df.area_valid
    df["n_lowdef"] = df.n_ice - df.n_valid
    return df


def load_or_compute(root, source, recompute):
    """Re-read the cache when its parameters match; otherwise compute the missing or stale members."""
    nevp = SOURCES[source]["nevp"]
    params = dict(source=source, nevp=nevp, conv_divisor=CONV_DIVISOR, def_floor=DEF_FLOOR, ice_min=ICE_MIN)
    path = os.path.join(CACHE_DIR, f"beta_rotation_ts_{source}.csv")
    old = pd.read_csv(path, parse_dates=["time"]) if os.path.exists(path) and not recompute else pd.DataFrame()
    parts = []
    for m in MEMBERS:
        sub = old[old.member == m] if len(old) else old
        if len(sub) and all(np.isclose(sub[k], v).all() if isinstance(v, float) else (sub[k] == v).all()
                            for k, v in params.items()):
            parts.append(sub)
            continue
        t0 = time.time()
        df = compute_member(m, root, source, nevp).assign(**params)
        print(f"{m}: {len(df)} records in {time.time() - t0:.0f} s")
        parts.append(df)
    out = pd.concat(parts, ignore_index=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    out.to_csv(path, index=False)
    print(f"cache: {path}")
    return out


def label_ends(ax, ends, gap_pt=12):
    """Direct labels (ink text) at the right end of each daily-mean line, nudged at least gap_pt apart."""
    trans = blended_transform_factory(ax.transData, ax.transAxes)
    gap = gap_pt / (ax.bbox.height * 72 / ax.figure.dpi)              # in axes fraction
    pts = sorted(((m, mdates.date2num(x), ax.transAxes.inverted().transform(
                   ax.transData.transform((mdates.date2num(x), y)))[1]) for m, y, x in ends), key=lambda e: e[2])
    placed = []
    for _, _, y in pts:
        placed.append(max(y, placed[-1] + gap) if placed else y)
    for (m, x, _), y in zip(pts, placed):
        ax.annotate(m, xy=(x, y), xycoords=trans, xytext=(8, 0), textcoords="offset points",
                    va="center", fontsize=9.5, color=INK, annotation_clip=False)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--source", choices=tuple(SOURCES), default=SOURCE)
    p.add_argument("--weight", choices=("count", "area"), default=WEIGHT)
    p.add_argument("--data-root", default=DATA_ROOT)
    p.add_argument("--recompute", action="store_true", help="ignore the cache and recompute every member")
    p.add_argument("--out-dir", default=HERE)
    args = p.parse_args()
    nevp, label = SOURCES[args.source]["nevp"], SOURCES[args.source]["label"]
    df = load_or_compute(args.data_root, args.source, args.recompute)

    fig, axes = plt.subplots(2, 1, figsize=(13, 8.6), sharex=True)
    fig.subplots_adjust(left=0.085, right=0.89, top=0.86, bottom=0.17, hspace=0.12)
    thr = nevp / CONV_DIVISOR
    panels = [(f"pct_conv_{args.weight}",
               f"% of ice converged\n(β ≤ {thr:g}, residual ≲ {100 * np.exp(-CONV_DIVISOR):.0f}%)"),
              (f"pct_rot_{args.weight}", "% of ice rotation-dominated\n(|ζ| / total deformation > 1)")]

    for ax, (col, ylab) in zip(axes, panels):
        for _, s, e in SEASONS[1:2]:
            ax.axvspan(np.datetime64(s), np.datetime64(e), color=WINTER, zorder=0, lw=0)
        for _, s, _ in SEASONS[1:]:
            ax.axvline(np.datetime64(s), color=MUTED, lw=0.6, ls=(0, (3, 3)), zorder=1)
        ends = []
        for m in MEMBERS:
            d = df[df.member == m].sort_values("time")
            daily = d[col].rolling(ROLL, center=True, min_periods=ROLL).mean()
            ax.plot(d.time, d[col], color=COLORS[m], lw=0.5, alpha=0.35, zorder=2)
            ax.plot(d.time, daily, color=COLORS[m], lw=2.0, zorder=3, solid_capstyle="round")
            last = daily.last_valid_index()
            ends.append((m, daily[last], d.time[last]))
        ax.set_ylabel(ylab, color=INK, fontsize=10.5)
        ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color(MUTED)
        ax.tick_params(colors=INK2, labelsize=9.5)
        lo, hi = np.nanmin(df[col]), np.nanmax(df[col])
        pad = 0.05 * (hi - lo)
        ax.set_ylim(max(0, lo - pad), min(100.5, hi + pad))
        label_ends(ax, ends)

    top = axes[0]
    for name, s, e in SEASONS:
        mid = np.datetime64(s) + (np.datetime64(e) - np.datetime64(s)) / 2
        top.text(mid, 1.02, name, transform=top.get_xaxis_transform(), ha="center", va="bottom",
                 fontsize=10, color=INK2)
    axes[1].set_xlim(df.time.min(), df.time.max())
    axes[1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    fig.legend(handles=[Line2D([], [], color=COLORS[m], lw=2.0, label=m) for m in MEMBERS]
               + [Line2D([], [], color=MUTED, lw=0.5, alpha=0.6, label="3 h record"),
                  Line2D([], [], color=MUTED, lw=2.0, label="daily (8-record) centred mean")],
               loc="upper right", bbox_to_anchor=(0.89, 0.955), ncol=6, frameon=False, fontsize=9.5)
    fig.suptitle(f"Solver convergence and rotation dominance through the 2019 season ({label})",
                 x=0.075, ha="left", y=0.975, fontsize=14, color=INK)

    wt = ("cell count" if args.weight == "count" else "ice area (cell area e1t·e2t)")
    beta_note = ("Offline β from scripts/estimate_beta_evp.py (3 h mean velocities, no snow mass); in-model v2 β has "
                 "run ~2x this estimate, so offline convergence is optimistic. β ≥ 50 by construction."
                 if args.source == "offline" else "β from NEMO's beta_evp field in _icemod.")
    caption = (f"Percentages weighted by {wt}. Upper: share of ice cells (siconc > {ICE_MIN}) with β ≤ nn_nevp"
               f"{'' if CONV_DIVISOR == 1 else f' / {CONV_DIVISOR:g}'} = {thr:g}; residual after nn_nevp iterations "
               f"~ exp(−nn_nevp/β). {beta_note} Lower: share of ice cells with total deformation ≥ {DEF_FLOOR:.0e} s⁻¹ "
               f"({DEF_FLOOR * 86400:.2g} d⁻¹) whose |ζ| / total deformation > 1; |ζ| = √(ζ² averaged F→T), total "
               "deformation = √(div² + tension² + shear²), as in plot_beta_vortdef_hierarchy.py. Coast-adjacent cells "
               "carry zero F-point ζ on land (free slip), which biases the ratio low there. Thin lines: each 3 h record; "
               "bold: centred daily (8-record) mean. Grey band: winter (Jun–Aug). ORCA05's two duplicate halo columns "
               "are excluded.")
    fig.text(0.075, 0.025, "\n".join(textwrap.wrap(caption, 190)), fontsize=8.5, color=INK2, va="bottom",
             linespacing=1.5)

    out = os.path.join(args.out_dir, f"beta_rotation_timeseries_{args.source}_{args.weight}.png")
    fig.savefig(out, dpi=200, facecolor="#ffffff")
    print(out)


if __name__ == "__main__":
    main()
