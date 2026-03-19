import os
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from src.pydantic_models import EarthdataDownloadVisualizeServiceRequest


def create_requested_var_names(
    request_params: EarthdataDownloadVisualizeServiceRequest,
) -> tuple[str, str]:
    requested_vars_slashes = [
        f"/{request_params.product}/Latitude",
        f"/{request_params.product}/Longitude",
    ]
    if request_params.include_scan_time_arrays:
        requested_vars_slashes.extend(
            [
                f"/{request_params.product}/ScanTime/Year",
                f"/{request_params.product}/ScanTime/Month",
                f"/{request_params.product}/ScanTime/DayOfMonth",
                f"/{request_params.product}/ScanTime/DayOfYear",
                f"/{request_params.product}/ScanTime/Hour",
                f"/{request_params.product}/ScanTime/Minute",
                f"/{request_params.product}/ScanTime/Second",
                f"/{request_params.product}/ScanTime/MilliSecond",
            ]
        )
    for var in request_params.observable_vars:
        if var not in requested_vars_slashes:
            requested_vars_slashes.append(var)

    requested_vars_underscores = [
        v[1:].replace("/", "_") for v in requested_vars_slashes
    ]
    return requested_vars_slashes, requested_vars_underscores


def extract_track_number_from_h5_url_or_fpath(
    h5_url_or_fpath: str,
    request_params: EarthdataDownloadVisualizeServiceRequest,
) -> str:
    fname = h5_url_or_fpath.split("/")[-1]
    bname = os.path.splitext(fname)[0]
    parts = bname.split(request_params.hdf5_bname_delimiter)
    track_number = parts[request_params.hdf5_bname_track_number_part_idx]
    return track_number


def extract_track_start_timestamp_from_h5_url_or_fpath(
    h5_url_or_fpath: str,
    request_params: EarthdataDownloadVisualizeServiceRequest,
) -> datetime:
    """
    Extract the track start timestamp from an HDF5 filename or URL and return a datetime object.

    Expected part format: "<yyyy><mm><dd>-S<hh><mm><ss>-E<hh><mm><ss>"
    Example part: "20251101-S023933-E041248" -> returns datetime(2025,11,1,2,39,33)

    Raises ValueError if the expected pattern cannot be found.
    """
    fname = h5_url_or_fpath.split("/")[-1]
    bname = os.path.splitext(fname)[0]
    parts = bname.split(request_params.hdf5_bname_delimiter)
    track_timestamps = parts[request_params.hdf5_bname_track_start_part_idx]

    m = re.search(r"(?P<date>\d{8})-S(?P<start>\d{6})", track_timestamps)
    if not m:
        raise ValueError(
            f"Couldn't parse start timestamp from '{track_timestamps}' in '{h5_url_or_fpath}'"
        )

    date = m.group("date")  # YYYYMMDD
    start = m.group("start")  # HHMMSS

    year = int(date[0:4])
    month = int(date[4:6])
    day = int(date[6:8])

    hour = int(start[0:2])
    minute = int(start[2:4])
    second = int(start[4:6])

    return datetime(year, month, day, hour, minute, second)


def _sanitize_track_basename(track_fname: str) -> str:
    # remove path separators and extension to use as HDF5 group/file base name
    base = Path(track_fname).name
    # remove or replace characters that might be awkward in group names
    return base.replace("/", "_").replace("\\", "_")


def _make_hdf5_path_from_field(field_name: str) -> list[str]:
    """
    Convert a field name like 'FS_VER_sigmaZeroNPCorrected' or 'FS_Latitude'
    into a list describing the path components: ['FS', 'VER', 'sigmaZeroNPCorrected']
    """
    # split on underscore — assumes fields begin with 'FS_...' as in your example
    parts = field_name.split("_")
    return parts


def _ensure_numpy(arr):
    if isinstance(arr, np.ndarray):
        return arr
    try:
        return np.asarray(arr)
    except Exception:
        # fallback: try to serialize to string
        return np.array(str(arr))
