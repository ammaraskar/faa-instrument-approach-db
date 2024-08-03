"""
Test against a known plate in test_data folder.
"""

from pathlib import Path
import pytest

import plate_analyzer


TEST_DATA_DIR = Path(__file__).parent / ".." / "test_data"
TEST_PLATE = TEST_DATA_DIR / "05035R7.pdf"
ATHENS_TEST_PLATE = TEST_DATA_DIR / "00983ILD27.pdf"
MARIN_STATE_TEST_PLATE = TEST_DATA_DIR / "05222VT15.pdf"
PORTLAND_TEST_PLATE = TEST_DATA_DIR / "00330IL10R.pdf"


@pytest.fixture(scope="session")
def extracted_information():
    return plate_analyzer.extract_information_from_plate(TEST_PLATE)


def test_extract_gets_correct_approach_title(extracted_information):
    assert extracted_information.approach_name == "RNAV (GPS) RWY 7"
    assert extracted_information.airport_name == "DUBOIS RGNL (DUJ)"


def test_extract_gets_correct_approach_plan_view_data(extracted_information):
    assert extracted_information.has_dme_arc == False
    assert extracted_information.has_procedure_turn == False
    assert extracted_information.has_hold_in_lieu_of_procedure_turn == True


def test_extract_gets_correct_waypoints(extracted_information):
    assert "TNKEE" in extracted_information.waypoints
    assert extracted_information.waypoints["TNKEE"].is_initial_approach_fix
    assert "WNKEE" in extracted_information.waypoints
    assert extracted_information.waypoints["WNKEE"].is_initial_approach_fix
    assert "EEYES" in extracted_information.waypoints
    assert extracted_information.waypoints["EEYES"].is_initial_approach_fix
    assert extracted_information.waypoints["EEYES"].is_intermediate_fix
    assert "PLEAZ" in extracted_information.waypoints
    assert extracted_information.waypoints["PLEAZ"].is_final_approach_fix


def test_extract_gets_correct_minimums(extracted_information):
    assert len(extracted_information.approach_minimums) == 4

    lpv_approach = extracted_information.approach_minimums[0]
    assert lpv_approach.approach_type == "LPV"
    assert lpv_approach.cat_a.altitude == "2017"
    assert lpv_approach.cat_a.visibility == "3/4"

    lnav_vnav_approach = extracted_information.approach_minimums[1]
    assert lnav_vnav_approach.approach_type == "LNAV/VNAV"
    assert lnav_vnav_approach.cat_a.altitude == "2160"
    assert lnav_vnav_approach.cat_a.visibility == "1"

    lnav_approach = extracted_information.approach_minimums[2]
    assert lnav_approach.approach_type == "LNAV"
    assert lnav_approach.cat_a.altitude == "2240"
    assert lnav_approach.cat_a.visibility == "1"
    assert lnav_approach.cat_d.altitude == "2240"
    assert lnav_approach.cat_d.visibility == "1 1/4"

    circling_approach = extracted_information.approach_minimums[3]
    assert circling_approach.approach_type == "CIRCLING (Expanded Radius)"
    assert circling_approach.cat_a.altitude == "2320"
    assert circling_approach.cat_a.visibility == "1"
    assert circling_approach.cat_b.altitude == "2360"
    assert circling_approach.cat_b.visibility == "1"
    assert circling_approach.cat_c.altitude == "2380"
    assert circling_approach.cat_c.visibility == "1 1/2"
    assert circling_approach.cat_d.altitude == "2400"
    assert circling_approach.cat_d.visibility == "2"


def test_extract_gets_correct_missed_approach(extracted_information):
    missed_instructions = extracted_information.missed_approach_instructions[1]
    assert (
        missed_instructions == "MISSED APPROACH: Climb to 4200 direct CELSY and hold."
    )


def test_extract_gets_correct_comments(extracted_information):
    comments = extracted_information.comments
    assert comments.non_standard_takeoff_minimums == True
    assert comments.non_standard_alternative_requirements == True
    assert "Circling NA for Cat D south of Rwy 7-25" in comments.comments
    assert "LNAV/VNAV NA below -21" in comments.comments


