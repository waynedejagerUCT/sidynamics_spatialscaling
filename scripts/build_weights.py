#!/usr/bin/env python3
"""
build_weights.py -- build SCRIP bilinear interpolation weights for every member of the
SEAICE_DYN_003 resolution hierarchy.

One script serves all targets. The SCRIP tool chain (scripgrid -> scrip -> scripshape) is
driven entirely by a namelist, and the only things that change between members are the
target domain_cfg file and the output filenames. Nothing about the procedure is
resolution-specific, so the member list below is data, not code.

WHAT GETS BUILT
---------------
Two computations per target, three files per target:

    ERA5    -> weights_bilin_era5_<tag>.nc
    GLORYS  -> weights_bilin_glorys_<tag>_sas.nc
               weights_bilin_glorys_<tag>_ice.nc   (byte-identical copy)

The two GLORYS files are identical in content but MUST have distinct filenames, because
the fldread weights cache is keyed by filename (fldread.F90:1078-1080). Two field sets
with different dimensionality cannot share one weights filename. So the second is a copy,
not a second computation.

CONSTRAINTS (all from the SEAICE_DYN_003 README, all still binding)
-------------------------------------------------------------------
* Bilinear, never bicubic. Bicubic smoothing and overshoot would corrupt the turning-angle
  diagnostic, and the corruption would differ by resolution, manufacturing a spurious
  resolution signal.
* T-point weights at every resolution. fld_rot hardcodes 'T' at fldread.F90:750-751
  regardless of which weights were built, so T-point is the internally consistent choice.
* Source grids stay GLOBAL. The weights hold absolute source indices and fldread derives
  the source decomposition from the data file's own dimensions at read time
  (fldread.F90:1200-1201). A subset source reads out of bounds, clamped rather than
  aborted, i.e. silently wrong.
* Weights are bound to the target grid. A weights file paired with a differently-trimmed
  domain fails SILENTLY -- structured interpolation artefacts, not a crash. The trim
  latitude is recorded in the output directory name and in this script's log.

USAGE
-----
    sintx                                  # compute node; GLOB16 is not head-node work
    conda deactivate 2>/dev/null || true
    source /scratch/djgway001/NEMO/env_nemo.sh
    conda activate nemo_analysis           # for the verification step only

    python3 -u build_weights.py --list
    python3 -u build_weights.py --target ORCA025_ANT40S --dry-run
    python3 -u build_weights.py --target ORCA025_ANT40S
    python3 -u build_weights.py --target ORCA025_GLOBAL     # Gate T0 reference
    python3 -u build_weights.py --all

CHECKED AGAINST tools/WEIGHTS/namelist_bilin (the shipped reference) ON 2026-09-14:
    - block/field names (&grid_inputs, &remap_inputs, &shape_inputs): match.
    - ew_wrap = 0: matches the shipped reference.
    - scripgrid requires a file literally named coordinates.nc in its run directory
      (stated in the reference namelist's own comment block) -- this script symlinks
      the real target domain_cfg.nc to that name in each per-source work directory.
    - ERA5/GLORYS longitude/latitude variable names confirmed by ncdump against the
      actual files, not assumed from the reference example (which uses a differently
      named CORE2 forcing file and 'lon'/'lat').
"""

import argparse
import os
import shutil
import subprocess
import sys

try:
    import netCDF4 as _nc4_check   # noqa: F401
    HAVE_NETCDF4 = True
except ImportError:
    HAVE_NETCDF4 = False

NEMO_ROOT = "/scratch/djgway001/NEMO"
WEIGHTS_BIN = f"{NEMO_ROOT}/nemo_5.0/tools/WEIGHTS/BLD/bin"
INPUTS = f"{NEMO_ROOT}/inputs"

TRIM_LAT = -40.0          # recorded in the log; weights are bound to this

