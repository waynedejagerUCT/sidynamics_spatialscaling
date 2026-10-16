#!/usr/bin/env python3
"""
audit_domain_cfg.py -- read-only audit of NEMO 5.0 domain configuration files.

Reports, for each domain_cfg file, everything needed to decide whether it can join
the SEAICE_DYN_003 resolution hierarchy and how it must be handled by the trimming
step. Makes NO modifications to any input file.

The resolution of global dimensions, configuration identity and grid periodicity
replicates SUBROUTINE domain_cfg at src/OCE/DOM/domain.F90:568-654 exactly,
including the legacy-compatibility fallback branches, so that the reported values
are what NEMO itself would resolve at initialisation rather than what the file
appears to say.

Usage
-----
    conda activate nemo_analysis
    python3 audit_domain_cfg.py domain_cfg_*.nc
    python3 audit_domain_cfg.py domain_cfg_ORCA05L*.nc --target-lat -30.0
    python3 audit_domain_cfg.py domain_cfg_*.nc --output AUDIT.txt --json AUDIT.json

Notes
-----
Only two-dimensional fields are read into memory; the three-dimensional vertical
scale factors are inspected for shape only. Peak memory is a few hundred megabytes
for the 1/16 degree file, so a head-node run is acceptable, but use an interactive
compute session (sintx) if in doubt.

MIZ  = marginal ice zone
CFL  = Courant-Friedrichs-Lewy (advective stability condition)
"""

import argparse
import json
import os
import sys

import numpy as np
import netCDF4 as nc

# Ice-shelf cavities are indicated by a first wet level deeper than 1.
CAVITY_THRESHOLD = 1

# Rows are treated as constant-latitude only if the spread across i is below this.
DEFAULT_ZONAL_TOL_DEG = 0.10

# Latitude band used for the coastline-comparability statistics.
ANTARCTIC_BAND_LAT = -60.0

# Latitude band used to report grid spacing relevant to the CFL estimate.
CFL_BAND_LAT = (-67.0, -63.0)


# --------------------------------------------------------------------------
# low-level readers
# --------------------------------------------------------------------------

def _leading_index(var, keep=2):
    """Index tuple that drops all dimensions except the trailing `keep` of them."""
    return tuple(0 for _ in range(var.ndim - keep))


def read_2d(ds, name, fill_float=np.nan, fill_int=0):
    """Read a variable as a plain 2-D (y, x) array, dropping leading t and z axes."""
    var = ds.variables[name]
    idx = _leading_index(var, keep=2)
    arr = var[idx] if idx else var[:]
    arr = np.ma.asarray(arr)
    n_masked = int(np.ma.count_masked(arr))
    if np.issubdtype(arr.dtype, np.floating):
        out = np.ma.filled(arr, fill_float).astype(np.float64)
    else:
        out = np.ma.filled(arr, fill_int).astype(np.int64)
    return out, n_masked


def getatt(ds, name, default):
    """Global attribute lookup mirroring iom_getatt's not-found defaults."""
    if name in ds.ncattrs():
        val = ds.getncattr(name)
        if isinstance(val, bytes):
            val = val.decode("utf-8", errors="replace")
        if isinstance(val, np.ndarray) and val.size == 1:
            val = val.item()
        return val
    return default


def get_scalar_var(ds, name):
    """Read a scalar netCDF variable, returning None if absent."""
    if name not in ds.variables:
        return None
    try:
        return np.asarray(ds.variables[name][:]).ravel()[0].item()
    except (IndexError, ValueError):
        return None


# --------------------------------------------------------------------------
# replication of domain.F90:568-654
# --------------------------------------------------------------------------

def resolve_dimensions(ds):
    """
    Global sizes from the SHAPE of e3t_0, as NEMO does at domain.F90:616-619.

    iom_varid returns dimension sizes in Fortran order, so idimsz(1:3) are the
    x, y and z extents. netCDF4 reports dimensions in C order, hence the reversal.
    Any scalar jpiglo/jpjglo/jpkglo variables in the file are NOT read by NEMO.
    """
    if "e3t_0" not in ds.variables:
        return None, None, None, None, "e3t_0 ABSENT -- NEMO cannot resolve dimensions"

    var = ds.variables["e3t_0"]
    fortran_dims = var.dimensions[::-1]
    if len(fortran_dims) < 3:
        return None, None, None, var.dimensions, "e3t_0 has fewer than 3 dimensions"

    kpi = ds.dimensions[fortran_dims[0]].size
    kpj = ds.dimensions[fortran_dims[1]].size
    kpk = ds.dimensions[fortran_dims[2]].size
    return kpi, kpj, kpk, var.dimensions, None


