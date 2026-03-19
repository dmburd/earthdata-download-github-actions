from typing import Any

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy as np
from bokeh.models import (
    ColorBar,
    ColumnDataSource,
    HoverTool,
    LabelSet,
    LinearColorMapper,
    Range1d,
)
from bokeh.palettes import Turbo256
from bokeh.plotting import figure
from bokeh.transform import transform
from shapely.geometry import MultiPolygon, Polygon

from src.pydantic_models import (
    EarthdataDownloadVisualizeServiceRequest,
    VisualizationSettings,
)


def get_land_polygons():
    """Extract land polygons from Natural Earth features"""
    land_geoms = cfeature.NaturalEarthFeature("physical", "land", "50m")
    polygons = []

    for geom in land_geoms.geometries():
        if isinstance(geom, Polygon):
            polygons.append(geom)
        elif isinstance(geom, MultiPolygon):
            polygons.extend(geom.geoms)

    return polygons


def get_polygon_source(polygons, projection):
    """Convert polygons to Bokeh ColumnDataSource"""
    xs, ys = [], []

    for polygon in polygons:
        # Extract exterior coordinates
        x, y = polygon.exterior.xy
        # Project coordinates if needed
        if projection:
            x, y = projection.transform_points(
                ccrs.PlateCarree(), np.array(x), np.array(y)
            )[:, :2].T
        xs.append(x.tolist())
        ys.append(y.tolist())

    return ColumnDataSource(data=dict(xs=xs, ys=ys))


def prepare_bokeh_figure(
    plot_title: str,
    request_params: EarthdataDownloadVisualizeServiceRequest,
) -> figure:
    # Extract bounding box coordinates as floats to avoid Bokeh validation errors with Decimal
    lon_min, lon_max = float(request_params.lon_min), float(request_params.lon_max)
    lat_min, lat_max = float(request_params.lat_min), float(request_params.lat_max)

    try:
        height_to_width_ratio = (lat_max - lat_min) / (lon_max - lon_min)
    except ZeroDivisionError:
        height_to_width_ratio = 1.0

    max_size_any = 600
    if height_to_width_ratio > 1.0:
        fig_height = max_size_any
        fig_width = int(fig_height / height_to_width_ratio)
    else:
        fig_width = max_size_any
        fig_height = int(fig_width * height_to_width_ratio)

    # Create Bokeh figure
    p = figure(
        title=plot_title,
        x_range=Range1d(lon_min, lon_max, bounds=(lon_min, lon_max)),
        y_range=Range1d(lat_min, lat_max, bounds=(lat_min, lat_max)),
        width=fig_width,
        height=fig_height,
        tools="pan,wheel_zoom,box_zoom,reset,save",
        toolbar_location="left",
    )

    # Configure plot appearance
    p.title.text_font_size = "16pt"

    return p


def draw_earth_features(
    p: figure,
    vis_settings: VisualizationSettings,
) -> figure:
    water_related_geoms = cfeature.NaturalEarthFeature("physical", "coastline", "50m")
    water_related_source = get_geojson_source(water_related_geoms)
    p.multi_line(
        xs="xs",
        ys="ys",
        source=water_related_source,
        line_color="black",
        line_width=1,
    )

    water_related_geoms = cfeature.NaturalEarthFeature("physical", "lakes", "10m")
    water_related_source = get_geojson_source(water_related_geoms)
    p.patches(
        xs="xs",
        ys="ys",
        source=water_related_source,
        fill_alpha=0.0,
        line_color="black",
        line_width=1,
    )

    if vis_settings.show_rivers:
        water_related_geoms = cfeature.NaturalEarthFeature(
            "physical", "rivers_lake_centerlines", "10m"
        )
        water_related_source = get_geojson_source(water_related_geoms)
        p.multi_line(
            xs="xs",
            ys="ys",
            source=water_related_source,
            line_color="blue",
            line_width=1.5,
            line_cap="round",
            line_join="round",
        )

    land_polygons = get_land_polygons()
    land_source = get_polygon_source(land_polygons, projection=None)
    p.patches(
        xs="xs",
        ys="ys",
        source=land_source,
        fill_color="#E0E0E0",  # Light gray
        fill_alpha=0.0,
        line_color="black",  # Outline color
        line_width=0.5,  # Outline thickness
    )

    return p