# ---------------------------------------------------------------------------
# Targets. tag -> (domain_cfg path, filename token)
#
# ORCA025_GLOBAL is the untrimmed reference needed for the Gate T0 trim-equivalence
# test. It is not a hierarchy member and its weights are throwaway once T0 passes.
# ---------------------------------------------------------------------------
TARGETS = {
    "ORCA2_ANT40S":   (f"{INPUTS}/ORCA2_ANT40S/domain_cfg.nc",   "orca2_ant40s"),
    "ORCA1_ANT40S":   (f"{INPUTS}/ORCA1_ANT40S/domain_cfg.nc",   "orca1_ant40s"),
    "ORCA05_ANT40S":  (f"{INPUTS}/ORCA05_ANT40S/domain_cfg.nc",  "orca05_ant40s"),
    "ORCA025_ANT40S": (f"{INPUTS}/ORCA025_ANT40S/domain_cfg.nc", "orca025_ant40s"),
    "GLOB16_ANT40S":  (f"{INPUTS}/GLOB16_ANT40S/domain_cfg.nc",  "glob16_ant40s"),
    "ORCA025_GLOBAL": (f"{INPUTS}/domain_cfgs/domain_cfg_ORCA025L75.nc", "orca025_global"),
}

# ---------------------------------------------------------------------------
# Sources. A representative file is enough -- scripgrid reads only the coordinate
# axes, and every month of a given source shares them.
#
# VERIFY the lon/lat variable names against the actual files before the first run.
# A wrong name aborts scripgrid, which is the good case; the bad case is a name that
# exists but is the wrong axis.
# ---------------------------------------------------------------------------
SOURCES = {
    "era5": {
        "sample": f"{INPUTS}/ERA5/raw/era5_10u_201903.nc",
        "lon": "longitude",
        "lat": "latitude",
    },
    "glorys": {
        "sample": f"{INPUTS}/GLORYS12/forcing_002/processed/glorys_uo_y2019m03.nc",
        "lon": "longitude",
        "lat": "latitude",
    },
}

# ---------------------------------------------------------------------------
# East-west wrap columns for scripshape.
#
# NOT SAFELY GUESSABLE. NEMO 4.2+ removed the halo from domain_cfg files entirely --
# Ni0glo/Nj0glo are the INNER dimensions and the halo is added at runtime (confirmed in
# the audit) -- which argues for 0. The classic ORCA convention was 2. A wrong value
# produces bad weights along the date line, which shows as a meridional stripe in the
# first output rather than a crash.
#
# Verify on the ORCA025 pair before building the rest: build with 0, run the 72-step
# validation, and plot sst_m across the date line per the README's interpolation check.
# ---------------------------------------------------------------------------
EW_WRAP = 0

NAMELIST_TEMPLATE = """&grid_inputs
    input_file       = '{src_sample}'
    nemo_file        = 'coordinates.nc'
    datagrid_file    = 'remap_data_grid.nc'
    nemogrid_file    = 'remap_nemo_grid.nc'
    method           = 'regular'
    input_lon        = '{src_lon}'
    input_lat        = '{src_lat}'
    nemo_lon         = 'glamt'
    nemo_lat         = 'gphit'
    nemo_mask        = 'none'
    nemo_mask_value  = 10
    input_mask       = 'none'
    input_mask_value = 10
/
&remap_inputs
    num_maps        = 1
    grid1_file      = 'remap_data_grid.nc'
    grid2_file      = 'remap_nemo_grid.nc'
    interp_file1    = 'data_to_nemo.nc'
    interp_file2    = 'nemo_to_data.nc'
    map1_name       = 'data to nemo bilinear mapping'
    map2_name       = 'nemo to data bilinear mapping'
    map_method      = 'bilinear'
    normalize_opt   = 'frac'
    output_opt      = 'scrip'
    restrict_type   = 'latitude'
    num_srch_bins   = 90
    luse_grid1_area = .false.
    luse_grid2_area = .false.
/
&shape_inputs
    interp_file = 'data_to_nemo.nc'
    output_file = '{weights_out}'
    ew_wrap     = {ew_wrap}
/
"""


