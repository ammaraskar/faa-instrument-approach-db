import pymupdf

from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass
class PlateComments:
    non_standard_takeoff_minimums: bool
    non_standard_alternative_requirements: bool
    comments: str


@dataclass
class SegmentedPlate:
    approach_course: Tuple[pymupdf.Rect, str]

    required_equipment: Optional[Tuple[pymupdf.Rect, str]]
    comments: Tuple[pymupdf.Rect, PlateComments]
    missed_approach_instructions: Tuple[pymupdf.Rect, str]

    approach_minimums_boxes: List[pymupdf.Rect]


def extract_text_from_segmented_plate(
    plate: pymupdf.Page, textpage, rectangles: List[pymupdf.Rect], debug=False
) -> SegmentedPlate:
    # Put the rectangles into a sparse 2d array by their y and then x positions
    # on the page:
    #
    #     0  1  2  3  4
    #   ------------
    # 0 | r1 r2 r3
    # 1 | r4 r5 r6 r7 r8
    # 2 | r9 r10
    #
    # rectangle_layout[0] = [r1, r2, r3]
    # rectangle_layout[1] = [r4, r5, r6, r7, r8]
    # rectangle_layout[2] = [r9, r10]
    rectangles.sort(key=lambda rect: (rect.top_left.y, rect.top_left.x))
    rectangle_layout = []
    previous_y = -1
    for r in rectangles:
        rectangle_y = round(r.top_left.y, 0)
        if previous_y != rectangle_y:
            rectangle_layout.append([])
            previous_y = rectangle_y
        rectangle_layout[-1].append(r)

    for rects in rectangle_layout:
        print(rects)

    approach_course_box = rectangle_layout[0][1]
    approach_text = plate.get_textbox(approach_course_box, textpage=textpage).strip()
    assert "APP CRS" in approach_text

    # Look for "MISSED APPROACH" on rows 0 to 4 for the missed approach
    # instructions.
    missed_approach_rect = None
    for i in range(0, 3):
        for rect in rectangle_layout[i]:
            rect_text = plate.get_textbox(rect, textpage=textpage)
            if "MISSED APPROACH" in rect_text:
                missed_approach_rect = rect

    if missed_approach_rect is None:
        raise ValueError("Could not find missed approach instructions")
    # Missed approach has very strange ordering in the pdf, we often end up with
    # things like:
    #   'direct CELSY and hold.  \nMISSED APPROACH: Climb to 4200'.
    # Therefore, re-extract the text with sorting.
    missed_approach_text = plate.get_text(
        option="words", sort=True, clip=missed_approach_rect
    )
    missed_approach_text = " ".join([m[4].strip() for m in missed_approach_text])

    # Comments box will be around half the width of the document, and its bottom
    # will line up with the missed approach box.
    comments_box = None
    for i in (1, 2):
        for rect in rectangle_layout[i]:
            if rect.width > (plate.rect.width * 0.4) and int(rect.bottom_left.y) == int(
                missed_approach_rect.bottom_left.y
            ):
                comments_box = rect
                break
    if comments_box is None:
        raise ValueError("Could not find comments box")
    # The left side of the comments box will have a "T" for non-standard takeoff
    # minimums and "A" for non-standard alternative requirements.
    non_standard_takeoff_minimums = False
    non_standard_alternative_requirements = False

    left_side_comments = pymupdf.Rect(
        comments_box.top_left, comments_box.bottom_left + pymupdf.Point(10, 0)
    )
    left_side_text = plate.get_textbox(rect=left_side_comments, textpage=textpage)
    if "A" in left_side_text:
        non_standard_takeoff_minimums = True
    if "T" in left_side_text:
        non_standard_alternative_requirements = True

    right_side_comments = pymupdf.Rect(
        left_side_comments.top_right, comments_box.bottom_right
    )
    comments_text = plate.get_text(option="words", sort=True, clip=right_side_comments)
    comments_text = " ".join([m[4].strip() for m in comments_text])

    comments = PlateComments(
        non_standard_takeoff_minimums,
        non_standard_alternative_requirements,
        comments=comments_text,
    )

    # If there is a required equipment box, it will be a narrow one above the
    # comments.
    required_equipment = None
    for i in (0, 1, 2):
        for rect in rectangle_layout[i]:
            if (
                rect != comments_box
                and int(rect.width - comments_box.width) == 0
                and rect.top_left.y > comments_box.top_left.y
            ):
                required_equipment_box = rect
                break

    if required_equipment_box:
        required_equipment = plate.get_text(
            option="words", sort=True, clip=required_equipment_box
        )
        required_equipment = " ".join([m[4].strip() for m in required_equipment])
        required_equipment = (required_equipment_box, required_equipment)

    return SegmentedPlate(
        approach_course=(approach_course_box, approach_text),
        required_equipment=required_equipment,
        missed_approach_instructions=(missed_approach_rect, missed_approach_text),
        comments=comments,
    )
