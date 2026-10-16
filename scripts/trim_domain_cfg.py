#!/usr/bin/env python3
"""
trim_domain_cfg.py -- subset a NEMO 5.0 domain configuration file in the j
(south-north) direction, retaining everything south of a target latitude.

Produces a domain file describing a zonally periodic band from the southern edge
of the source grid up to the first row that would cross the target latitude. The
full i extent is retained so that east-west periodicity survives; the north-pole
fold is disabled because the new northern edge is an ordinary open row in the
middle of the ocean rather than a seam at the pole.

Intended for a standalone sea-ice configuration (SAS + SI3) with a prescribed
ocean, where no physical mechanism connects the Antarctic sea-ice field to the
discarded northern rows. See the accompanying audit report for the per-file
evidence supporting that claim.

The row index is DERIVED from each file's own gphit rather than supplied, so the
same invocation is correct at every resolution in the hierarchy.

Metadata handling
-----------------
NEMO resolves global dimensions from the SHAPE of e3t_0 (domain.F90:616-619) and
ignores any jpiglo/jpjglo/jpkglo scalar variables. It resolves periodicity from
four global attributes, falling back to a legacy jperio variable only when both
the NFold and NFtype attributes are absent (domain.F90:622-643). This script
therefore writes real NFold and NFtype attributes -- which is what disables the
fallback -- and additionally corrects the legacy variable and the stale size
scalars, so that external tools reading the file agree with what NEMO resolves.

Usage
-----
    conda activate nemo_analysis

    python3 trim_domain_cfg.py domain_cfg_ORCA025L75.nc \\
            ../ORCA025_ANT30S/domain_cfg.nc \\
            --cfg-name ORCA --cfg-index 4

    python3 trim_domain_cfg.py domain_cfg_ORCA2L31.nc \\
            ../ORCA2_ANT30S/domain_cfg.nc --dry-run

Run the 1/16 degree file under an interactive compute session (sintx); it writes
several gigabytes and is not a head-node operation.
"""

import argparse
import datetime as _dt
import os
import sys

import numpy as np
import netCDF4 as nc

# Level indices marking land. Zeroing both makes a cell dry at every depth.
LAND_LEVEL = 0

# Legacy jperio value for "cyclic east-west, no fold" (domain.F90:634-642).
JPERIO_IPERIO_ONLY = 1

# Variables holding a first/last wet level, zeroed on the northern wall rows.
LEVEL_VARS = ("top_level", "bottom_level", "mbku", "mbkv", "mbkf")

DEFAULT_TARGET_LAT = -30.0
DEFAULT_WALL_ROWS = 2
DEFAULT_ZONAL_TOL_DEG = 0.10


# --------------------------------------------------------------------------
# helpers shared with audit_domain_cfg.py
# --------------------------------------------------------------------------

def getatt(ds, name, default):
    if name in ds.ncattrs():
        val = ds.getncattr(name)
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        if isinstance(val, (np.ndarray, np.generic)) and np.size(val) == 1:
            val = np.asarray(val).item()
        return val
    return default


def get_scalar_var(ds, name):
    if name not in ds.variables:
        return None
    try:
        return np.asarray(ds.variables[name][:]).ravel()[0].item()
    except (IndexError, ValueError):
        return None


def read_2d(ds, name):
    var = ds.variables[name]
    idx = tuple(0 for _ in range(var.ndim - 2))
    arr = np.ma.asarray(var[idx] if idx else var[:])
    if np.issubdtype(arr.dtype, np.floating):
        return np.ma.filled(arr, np.nan).astype(np.float64)
    return np.ma.filled(arr, 0).astype(np.int64)


def resolve_dimensions(ds):
    """Global sizes from the shape of e3t_0, in Fortran order (x, y, z)."""
    var = ds.variables["e3t_0"]
    fort = var.dimensions[::-1]
    return (ds.dimensions[fort[0]].size,
            ds.dimensions[fort[1]].size,
            ds.dimensions[fort[2]].size)


