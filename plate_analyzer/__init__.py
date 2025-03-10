from . import segmentation, text_extraction
import re
from dataclasses import dataclass
from typing import List

import pymupdf


class PlateAnalyzerException(Exception):
    """
    Thrown when analysis of a plate fails
    """

    pass


class PlateNeedsOCRException(PlateAnalyzerException):
    pass


def extract_information_from_plate(plate_path, debug=False):
    pdf = pymupdf.open(plate_path, filetype="pdf")
    return extract_information_from_pdf(pdf, debug=debug)


def extract_information_from_pdf(pdf, debug=False):
    plate = pdf[0]

    drawings = plate.get_drawings()
    textpage = plate.get_textpage()

    # See if we need to run OCR on the page.
    text = textpage.extractText()
    if "CATEGORY" not in text:
        raise PlateNeedsOCRException("Plate requires OCR, no CATEGORY text")

    rectangles = segmentation.segment_plate_into_rectangles(
        plate, drawings, debug=debug
    )
    text_info = text_extraction.extract_text_from_segmented_plate(
        plate, drawings, textpage, rectangles, debug=debug
    )

    if debug:
        print(
            "---- ", text_info.approach_name, " - ", text_info.airport_name, "--------"
        )
        print("Has ARC:", text_info.has_dme_arc)
        print("Has procedure turn:", text_info.has_procedure_turn)
        print("Has hold-in-lieu:", text_info.has_hold_in_lieu_of_procedure_turn)
        for appch in text_info.approach_minimums:
            print(appch)

    return text_info


@dataclass
class RadarApproachAirport:
    airport: str
    has_par: bool
    has_asr: bool


# Matches stuff like `(KRUY)` with the capture group being the ICAO code.
ICAO_CODE_REGEX = re.compile(r"\(([A-Z]{4})\)")
THREE_LETTER_FAA_CODE_REGEX = re.compile(r"\(([A-Z]{3})\)")


def get_airports_from_radar_minimums(pdf: pymupdf.Document, debug=False) -> List[RadarApproachAirport]:
    airports = []

    for page in pdf:
        textpage = page.get_textpage()
        text = textpage.extractText()

        if "RADAR INSTRUMENT APPROACH MINIMUMS" not in text:
            if debug:
                print("Page does not have radar approach minimums text")
            continue

        # Get the airport code, it'll be a paranthesized 4-letter icao code.
        result = ICAO_CODE_REGEX.search(text)
        if result is None:
            if debug:
                print("Could not find ICAO airport code in page, trying FAA")
            # Could be a 3-letter faa code.
            result = THREE_LETTER_FAA_CODE_REGEX.search(text)
            if result is None:
                print("Could not find ICAO or FAA code on page.")
                continue
            icao_code = "K" + result.group(1)
        else:
            icao_code = result.group(1)

        # Now see if the words "PAR" and "ASR" show up on the page.
        has_par = "PAR" in text
        has_asr = "ASR" in text

        airports.append(
            RadarApproachAirport(airport=icao_code, has_par=has_par, has_asr=has_asr))

    return airports
