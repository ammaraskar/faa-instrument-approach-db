from plate_analyzer.scrape_faa_dtpp_zip import (
    create_approach_to_airport,
    get_approach_type_and_runway_from_title,
    calculate_heading_angle_difference,
)
from plate_analyzer.text_extraction import SegmentedPlate, Waypoint, PlateComments
from plate_analyzer.schema import Airport, Runway, ApproachType

from pathlib import Path

import pytest


def test_calculate_heading_angle_difference():
    simple_difference = calculate_heading_angle_difference(10, 0)
    assert simple_difference == 10

    around_the_top = calculate_heading_angle_difference(355, 10)
    assert around_the_top == 15

    large_difference = calculate_heading_angle_difference(0, 180)
    assert large_difference == 180

    almost_large = calculate_heading_angle_difference(179, 360)
    assert almost_large == 179


def test_create_approach_to_airport():
    test_airport = Airport(
        id="KSFO",
        name="San Fransisco International",
        latitude="1N",
        longitude="2W",
        runways=[Runway(name="RW19L", bearing=194.0, threshold_elevation=11)],
        approaches=[],
    )

    UPEND_waypoint = Waypoint()
    UPEND_waypoint.is_initial_approach_fix = True

    plate_info = SegmentedPlate(
        approach_name="ILS or LOC RWY 19L",
        airport_name="SAN FRANCISCO INTL (SFO)",
        approach_course=(None, "APP CRS\n 193°"),
        has_dme_arc=False,
        has_procedure_turn=False,
        has_hold_in_lieu_of_procedure_turn=False,
        waypoints={
            "UPEND": UPEND_waypoint,
            "ROGGE": Waypoint(),
        },
        required_equipment=(None, "RNP APCH - GPS."),
        comments=PlateComments(
            non_standard_takeoff_minimums=True,
            non_standard_alternative_requirements=True,
            comments="Inop table does not apply to S-LOC Rwy 19L or Sidestep Rwy 19R. "
            "Simultaenous approach authorized.",
        ),
        missed_approach_instructions=(
            None,
            "MISSED APPROACH: Climb to 1100 then climbing left turn to 400 "
            "direct to PRTLA and hold. * Missed approach requires minimum climb "
            "of 357 feet per NM to 2000.",
        ),
        approach_minimums=[],
    )

    approach = create_approach_to_airport(
        test_airport, plate_info, "ILS OR LOC RWY 19L", "1.pdf"
    )
    assert approach.name == "ILS OR LOC RWY 19L"
    assert approach.plate_file == "1.pdf"
    assert approach.runway == "RW19L"
    assert approach.approach_course == 193
    assert approach.runway_approach_offset_angle == 1.0

    assert "Simultaenous approach authorized." in approach.comments.text_comments
    assert approach.comments.has_non_standard_takeoff_minimums
    assert approach.comments.has_non_standard_alternative_requirements

    assert approach.missed_instructions == plate_info.missed_approach_instructions[1]

    assert approach.has_dme_arc == False
    assert approach.has_hold_in_lieu_of_procedure_turn == False
    assert approach.has_procedure_turn == False


def test_approach_types_handles_or_conjuctions():
    types, runway = get_approach_type_and_runway_from_title("ILS OR LOC RWY 19L")
    assert runway == "19L"
    assert types == [ApproachType.ILS, ApproachType.LOCALIZER]


def test_approach_types_handles_non_runway_approach():
    types, runway = get_approach_type_and_runway_from_title("VOR-B")
    assert runway == None
    assert types == [ApproachType.VOR]


def test_approach_types_handles_high_altitude_approaches():
    types, runway = get_approach_type_and_runway_from_title("HI-ILS OR LOC RWY 15")
    assert runway == "15"
    assert types == [ApproachType.HIGH_ILS, ApproachType.HIGH_LOC]


def test_approach_types_handles_vor_suffix():
    types, runway = get_approach_type_and_runway_from_title("VOR-1 RWY 14L")
    assert runway == "14L"
    assert types == [ApproachType.VOR]


# This test requires a decently sized `d-tpp_Metafile.xml` file, so skip if
# not present.
import xml.etree.ElementTree as ET

TEST_DATA_DIR = Path(__file__).parent / ".." / "test_data"
METADATA_FILE = TEST_DATA_DIR / "d-tpp_Metafile.xml"


@pytest.mark.skipif(
    not METADATA_FILE.exists(),
    reason="Needs d-tpp_Metafile.xml file in test_data folder",
)
def test_resolve_approach_types():
    with METADATA_FILE.open() as f:
        metadata = ET.fromstring(f.read())

    for record in metadata.iter("record"):
        chart_code = record.find("chart_code").text
        if chart_code != "IAP":
            continue
        chart_name = record.find("chart_name").text
        if ("VISUAL" in chart_name) or ("COPTER" in chart_name):
            continue
        # Ignore continuation pages and "Attention All Users" pages
        if ("AAUP" in chart_name) or ("CONT." in chart_name):
            continue

        # Make sure we can successfully get approach types and runways out of
        # all of these.
        get_approach_type_and_runway_from_title(chart_name)
