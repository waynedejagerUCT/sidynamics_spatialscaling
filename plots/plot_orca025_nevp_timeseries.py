#!/usr/bin/env python3
"""Two-panel time series for the ORCA025 solver-sensitivity test (A16): nn_nevp = 100 (v1), 500 (v2), 2000.
Upper: % of ice converged to a residual <= CONV_RESIDUAL, i.e. beta <= nn_nevp / ln(1/CONV_RESIDUAL)
(residual after nn_nevp aEVP iterations ~ exp(-nn_nevp/beta)). beta is the offline estimate for v1, which
has no beta_evp field, and NEMO's own beta_evp for 500 and 2000 (offline beta shown dashed as a cross-check).
Lower: % of ice with |zeta| / total deformation > 1.
Every 3 h record, 18 Mar - 31 Oct 2019. Per-record results are cached as CSV under
~/Data/intermediate/SEAICE_DYN_003/ (several residual thresholds, both weightings) and re-read on later runs.
Usage: python plot_orca025_nevp_timeseries.py [--weight count|area] [--residual 0.05] [--recompute]
Run in env010."""
import argparse, glob, os, sys, textwrap, time
import numpy as np, pandas as pd, xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
sys.path.insert(0, HERE)
from kinematics import DATA_ROOTS, ICE_MIN, DEF_FLOOR, load_grid, interior_cols, load_record, rotation_ratio
from estimate_beta_evp import beta_offline
from plot_beta_rotation_timeseries import label_ends, SEASONS, ROLL, CACHE_DIR, INK, INK2, MUTED, GRID, WINTER

CONV_RESIDUAL = 0.05               # converged: residual <= 5% (>= 95% converged); must be one of RESIDUALS
RESIDUALS = {"r37": np.exp(-1), "r10": 0.10, "r05": 0.05, "r01": 0.01}   # cached thresholds
WEIGHT = "count"                   # "count" (cells) or "area" (e1t*e2t)
GRID_NAME = "ORCA025"
RUNS = {100:  {"root": DATA_ROOTS["v1"], "dir": "ORCA025",          "label": "100 (v1)"},
        500:  {"root": DATA_ROOTS["v2"], "dir": "ORCA025",          "label": "500 (v2)"},
        2000: {"root": DATA_ROOTS["v2"], "dir": "ORCA025_NEVP2000", "label": "2000"}}
CACHE = os.path.join(CACHE_DIR, "orca025_nevp_ts.csv")

# Colours (dataviz reference palette): one sequential blue ramp, light -> dark with iteration count (ordinal).
COLORS = {100: "#6da7ec", 500: "#256abf", 2000: "#0d366b"}


def compute_run(nevp, run, g, cols):
    """One row per 3 h record: ice counts/areas, converged subsets (offline and, where output, model beta)
    at every cached residual, and the rotation-dominated subset."""
    area = (g["e1e2t"] / 1e6)[:, cols]                         # km2
    ocean = g["tmask"][:, cols]
    rows = []
    files = sorted(glob.glob(f"{run['root']}/{run['dir']}/*_3h_icemod_*.nc"))
    if not files:
        raise SystemExit(f"no _icemod files under {run['root']}/{run['dir']}")
    for f in files:
        with xr.open_dataset(f) as ds:
            times, has_model = ds.time_counter.values, "beta_evp" in ds
            for t in range(ds.sizes["time_counter"]):
                a, h, u, v = load_record(ds, t)
                ice = ocean & (np.nan_to_num(a[:, cols]) > ICE_MIN)
                betas = {"offline": beta_offline(a, h, u, v, g)[:, cols]}
                if has_model:
                    betas["model"] = ds.beta_evp[t].values.astype("f8")[:, cols]
                ratio, total_def = (x[:, cols] for x in rotation_ratio(u, v, g))
                valid = ice & (total_def >= DEF_FLOOR)
                rot = valid & (ratio > 1)
                row = dict(time=times[t], nevp=nevp, n_ice=int(ice.sum()), area_ice=area[ice].sum(),
                           n_valid=int(valid.sum()), area_valid=area[valid].sum(),
                           n_rot=int(rot.sum()), area_rot=area[rot].sum())
                for src, b in betas.items():
                    for tag, r in RESIDUALS.items():
                        conv = ice & (b <= nevp / np.log(1 / r))
                        row[f"n_conv_{src}_{tag}"], row[f"area_conv_{src}_{tag}"] = int(conv.sum()), area[conv].sum()
                rows.append(row)
    return pd.DataFrame(rows).drop_duplicates("time").sort_values("time")