def run(cmd, cwd, log):
    """Run one SCRIP stage, streaming output to a log file and failing loudly."""
    print(f"    $ {' '.join(cmd)}", flush=True)
    with open(log, "w") as fh:
        proc = subprocess.run(cmd, cwd=cwd, stdout=fh, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        print(f"    FAILED (exit {proc.returncode}); see {log}", file=sys.stderr)
        with open(log) as fh:
            tail = fh.readlines()[-20:]
        sys.stderr.writelines(tail)
        raise SystemExit(1)


def verify(weights_path, domain_cfg):
    """Confirm the weights file matches the target grid it claims to serve.

    Requires netCDF4, which lives in nemo_analysis, not the no-conda build
    environment (convention 6). If unavailable, skip rather than crash --
    the SCRIP stages themselves already succeeded and produced the file;
    this check is a structural cross-check on top, not the build itself.
    """
    if not HAVE_NETCDF4:
        print(f"    verify: SKIPPED (netCDF4 not available in this environment -- "
              f"run 'conda activate nemo_analysis' then "
              f"'python3 build_weights.py --verify-only {os.path.basename(weights_path)}')")
        return

    import netCDF4 as nc
    import numpy as np

    with nc.Dataset(domain_cfg) as d:
        e3t = d.variables["e3t_0"]
        fort = e3t.dimensions[::-1]
        want = (d.dimensions[fort[0]].size, d.dimensions[fort[1]].size)

    with nc.Dataset(weights_path) as w:
        dims = {k: v.size for k, v in w.dimensions.items()}
        # scripshape's SCRIP-format output uses 'lon'/'lat' for the destination grid
        # shape (confirmed against actual output on this tree), not 'x'/'y'.
        got = (dims.get("lon"), dims.get("lat"))
        nsrc = len([v for v in w.variables if v.startswith("src")])
        nwgt = len([v for v in w.variables if v.startswith("wgt")])
        finite = True
        for v in w.variables:
            if v.startswith("wgt"):
                a = np.ma.filled(w.variables[v][:], np.nan)
                if not np.isfinite(a).all():
                    finite = False

    ok = (got == want) and nsrc == 4 and nwgt == 4 and finite
    print(f"    verify: target {want}, weights {got}, "
          f"{nsrc} src / {nwgt} wgt arrays, all finite: {finite}  "
          f"-> {'PASS' if ok else 'FAIL'}")
    if not ok:
        raise SystemExit(f"verification failed for {weights_path}")


def build(target, dry_run, emit_namelist):
    domain_cfg, tag = TARGETS[target]
    if not os.path.exists(domain_cfg):
        raise SystemExit(f"missing domain file: {domain_cfg}")

    outdir = os.path.join(os.path.dirname(domain_cfg), "weights")
    workroot = os.path.join(outdir, ".work")

    print("=" * 74)
    print(f"TARGET {target}")
    print(f"  domain_cfg : {domain_cfg}")
    print(f"  output dir : {outdir}")
    print(f"  trim lat   : {TRIM_LAT}   (weights are bound to this)")
    print("=" * 74)

    for src_name, src in SOURCES.items():
        if not os.path.exists(src["sample"]) and not dry_run:
            raise SystemExit(f"missing source sample: {src['sample']}")

        weights_name = (f"weights_bilin_{src_name}_{tag}.nc" if src_name == "era5"
                        else f"weights_bilin_{src_name}_{tag}_sas.nc")
        work = os.path.join(workroot, src_name)
        namelist = NAMELIST_TEMPLATE.format(
            src_sample=src["sample"], domain_cfg=domain_cfg,
            src_lon=src["lon"], src_lat=src["lat"],
            weights_out=weights_name, ew_wrap=EW_WRAP,
        )

        if emit_namelist:
            print(namelist)
            continue

        print(f"\n  SOURCE {src_name} -> {weights_name}")
        if dry_run:
            print("    [dry run] namelist that would be written:")
            print("    " + namelist.replace("\n", "\n    "))
            continue

        os.makedirs(work, exist_ok=True)
        os.makedirs(outdir, exist_ok=True)

        # scripgrid requires a file literally named coordinates.nc in the run directory
        # (tools/WEIGHTS/namelist_bilin: "scripgrid always needs a coordinates.nc file
        # in the current directory") -- the nemo_file namelist field alone is not
        # sufficient. Symlink the real target in under that name.
        coord_link = os.path.join(work, "coordinates.nc")
        if os.path.lexists(coord_link):
            os.remove(coord_link)
        os.symlink(os.path.abspath(domain_cfg), coord_link)

        nl_path = os.path.join(work, "namelist_reshape_bilin")
        with open(nl_path, "w") as fh:
            fh.write(namelist)

        for stage in ("scripgrid", "scrip", "scripshape"):
            run([os.path.join(WEIGHTS_BIN, f"{stage}.exe"), "namelist_reshape_bilin"],
                cwd=work, log=os.path.join(work, f"{stage}.log"))

        produced = os.path.join(work, weights_name)
        if not os.path.exists(produced):
            raise SystemExit(f"scripshape did not produce {produced}")
        final = os.path.join(outdir, weights_name)
        shutil.move(produced, final)
        verify(final, domain_cfg)

        # The GLORYS weights serve two namelist blocks with different dimensionality,
        # and the fldread cache is keyed by filename, so the second needs its own name.
        if src_name == "glorys":
            ice = final.replace("_sas.nc", "_ice.nc")
            shutil.copyfile(final, ice)
            print(f"    copied -> {os.path.basename(ice)}")

    if not dry_run and not emit_namelist:
        print(f"\n  done. Intermediates left in {workroot} -- delete once satisfied.")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--target", choices=sorted(TARGETS))
    p.add_argument("--all", action="store_true", help="every hierarchy member (not GLOBAL)")
    p.add_argument("--dry-run", action="store_true", help="show namelists, write nothing")
    p.add_argument("--emit-namelist", action="store_true",
                   help="print the namelist only, for diffing against the shipped reference")
    p.add_argument("--list", action="store_true")
    p.add_argument("--verify-only", metavar="TARGET",
                   help="skip building; just verify all weights already built for TARGET "
                        "(run this in nemo_analysis after a build done without conda)")
    args = p.parse_args()

    if args.verify_only:
        if not HAVE_NETCDF4:
            raise SystemExit("--verify-only needs netCDF4: conda activate nemo_analysis")
        domain_cfg, tag = TARGETS[args.verify_only]
        outdir = os.path.join(os.path.dirname(domain_cfg), "weights")
        names = [f"weights_bilin_era5_{tag}.nc",
                 f"weights_bilin_glorys_{tag}_sas.nc",
                 f"weights_bilin_glorys_{tag}_ice.nc"]
        for name in names:
            path = os.path.join(outdir, name)
            if not os.path.exists(path):
                print(f"    MISSING: {path}")
                continue
            print(f"  {name}")
            verify(path, domain_cfg)
        return 0

    if args.list:
        for k, (path, tag) in sorted(TARGETS.items()):
            mark = "ok " if os.path.exists(path) else "MISSING"
            print(f"  {mark}  {k:16s} {tag:16s} {path}")
        return 0

    if args.all:
        targets = [t for t in sorted(TARGETS) if t != "ORCA025_GLOBAL"]
    elif args.target:
        targets = [args.target]
    else:
        p.error("give --target, --all or --list")

    for t in targets:
        build(t, args.dry_run, args.emit_namelist)
    return 0


if __name__ == "__main__":
    sys.exit(main())