def resolve_config_identity(ds):
    """Configuration name and index, replicating domain.F90:598-614."""
    cd_cfg = getatt(ds, "CfgName", "UNKNOWN")
    kk_cfg = getatt(ds, "CfgIndex", -999)
    route = "modern attributes (CfgName/CfgIndex)"

    if cd_cfg == "UNKNOWN" and kk_cfg == -999:
        has_orca = "ORCA" in ds.variables and "ORCA_index" in ds.variables
        if has_orca:
            cd_cfg = "ORCA"
            raw = get_scalar_var(ds, "ORCA_index")
            kk_cfg = int(round(raw)) if raw is not None else -999
            route = "legacy variables (ORCA/ORCA_index)"
        else:
            cd_cfg = getatt(ds, "cn_cfg", "UNKNOWN")
            kk_cfg = getatt(ds, "nn_cfg", -999)
            route = "attributes (cn_cfg/nn_cfg)"

    if cd_cfg == "UNKNOWN" and kk_cfg == -999:
        route = "NONE -- resolves to UNKNOWN / -999"

    return str(cd_cfg), int(kk_cfg), route


def resolve_periodicity(ds):
    """
    Grid periodicity and north fold, replicating domain.F90:622-643.

    The legacy fallback fires only when BOTH the NFold integer attribute and the
    NFtype character attribute are absent AND a jperio variable exists. Writing a
    real NFold/NFtype pair is therefore what disables it; overwriting jperio alone
    would not.
    """
    iatt_i = getatt(ds, "Iperio", -999)
    iatt_j = getatt(ds, "Jperio", -999)
    iatt_n = getatt(ds, "NFold", -999)
    catt = str(getatt(ds, "NFtype", "UNKNOWN"))

    ld_iperio = (iatt_i == 1)
    ld_jperio = (iatt_j == 1)
    ld_nfold = (iatt_n == 1)
    nftype = catt.strip() if len(catt.strip()) == 1 else "-"
    route = "modern attributes (Iperio/Jperio/NFold/NFtype)"

    jperio = get_scalar_var(ds, "jperio")
    legacy_fired = False
    if iatt_n == -999 and catt == "UNKNOWN" and jperio is not None:
        legacy_fired = True
        ip = int(round(jperio))
        ld_iperio = ip in (1, 4, 6, 7)
        ld_jperio = ip in (2, 7)
        ld_nfold = 3 <= ip <= 6
        if ip in (3, 4):
            nftype = "T"
        elif ip in (5, 6):
            nftype = "F"
        else:
            nftype = "-"
        route = f"LEGACY fallback from jperio variable (= {ip})"

    return {
        "Iperio": bool(ld_iperio),
        "Jperio": bool(ld_jperio),
        "NFold": bool(ld_nfold),
        "NFtype": nftype,
        "route": route,
        "legacy_fired": legacy_fired,
        "jperio_variable": jperio,
        "attrs_present": {
            "Iperio": iatt_i != -999,
            "Jperio": iatt_j != -999,
            "NFold": iatt_n != -999,
            "NFtype": catt != "UNKNOWN",
        },
    }


# --------------------------------------------------------------------------
# grid geometry and the proposed cut
# --------------------------------------------------------------------------

def surface_wet_mask(ds):
    """
    Boolean mask of cells wet at the SURFACE (ocean level 1).

    This is the mask that matters under a standalone sea-ice configuration: it sets
    tmask(:,:,1), which sets fimask at icedyn_rhg_evp.F90:220-221, which shapes
    coastal ice deformation. Cells under an ice-shelf cavity (top_level > 1) are dry
    at the surface even though the column below them is ocean.
    """
    if "top_level" in ds.variables:
        top, _ = read_2d(ds, "top_level")
        return (top == 1), top, "top_level == 1"
    if "bottom_level" in ds.variables:
        bot, _ = read_2d(ds, "bottom_level")
        return (bot > 0), None, "bottom_level > 0 (top_level absent)"
    return None, None, "UNAVAILABLE -- neither top_level nor bottom_level present"


