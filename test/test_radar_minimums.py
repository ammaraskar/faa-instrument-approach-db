import plate_analyzer
import pymupdf

from pathlib import Path


TEST_DATA_DIR = Path(__file__).parent / ".." / "test_data"
TEST_RADAR_MINS_FILE = TEST_DATA_DIR / "SW3RAD_radar_minimums.pdf"


def test_gets_all_airports_in_minimums_file():
    pdf = pymupdf.open(TEST_RADAR_MINS_FILE, filetype="pdf")
    radar_approaches = plate_analyzer.get_airports_from_radar_minimums(pdf, debug=True)

    assert len(radar_approaches) == 5

    knfg = radar_approaches[0]
    assert knfg.airport == "KNFG"
    assert knfg.has_par == True
    assert knfg.has_asr == True

    knuc = radar_approaches[4]
    assert knuc.airport == "KNUC"
    assert knuc.has_par == True
    assert knuc.has_asr == True
