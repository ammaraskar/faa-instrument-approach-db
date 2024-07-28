"""
Opens up a FAA Digital-Terminal Procedures Publication (Complete)
https://www.faa.gov/air_traffic/flight_info/aeronav/digital_products/dtpp/
zip file and analyzes each plate present in the zip.
"""

import collections
import zipfile
import pathlib
import io
import traceback
import xml.etree.ElementTree as ET
from plate_analyzer import (
    extract_information_from_pdf,
    PlateNeedsOCRException,
    PlateAnalyzerException,
)
from plate_analyzer.schema import (
    AnalysisResult,
    Failure,
    Airport,
    ApproachName,
    SkippedApproach,
)

import pymupdf


def scan_dtpp_file(zip):
    with zipfile.ZipFile(zip, "r") as dtpp_zip:
        for i, file_info in enumerate(dtpp_zip.infolist()):
            if "COPTER" in file_info.filename:
                continue

            # if i not in (5,):
            #    continue
            if i > 5000:
                break

            # if file_info.filename != '05216IL30.PDF': continue

            print(i, file_info)
            with dtpp_zip.open(file_info.filename) as approach_zip:
                pdf_data = io.BytesIO(approach_zip.read())
                pdf = pymupdf.open(filetype="pdf", stream=pdf_data)
                try:
                    extract_information_from_pdf(pdf, debug=False)
                except PlateNeedsOCRException:
                    print("OCR needed")


def analyze_dtpp_zips(folder) -> AnalysisResult:
    """Given a folder containing the `DDTPPX_CYCLE.zip` files, analyzes all
    the approach plates inside."""
    folder_path = pathlib.Path(folder)

    # Find the metadata file amongst the zips.
    metadata = None
    for zip_path in folder_path.glob("DDTPP*.zip"):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            for file in dtpp_zip.namelist():
                if file != "d-TPP_Metafile.xml":
                    continue
                with dtpp_zip.open(file) as f:
                    metadata = ET.fromstring(f.read())
                break

    if metadata is None:
        raise ValueError("Did not locate d-TPP_Metafile.xml in any zip")

    skipped = collections.defaultdict(list)
    # Maps the approach file pdf name to the airport the approach is for, as
    # well as the name of the approach.
    approach_file_to_airport = {}
    for airport in metadata.iter("airport_name"):
        # Some local US only airports don't have icao identifiers.
        airport_id = airport.attrib["icao_ident"]
        if not airport_id:
            airport_id = airport.attrib["apt_ident"]

        for record in airport.iter("record"):
            # Specifically note instrument approaches.
            chart_code = record.find("chart_code").text
            if chart_code != "IAP":
                continue
            pdf_file = record.find("pdf_name").text
            chart_name = record.find("chart_name").text

            # Note if it's a civil or joint-use procedure. We can't parse
            # military procedures yet because their pdfs don't have text...
            civil_procedure = record.find("civil").text
            is_military = civil_procedure == "N" or civil_procedure == "H"

            # Skip visual and copter approaches.
            if "VISUAL" in chart_name:
                skipped["VISUAL"].append(
                    ApproachName(name=chart_name, airport=airport_id)
                )
                continue
            if "COPTER" in chart_name:
                skipped["COPTER"].append(
                    ApproachName(name=chart_name, airport=airport_id)
                )
                continue
            if is_military:
                skipped["MILITARY"].append(
                    ApproachName(name=chart_name, airport=airport_id)
                )
                continue

            approach_file_to_airport[pdf_file] = (airport_id, chart_name)

    failures = []
    # Now iterate through each approach, and attempt to analyze it.
    for zip_path in folder_path.glob("DDTPP*.zip"):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            i = 0
            for file in dtpp_zip.namelist():
                # TODO: remove this, for limited testing
                # if i > 100:
                #    break
                if file != "06065R8.PDF":
                    continue

                if file not in approach_file_to_airport:
                    print("Ignoring file", file)
                    continue

                i += 1

                airport, approach = approach_file_to_airport[file]
                with dtpp_zip.open(file) as approach_zip:
                    pdf_data = io.BytesIO(approach_zip.read())
                    pdf = pymupdf.open(filetype="pdf", stream=pdf_data)
                    try:
                        print("Analyzing", file)
                        extract_information_from_pdf(pdf, debug=False)
                    except Exception as e:
                        exc_frame = traceback.extract_tb(e.__traceback__, limit=1)[0]
                        failures.append(
                            Failure(
                                exception_message=f"{repr(e)} {exc_frame.filename}:{exc_frame.lineno}",
                                zip_file=zip_path.name,
                                file_name=file,
                                approach=ApproachName(
                                    name=approach,
                                    airport=airport,
                                ),
                            )
                        )

    skipped_approaches = []
    for skip_reason, skipped_list in skipped.items():
        skipped_approaches.append(
            SkippedApproach(
                skip_reason=skip_reason,
                approaches=skipped_list,
            )
        )
        print(f"SKIPPED because {skip_reason}: ", len(skipped_list))

    for failure in failures:
        print(
            f"Failed {failure.file_name} in {failure.zip_file}. "
            f"{failure.approach.name} at {failure.approach.airport}. "
            f"Exception: {failure.exception_message}"
        )

    return AnalysisResult(
        airports={}, failures=failures, skipped_approaches=skipped_approaches
    )


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

    meta_file = folder_path / "d-tpp_Metafile.xml"
    with meta_file.open("r") as f:
        metadata = ET.fromstring(f.read())

    for airport in metadata.iter("airport_name"):
        # Some local US only airports don't have icao identifiers.
        airport_id = airport.attrib["icao_ident"]
        if not airport_id:
            airport_id = airport.attrib["apt_ident"]

        for record in airport.iter("record"):
            pdf_file = record.find("pdf_name").text
            if pdf_file:
                all_pdfs_in_metadata.add(pdf_file)

            # Specifically note instrument approaches.
            chart_code = record.find("chart_code").text
            if chart_code != "IAP":
                continue
            approach_pdfs_in_metadata.add(pdf_file)

    # Now collect the pdfs in the actual zips.
    for zip_path in folder_path.glob("DDTPP*.zip"):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            for file_info in dtpp_zip.infolist():
                if "compare_pdf" in file_info.filename or ".xml" in file_info.filename:
                    break
                approach_pdfs_in_zips.add(file_info.filename)

    # Let's see if there's any metadata files not present in the zips.
    in_metadata_not_in_zips = approach_pdfs_in_metadata - approach_pdfs_in_zips
    assert in_metadata_not_in_zips == {"DELETED_JOB.PDF"}

    # Let's look at the ones in the zip but not in the metadata.
    in_zip_but_not_metadata = approach_pdfs_in_zips - all_pdfs_in_metadata
    print("In zip but not metadata", in_zip_but_not_metadata)
