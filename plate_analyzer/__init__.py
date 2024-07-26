from . import segmentation, text_extraction

import pymupdf


class PlateAnalyzerException(Exception):
    """
    Thrown when analysis of a plate fails
    """
    pass


class PlateNeedsOCRException(PlateAnalyzerException):
    pass


def extract_information_from_plate(plate_path, debug=False):
    pdf = pymupdf.open(plate_path, filetype='pdf')
    plate = pdf[0]

    drawings = plate.get_drawings()
    textpage = plate.get_textpage()

    # See if we need to run OCR on the page.
    text = textpage.extractText()
    if 'CATEGORY' not in text:
        raise PlateNeedsOCRException("Plate requires OCR, no CATEGORY text")

    rectangles = segmentation.segment_plate_into_rectangles(
        plate, drawings, debug=debug
    )
    text_info = text_extraction.extract_text_from_segmented_plate(
        plate, drawings, textpage, rectangles, debug=debug
    )

    print("Has ARC:", text_info.has_dme_arc)
    print("Has procedure turn:", text_info.has_procedure_turn)
    print("Has hold-in-lieu:", text_info.has_hold_in_lieu_of_procedure_turn)
    for appch in text_info.approach_minimums:
        print(appch)

    return text_info
