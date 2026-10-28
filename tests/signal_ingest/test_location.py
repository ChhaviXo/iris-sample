from app.signal_ingest.location import resolve_location


def test_location_resolver_transforms_explicit_coordinates() -> None:
    result = resolve_location(
        "Site coordinates: latitude=50.1109, longitude=8.6821"
    )

    assert result.quality_status == "resolved"
    assert result.geometry is not None
    assert result.geometry.srid == 25832
    assert result.geometry.data.startswith("POINT (")


def test_location_resolver_does_not_guess_from_place_names() -> None:
    result = resolve_location("The article discusses a data center in Frankfurt.")

    assert result.quality_status == "unresolved_location"
    assert result.geometry is None
    assert result.latitude is None
    assert result.longitude is None


def test_location_resolver_rejects_coordinates_outside_crs_area() -> None:
    result = resolve_location(
        "Site coordinates: latitude=40.7128, longitude=-74.0060"
    )

    assert result.quality_status == "outside_epsg_25832_area"
    assert result.geometry is None