def get_geojson_source(feature):
    """Convert cartopy feature to Bokeh ColumnDataSource"""
    xs, ys = [], []

    for geom in feature.geometries():
        if geom.is_empty:
            continue

        # Normalize Multi* into parts
        parts = getattr(geom, "geoms", [geom])
        for g in parts:
            gt = g.geom_type

            if gt in ("LineString", "LinearRing"):
                x, y = g.xy
                xs.append(list(x))
                ys.append(list(y))

            elif gt == "MultiLineString":
                for line in g.geoms:
                    x, y = line.xy
                    xs.append(list(x))
                    ys.append(list(y))

            elif gt == "Polygon":
                # outline (exterior)
                x, y = g.exterior.xy
                xs.append(list(x))
                ys.append(list(y))
                # (optional) holes
                # for ring in g.interiors:
                #     rx, ry = ring.xy
                #     xs.append(list(rx))
                #     ys.append(list(ry))

            elif gt == "MultiPolygon":
                for poly in g.geoms:
                    x, y = poly.exterior.xy
                    xs.append(list(x))
                    ys.append(list(y))
                    # (optional) holes
                    # for ring in poly.interiors:
                    #     rx, ry = ring.xy
                    #     xs.append(list(rx))
                    #     ys.append(list(ry))

    return ColumnDataSource(dict(xs=xs, ys=ys))


def add_geo_grid(p, lon_min, lon_max, lat_min, lat_max):
    """Add geographic gridlines and labels"""
    # Generate grid positions
    lon_ticks = np.linspace(lon_min, lon_max, 5)
    lat_ticks = np.linspace(lat_min, lat_max, 5)

    # Gridline style
    grid_opts = {"color": "#666666", "alpha": 0.4, "line_width": 1}

    # Add longitude lines
    for lon in lon_ticks:
        p.line([lon, lon], [lat_min, lat_max], **grid_opts)

    # Add latitude lines
    for lat in lat_ticks:
        p.line([lon_min, lon_max], [lat, lat], **grid_opts)

    # Configure labels
    label_opts = {
        "text_font_size": "12pt",
        "text_baseline": "top",
        "text_align": "center",
    }

    # Format labels like Cartopy's formatters
    def lon_formatter(lon):
        return f"{abs(lon):.1f}°{'W' if lon < 0 else 'E'}"

    def lat_formatter(lat):
        return f"{abs(lat):.1f}°{'S' if lat < 0 else 'N'}"

    # Longitude labels (bottom)
    lon_labels = ColumnDataSource(
        data={
            "x": lon_ticks,
            "y": [lat_min] * len(lon_ticks),
            "text": [lon_formatter(lon) for lon in lon_ticks],
        }
    )
    p.add_layout(LabelSet(x="x", y="y", text="text", source=lon_labels, **label_opts))

    # Latitude labels (left)
    lat_labels = ColumnDataSource(
        data={
            "x": [lon_min] * len(lat_ticks),
            "y": lat_ticks,
            "text": [lat_formatter(lat) for lat in lat_ticks],
        }
    )
    p.add_layout(LabelSet(x="x", y="y", text="text", source=lat_labels, **label_opts))


def draw_points_colorbar(
    p: Any,
    source: ColumnDataSource,
    observable: np.ndarray,
    request_params: EarthdataDownloadVisualizeServiceRequest,
    vis_settings: VisualizationSettings,
):
    color_mapper = LinearColorMapper(
        palette=Turbo256,
        low=min(observable),
        high=max(observable),
    )

    p.scatter(
        "longitude",
        "latitude",
        source=source,
        marker="circle",
        size=6,
        fill_color=transform("observable", color_mapper),
        fill_alpha=1.0,  # 0.5,
        line_color=None,
    )

    observable_print_name = request_params.observable_name_to_colorbar_title.get(
        request_params.observable_vars[0],
        request_params.observable_vars[0],
    )

    if vis_settings.add_hover_tool:
        tooltips = [
            ("(lat, lon)", "(@latitude{0.000}, @longitude{0.000})"),
            (observable_print_name, "@observable{0.00}"),
        ]
        hover = HoverTool(tooltips=tooltips)
        p.add_tools(hover)

    color_bar = ColorBar(
        color_mapper=color_mapper,
        label_standoff=12,
        width=8,
        location=(0, 0),
        title=observable_print_name,
        title_text_font_size="16pt",
        title_text_font_style="normal",
        major_label_text_font_size="14pt",
    )
    p.add_layout(color_bar, "right")
