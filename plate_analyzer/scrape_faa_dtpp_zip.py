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
import re
import multiprocessing
from typing import Optional, Tuple, List

from plate_analyzer import (
    extract_information_from_pdf,
    PlateNeedsOCRException,
)
from plate_analyzer.text_extraction import SegmentedPlate, ApproachMinimum
from plate_analyzer.cifp_analysis import analyze_cifp_file
from plate_analyzer.schema import (
    AnalysisResult,
    Failure,
    Airport,
    ApproachName,
    SkippedApproach,
    Approach,
    ApproachComments,
    ApproachType,
    ApproachMinimums,
    MinimumsValue,
    APPROACH_NOT_ALLOWED,
)

import pymupdf
from tqdm import tqdm


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


def analyze_dtpp_zips(folder, cifp_file, num_worker_processes=None) -> AnalysisResult:
    """Given a folder containing the `DDTPPX_CYCLE.zip` files, analyzes all
    the approach plates inside. Combines with airport data from the
    `cifp` file to spit out a full analysis.
    """
    folder_path = pathlib.Path(folder)

    # Find the metadata file amongst the zips.
    metadata = None
    dtpp_cycle = None
    for zip_path in folder_path.glob("DDTPP*.zip"):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            for file in dtpp_zip.namelist():
                if file != "d-TPP_Metafile.xml":
                    continue
                with dtpp_zip.open(file) as f:
                    metadata = ET.fromstring(f.read())
                # File name is usually something like `DDTPPE_240711`
                # Stuff after the underscore is the cycle.
                dtpp_cycle = zip_path.stem.split("_")[1]
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
    approaches_by_airport = collections.defaultdict(list)

    # Now iterate through each approach, and attempt to analyze it.
    def pdf_processing_futures_iterator():
        for file, pdf_data in dtpp_pdf_processing_iterator(folder_path):
            if file not in approach_file_to_airport:
                # print("Ignoring file", file)
                continue
            yield (file, pdf_data)

    # Intentionally don't use a full cpu count worth of processes as this
    # actually seems to slow stuff down.
    if num_worker_processes is None:
        num_worker_processes = (multiprocessing.cpu_count() // 2) + 1

    with multiprocessing.Pool(processes=num_worker_processes) as pool:
        # Set up a progress bar for counting as results come in...
        with tqdm(total=len(approach_file_to_airport)) as pbar:
            for file, approach_info, exception_message in pool.imap_unordered(
                process_single_dtpp_pdf, pdf_processing_futures_iterator()
            ):
                pbar.update(1)

                if exception_message is None:
                    airport, approach = approach_file_to_airport[file]
                    approaches_by_airport[airport].append(
                        (approach_info, approach, file)
                    )
                    continue

                # It threw an exception, add it to the failures.
                failures.append(
                    Failure(
                        exception_message=exception_message,
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

    cifp_airports = analyze_cifp_file(cifp_file)
    # Merge data from the cifp dataset with the approach plates.
    airports = {}
    for airport, approaches in approaches_by_airport.items():
        cifp_airport = cifp_airports[airport]
        for plate_info, approach_name, file_name in approaches:
            cifp_airport.approaches.append(
                create_approach_to_airport(
                    cifp_airport, plate_info, approach_name, file_name
                )
            )
        airports[airport] = cifp_airport

    return AnalysisResult(
        dtpp_cycle_number=dtpp_cycle,
        airports=airports,
        failures=failures,
        skipped_approaches=skipped_approaches,
    )


def dtpp_pdf_processing_iterator(folder_path: pathlib.Path):
    """
    Provides an iterator over the DDTPP zip files in a folder, yielding the name
    of files and pdf data as io.BytesIO of any files in the approach_file_to_airport
    dict.
    """
    for zip_path in folder_path.glob("DDTPP*.zip"):
        with zipfile.ZipFile(zip_path, "r") as dtpp_zip:
            for file in dtpp_zip.namelist():
                with dtpp_zip.open(file) as approach_zip:
                    pdf_data = io.BytesIO(approach_zip.read())

                yield (file, pdf_data)


# Passed as a single arg because we use this with pool.imap_unordered.
def process_single_dtpp_pdf(
    arg: Tuple[str, io.BytesIO]
) -> Tuple[str, SegmentedPlate, Exception]:
    file_name, pdf_data = arg

    try:
        pdf = pymupdf.open(filetype="pdf", stream=pdf_data)
        approach_info = extract_information_from_pdf(pdf, debug=False)
        return (file_name, approach_info, None)
    except KeyboardInterrupt as e:
        print("Keyboard interrupt in process_single_dtpp_pdf")
        raise e
    except Exception as e:
        exc_frame = traceback.extract_tb(e.__traceback__)[-1]
        exception_message = f"{repr(e)} {exc_frame.filename}:{exc_frame.lineno}"

        return (file_name, None, exception_message)


def create_approach_to_airport(
    airport: Airport, plate_info: SegmentedPlate, approach_name: str, file_name: str
) -> Approach:

    approach_course = get_approach_course_in_degrees(plate_info)
    # See if this approach is to a runway.
    approach_types, runway = get_approach_type_and_runway_from_title(approach_name)
    runway_approach_offset_angle = None
    if runway is not None:
        runway = f"RW{runway}"
        # Cool, now see if we have this runway in the cifp airport info.
        airport_runway = [r for r in airport.runways if r.name == runway]
        # Calculate the offset from the approach course to the runway.
        if airport_runway and approach_course is not None:
            runway_approach_offset_angle = calculate_heading_angle_difference(
                approach_course, airport_runway[0].bearing
            )
        # If the runway isn't in cifp data, make it None so we don't include
        # it in the output.
        if not airport_runway:
            runway = None

    return Approach(
        name=approach_name,
        plate_file=file_name,
        types=approach_types,
        comments=ApproachComments(
            text_comments=plate_info.comments.comments,
            has_non_standard_takeoff_minimums=plate_info.comments.non_standard_takeoff_minimums,
            has_non_standard_alternative_requirements=plate_info.comments.non_standard_alternative_requirements,
        ),
        missed_instructions=plate_info.missed_approach_instructions[1],
        # Runway/approach course info.
        approach_course=approach_course,
        runway=runway,
        runway_approach_offset_angle=runway_approach_offset_angle,
        # Approach features.
        has_dme_arc=plate_info.has_dme_arc,
        has_procedure_turn=plate_info.has_procedure_turn,
        has_hold_in_lieu_of_procedure_turn=plate_info.has_hold_in_lieu_of_procedure_turn,
        # Minimums.
        minimums=minimums_from_plate_info(plate_info),
    )


def minimums_from_plate_info(plate_info: SegmentedPlate) -> List[ApproachMinimums]:
    minimums = []

    for min in plate_info.approach_minimums:
        # Get rid of any footnote markers.
        approach_type = min.approach_type.replace("*", "").replace("#", "").strip()
        minimums.append(
            ApproachMinimums(
                minimums_type=approach_type,
                cat_a=minimums_values_from_plate(min.cat_a),
                cat_b=minimums_values_from_plate(min.cat_b),
                cat_c=minimums_values_from_plate(min.cat_c),
                cat_d=minimums_values_from_plate(min.cat_d),
            )
        )

    return minimums


def minimums_values_from_plate(
    minimums_values: Optional[ApproachMinimum],
) -> MinimumsValue:
    if minimums_values is None:
        return APPROACH_NOT_ALLOWED
    if minimums_values == "Unknown":
        return None
    return MinimumsValue(
        altitude=minimums_values.altitude,
        rvr=minimums_values.rvr,
        visibility=minimums_values.visibility,
    )


RUNWAY_NAME_REGEX = re.compile(r"RWY (\d\d?[A-Z]?)")
APPROACH_NAME_SUFFIX_REGEX = re.compile(r"-[A-Z]$")
APPROACH_TYPE_SUFFIX_REGEX = re.compile(r"\b[A-Z]$$")


def get_approach_type_and_runway_from_title(
    approach_name: str,
) -> Tuple[List[str], str]:
    """
    Take an approch name like: ILS OR LOC RWY 19L
    and determine the approach types, ['ILS', 'LOC'] and the runway if present.
    """
    runway = None
    runway_matches = RUNWAY_NAME_REGEX.search(approach_name)
    # See if the approach is to a runway.
    if runway_matches:
        runway = runway_matches.group(1)
        # Delete everything after the runway, so we're left with just
        # `ILS or LOC`
        approach_name = approach_name[: runway_matches.span()[0]].strip()
    else:
        # Otherwise look for an approach suffix, used when an approach doesn't
        # go to a runway like: VOR-A
        # and strip it out.
        approach_name = APPROACH_NAME_SUFFIX_REGEX.sub("", approach_name).strip()

    # Some military plates will have things like `HI-TACAN` or `HI-ILS or LOC`
    # indicating a high altitude approach.
    has_high_suffix = False
    if approach_name.startswith("HI-"):
        has_high_suffix = True
        approach_name = approach_name.replace("HI-", "")

    approach_types = []
    for type_string in approach_name.split(" OR "):
        # Ignore PRM approaches for now, they seem pretty esoteric lol.
        if "PRM" in type_string:
            type_string = type_string.replace("PRM", "").strip()
        # Ignore the converging prefix for ISL approaches.
        if "CONVERGING ILS" in type_string:
            type_string = type_string.replace("CONVERGING ", "")
        # Some VOR approaches have a suffix to denote two different types of
        # VORs in, like `VOR-1 RWY 14L` and `VOR-3 RWY 14L`.
        if type_string.startswith("VOR") and type_string[-2] == "-":
            type_string = type_string[:-2]

        # Check if there is a suffix on this approach. Multiple approaches into
        # the same runway will often get a suffix like: `RNAV (GPS) Y`
        type_string = APPROACH_TYPE_SUFFIX_REGEX.sub("", type_string.strip())
        approach_types.append(
            ApproachType.from_approach_title(
                type_string.strip(), is_high_alt=has_high_suffix
            )
        )

    return (approach_types, runway)


APPROACH_COURSE_REGEX = re.compile(r"(\d\d?\d?)°")


def get_approach_course_in_degrees(plate_info: SegmentedPlate) -> Optional[float]:
    app_course = plate_info.approach_course[1]
    degree_match = APPROACH_COURSE_REGEX.search(app_course)
    if not degree_match:
        return

    try:
        return float(degree_match.group(1))
    except ValueError:
        return


def calculate_heading_angle_difference(h1: float, h2: float) -> float:
    """
    Calculate the difference between two headings.

    For example:
        350°, 355° = 5°.
        359°, 04° = 6°
    """
    angle1 = (h1 - h2) % 360
    angle2 = (h2 - h1) % 360
    return min(angle1, angle2)


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