def load_or_compute(recompute):
    params = dict(def_floor=DEF_FLOOR, ice_min=ICE_MIN)
    old = pd.read_csv(CACHE, parse_dates=["time"]) if os.path.exists(CACHE) else pd.DataFrame()
    g = load_grid(GRID_NAME, RUNS[100]["root"], RUNS[100]["dir"])   # the three runs share one trimmed domain
    cols = interior_cols(g)
    parts = []
    for nevp, run in RUNS.items():
        sub = old[old.nevp == nevp] if len(old) else old
        if len(sub) and not recompute and all(np.isclose(sub[k], v).all() for k, v in params.items()):
            parts.append(sub)
            continue
        t0 = time.time()
        df = compute_run(nevp, run, g, cols).assign(**params)
        print(f"nn_nevp = {nevp}: {len(df)} records in {time.time() - t0:.0f} s")
        parts.append(df)
    out = pd.concat(parts, ignore_index=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    out.to_csv(CACHE, index=False)
    print(f"cache: {CACHE}")
    return out


def pct(df, kind, weight, src=None, tag=None):
    """Percentage series: converged (of ice) or rotation-dominated (of ice above the deformation floor)."""
    w = "n" if weight == "count" else "area"
    if kind == "conv":
        return 100 * df[f"{w}_conv_{src}_{tag}"] / df[f"{w}_ice"]
    return 100 * df[f"{w}_rot"] / df[f"{w}_valid"]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--weight", choices=("count", "area"), default=WEIGHT)
    p.add_argument("--residual", type=float, default=CONV_RESIDUAL,
                   help=f"convergence residual; one of {sorted(round(r, 3) for r in RESIDUALS.values())}")
    p.add_argument("--recompute", action="store_true")
    p.add_argument("--out-dir", default=HERE)
    args = p.parse_args()
    tag = next((k for k, r in RESIDUALS.items() if np.isclose(r, args.residual, atol=1e-3)), None)
    if tag is None:
        raise SystemExit(f"--residual must be one of the cached thresholds {list(RESIDUALS.values())}")
    res = RESIDUALS[tag]
    df = load_or_compute(args.recompute)

    fig, axes = plt.subplots(2, 1, figsize=(13, 8.6), sharex=True)
    fig.subplots_adjust(left=0.085, right=0.88, top=0.86, bottom=0.19, hspace=0.12)
    for ax in axes:
        ax.axvspan(np.datetime64(SEASONS[1][1]), np.datetime64(SEASONS[1][2]), color=WINTER, zorder=0, lw=0)
        for _, s, _ in SEASONS[1:]:
            ax.axvline(np.datetime64(s), color=MUTED, lw=0.6, ls=(0, (3, 3)), zorder=1)

    # Upper: convergence. v1 uses offline beta; 500/2000 use NEMO's beta_evp, offline dashed for comparison.
    ax, ends, unreachable = axes[0], [], []
    for nevp in RUNS:
        d = df[df.nevp == nevp].sort_values("time")
        src = "model" if f"n_conv_model_{tag}" in d and d[f"n_conv_model_{tag}"].notna().all() else "offline"
        y = pct(d, "conv", args.weight, src, tag)
        if nevp / np.log(1 / res) < 50:                # beta >= 50 by construction: threshold unreachable
            unreachable.append(nevp)
            continue
        daily = y.rolling(ROLL, center=True, min_periods=ROLL).mean()
        ax.plot(d.time, y, color=COLORS[nevp], lw=0.5, alpha=0.35, zorder=2)
        ax.plot(d.time, daily, color=COLORS[nevp], lw=2.0, zorder=3, solid_capstyle="round")
        if src == "model":
            yo = pct(d, "conv", args.weight, "offline", tag).rolling(ROLL, center=True, min_periods=ROLL).mean()
            ax.plot(d.time, yo, color=COLORS[nevp], lw=1.0, ls=(0, (4, 2)), zorder=3)
        last = daily.last_valid_index()
        ends.append((RUNS[nevp]["label"], daily[last], d.time[last]))
    for nevp in unreachable:
        ax.text(0.01, 0.04, f"nn_nevp = {RUNS[nevp]['label']}: 0% at every record — β ≥ 50 by construction, so the "
                f"residual is ≥ e^(−{nevp}/50) = {100 * np.exp(-nevp / 50):.1f}% > {100 * res:.0f}%",
                transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")
    ax.set_ylabel(f"% of ice converged\n(residual ≤ {100 * res:.0f}%: β ≤ nn_nevp / {np.log(1 / res):.2f})",
                  color=INK, fontsize=10.5)

    # Lower: rotation dominance, all three settings.
    ax2, ends2 = axes[1], []
    for nevp in RUNS:
        d = df[df.nevp == nevp].sort_values("time")
        y = pct(d, "rot", args.weight)
        daily = y.rolling(ROLL, center=True, min_periods=ROLL).mean()
        ax2.plot(d.time, y, color=COLORS[nevp], lw=0.5, alpha=0.35, zorder=2)
        ax2.plot(d.time, daily, color=COLORS[nevp], lw=2.0, zorder=3, solid_capstyle="round")
        last = daily.last_valid_index()
        ends2.append((RUNS[nevp]["label"], daily[last], d.time[last]))
    ax2.set_ylabel("% of ice rotation-dominated\n(|ζ| / total deformation > 1)", color=INK, fontsize=10.5)

    for a, e in ((ax, ends), (ax2, ends2)):
        a.grid(axis="y", color=GRID, lw=0.6); a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            a.spines[sp].set_color(MUTED)
        a.tick_params(colors=INK2, labelsize=9.5)
        ys = [l.get_ydata() for l in a.get_lines() if len(l.get_ydata()) > 2]
        lo, hi = np.nanmin([np.nanmin(np.asarray(v, float)) for v in ys]), np.nanmax([np.nanmax(np.asarray(v, float)) for v in ys])
        pad = 0.06 * (hi - lo)
        a.set_ylim(max(0, lo - pad), min(100.5, hi + pad))
        label_ends(a, e)
    for name, s, e in SEASONS:
        mid = np.datetime64(s) + (np.datetime64(e) - np.datetime64(s)) / 2
        axes[0].text(mid, 1.02, name, transform=axes[0].get_xaxis_transform(), ha="center", va="bottom",
                     fontsize=10, color=INK2)
    axes[1].set_xlim(df.time.min(), df.time.max())
    axes[1].xaxis.set_major_locator(mdates.MonthLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    fig.legend(handles=[Line2D([], [], color=COLORS[n], lw=2.0, label=f"nn_nevp = {RUNS[n]['label']}") for n in RUNS]
               + [Line2D([], [], color=MUTED, lw=1.0, ls=(0, (4, 2)), label="offline β (500, 2000)"),
                  Line2D([], [], color=MUTED, lw=0.5, alpha=0.6, label="3 h record")],
               loc="upper right", bbox_to_anchor=(0.88, 0.955), ncol=5, frameon=False, fontsize=9.5)
    fig.suptitle("ORCA025 solver sensitivity: convergence and rotation dominance through the 2019 season",
                 x=0.085, ha="left", y=0.975, fontsize=14, color=INK)

    wt = "cell count" if args.weight == "count" else "ice area (cell area e1t·e2t)"
    caption = (f"Percentages weighted by {wt}. Upper: share of ice cells (siconc > {ICE_MIN}) whose aEVP residual "
               f"after nn_nevp iterations, ~exp(−nn_nevp/β), is ≤ {100 * res:.0f}%, i.e. β ≤ nn_nevp / "
               f"{np.log(1 / res):.2f}. β: offline estimate (scripts/estimate_beta_evp.py; 3 h mean velocities, no "
               "snow mass) for nn_nevp = 100, which has no beta_evp output; NEMO's beta_evp (3 h mean) for 500 and "
               "2000, with the offline estimate dashed (daily mean) as a cross-check. Lower: share of ice cells with "
               f"total deformation ≥ {DEF_FLOOR:.0e} s⁻¹ whose |ζ| / total deformation > 1 (|ζ| = √(ζ² averaged F→T); "
               "total deformation = √(div² + tension² + shear²)). Coast-adjacent cells carry zero F-point ζ on land "
               "(free slip), biasing the ratio low there. Thin lines: each 3 h record; bold: centred daily (8-record) "
               "mean. Grey band: winter (Jun–Aug).")
    fig.text(0.085, 0.025, "\n".join(textwrap.wrap(caption, 190)), fontsize=8.5, color=INK2, va="bottom",
             linespacing=1.5)

    out = os.path.join(args.out_dir, f"orca025_nevp_timeseries_{tag}_{args.weight}.png")
    fig.savefig(out, dpi=200, facecolor="#ffffff")
    print(out)


if __name__ == "__main__":
    main()
