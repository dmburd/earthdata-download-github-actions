import numpy as np
from bokeh.models import ColumnDataSource

from src.pydantic_models import (
    EarthdataDownloadVisualizeServiceRequest,
    VisualizationSettings,
)
from src.utils.common import create_requested_var_names
from src.utils.map_drawing_bokeh import (
    draw_earth_features,
    draw_points_colorbar,
    prepare_bokeh_figure,
)


def visualize_single_track(
    request_params: EarthdataDownloadVisualizeServiceRequest,
    track_number: str,
    single_track_arr_dict: dict[str, np.ndarray],
    vis_settings: VisualizationSettings,
) -> object:
    requested_vars_slashes, requested_vars_underscores = create_requested_var_names(
        request_params
    )
    latitude_var_name = next(
        v for v in requested_vars_underscores if "latitude" in v.lower()
    )
    longitude_var_name = next(
        v for v in requested_vars_underscores if "longitude" in v.lower()
    )
    single_observable_var_name_slashes = request_params.observable_vars[0]
    single_observable_var_name_idx = requested_vars_slashes.index(
        single_observable_var_name_slashes
    )
    single_observable_var_name_underscores = requested_vars_underscores[
        single_observable_var_name_idx
    ]

    latitude = single_track_arr_dict[latitude_var_name].flatten()
    longitude = single_track_arr_dict[longitude_var_name].flatten()
    observable = single_track_arr_dict[single_observable_var_name_underscores][
        :, :, request_params.product_idx_for_sigma_zero
    ].flatten()

    p = prepare_bokeh_figure(
        f"Track {track_number}",
        request_params,
    )

    source = ColumnDataSource(
        data=dict(
            latitude=latitude,
            longitude=longitude,
            observable=observable,
            marker_sizes=np.full_like(observable, 3),
        )
    )

    draw_points_colorbar(
        p,
        source,
        observable,
        request_params,
        vis_settings,
    )

    p = draw_earth_features(p, vis_settings)

    return p
