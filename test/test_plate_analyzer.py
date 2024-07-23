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


@pytest.fixture(scope="session")
def extracted_information():
    return plate_analyzer.extract_information_from_plate(TEST_PLATE)


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
    assert extracted_information.required_equipment[1] == 'RNP APCH.'


@pytest.fixture(scope="session")
def athens_info():
    return plate_analyzer.extract_information_from_plate(ATHENS_TEST_PLATE)


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


def test_extract_gets_correct_required_equipment_for_martin(marin_state_info):
    assert marin_state_info.required_equipment[1] == 'DME required.'


def test_extract_gets_correct_missed_approach_for_martin(marin_state_info):
    missed_instructions = marin_state_info.missed_approach_instructions[1]
    assert missed_instructions == (
        "MISSED APPROACH: Climbing right turn to 2500 on BAL VORTAC R-068 and "
        "BAL 11 DME Arc clockwise to BOAST INT/BAL 11 DME and hold."
    )


def test_extract_gets_correct_approach_course_for_martin(marin_state_info):
    assert 'Arc' in marin_state_info.approach_course[1]


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
