from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class EarthdataDownloadVisualizeServiceRequest(BaseModel):
    """
    The schema for the input request to the earthdata-download-visualize-service.
    """

    lat_min: Decimal = Field(
        description=("The minimum latitude of the bounding box."),
        examples=[
            "-90",
        ],
    )
    lat_max: Decimal = Field(
        description=("The maximum latitude of the bounding box."),
        examples=[
            "90",
        ],
    )
    lon_min: Decimal = Field(
        description=("The minimum longitude of the bounding box."),
        examples=[
            "-180",
        ],
    )
    lon_max: Decimal = Field(
        description=("The maximum longitude of the bounding box."),
        examples=[
            "180",
        ],
    )
    date_min: str = Field(
        description=("The start date of the time range."),
        examples=[
            "2022-01-01",
        ],
    )
    date_max: str = Field(
        description=("The end date of the time range."),
        examples=[
            "2022-12-31",
        ],
    )
    product: str = Field(
        description=("The product identifier (e.g., 'FS' for a specific dataset)."),
        examples=[
            "FS",
        ],
    )
    observable_vars: list[str] = Field(
        description=(
            "List of observable variable paths within the HDF5 file structure."
        ),
        examples=[
            ["/FS/VER/sigmaZeroNPCorrected"],
        ],
    )
    product_idx_for_sigma_zero: int = Field(
        default=0,
        description=(
            "Index that should be selected for the last axis of the sigmaZeroNPCorrected array."
        ),
        examples=[
            0,
            1,
        ],
    )
    observable_name_to_colorbar_title: dict[str, str] = Field(
        default={"/FS/VER/sigmaZeroNPCorrected": "NRCS Ku-band (dB)"},
        description=(
            "Mapping of observable variable names to their colorbar titles for visualization."
        ),
        examples=[
            {"/FS/VER/sigmaZeroNPCorrected": "NRCS Ku-band (dB)"},
        ],
    )
    include_scan_time_arrays: bool = Field(
        default=True,
        description=("Whether scan time arrays should be included in the output."),
        examples=[
            True,
            False,
        ],
    )
    hdf5_bname_delimiter: str = Field(
        default=".",
        description=("Delimiter used to split HDF5 file basename into parts."),
        examples=[
            ".",
        ],
    )
    hdf5_bname_track_number_part_idx: int = Field(
        default=-2,
        description=(
            "Index of the track number part in the split HDF5 basename (negative indexing from end)."
        ),
        examples=[
            -2,
        ],
    )
    hdf5_bname_track_start_part_idx: int = Field(
        default=-3,
        description=(
            "Index of the track start time part in the split HDF5 basename (negative indexing from end)."
        ),
        examples=[
            -3,
        ],
    )

    @field_validator("lat_min", "lat_max")
    @classmethod
    def validate_latitude(cls, v: Decimal) -> Decimal:
        if v < -90 or v > 90:
            raise ValueError("Latitude must be between -90 and 90 degrees.")
        return v

    @field_validator("lon_min", "lon_max")
    @classmethod
    def validate_longitude(cls, v: Decimal) -> Decimal:
        if v < -180 or v > 180:
            raise ValueError("Longitude must be between -180 and 180 degrees.")
        return v

    @field_validator("date_min", "date_max")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError("Dates must be in the format 'YYYY-MM-DD'.") from e
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "EarthdataDownloadVisualizeServiceRequest":
        if self.date_min and self.date_max:
            date_min_parsed = datetime.strptime(self.date_min, "%Y-%m-%d")
            date_max_parsed = datetime.strptime(self.date_max, "%Y-%m-%d")
            if date_min_parsed > date_max_parsed:
                raise ValueError("date_min must be less than or equal to date_max.")
        return self

    @model_validator(mode="after")
    def validate_coordinates_range(self) -> "EarthdataDownloadVisualizeServiceRequest":
        if self.lat_min is not None and self.lat_max is not None:
            if self.lat_min >= self.lat_max:
                raise ValueError("lat_min must be strictly less than lat_max.")
        if self.lon_min is not None and self.lon_max is not None:
            if self.lon_min >= self.lon_max:
                raise ValueError("lon_min must be strictly less than lon_max.")
        return self


class VisualizationSettings(BaseModel):
    show_rivers: bool = Field(
        default=False,
        description=("Show rivers as multilines."),
        examples=[
            True,
            False,
        ],
    )
    separate_plots: bool = Field(
        default=False,
        description=("Visualize each track separately."),
        examples=[
            True,
            False,
        ],
    )
    add_hover_tool: bool = Field(
        default=False,
        description=(
            "Add hover tool (usable only for a narrow range of zoom level, but can be turned off)."
        ),
        examples=[
            True,
            False,
        ],
    )
    max_num_tracks_to_show_in_html: int = Field(
        default=2,
        description=("Maximum number of tracks to show in the saved HTML file."),
        examples=[
            2,
            3,
        ],
    )
