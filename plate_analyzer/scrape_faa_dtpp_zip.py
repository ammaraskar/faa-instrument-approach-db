"""
Opens up a FAA Digital-Terminal Procedures Publication (Complete)
https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/
zip file and analyzes each plate present in the zip.
"""
import zipfile
import tempfile
import pathlib
from plate_analyzer import extract_information_from_plate


def scan_dtpp_file(zip):
    with zipfile.ZipFile(zip, 'r') as dtpp_zip:
        for file_info in dtpp_zip.infolist():
            print(file_info)
            with dtpp_zip.open(file_info.filename) as approach_zip:
                analyze_zip_approach_file(approach_zip)
            break


def analyze_zip_approach_file(file):
    temp_file = pathlib.Path(tempfile.gettempdir()) / 'analyze_plate.pdf'
    with temp_file.open('wb') as f:
        f.write(file.read())
    extract_information_from_plate(temp_file)