def test_extract_gets_correct_requried_equipment(extracted_information):
    assert extracted_information.required_equipment[1] == "RNP APCH."


@pytest.fixture(scope="session")
def athens_info():
    return plate_analyzer.extract_information_from_plate(ATHENS_TEST_PLATE)


def test_extract_gets_correct_approach_title_for_athens(athens_info):
    assert athens_info.approach_name == "ILS or LOC/DME RWY 27"
    assert athens_info.airport_name == "ATHENS/BEN EPPS(AHN)"


def test_extract_gets_correct_approach_plan_view_data_for_athens(athens_info):
    assert athens_info.has_dme_arc == False
    assert athens_info.has_procedure_turn == True
    assert athens_info.has_hold_in_lieu_of_procedure_turn == False


def test_extract_gets_correct_waypoints_for_athens(athens_info):
    assert "BLLDG" in athens_info.waypoints
    assert athens_info.waypoints["BLLDG"].is_initial_approach_fix
    assert "VESTO" in athens_info.waypoints
    assert athens_info.waypoints["VESTO"].is_initial_approach_fix
    assert "IMAVE" in athens_info.waypoints
    assert athens_info.waypoints["IMAVE"].is_intermediate_fix


def test_extract_gets_correct_requried_equipment_for_athens(athens_info):
    assert athens_info.required_equipment is None


def test_extract_gets_correct_missed_approach_for_athens(athens_info):
    missed_instructions = athens_info.missed_approach_instructions[1]
    assert missed_instructions == (
        "MISSED APPROACH: Climb to 1500 then climbing left turn to 2500 on heading "
        "060° and AHN VOR/DME R-092 to VESTO INT/ AHN 23.6 DME and hold."
    )


def test_extract_gets_correct_comments_for_athens(athens_info):
    comments = athens_info.comments
    assert comments.non_standard_takeoff_minimums == True
    assert comments.non_standard_alternative_requirements == True
    assert "Night landing: Rwy 2, 20 NA." in comments.comments
    assert "Simultaneous reception of I-AHN and AHN DME Required." in comments.comments
    assert "VDP NA with Winder altimeter setting." in comments.comments


def test_extract_gets_correct_approach_course_for_athens(athens_info):
    assert athens_info.approach_course[1] == "274°"


def test_extract_gets_correct_minimums_for_athens(athens_info):
    assert len(athens_info.approach_minimums) == 3

    ils_approach = athens_info.approach_minimums[0]
    assert ils_approach.approach_type == "S-ILS 27"
    assert ils_approach.cat_a.altitude == "1013"
    assert ils_approach.cat_a.visibility == "3/4"
    assert ils_approach.cat_d == ils_approach.cat_a

    loc_approach = athens_info.approach_minimums[1]
    assert loc_approach.approach_type == "S-LOC 27"
    assert loc_approach.cat_a.altitude == "1160"
    assert loc_approach.cat_a.visibility == "3/4"
    assert ils_approach.cat_d == ils_approach.cat_a

    circling_approach = athens_info.approach_minimums[2]
    assert circling_approach.approach_type == "CIRCLING (Expanded Radius)"
    assert circling_approach.cat_a.altitude == "1260"
    assert circling_approach.cat_a.visibility == "1"
    assert circling_approach.cat_b.altitude == "1280"
    assert circling_approach.cat_b.visibility == "1"
    assert circling_approach.cat_c.altitude == "1320"
    assert circling_approach.cat_c.visibility == "1 1/2"
    assert circling_approach.cat_d.altitude == "1460"
    assert circling_approach.cat_d.visibility == "2"


@pytest.fixture(scope="session")
def marin_state_info():
    return plate_analyzer.extract_information_from_plate(MARIN_STATE_TEST_PLATE)


def test_extract_gets_correct_approach_title_for_martin(marin_state_info):
    assert marin_state_info.approach_name == "VOR or TACAN RWY 15"
    assert marin_state_info.airport_name == "MARTIN STATE (MTN)"


def test_extract_gets_correct_approach_plan_view_data_for_martin(marin_state_info):
    assert marin_state_info.has_dme_arc == True
    assert marin_state_info.has_procedure_turn == False
    assert marin_state_info.has_hold_in_lieu_of_procedure_turn == False


