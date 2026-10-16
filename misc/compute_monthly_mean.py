#!/usr/bin/env python3
"""
Compute monthly mean sea ice drift (speed, dX, dY) from daily SH files.
One output file per year-month, e.g. sh_monthly_mean_1991_01.nc

Speed is computed PER DAY first (hypot of dX,dY), then averaged over the
month -- this is the correct order (see prior discussion: averaging dX/dY
first and then taking the magnitude gives NET drift, not mean speed).
"""

import xarray as xr
import numpy as np
from pathlib import Path

BASE = Path("/home/waynedj/Data/seaicedrift/osisaf/24hr/south/merged")
OUT_DIR = BASE / "monthly_mean"
OUT_DIR.mkdir(exist_ok=True)

YEARS = range(1991, 2026)  # 1991-2025 inclusive

for yr in YEARS:
    for mo in range(1, 13):
        month_dir = BASE / str(yr) / f"{mo:02d}"
        files = sorted(month_dir.glob("*.nc"))

        if not files:
            print(f"{yr}-{mo:02d}: no files found, skipping")
            continue

        # open all daily files for the month, stacked along time
        # data_vars="minimal": lat/lon are a fixed grid (no time dimension),
        # so don't stack them across files -- only concat variables that
        # actually vary with time (dX, dY, status_flag, etc.)
        ds = xr.open_mfdataset(files, combine="by_coords", data_vars="minimal")

        # keep only good-quality vectors (flag >= 20); reject everything else
        good = ds["status_flag"] >= 20
        dX = ds["dX"].where(good)
        dY = ds["dY"].where(good)

        # daily speed (km/day, since displacement is over a fixed 24h window)
        speed = np.hypot(dX, dY)

        # monthly means, skipping NaNs (masked/missing days per pixel)
        dX_mean = dX.mean(dim="time", skipna=True)
        dY_mean = dY.mean(dim="time", skipna=True)
        speed_mean = speed.mean(dim="time", skipna=True)

        # number of valid (unmasked) days per pixel -- useful for later
        # applying a minimum-coverage threshold in the climatology step
        n_valid = good.sum(dim="time")

        # assemble output dataset, carry over lat/lon for reference
        out = xr.Dataset(
            {
                "dX_mean": dX_mean,
                "dY_mean": dY_mean,
                "speed_mean": speed_mean,
                "n_valid_days": n_valid,
            },
            coords={"lat": ds["lat"], "lon": ds["lon"]},
        )
        out["speed_mean"].attrs = {}  # clear inherited dX attrs before relabeling
        out["speed_mean"].attrs["units"] = "km/day"
        out["speed_mean"].attrs["long_name"] = "mean daily speed over the month"
        out["dX_mean"].attrs["units"] = "km"
        out["dY_mean"].attrs["units"] = "km"
        out["n_valid_days"].attrs = {}  # clear inherited status_flag attrs
        out["n_valid_days"].attrs["long_name"] = "number of days with good-quality vector (status_flag >= 20)"

        # record which product (cdr/icdr) this month came from, since
        # dX/dY/status_flag are identical between the two -- filenames
        # are the only place this info exists otherwise
        out.attrs["source_product"] = "cdr" if "cdr-v1p0" in files[0].name else "icdr"

        out_name = f"sh_monthly_mean_{yr}_{mo:02d}.nc"
        out.to_netcdf(OUT_DIR / out_name)

        ds.close()

        print(f"{yr}-{mo:02d}: {len(files)} daily files -> {out_name}")

print("Done.")
