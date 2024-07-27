"""
Opens up a FAA Digital-Terminal Procedures Publication (Complete)
https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/
zip file and analyzes each plate present in the zip.
"""

import zipfile
import tempfile
import pathlib
from plate_analyzer import extract_information_from_plate, PlateNeedsOCRException


ignored_approaches = set(
    [
        # This plate is busted, table for the category has no divider
        # between the word "CATEGORY" and "A"
        "05052IL9R.PDF",
        # Also busted, no category seperator line between A and B.
        "05091N18L.PDF",
        # ILS RWY 19C (CAT II & III) at Dulles, very complicated.
        "05100I19CC2_3.PDF",
        # ILS RWY 19R (CAT II & III) at Dulles, very complicated.
        "05100I19RC2_3.PDF",
        # VOR-C at ELY, missing complete line in cat B/cat C seperator.
        "05163VC.PDF",
        # ILS/LOC 24 at FEP Missed approach box line messed up.
        "05641IL24.PDF",
        # VOR 28 at BJJ, plan view line has two separate segments.
        "05663V28.PDF",
    ]
)


def scan_dtpp_file(zip):
    with zipfile.ZipFile(zip, "r") as dtpp_zip:
        for i, file_info in enumerate(dtpp_zip.infolist()):
            if "COPTER" in file_info.filename:
                continue

            if file_info.filename.upper() in ignored_approaches:
                continue

            # if i not in (5,):
            #    continue
            if i > 5000:
                break

            # if file_info.filename != '05216IL30.PDF': continue

            print(i, file_info)
            with dtpp_zip.open(file_info.filename) as approach_zip:
                try:
                    analyze_zip_approach_file(approach_zip)
                except PlateNeedsOCRException:
                    print("OCR needed")


def analyze_zip_approach_file(file):
    temp_file = pathlib.Path(tempfile.gettempdir()) / "analyze_plate.pdf"
    with temp_file.open("wb") as f:
        f.write(file.read())
    extract_information_from_plate(temp_file, debug=True)