def test_extract_gets_correct_waypoints_for_martin(marin_state_info):
    assert "SLOAF" in marin_state_info.waypoints
    assert marin_state_info.waypoints["SLOAF"].is_initial_approach_fix
    assert "CUMBE" in marin_state_info.waypoints
    assert marin_state_info.waypoints["CUMBE"].is_intermediate_fix
    assert "GOVES" in marin_state_info.waypoints
    assert "ZOVAP" in marin_state_info.waypoints


def test_extract_gets_correct_required_equipment_for_martin(marin_state_info):
    assert marin_state_info.required_equipment[1] == "DME required."


def test_extract_gets_correct_missed_approach_for_martin(marin_state_info):
    missed_instructions = marin_state_info.missed_approach_instructions[1]
    assert missed_instructions == (
        "MISSED APPROACH: Climbing right turn to 2500 on BAL VORTAC R-068 and "
        "BAL 11 DME Arc clockwise to BOAST INT/BAL 11 DME and hold."
    )


def test_extract_gets_correct_approach_course_for_martin(marin_state_info):
    assert "Arc" in marin_state_info.approach_course[1]


def test_extract_gets_correct_minimums_for_martin(marin_state_info):
    assert len(marin_state_info.approach_minimums) == 2

    straight_in_approach = marin_state_info.approach_minimums[0]
    assert straight_in_approach.approach_type == "S-15"
    assert straight_in_approach.cat_a.altitude == "920"
    assert straight_in_approach.cat_a.visibility == "1 1/4"
    assert straight_in_approach.cat_b == straight_in_approach.cat_a
    assert straight_in_approach.cat_c.altitude == "920"
    assert straight_in_approach.cat_c.visibility == "2 1/2"
    assert straight_in_approach.cat_d == straight_in_approach.cat_c

    circling_approach = marin_state_info.approach_minimums[1]
    assert circling_approach.approach_type == "CIRCLING"
    assert circling_approach.cat_a.altitude == "920"
    assert circling_approach.cat_a.visibility == "1 1/4"
    assert circling_approach.cat_b == circling_approach.cat_a
    assert circling_approach.cat_c.altitude == "920"
    assert circling_approach.cat_c.visibility == "2 3/4"
    assert circling_approach.cat_d.altitude == "920"
    assert circling_approach.cat_d.visibility == "3"


@pytest.fixture(scope="session")
def portland_info():
    return plate_analyzer.extract_information_from_plate(PORTLAND_TEST_PLATE)


def test_extract_gets_correct_approach_title_for_portland(portland_info):
    assert portland_info.approach_name == "ILS or LOC RWY 10R"
    assert portland_info.airport_name == "PORTLAND INTL (PDX)"


def test_extract_gets_correct_minimums_for_portland(portland_info):
    # Test for whe non-circling minimums have a height above threshold number.
    ils_approach = portland_info.approach_minimums[0]
    assert ils_approach.approach_type == "S-ILS 10R"
    assert ils_approach.cat_a.altitude == "224"
    assert ils_approach.cat_a.rvr == "18"
    assert ils_approach.cat_d == ils_approach.cat_a
    
    localizer_approach = portland_info.approach_minimums[1]
    assert localizer_approach.approach_type == "S-LOC 10R"
    assert localizer_approach.cat_a.altitude == "860"
    assert localizer_approach.cat_a.rvr == "24"
    assert localizer_approach.cat_b.altitude == "860"
    assert localizer_approach.cat_b.rvr == "40"
    assert localizer_approach.cat_c.altitude == "860"
    assert localizer_approach.cat_c.visibility == "1 7/8"
    assert localizer_approach.cat_d == localizer_approach.cat_c

    circling_approach = portland_info.approach_minimums[2]
    assert circling_approach.approach_type == "CIRCLING (Expanded Radius)"
    assert circling_approach.cat_a.altitude == "860"
    assert circling_approach.cat_a.visibility == "1 1/4"
    assert circling_approach.cat_b == circling_approach.cat_a
    assert circling_approach.cat_c.altitude == "1060"
    assert circling_approach.cat_c.visibility == "3"
    assert circling_approach.cat_d == circling_approach.cat_c
