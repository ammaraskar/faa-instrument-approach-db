"""
Grab information from the CIFP about the airports.
"""

from plate_analyzer.schema import Runway, Airport

import arinc424


# arinc 424 record identifier codes for stuff we're interested in.
VHF_NAVAID_CODE = "D"
ENROUTE_WAYPOINT_CODE = "EA"
AIRPORT_CODE = "PA"
AIRPORT_RUNWAY_CODE = "PG"
AIRPORT_APPROACH_CODE = "PF"


def analyze_cifp_file(cifp_path):
    records = []

    with open(cifp_path, "r") as f:
        for line in f:
            record = arinc424.Record()
            record.read(line)
            records.append(record)

    airports = {}

    # First handle airports
    for record in records:
        if record.code == AIRPORT_CODE:
            airport = handle_airport_record(record)
            airports[airport.id] = airport

    # Next handle everything else.
    for record in records:
        if record.code == AIRPORT_RUNWAY_CODE:
            airport_id, runway = handle_airport_runway_record(record)
            if runway is not None:
                airports[airport_id].runways.append(runway)

    return airports


def handle_airport_record(record: arinc424.Record):
    airport_id = get_arinc424_field_value(record, "Airport ICAO Identifier")
    airport_name = get_arinc424_field_value(record, "Airport Name")
    latitude = get_arinc424_field_value(record, "Airport Reference Pt. Latitude")
    longitude = get_arinc424_field_value(record, "Airport Reference Pt. Longitude")

    return Airport(
        id=airport_id,
        name=airport_name,
        latitude=latitude,
        longitude=longitude,
        runways=[],
        approaches=[],
    )


def handle_airport_runway_record(record: arinc424.Record):
    airport_id = get_arinc424_field_value(record, "Airport ICAO Identifier")

    runway_name = get_arinc424_field_value(record, "Runway Identifier")
    bearing = get_arinc424_field_value(record, "Runway Magnetic Bearing")
    # Seaplane runways often don't have exact bearings.
    if bearing == "":
        return (airport_id, None)
    bearing = int(bearing) / 10.0

    threshold_elevation = get_arinc424_field_value(
        record, "Landing Threshold Elevation"
    )
    if threshold_elevation.startswith("-"):
        threshold_elevation = -int(threshold_elevation.replace("-", ""))
    else:
        threshold_elevation = int(threshold_elevation)

    return airport_id, Runway(
        name=runway_name, bearing=bearing, threshold_elevation=threshold_elevation
    )


def get_arinc424_field_value(record: arinc424.Record, name: str) -> str:
    """Gets the value of a arinc424 field from the record."""
    for field in record.fields:
        if field.name != name:
            continue
        return field.value.strip()

    raise KeyError(f"Field {name} not found in {record}")
