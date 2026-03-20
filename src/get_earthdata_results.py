import os
import pprint
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import earthaccess
import h5py
import numpy as np
from loguru import logger
from pydap.client import open_url
from pydap.net import create_session

from src.config import (
    B2_SAVED_RESULTS_ROOTDIR,
    EARTHDATA_MAX_NUM_REQUESTS_PER_SEC,
    EDL_TOKEN,
    LOCAL_SAVED_RESULTS_ROOTDIR,
)
from src.pydantic_models import EarthdataDownloadVisualizeServiceRequest
from src.utils.b2 import B2_BUCKET
from src.utils.common import (
    _ensure_numpy,
    _make_hdf5_path_from_field,
    _sanitize_track_basename,
    create_requested_var_names,
)

pp = pprint.PrettyPrinter(indent=4, width=200)


def get_search_data_results(
    request_params: EarthdataDownloadVisualizeServiceRequest,
) -> list[str]:
    temporal = (
        f"{request_params.date_min}T00:00:00Z",
        f"{request_params.date_max}T23:59:59Z",
    )

    results = earthaccess.search_data(
        short_name=request_params.product_short_name,
        bounding_box=(
            request_params.lon_min,
            request_params.lat_min,
            request_params.lon_max,
            request_params.lat_max,
        ),
        temporal=temporal,
        count=-1,
    )

    return results


def _process_granule(
    opendap_url_no_slicing: str,
    requested_vars_underscores: list[str],
    request_params: EarthdataDownloadVisualizeServiceRequest,
    token: str,
) -> tuple[str, dict]:
    """Process a single granule: fetch full lat/lon via pydap to find scan indices,
    then fetch only the sliced rows for all requested variables.

    Each call creates its own session so threads don't share a non-thread-safe
    requests.Session.
    """
    session = create_session(session_kwargs={"token": token})

    # Open for metadata only — pydap fetches the DDS (shape/type info) without
    # downloading any array data. Reused for ndim lookups in Round Trip 2.
    ds = open_url(opendap_url_no_slicing, session=session)

    # --- Round trip 1: full lat/lon to determine scan index range ---
    # DAP4 CE [start:stride:end] with stride 1 fetches the complete swath.
    # Use explicit bounds (no empty []) to avoid a pydap dimension-swap bug.
    stride_val = 1
    n_scans, n_pixels = ds["FS_Latitude"].shape[:2]
    url_latlon = opendap_url_no_slicing.replace(
        "FS_Latitude",
        f"FS_Latitude[0:{stride_val}:{n_scans - 1}][0:{stride_val}:{n_pixels - 1}]",
    ).replace(
        "FS_Longitude",
        f"FS_Longitude[0:{stride_val}:{n_scans - 1}][0:{stride_val}:{n_pixels - 1}]",
    )
    ds_latlon = open_url(url_latlon, session=session)
    lat = np.array([row for row in ds_latlon["FS_Latitude"].data[:]])
    lon = np.array([row for row in ds_latlon["FS_Longitude"].data[:]])

    mask = (
        (lat >= request_params.lat_min)
        & (lat <= request_params.lat_max)
        & (lon >= request_params.lon_min)
        & (lon <= request_params.lon_max)
    )
    scan_idx = np.where(mask.any(axis=1))[0]

    if scan_idx.size == 0:
        # Granule returned by metadata search but doesn't actually overlap the bbox.
        track_fname = opendap_url_no_slicing.split("?")[0].split("/")[-1]
        logger.warning(f"No bbox-intersecting scans found in {track_fname} — skipping")
        return None

    i0 = int(scan_idx[0])
    i1 = int(scan_idx[-1])
    logger.info(f"{(i0, i1)=}")

    # --- Round trip 2: fetch only the sliced rows (full pixel width) ---
    opendap_url_slicing = opendap_url_no_slicing
    for var_underscore in requested_vars_underscores:
        ndim = len(ds[var_underscore].shape)
        var_with_slicing = f"{var_underscore}[{i0}:{i1}]" + "[]" * (ndim - 1)
        opendap_url_slicing = opendap_url_slicing.replace(
            var_underscore, var_with_slicing
        )

    ds_sliced = open_url(opendap_url_slicing, session=session)

    arr_dict: dict[str, np.ndarray] = {}
    for var_name in requested_vars_underscores:
        if var_name in ds_sliced:
            # pydap returns a proxy; [:] triggers the actual download.
            # Generator comprehension avoids NumPy DeprecationWarning and the
            # "array already cleared" RuntimeError from calling list() on the stream.
            data_obj = ds_sliced[var_name]
            arr_dict[var_name] = np.array([x for x in data_obj.data[:]])

    track_fname = opendap_url_no_slicing.split("?")[0].split("/")[-1]
    return track_fname, arr_dict


