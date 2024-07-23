"""
Test against a known plate in test_data folder.
"""

from pathlib import Path
import pytest

import plate_analyzer


TEST_DIR = Path(__file__).parent
TEST_PLATE = TEST_DIR / ".." / "test_data" / "05035R7.PDF"


@pytest.fixture(scope="class")
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
