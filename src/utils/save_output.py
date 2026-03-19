import json
from pathlib import Path

import numpy as np
from bokeh.layouts import column
from bokeh.plotting import output_file, save
from loguru import logger

from src.config import LOCAL_SAVED_RESULTS_ROOTDIR, B2_SAVED_RESULTS_ROOTDIR
from src.pydantic_models import (
    EarthdataDownloadVisualizeServiceRequest,
    VisualizationSettings,
)
from src.utils.common import extract_track_number_from_h5_url_or_fpath
from src.utils.visualization import visualize_single_track
from src.utils.b2 import B2_BUCKET


def save_output_dict_structure(
    track_fname_to_arr_dict: dict[str, dict[str, np.ndarray]],
    output_path: Path,
):
    output_str_lines = ["{"]
    for i, (fname, arrs) in enumerate(track_fname_to_arr_dict.items()):
        output_str_lines.append(f'    "{fname}": {{')
        var_items = []
        for var, arr in arrs.items():
            shape_str = ",".join(map(str, arr.shape))
            var_items.append(f'        "{var}": ["{arr.dtype}", [{shape_str}]]')

        output_str_lines.append(",\n".join(var_items))

        if i < len(track_fname_to_arr_dict) - 1:
            output_str_lines.append("    },")
        else:
            output_str_lines.append("    }")
    output_str_lines.append("}")

    with open(output_path / "output_dict_structure.json", "w") as f:
        f.write("\n".join(output_str_lines) + "\n")

    relpath = output_path.relative_to(LOCAL_SAVED_RESULTS_ROOTDIR)

    b2_file_path = Path(B2_SAVED_RESULTS_ROOTDIR) / relpath / "output_dict_structure.json"

    B2_BUCKET.upload_local_file(
        local_file=output_path / "output_dict_structure.json",
        file_name=str(b2_file_path),
    )


def save_few_tracks_visualized(
    request_params: EarthdataDownloadVisualizeServiceRequest,
    track_fname_to_arr_dict: dict[str, dict[str, np.ndarray]],
    output_path: Path,
):
    vis_settings = VisualizationSettings()
    max_tracks = vis_settings.max_num_tracks_to_show_in_html

    track_items = list(track_fname_to_arr_dict.items())
    if len(track_items) > max_tracks:
        logger.info(
            f"Limiting visualization to first {max_tracks} tracks (out of {len(track_items)})"
        )
        track_items = track_items[:max_tracks]

    track_figures = []
    for track_fname, single_track_arr_dict in track_items:
        track_number = extract_track_number_from_h5_url_or_fpath(
            track_fname,
            request_params,
        )
        track_figures.append(
            visualize_single_track(
                request_params,
                track_number,
                single_track_arr_dict,
                vis_settings,
            )
        )

    if track_figures:
        combined_html_path = output_path / "few_tracks_visualized.html"
        output_file(combined_html_path, title="Few Tracks Visualized")
        save(column(*track_figures, sizing_mode="stretch_width"))
        logger.info(
            f"Visualized few tracks in a single HTML page: {combined_html_path}"
        )
    else:
        logger.info("No track figures were generated")

    relpath = output_path.relative_to(LOCAL_SAVED_RESULTS_ROOTDIR)

    b2_file_path = Path(B2_SAVED_RESULTS_ROOTDIR) / relpath / "few_tracks_visualized.html"

    B2_BUCKET.upload_local_file(
        local_file=output_path / "few_tracks_visualized.html",
        file_name=str(b2_file_path),
    )


def save_output_files(
    request_params: EarthdataDownloadVisualizeServiceRequest,
    track_fname_to_arr_dict: dict[str, dict[str, np.ndarray]],
    output_dir: str,
):
    """
    Saves outputs to disk.
    """
    output_path = Path(LOCAL_SAVED_RESULTS_ROOTDIR) / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    # (1) Save input request
    with open(output_path / "input_request.json", "w") as f:
        json.dump(request_params.model_dump(), f, default=str, indent=4)

    relpath = output_path.relative_to(LOCAL_SAVED_RESULTS_ROOTDIR)

    b2_file_path = Path(B2_SAVED_RESULTS_ROOTDIR) / relpath / "input_request.json"

    B2_BUCKET.upload_local_file(
        local_file=output_path / "input_request.json",
        file_name=str(b2_file_path),
    )
    print(f"local_file = {output_path / 'input_request.json'}")
    print(f"file_name = {b2_file_path}")

    # (2) Save output dict structure
    save_output_dict_structure(track_fname_to_arr_dict, output_path)

    # (3) Save few tracks visualized
    save_few_tracks_visualized(request_params, track_fname_to_arr_dict, output_path)
