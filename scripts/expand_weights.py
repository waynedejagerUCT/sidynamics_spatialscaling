#!/usr/bin/env python3
"""
expand_weights.py -- rewrite a compacted SCRIP weights file into positional form.

THE PROBLEM
  scripshape writes one entry per LINK, in link order. When SCRIP maps every
  destination point, link order and destination order coincide and dst0k[n] == n+1,
  which is what NEMO assumes: fldread reads src0k/wgt0k as 2-D arrays shaped like the
  target grid and applies entry (j,i) to destination cell (j,i). It does not consult
  dst0k at all.

  If SCRIP skips any destination -- e.g. eORCA05's southward extension reaches -85.79 S
  while GLORYS12 stops at -80.0 S, so cells south of the source's limit find no
  enclosing stencil -- the links are compacted and every entry after the first skipped
  cell sits at the wrong position. NEMO then reads the whole domain's forcing from the
  wrong source cells, with the tail left at zero. It does not crash.

THE FIX
  Scatter each link to the slot its own dst0k names; leave skipped destinations zero.
  Skipped cells are outside the source's coverage and are land in the target mask, so
  they are masked at runtime and a zero weight there is correct.

USAGE
  conda activate nemo_analysis
  python3 -u expand_weights.py IN.nc OUT.nc --domain-cfg <trimmed domain_cfg.nc>
  python3 -u expand_weights.py --verify-only FILE.nc --domain-cfg <trimmed domain_cfg.nc>

Refuses to overwrite an existing output. Non-zero exit on any check failure.
"""
import argparse
import os
import shutil
import sys

import netCDF4
import numpy as np

NK = 4  # bilinear: four source points per destination


def wet_mask(domain_cfg):
    with netCDF4.Dataset(domain_cfg) as nc:
        tl = np.asarray(nc.variables["top_level"][:]).squeeze()
    return tl > 0


def check(path, domain_cfg, label):
    """Every check that must hold for a weights file NEMO will read positionally."""
    fails = []
    mask = wet_mask(domain_cfg)
    with netCDF4.Dataset(path) as nc:
        shape = nc.variables["src01"].shape          # (lat, lon) = (nj, ni)
        n = int(np.prod(shape))
        if shape != mask.shape:
            fails.append(f"shape {shape} != domain_cfg {mask.shape}")
            print(f"{label}: FAIL shape mismatch -- later checks skipped")
            return fails

        tot = np.zeros(shape)
        for k in range(1, NK + 1):
            dst = np.asarray(nc.variables[f"dst{k:02d}"][:]).astype(np.int64).ravel()
            off = np.flatnonzero(dst != np.arange(1, n + 1))
            if off.size:
                fails.append(f"dst{k:02d} not positional: {off.size} slots differ, "
                             f"first at index {int(off[0])}")
            tot += np.asarray(nc.variables[f"wgt{k:02d}"][:])

        n_wet_bad = int(((tot == 0) & mask).sum())
        if n_wet_bad:
            fails.append(f"{n_wet_bad} WET cells have zero total weight")
        n_land_zero = int(((tot == 0) & ~mask).sum())

        finite = np.isfinite(tot).all()
        if not finite:
            fails.append("non-finite weights present")

        print(f"{label}: shape={shape} wet={int(mask.sum())} "
              f"zero-weight land cells={n_land_zero} "
              f"weight-sum range [{tot[tot > 0].min():.6f}, {tot.max():.6f}]")

    for f in fails:
        print(f"{label}: FAIL {f}")
    if not fails:
        print(f"{label}: PASS")
    return fails


def expand(src_path, out_path, domain_cfg):
    if os.path.exists(out_path):
        raise SystemExit(f"refusing to overwrite existing file: {out_path}")

    with netCDF4.Dataset(src_path) as nc:
        shape = nc.variables["src01"].shape
        n = int(np.prod(shape))
        links = {}
        for k in range(1, NK + 1):
            dst = np.asarray(nc.variables[f"dst{k:02d}"][:]).astype(np.int64).ravel()
            src = np.asarray(nc.variables[f"src{k:02d}"][:]).ravel()
            wgt = np.asarray(nc.variables[f"wgt{k:02d}"][:]).ravel()
            keep = dst > 0                                    # real links only
            if keep.sum() == n and (dst == np.arange(1, n + 1)).all():
                print(f"  dst{k:02d}: already positional, copying through")
            else:
                print(f"  dst{k:02d}: {int(keep.sum())} links -> {n} slots "
                      f"({n - int(keep.sum())} skipped destinations)")
            # duplicate destinations would mean the file is malformed in a way this
            # script cannot repair -- stop rather than silently keeping the last one
            d = dst[keep]
            if np.unique(d).size != d.size:
                raise SystemExit(f"dst{k:02d} has duplicate destination indices")
            new_src = np.zeros(n, dtype=src.dtype)
            new_wgt = np.zeros(n, dtype=wgt.dtype)
            new_src[d - 1] = src[keep]
            new_wgt[d - 1] = wgt[keep]
            # Skipped slots keep wgt=0, so whatever they point at is multiplied by
            # zero. But the index must be VALID and NEARBY: fldread sizes each rank's
            # source read box from MINVAL/MAXVAL of the indices in its subdomain
            # (fldread.F90:1215-1222) and allocates it. A far filler (0 crashes, 1
            # spans the whole source) inflates that box. Fill from the nearest mapped
            # neighbour in array order, which leaves every box unchanged.
            pos = np.arange(n)
            have = new_src > 0
            if not have.any():
                raise SystemExit("no mapped links at all")
            fwd = np.maximum.accumulate(np.where(have, pos, 0))
            new_src = new_src[fwd]
            have = new_src > 0
            if not have.all():                       # leading gap before any link
                bwd = np.minimum.accumulate(np.where(have, pos, n - 1)[::-1])[::-1]
                new_src = new_src[bwd]
            links[k] = (np.arange(1, n + 1), new_src, new_wgt)

    shutil.copyfile(src_path, out_path)                       # preserve dims and attrs
    with netCDF4.Dataset(out_path, "a") as nc:
        for k, (dst, src, wgt) in links.items():
            nc.variables[f"dst{k:02d}"][:] = dst.reshape(shape)
            nc.variables[f"src{k:02d}"][:] = src.reshape(shape)
            nc.variables[f"wgt{k:02d}"][:] = wgt.reshape(shape)
        hist = getattr(nc, "history", "")
        nc.history = (hist + "; " if hist else "") + (
            "expand_weights.py: links scattered from link order to destination "
            "position; destinations outside source coverage left at zero weight")

    return check(out_path, domain_cfg, os.path.basename(out_path))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="compacted weights file to read")
    ap.add_argument("out", nargs="?", help="positional weights file to write")
    ap.add_argument("--verify-only", metavar="FILE",
                    help="check an existing file instead of writing one")
    ap.add_argument("--domain-cfg", required=True,
                    help="the TRIMMED domain_cfg.nc this weights file targets")
    args = ap.parse_args()

    if args.verify_only:
        fails = check(args.verify_only, args.domain_cfg,
                      os.path.basename(args.verify_only))
    else:
        if not (args.src and args.out):
            ap.error("give SRC and OUT, or --verify-only FILE")
        print(f"reading  {args.src}")
        fails = expand(args.src, args.out, args.domain_cfg)
        print(f"wrote    {args.out}")

    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
