from plate_analyzer.scrape_faa_dtpp_zip import create_approach_to_airport
from plate_analyzer.text_extraction import SegmentedPlate, Waypoint, PlateComments
from plate_analyzer.schema import Airport, Runway


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
        has_procedure_turn=False,
        approach_minimums=[],
    )

    approach = create_approach_to_airport(
        test_airport, plate_info, "ILS OR LOC RWY 19L", "1.pdf"
    )
    assert approach.name == "ILS OR LOC RWY 19L"
    assert approach.plate_file == "1.pdf"
    assert approach.runway == "19L"
    assert approach.approach_course == 193
    assert approach.runway_approach_offset_angle == 1.0