def find_cut_row(gphit, target_lat):
    """
    Northernmost j retained such that EVERY cell in that row lies at or south of
    target_lat, taking the contiguous block from the southern edge.

    Latitude is the fixed quantity and the row index is derived, so the same
    criterion applies unchanged at every resolution in the hierarchy.
    """
    row_max = gphit.max(axis=1)
    ok = row_max <= target_lat

    if not ok[0]:
        return None, {"error": "southernmost row already lies north of the target latitude"}

    if ok.all():
        j_north = gphit.shape[0] - 1
        stragglers = 0
    else:
        first_fail = int(np.argmin(ok))
        j_north = first_fail - 1
        stragglers = int(ok[first_fail:].sum())

    row = gphit[j_north, :]
    info = {
        "j_north_0based": int(j_north),
        "j_north_1based": int(j_north + 1),
        "rows_retained": int(j_north + 1),
        "rows_total": int(gphit.shape[0]),
        "fraction_retained": float((j_north + 1) / gphit.shape[0]),
        "row_lat_min": float(row.min()),
        "row_lat_max": float(row.max()),
        "zonal_spread_deg": float(row.max() - row.min()),
        "next_row_lat_max": (float(gphit[j_north + 1, :].max())
                             if j_north + 1 < gphit.shape[0] else None),
        "stragglers_north": stragglers,
    }
    return j_north, info


def spacing_stats(ds, gphit, wet, j_north):
    """Grid spacing within the retained domain, for CFL and offset scoping."""
    out = {}
    for name, label in (("e1t", "zonal"), ("e2t", "meridional")):
        if name not in ds.variables:
            continue
        e, _ = read_2d(ds, name)
        sel = np.zeros_like(gphit, dtype=bool)
        sel[: j_north + 1, :] = True
        if wet is not None:
            sel &= wet
        if sel.any():
            out[f"{name}_min_km_retained"] = float(np.nanmin(e[sel]) / 1000.0)
            out[f"{name}_median_km_retained"] = float(np.nanmedian(e[sel]) / 1000.0)

        band = sel & (gphit >= CFL_BAND_LAT[0]) & (gphit <= CFL_BAND_LAT[1])
        if band.any():
            out[f"{name}_median_km_65S"] = float(np.nanmedian(e[band]) / 1000.0)
    return out


def variable_inventory(ds):
    """Split variables by whether they carry the y dimension and must be sliced."""
    y_dim = "y" if "y" in ds.dimensions else None
    if y_dim is None:
        candidates = [d for d in ds.dimensions if d.lower().startswith("y")]
        y_dim = candidates[0] if candidates else None

    to_slice, pass_through = [], []
    for name, var in ds.variables.items():
        (to_slice if (y_dim and y_dim in var.dimensions) else pass_through).append(name)
    return y_dim, sorted(to_slice), sorted(pass_through)


# --------------------------------------------------------------------------
# per-file audit
# --------------------------------------------------------------------------

