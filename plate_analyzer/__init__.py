from . import segmentation, text_extraction

import pymupdf


def extract_information_from_plate(plate_path, debug=False):
    pdf = pymupdf.open(plate_path, filetype='pdf')
    plate = pdf[0]

    drawings = plate.get_drawings()
    textpage = plate.get_textpage()

    rectangles = segmentation.segment_plate_into_rectangles(
        plate, drawings, debug=debug
    )
    text_info = text_extraction.extract_text_from_segmented_plate(
        plate, drawings, textpage, rectangles, debug=debug
    )

    for appch in text_info.approach_minimums:
        print(appch)

    return text_info