def _process_granule_with_retry(
    opendap_url_no_slicing: str,
    requested_vars_underscores: list[str],
    request_params: EarthdataDownloadVisualizeServiceRequest,
    token: str,
    max_retries: int = 12,
):
    """Wrapper around _process_granule with retry logic to handle transient network errors."""
    for attempt in range(max_retries):
        try:
            return _process_granule(
                opendap_url_no_slicing,
                requested_vars_underscores,
                request_params,
                token,
            )
        except Exception as e:
            if attempt < max_retries - 1:
                track_fname = opendap_url_no_slicing.split("?")[0].split("/")[-1]
                logger.warning(
                    f"Error processing {track_fname} (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {2 ** attempt}s..."
                )
                jitter = random.uniform(0, 1)
                time.sleep((2 ** attempt) + jitter)
            else:
                track_fname = opendap_url_no_slicing.split("?")[0].split("/")[-1]
                logger.error(f"Failed to process {track_fname} after {max_retries} attempts: {e}")
                raise


def _write_track_to_hdf5_per_track(output_path: Path, track_fname: str, var_dict: dict):
    """
    Create a single HDF5 file for this track with datasets placed under
    groups according to the underscore-separated field name (e.g. '/FS/VER/sigmaZeroNPCorrected').
    """
    basename = _sanitize_track_basename(track_fname)
    h5_path = output_path / basename
    with h5py.File(h5_path, "w") as h5f:
        # optionally store original filename as attribute
        h5f.attrs["original_track_fname"] = track_fname
        for field_name, arr in var_dict.items():
            np_arr = _ensure_numpy(arr)
            parts = _make_hdf5_path_from_field(field_name)
            if not parts:
                # skip empty names
                continue
            # create nested groups for all but last part
            grp = h5f
            for p in parts[:-1]:
                grp = grp.require_group(p)
            dset_name = parts[-1]
            # create or overwrite dataset
            if dset_name in grp:
                del grp[dset_name]
            # compression helps reduce file size; choose gzip
            grp.create_dataset(dset_name, data=np_arr, compression="gzip", compression_opts=4)

    relpath = h5_path.relative_to(LOCAL_SAVED_RESULTS_ROOTDIR)

    b2_file_path = Path(B2_SAVED_RESULTS_ROOTDIR) / relpath

    B2_BUCKET.upload_local_file(
        local_file=h5_path,
        file_name=str(b2_file_path),
    )