def audit_file(path, target_lat, zonal_tol, out):
    def w(line=""):
        out.append(line)

    rec = {"path": os.path.abspath(path)}
    warnings = []

    w("=" * 78)
    w(f"FILE   {os.path.basename(path)}")
    w("=" * 78)

    if not os.path.exists(path):
        w("  MISSING -- file does not exist")
        rec["error"] = "missing"
        return rec, ["file does not exist"]

    size_gb = os.path.getsize(path) / 1024**3
    rec["size_gb"] = round(size_gb, 3)

    with nc.Dataset(path, "r") as ds:
        rec["format"] = ds.data_model
        w(f"  size {size_gb:8.3f} GB      format {ds.data_model}")

        dims = {k: (v.size, v.isunlimited()) for k, v in ds.dimensions.items()}
        w("  dimensions: " + ", ".join(
            f"{k}={s}{' (UNLIMITED)' if u else ''}" for k, (s, u) in dims.items()))
        rec["dimensions"] = {k: s for k, (s, _) in dims.items()}

        # -- dimensions as NEMO resolves them -------------------------------
        kpi, kpj, kpk, e3t_dims, err = resolve_dimensions(ds)
        w("")
        w("  -- global size, resolved from the SHAPE of e3t_0 (domain.F90:616-619)")
        if err:
            w(f"     {err}")
            warnings.append(err)
            rec["error"] = err
            return rec, warnings
        w(f"     e3t_0 dimensions (C order): {e3t_dims}")
        w(f"     Ni0glo = {kpi}    Nj0glo = {kpj}    jpkglo = {kpk}")
        rec.update({"Ni0glo": kpi, "Nj0glo": kpj, "jpkglo": kpk})

        # Scalar variables and decomposition attributes are NOT read by NEMO and
        # routinely go stale after an offline slice.
        stale = []
        for vname, actual in (("jpiglo", kpi), ("jpjglo", kpj), ("jpkglo", kpk)):
            val = get_scalar_var(ds, vname)
            if val is not None:
                flag = "OK" if int(val) == actual else "STALE"
                w(f"     scalar variable {vname:8s} = {int(val):6d}  ({flag}, not read by NEMO)")
                if int(val) != actual:
                    stale.append(f"{vname}={int(val)} vs actual {actual}")
        dsg = getatt(ds, "DOMAIN_size_global", None)
        if dsg is not None:
            dsg = [int(v) for v in np.atleast_1d(dsg)]
            flag = "OK" if dsg[:2] == [kpi, kpj] else "STALE"
            w(f"     attribute DOMAIN_size_global = {dsg}  ({flag}, not read by NEMO)")
            if dsg[:2] != [kpi, kpj]:
                stale.append(f"DOMAIN_size_global={dsg} vs actual [{kpi}, {kpj}]")
        rec["stale_metadata"] = stale
        if stale:
            warnings.append("stale metadata present (harmless, NEMO ignores it): "
                            + "; ".join(stale))

        # -- configuration identity ----------------------------------------
        cd_cfg, kk_cfg, cfg_route = resolve_config_identity(ds)
        w("")
        w("  -- configuration identity (domain.F90:598-614)")
        w(f"     CfgName = {cd_cfg}    CfgIndex = {kk_cfg}")
        w(f"     resolved via: {cfg_route}")
        rec.update({"CfgName": cd_cfg, "CfgIndex": kk_cfg, "cfg_route": cfg_route})
        if cd_cfg == "UNKNOWN":
            warnings.append("configuration identity resolves to UNKNOWN/-999 "
                            "(cosmetic only; appears as such in ocean.output)")

        # -- periodicity ----------------------------------------------------
        per = resolve_periodicity(ds)
        w("")
        w("  -- periodicity and north fold (domain.F90:622-643)")
        w(f"     Iperio = {per['Iperio']}   Jperio = {per['Jperio']}   "
          f"NFold = {per['NFold']}   NFtype = '{per['NFtype']}'")
        w(f"     resolved via: {per['route']}")
        present = ", ".join(k for k, v in per["attrs_present"].items() if v) or "none"
        w(f"     modern attributes present: {present}")
        if per["jperio_variable"] is not None:
            w(f"     legacy jperio variable present, value = {int(per['jperio_variable'])}")
        rec["periodicity"] = {k: per[k] for k in
                              ("Iperio", "Jperio", "NFold", "NFtype", "route", "legacy_fired")}
        rec["periodicity"]["jperio_variable"] = per["jperio_variable"]

        if per["legacy_fired"]:
            warnings.append(
                "periodicity comes from the LEGACY jperio fallback. The trim must write "
                "real NFold and NFtype attributes to disable that branch -- overwriting "
                "jperio alone would not.")
        if per["NFold"]:
            w("     NOTE: a north fold is active. After trimming, the northern edge is an")
            w("           ordinary open row and the fold MUST be disabled "
              "(NFold=0, NFtype='-').")

        # -- cavities -------------------------------------------------------
        wet, top, wet_route = surface_wet_mask(ds)
        w("")
        w("  -- ice-shelf cavities and the surface land-sea mask")
        w(f"     surface wet mask from: {wet_route}")
        isfcav_attr = getatt(ds, "IsfCav", None)
        isfcav_var = get_scalar_var(ds, "ln_isfcav")
        w(f"     declared: IsfCav attribute = {isfcav_attr}, "
          f"ln_isfcav variable = {isfcav_var}")
        if top is not None:
            n_cav = int((top > CAVITY_THRESHOLD).sum())
            w(f"     top_level range = [{int(top.min())}, {int(top.max())}]   "
              f"cavity cells (top_level > 1) = {n_cav}")
            rec["cavity_cells"] = n_cav
            rec["top_level_range"] = [int(top.min()), int(top.max())]
            if n_cav > 0 and not (isfcav_attr == 1 or isfcav_var == 1):
                warnings.append("cavity cells present but the declared cavity flag is not set "
                                "-- trust the array, not the label")
            if n_cav == 0 and (isfcav_attr == 1 or isfcav_var == 1):
                warnings.append("cavity flag is set but no cavity cells exist "
                                "-- trust the array, not the label")
        rec["IsfCav_attr"] = isfcav_attr
        rec["ln_isfcav_var"] = isfcav_var

        # -- geometry and the proposed cut ----------------------------------
        if "gphit" not in ds.variables:
            w("")
            w("  gphit ABSENT -- cannot evaluate the trim")
            warnings.append("gphit absent")
            return rec, warnings

        gphit, n_masked = read_2d(ds, "gphit")
        if n_masked:
            warnings.append(f"gphit carries {n_masked} masked values")

        w("")
        w("  -- grid geometry")
        w(f"     gphit range = [{gphit.min():.6f}, {gphit.max():.6f}]")
        rec["gphit_min"] = float(gphit.min())
        rec["gphit_max"] = float(gphit.max())

        if wet is not None:
            south_wet = float(gphit[wet].min())
            w(f"     southernmost surface-wet latitude = {south_wet:.6f}")
            rec["southernmost_wet_lat"] = south_wet
            rec["wet_cells_total"] = int(wet.sum())
            band = wet & (gphit <= ANTARCTIC_BAND_LAT)
            rec["wet_cells_south_of_60S"] = int(band.sum())
            w(f"     surface-wet cells: {int(wet.sum())} total, "
              f"{int(band.sum())} south of {ANTARCTIC_BAND_LAT:.0f} degrees")

        j_north, cut = find_cut_row(gphit, target_lat)
        w("")
        w(f"  -- proposed trim at {target_lat:.2f} degrees latitude")
        if j_north is None:
            w(f"     {cut['error']}")
            warnings.append(cut["error"])
            rec["cut"] = cut
            return rec, warnings

        w(f"     northernmost retained row j = {cut['j_north_0based']} "
          f"(0-based) / {cut['j_north_1based']} (1-based)")
        w(f"     rows retained = {cut['rows_retained']} of {cut['rows_total']} "
          f"({100 * cut['fraction_retained']:.1f} per cent)")
        w(f"     that row spans latitude [{cut['row_lat_min']:.6f}, "
          f"{cut['row_lat_max']:.6f}]")
        w(f"     zonal spread across the row = {cut['zonal_spread_deg']:.6f} degrees")
        if cut["next_row_lat_max"] is not None:
            w(f"     first discarded row reaches {cut['next_row_lat_max']:.6f}")
        w(f"     approximate reduction factor = "
          f"{1.0 / cut['fraction_retained']:.2f}x")
        rec["cut"] = cut

        if cut["zonal_spread_deg"] > zonal_tol:
            warnings.append(
                f"cut row is not zonally uniform: spread {cut['zonal_spread_deg']:.4f} "
                f"degrees exceeds tolerance {zonal_tol:.4f}. A constant-j cut is NOT a "
                f"constant-latitude cut on this grid.")
        if cut["stragglers_north"]:
            warnings.append(
                f"{cut['stragglers_north']} rows north of the contiguous block also lie "
                f"south of the target latitude -- grid is non-monotonic in j; inspect "
                f"before trimming")

        # -- spacing --------------------------------------------------------
        sp = spacing_stats(ds, gphit, wet, j_north)
        if sp:
            w("")
            w("  -- grid spacing within the retained domain")
            for k in sorted(sp):
                w(f"     {k:32s} {sp[k]:10.3f}")
            rec["spacing"] = sp

        # -- variable inventory ---------------------------------------------
        y_dim, to_slice, pass_through = variable_inventory(ds)
        w("")
        w(f"  -- variable inventory (y dimension = '{y_dim}')")
        w(f"     {len(to_slice)} variables carry y and MUST be sliced:")
        w("       " + ", ".join(to_slice))
        w(f"     {len(pass_through)} variables do not and pass through unchanged:")
        w("       " + (", ".join(pass_through) if pass_through else "(none)"))
        rec["vars_to_slice"] = to_slice
        rec["vars_pass_through"] = pass_through

    # -- warnings -----------------------------------------------------------
    w("")
    if warnings:
        w(f"  WARNINGS ({len(warnings)}):")
        for i, msg in enumerate(warnings, 1):
            w(f"    {i}. {msg}")
    else:
        w("  WARNINGS: none")
    w("")

    rec["warnings"] = warnings
    return rec, warnings


