"""
Opens up a FAA Digital-Terminal Procedures Publication (Complete)
https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/
zip file and analyzes each plate present in the zip.
"""

import zipfile
import tempfile
import pathlib
import xml.etree.ElementTree as ET
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


def verify_contents_of_zip_against_metadata(folder):
    """Checks the contents of the d-tpp_Metafile.xml against the zip files
    containing the pdfs to see if all the expected files are present.

    This is mostly just a testing function I wrote to see the contents of these
    files myself, not used in any actual scraping code.
    """
    folder_path = pathlib.Path(folder)

    approach_pdfs_in_metadata = set()
    all_pdfs_in_metadata = set()
    approach_pdfs_in_zips = set()

    meta_file = folder_path / 'd-tpp_Metafile.xml'
    with meta_file.open('r') as f:
        metadata = ET.fromstring(f.read())

    for airport in metadata.iter('airport_name'):
        # Some local US only airports don't have icao identifiers.
        airport_id = airport.attrib['icao_ident']
        if not airport_id:
            airport_id = airport.attrib['apt_ident']
        
        for record in airport.iter('record'):
            pdf_file = record.find('pdf_name').text
            if pdf_file:
                all_pdfs_in_metadata.add(pdf_file)

            # Specifically note instrument approaches.
            chart_code = record.find('chart_code').text
            if chart_code != 'IAP':
                continue
            approach_pdfs_in_metadata.add(pdf_file)

    # Now collect the pdfs in the actual zips.
    for zip_path in folder_path.glob('DDTPP*.zip'):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            for file_info in dtpp_zip.infolist():
                if 'compare_pdf' in file_info.filename or '.xml' in file_info.filename:
                    break
                approach_pdfs_in_zips.add(file_info.filename)

    # Let's see if there's any metadata files not present in the zips.
    in_metadata_not_in_zips = approach_pdfs_in_metadata - approach_pdfs_in_zips
    assert in_metadata_not_in_zips == {'DELETED_JOB.PDF'}

    # Let's look at the ones in the zip but not in the metadata.
    in_zip_but_not_metadata = approach_pdfs_in_zips - all_pdfs_in_metadata
    print("In zip but not metadata", in_zip_but_not_metadata)