def get_earthdata_results(
    request_params: EarthdataDownloadVisualizeServiceRequest,
    request_timestamp_str: str | None = None,
) -> dict[str, dict[str, tuple[int, int]]]:
    """Download the sliced arrays (granules processed in parallel)."""
    results = get_search_data_results(request_params)
    requested_vars_slashes, requested_vars_underscores = create_requested_var_names(
        request_params
    )

    if EDL_TOKEN:
        os.environ["EARTHDATA_TOKEN"] = EDL_TOKEN
    token = os.environ["EARTHDATA_TOKEN"]

    # Build unsliced OPeNDAP URLs with constraint expressions
    opendap_urls_no_slicing = []
    for item in results:
        for urls in item["umm"]["RelatedUrls"]:
            if "OPENDAP" in urls.get("Description", "").upper():
                url = urls["URL"].replace("https", "dap4")
                ce = "?dap4.ce=/" + ";/".join(requested_vars_underscores)
                opendap_urls_no_slicing.append(url + ce)

    for url in opendap_urls_no_slicing:
        logger.info(url)

    # Process all granules in batches. Each granule makes two sequential network round
    # trips. Within a batch, the granules are independent and run concurrently.
    track_fname_to_arr_dict: dict[str, dict] = {}

    # https://forum.earthdata.nasa.gov/viewtopic.php?t=3734#p13338
    # "Each load balanced server has a request limit of 25 requests per second per IP.
    # We have 4 load balanced servers so that means if perfectly load balanced
    # we have a request limit of 100 requests/second per IP."

    # Calculate optimal batch size to respect the EARTHDATA_MAX_NUM_REQUESTS_PER_SEC limit
    # For each granule, we make multiple sequential HTTP requests:
    # 1. open_url(no_slicing) -> fetches .dmr (1 request)
    # 2. open_url(url_latlon) -> fetches .dmr (1 request)
    # 3. ds_latlon['FS_Latitude'].data[:] -> actual byte fetch over DAP (1 request)
    # 4. ds_latlon['FS_Longitude'].data[:] -> actual byte fetch over DAP (1 request)
    # 5. open_url(opendap_url_slicing) -> fetches .dmr (1 request)
    # 6. ds_sliced[var] -> byte fetch over DAP (1 request per variable)
    # Total requests per granule = 5 + len(requested_vars_underscores)
    requests_per_granule = 5 + len(requested_vars_underscores)

    # We want max EARTHDATA_MAX_NUM_REQUESTS_PER_SEC (due to NASA's limit)
    # Assuming the batch might finish in <1 second (burst):
    batch_size = max(1, EARTHDATA_MAX_NUM_REQUESTS_PER_SEC // requests_per_granule)
    logger.info(f"{batch_size=}")

    for i in range(0, len(opendap_urls_no_slicing), batch_size):
        batch_start_time = time.time()
        batch_urls = opendap_urls_no_slicing[i : i + batch_size]
        logger.info(
            f"Processing batch {i // batch_size + 1}"
            f" of {-(-len(opendap_urls_no_slicing) // batch_size)}"
            f" ({len(batch_urls)} granules)"
        )

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(
                    _process_granule_with_retry,
                    url,
                    requested_vars_underscores,
                    request_params,
                    token,
                ): url
                for url in batch_urls
            }
            for future in as_completed(futures):
                result = future.result()
                if result is None:
                    continue
                track_fname, arr_dict = result
                track_fname_to_arr_dict[track_fname] = arr_dict

            # Save downloaded tracks of the current batch sequentially
            if request_timestamp_str is not None and request_params is not None:
                output_path = Path(LOCAL_SAVED_RESULTS_ROOTDIR) / request_timestamp_str
                hdf5_dir = output_path / "tracks_hdf5"
                hdf5_dir.mkdir(parents=True, exist_ok=True)
                for future in futures.keys():
                    if future.exception() is None and future.result() is not None:
                        track_fname, arr_dict = future.result()
                        _write_track_to_hdf5_per_track(hdf5_dir, track_fname, arr_dict)

        # To strictly enforce the limit, ensure at least 1 second passes before next batch bursts
        elapsed = time.time() - batch_start_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)

    logger.info("Completed")
    return track_fname_to_arr_dict


if __name__ == "__main__":
    request_params = EarthdataDownloadVisualizeServiceRequest(
        lat_min=59.5,
        lat_max=62.6,
        # lat_max=52.6,  # for testing
        lon_min=28.0,
        lon_max=33.8,
        date_min="2025-11-01",
        date_max="2025-11-02",
        product="FS",
        observable_vars=["/FS/VER/sigmaZeroNPCorrected"],
    )
    output_dict = get_earthdata_results(request_params)