# --------------------------------------------------------------------------

def summary_table(records, target_lat, out):
    out.append("=" * 78)
    out.append(f"SUMMARY -- proposed trim at {target_lat:.2f} degrees latitude")
    out.append("=" * 78)
    hdr = (f"{'file':<28}{'Ni0glo':>8}{'Nj0glo':>8}{'jpk':>6}"
           f"{'fold':>6}{'cav':>6}{'keep':>8}{'frac':>8}")
    out.append(hdr)
    out.append("-" * len(hdr))
    for r in records:
        if "Ni0glo" not in r:
            out.append(f"{os.path.basename(r['path']):<28}{'--':>8}")
            continue
        per = r.get("periodicity", {})
        fold = (per.get("NFtype", "?") if per.get("NFold") else "none")
        cut = r.get("cut", {})
        keep = cut.get("rows_retained", "--")
        frac = cut.get("fraction_retained")
        out.append(
            f"{os.path.basename(r['path']):<28}"
            f"{r['Ni0glo']:>8}{r['Nj0glo']:>8}{r['jpkglo']:>6}"
            f"{fold:>6}{r.get('cavity_cells', '?'):>6}"
            f"{keep:>8}"
            f"{(f'{100 * frac:.1f}%' if frac else '--'):>8}")
    out.append("")