def resolve_config_identity(ds):
    cd_cfg = getatt(ds, "CfgName", "UNKNOWN")
    kk_cfg = getatt(ds, "CfgIndex", -999)
    if cd_cfg == "UNKNOWN" and kk_cfg == -999:
        if "ORCA" in ds.variables and "ORCA_index" in ds.variables:
            raw = get_scalar_var(ds, "ORCA_index")
            cd_cfg, kk_cfg = "ORCA", (int(round(raw)) if raw is not None else -999)
        else:
            cd_cfg = getatt(ds, "cn_cfg", "UNKNOWN")
            kk_cfg = getatt(ds, "nn_cfg", -999)
    return str(cd_cfg), int(kk_cfg)


def resolve_periodicity(ds):
    """Periodicity as NEMO resolves it, including the legacy fallback."""
    iatt_n = getatt(ds, "NFold", -999)
    catt = str(getatt(ds, "NFtype", "UNKNOWN"))
    ld = {
        "Iperio": getatt(ds, "Iperio", -999) == 1,
        "Jperio": getatt(ds, "Jperio", -999) == 1,
        "NFold": iatt_n == 1,
        "NFtype": catt.strip() if len(catt.strip()) == 1 else "-",
    }
    jperio = get_scalar_var(ds, "jperio")
    if iatt_n == -999 and catt == "UNKNOWN" and jperio is not None:
        ip = int(round(jperio))
        ld["Iperio"] = ip in (1, 4, 6, 7)
        ld["Jperio"] = ip in (2, 7)
        ld["NFold"] = 3 <= ip <= 6
        ld["NFtype"] = "T" if ip in (3, 4) else ("F" if ip in (5, 6) else "-")
    return ld


def find_y_dim(ds):
    if "y" in ds.dimensions:
        return "y"
    cands = [d for d in ds.dimensions if d.lower().startswith("y")]
    if not cands:
        raise SystemExit("ERROR: cannot identify the y dimension in this file")
    return cands[0]


def find_cut_row(gphit, target_lat):
    """Northernmost j whose every cell lies at or south of target_lat."""
    ok = gphit.max(axis=1) <= target_lat
    if not ok[0]:
        raise SystemExit("ERROR: southernmost row already lies north of the target "
                         "latitude -- nothing to retain")
    if ok.all():
        return gphit.shape[0] - 1, 0
    first_fail = int(np.argmin(ok))
    return first_fail - 1, int(ok[first_fail:].sum())


# --------------------------------------------------------------------------
# the trim
# --------------------------------------------------------------------------

def copy_variable(src_var, dst_var, y_axis, ny_new):
    """
    Copy data, slicing the y axis. Variables with more than two dimensions are
    copied one 2-D slab at a time so that the 3-D vertical scale factors of the
    fine grids never have to be held in memory in full.
    """
    if src_var.ndim <= 2:
        idx = [slice(None)] * src_var.ndim
        if y_axis is not None:
            idx[y_axis] = slice(0, ny_new)
        dst_var[...] = src_var[tuple(idx)]
        return

    lead_shape = src_var.shape[:-2]
    for lead in np.ndindex(*lead_shape):
        src_idx = list(lead) + [slice(None), slice(None)]
        dst_idx = list(lead) + [slice(None), slice(None)]
        if y_axis is not None:
            if y_axis < len(lead_shape):                 # y among the leading axes
                raise SystemExit(f"ERROR: unexpected dimension order in "
                                 f"{src_var.name}: {src_var.dimensions}")
            src_idx[y_axis] = slice(0, ny_new)
        dst_var[tuple(dst_idx)] = src_var[tuple(src_idx)]


