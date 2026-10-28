"""Conservative location resolution for signal-ingest records."""

from __future__ import annotations

from dataclasses import dataclass
import re

from geoalchemy2.elements import WKTElement
from pyproj import Transformer


EPSG_WGS84 = 4326
EPSG_ETRS89_UTM_32N = 25832
EPSG_25832_MIN_LONGITUDE = 6.0
EPSG_25832_MAX_LONGITUDE = 12.0

COORDINATE_PATTERN = re.compile(
    r"\b(?:latitude|lat)\s*[:=]\s*"
    r"(?P<latitude>-?\d+(?:\.\d+)?)"
    r"[^\d-]+"
    r"(?:longitude|lon|lng)\s*[:=]\s*"
    r"(?P<longitude>-?\d+(?:\.\d+)?)\b",
    flags=re.IGNORECASE,
)

LOCATION_CONTEXT_PATTERN = re.compile(
    r"\b(?:located\s+in|based\s+in|in|near|at|around)\s+"
    r"(?P<location>[A-Z][A-Za-zÀ-ÖØ-öø-ÿ.'-]*(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ.'-]*){0,3})"
)


@dataclass(frozen=True)
class LocationResult:
    """Location fields ready to be copied into the staging model."""

    geographic_context: str | None
    latitude: float | None
    longitude: float | None
    geometry: WKTElement | None
    quality_status: str
    quality_notes: str


def resolve_location(text: str) -> LocationResult:
    """Resolve only explicit labelled coordinates from source text.

    The current feed contains place names in free text but no structured
    coordinates. This resolver intentionally avoids guessing city-center
    points or silently geocoding ambiguous text.
    """

    match = COORDINATE_PATTERN.search(text)

    if match is None:
        context_match = LOCATION_CONTEXT_PATTERN.search(text)
        geographic_context = (
            f"source text: {context_match.group(0).strip()}"
            if context_match
            else None
        )
        return LocationResult(
            geographic_context=geographic_context,
            latitude=None,
            longitude=None,
            geometry=None,
            quality_status="unresolved_location",
            quality_notes=(
                "The source has no explicitly labelled latitude/longitude; "
                "textual location context was retained when detected."
            ),
        )

    latitude = float(match.group("latitude"))
    longitude = float(match.group("longitude"))
    geographic_context = (
        f"source coordinates: latitude={latitude}, longitude={longitude}"
    )

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return LocationResult(
            geographic_context=geographic_context,
            latitude=latitude,
            longitude=longitude,
            geometry=None,
            quality_status="invalid_coordinates",
            quality_notes="Coordinates are outside valid latitude/longitude ranges.",
        )

    if not (
        EPSG_25832_MIN_LONGITUDE
        <= longitude
        <= EPSG_25832_MAX_LONGITUDE
    ):
        return LocationResult(
            geographic_context=geographic_context,
            latitude=latitude,
            longitude=longitude,
            geometry=None,
            quality_status="outside_epsg_25832_area",
            quality_notes=(
                "The source coordinates are outside the EPSG:25832 area of use."
            ),
        )

    transformer = Transformer.from_crs(
        EPSG_WGS84,
        EPSG_ETRS89_UTM_32N,
        always_xy=True,
    )
    easting, northing = transformer.transform(longitude, latitude)

    return LocationResult(
        geographic_context=geographic_context,
        latitude=latitude,
        longitude=longitude,
        geometry=WKTElement(
            f"POINT ({easting} {northing})",
            srid=EPSG_ETRS89_UTM_32N,
        ),
        quality_status="resolved",
        quality_notes="Explicit source coordinates transformed to EPSG:25832.",
    )