def main():
    p = argparse.ArgumentParser(
        description="Read-only audit of NEMO domain_cfg files for the "
                    "SEAICE_DYN_003 resolution hierarchy.")
    p.add_argument("files", nargs="+", help="domain_cfg netCDF files to audit")
    p.add_argument("--target-lat", type=float, default=-30.0,
                   help="northern trim latitude in degrees (default: -30.0)")
    p.add_argument("--zonal-tol", type=float, default=DEFAULT_ZONAL_TOL_DEG,
                   help="maximum acceptable latitude spread across the cut row, "
                        f"in degrees (default: {DEFAULT_ZONAL_TOL_DEG})")
    p.add_argument("--output", help="also write the text report to this path")
    p.add_argument("--json", dest="json_path",
                   help="write a machine-readable record to this path")
    args = p.parse_args()

    out = []
    out.append(f"NEMO domain_cfg audit -- target trim latitude {args.target_lat:.2f} degrees")
    out.append(f"netCDF4 {nc.__version__}, numpy {np.__version__}")
    out.append("")

    records, total_warnings = [], 0
    for path in args.files:
        try:
            rec, warns = audit_file(path, args.target_lat, args.zonal_tol, out)
        except Exception as exc:                      # keep auditing the remaining files
            out.append(f"  FAILED: {type(exc).__name__}: {exc}")
            out.append("")
            rec, warns = {"path": os.path.abspath(path), "error": str(exc)}, [str(exc)]
        records.append(rec)
        total_warnings += len(warns)

    summary_table(records, args.target_lat, out)
    out.append(f"{len(records)} file(s) audited, {total_warnings} warning(s) total.")

    text = "\n".join(out)
    print(text)

    if args.output:
        with open(args.output, "w") as fh:
            fh.write(text + "\n")
        print(f"\n[text report written to {args.output}]", file=sys.stderr)

    if args.json_path:
        with open(args.json_path, "w") as fh:
            json.dump({"target_lat": args.target_lat, "files": records}, fh, indent=2)
        print(f"[json record written to {args.json_path}]", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