def trim(src_path, dst_path, target_lat, wall_rows, zonal_tol,
         cfg_name, cfg_index, dry_run):

    log = []

    def w(line=""):
        log.append(line)
        print(line, flush=True)

    w("=" * 78)
    w(f"TRIM  {os.path.basename(src_path)}  ->  {dst_path}")
    w("=" * 78)

    with nc.Dataset(src_path, "r") as src:
        y_dim = find_y_dim(src)
        ny_src = src.dimensions[y_dim].size
        kpi, kpj, kpk = resolve_dimensions(src)
        if kpj != ny_src:
            raise SystemExit(f"ERROR: e3t_0 y extent ({kpj}) disagrees with the "
                             f"'{y_dim}' dimension ({ny_src})")

        gphit = read_2d(src, "gphit")
        j_north, stragglers = find_cut_row(gphit, target_lat)
        ny_new = j_north + 1

        row = gphit[j_north, :]
        spread = float(row.max() - row.min())

        w(f"  source grid          {kpi} x {kpj} x {kpk}   format {src.data_model}")
        w(f"  target latitude      {target_lat:.4f}")
        w(f"  cut row j            {j_north} (0-based)")
        w(f"  rows retained        {ny_new} of {ny_src} "
          f"({100.0 * ny_new / ny_src:.1f} per cent)")
        w(f"  cut row latitude     [{row.min():.6f}, {row.max():.6f}]")
        w(f"  zonal spread         {spread:.6f} degrees")
        w(f"  northern wall        {wall_rows} row(s)")

        if spread > zonal_tol:
            raise SystemExit(f"ERROR: cut row is not zonally uniform "
                             f"(spread {spread:.6f} > tolerance {zonal_tol:.6f}). "
                             f"A constant-j cut is not a constant-latitude cut here.")
        if stragglers:
            raise SystemExit(f"ERROR: {stragglers} rows north of the contiguous block "
                             f"also lie south of the target latitude -- gphit is not "
                             f"monotonic in j. Inspect before trimming.")
        if ny_new <= wall_rows + 1:
            raise SystemExit(f"ERROR: only {ny_new} rows retained, which cannot "
                             f"support a {wall_rows}-row wall")

        src_cfg_name, src_cfg_index = resolve_config_identity(src)
        src_per = resolve_periodicity(src)
        w(f"  source identity      CfgName={src_cfg_name}  CfgIndex={src_cfg_index}")
        w(f"  source periodicity   Iperio={src_per['Iperio']}  "
          f"Jperio={src_per['Jperio']}  NFold={src_per['NFold']}  "
          f"NFtype='{src_per['NFtype']}'")

        if cfg_name is None:
            cfg_name = src_cfg_name
        if cfg_index is None:
            cfg_index = src_cfg_index
        if cfg_name == "UNKNOWN" or cfg_index == -999:
            raise SystemExit(
                "ERROR: the source file does not carry a resolvable configuration "
                "identity. Supply it explicitly with --cfg-name and --cfg-index "
                "(for the 1/4 degree file: --cfg-name ORCA --cfg-index 4).")
        w(f"  output identity      CfgName={cfg_name}  CfgIndex={cfg_index}")

        y_vars = [n for n, v in src.variables.items() if y_dim in v.dimensions]
        other_vars = [n for n in src.variables if n not in y_vars]
        w(f"  variables to slice   {len(y_vars)}")
        w(f"  variables unchanged  {len(other_vars)}")

        if dry_run:
            w("")
            w("  DRY RUN -- no file written")
            return log

        os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
        if os.path.exists(dst_path):
            raise SystemExit(f"ERROR: {dst_path} already exists; remove it first")

        w("")
        w("  writing...")
        with nc.Dataset(dst_path, "w", format=src.data_model) as dst:

            for name, dim in src.dimensions.items():
                size = ny_new if name == y_dim else (None if dim.isunlimited() else dim.size)
                dst.createDimension(name, size)

            for name, sv in src.variables.items():
                filters = sv.filters() or {}
                fill = sv.getncattr("_FillValue") if "_FillValue" in sv.ncattrs() else None

                chunks = None
                if sv.chunking() not in (None, "contiguous"):
                    chunks = [min(c, dst.dimensions[d].size or c)
                              for c, d in zip(sv.chunking(), sv.dimensions)]

                dv = dst.createVariable(
                    name, sv.dtype, sv.dimensions,
                    zlib=bool(filters.get("zlib", False)),
                    complevel=int(filters.get("complevel", 4)),
                    shuffle=bool(filters.get("shuffle", False)),
                    chunksizes=chunks,
                    fill_value=fill,
                )
                for att in sv.ncattrs():
                    if att != "_FillValue":
                        dv.setncattr(att, sv.getncattr(att))

                y_axis = sv.dimensions.index(y_dim) if y_dim in sv.dimensions else None
                copy_variable(sv, dv, y_axis, ny_new)

            # ---- northern land wall ---------------------------------------
            wall_start = ny_new - wall_rows
            killed = 0
            for name in LEVEL_VARS:
                if name not in dst.variables:
                    continue
                lv = dst.variables[name]
                y_axis = lv.dimensions.index(y_dim)
                idx = [slice(None)] * lv.ndim
                idx[y_axis] = slice(wall_start, ny_new)
                if name == "top_level":
                    killed = int((np.asarray(lv[tuple(idx)]) == 1).sum())
                lv[tuple(idx)] = LAND_LEVEL
            w(f"    land wall applied to rows {wall_start}..{ny_new - 1}; "
              f"{killed} previously wet surface cells closed")

            # ---- corrected size scalars -----------------------------------
            for name, value in (("jpiglo", kpi), ("jpjglo", ny_new), ("jpkglo", kpk)):
                if name in dst.variables:
                    dst.variables[name][...] = value
                    w(f"    scalar {name} set to {value}")

            # ---- periodicity ----------------------------------------------
            dst.setncattr("Iperio", np.int32(1))
            dst.setncattr("Jperio", np.int32(0))
            dst.setncattr("NFold", np.int32(0))
            dst.setncattr("NFtype", "-")
            w("    attributes set: Iperio=1 Jperio=0 NFold=0 NFtype='-'")

            if "jperio" in dst.variables:
                dst.variables["jperio"][...] = JPERIO_IPERIO_ONLY
                w(f"    legacy jperio variable set to {JPERIO_IPERIO_ONLY} "
                  f"(cyclic east-west, no fold)")

            # ---- configuration identity -----------------------------------
            dst.setncattr("CfgName", cfg_name)
            dst.setncattr("CfgIndex", np.int32(cfg_index))
            if "ORCA_index" in dst.variables:
                dst.variables["ORCA_index"][...] = cfg_index

            # ---- decomposition attributes, if the source carried them ------
            for att, val in (("DOMAIN_size_global", [kpi, ny_new]),
                             ("DOMAIN_size_local", [kpi, ny_new]),
                             ("DOMAIN_position_last", [kpi, ny_new])):
                if att in src.ncattrs():
                    dst.setncattr(att, np.array(val, dtype=np.int32))

            # ---- provenance ------------------------------------------------
            stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dst.setncattr("TrimScript", "trim_domain_cfg.py")
            dst.setncattr("TrimDate", stamp)
            dst.setncattr("TrimSourceFile", os.path.abspath(src_path))
            dst.setncattr("TrimTargetLat", float(target_lat))
            dst.setncattr("TrimCutRowLat", float(row.max()))
            dst.setncattr("TrimRowsRetained", np.int32(ny_new))
            dst.setncattr("TrimRowsOriginal", np.int32(ny_src))
            dst.setncattr("TrimWallRows", np.int32(wall_rows))
            prior = getatt(src, "history", "")
            dst.setncattr("history",
                          f"{stamp}: trim_domain_cfg.py -- retained j=0..{j_north} "
                          f"(<= {target_lat} degrees), north fold disabled, "
                          f"{wall_rows}-row land wall\n" + str(prior))

    w("  written.")
    return log


