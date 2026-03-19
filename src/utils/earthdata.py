import earthaccess

from src.pydantic_models import EarthdataDownloadVisualizeServiceRequest


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
