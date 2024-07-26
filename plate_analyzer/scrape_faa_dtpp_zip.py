"""
Opens up a FAA Digital-Terminal Procedures Publication (Complete)
https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/
zip file and analyzes each plate present in the zip.
"""
import zipfile
import tempfile
import pathlib
from plate_analyzer import extract_information_from_plate, PlateNeedsOCRException


def scan_dtpp_file(zip):
    with zipfile.ZipFile(zip, 'r') as dtpp_zip:
        for i, file_info in enumerate(dtpp_zip.infolist()):
            #if i not in (5,):
            #    continue
            if i > 100:
                break

            print(file_info)
            with dtpp_zip.open(file_info.filename) as approach_zip:
                try:
                    analyze_zip_approach_file(approach_zip)
                except PlateNeedsOCRException:
                    print("OCR needed")



def analyze_zip_approach_file(file):
    temp_file = pathlib.Path(tempfile.gettempdir()) / 'analyze_plate.pdf'
    with temp_file.open('wb') as f:
        f.write(file.read())
    extract_information_from_plate(temp_file, debug=True)