# --------------------------------------------------------------------------
# verification
# --------------------------------------------------------------------------

def verify(dst_path, src_path, target_lat, wall_rows, log):
    def w(line=""):
        log.append(line)
        print(line, flush=True)

    w("")
    w("-- verification (re-opened from disk)")
    failures = []

    with nc.Dataset(dst_path, "r") as ds:
        kpi, kpj, kpk = resolve_dimensions(ds)
        y_dim = find_y_dim(ds)
        w(f"   resolved size        {kpi} x {kpj} x {kpk}")
        if kpj != ds.dimensions[y_dim].size:
            failures.append("e3t_0 y extent disagrees with the y dimension")

        per = resolve_periodicity(ds)
        w(f"   resolved periodicity Iperio={per['Iperio']}  Jperio={per['Jperio']}  "
          f"NFold={per['NFold']}  NFtype='{per['NFtype']}'")
        if per["NFold"]:
            failures.append("NORTH FOLD STILL ACTIVE -- fatal")
        if per["Jperio"]:
            failures.append("j-periodicity active -- fatal")
        if not per["Iperio"]:
            failures.append("i-periodicity lost -- fatal")
        if per["NFtype"] != "-":
            failures.append(f"NFtype is '{per['NFtype']}', expected '-'")

        cfg_name, cfg_index = resolve_config_identity(ds)
        w(f"   resolved identity    CfgName={cfg_name}  CfgIndex={cfg_index}")
        if cfg_name == "UNKNOWN" or cfg_index == -999:
            failures.append("configuration identity does not resolve")

        for name, expect in (("jpiglo", kpi), ("jpjglo", kpj), ("jpkglo", kpk)):
            val = get_scalar_var(ds, name)
            if val is not None and int(val) != expect:
                failures.append(f"scalar {name}={int(val)} disagrees with {expect}")
        jp = get_scalar_var(ds, "jperio")
        if jp is not None and int(jp) != JPERIO_IPERIO_ONLY:
            failures.append(f"legacy jperio={int(jp)} not corrected")

        gphit = read_2d(ds, "gphit")
        w(f"   gphit range          [{gphit.min():.6f}, {gphit.max():.6f}]")
        if gphit.max() > target_lat:
            failures.append(f"gphit reaches {gphit.max():.6f}, north of the target")

        if "top_level" in ds.variables:
            top = read_2d(ds, "top_level")
            wet = top == 1
            wall = np.zeros_like(wet)
            wall[kpj - wall_rows:, :] = True
            n_wall_wet = int((wet & wall).sum())
            w(f"   surface-wet cells    {int(wet.sum())}")
            w(f"   wet cells in wall    {n_wall_wet} (must be 0)")
            if n_wall_wet:
                failures.append(f"{n_wall_wet} wet cells remain in the wall rows")
            if wet.any():
                w(f"   wet latitude range   [{gphit[wet].min():.6f}, "
                  f"{gphit[wet].max():.6f}]")
            else:
                failures.append("no surface-wet cells remain -- something is wrong")

        # Field-by-field equality against the source over the retained rows.
        with nc.Dataset(src_path, "r") as src:
            checked, mismatched = 0, []
            for name in ("gphit", "glamt", "e1t", "e2t", "ff_t"):
                if name not in ds.variables or name not in src.variables:
                    continue
                a, b = read_2d(ds, name), read_2d(src, name)[:kpj, :]
                checked += 1
                if not np.allclose(a, b, rtol=0, atol=0, equal_nan=True):
                    mismatched.append(name)
            w(f"   bitwise field check  {checked} field(s) compared to source, "
              f"{len(mismatched)} mismatch(es)")
            for name in mismatched:
                failures.append(f"{name} differs from the source over retained rows")

    w("")
    if failures:
        w(f"   VERIFICATION FAILED ({len(failures)}):")
        for i, f in enumerate(failures, 1):
            w(f"     {i}. {f}")
        return False
    w("   VERIFICATION PASSED")
    return True


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Trim a NEMO domain_cfg file to a target latitude.")
    p.add_argument("source", help="input domain_cfg netCDF file (never modified)")
    p.add_argument("output", help="output path for the trimmed file")
    p.add_argument("--target-lat", type=float, default=DEFAULT_TARGET_LAT,
                   help=f"northern trim latitude (default: {DEFAULT_TARGET_LAT})")
    p.add_argument("--wall-rows", type=int, default=DEFAULT_WALL_ROWS,
                   help=f"northernmost rows forced to land "
                        f"(default: {DEFAULT_WALL_ROWS})")
    p.add_argument("--zonal-tol", type=float, default=DEFAULT_ZONAL_TOL_DEG,
                   help="maximum acceptable latitude spread across the cut row")
    p.add_argument("--cfg-name", default=None,
                   help="CfgName to write (default: as resolved from the source)")
    p.add_argument("--cfg-index", type=int, default=None,
                   help="CfgIndex to write (default: as resolved from the source)")
    p.add_argument("--dry-run", action="store_true",
                   help="report the plan without writing anything")
    p.add_argument("--log", help="also write this report to a file")
    args = p.parse_args()

    log = trim(args.source, args.output, args.target_lat, args.wall_rows,
               args.zonal_tol, args.cfg_name, args.cfg_index, args.dry_run)

    ok = True
    if not args.dry_run:
        ok = verify(args.output, args.source, args.target_lat, args.wall_rows, log)

    if args.log:
        with open(args.log, "w") as fh:
            fh.write("\n".join(log) + "\n")
        print(f"\n[log written to {args.log}]", file=sys.stderr)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
