import pymupdf

from . import drawing_extraction

import collections
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict


@dataclass
class PlateComments:
    non_standard_takeoff_minimums: bool
    non_standard_alternative_requirements: bool
    comments: str


@dataclass
class ApproachMinimum:
    altitude: str
    rvr: Optional[str]
    visibility: Optional[str]


@dataclass
class ApproachCategory:
    approach_type: str
    # Altitude, visibility for each category.
    # e.g 300 3/4
    cat_a: ApproachMinimum
    cat_b: ApproachMinimum
    cat_c: ApproachMinimum
    cat_d: ApproachMinimum
    # Used if these minimums are valid based on a condition, such as being
    # able to identify a particular fix.
    condition: Optional[str]


@dataclass
class Waypoint:
    is_initial_approach_fix: bool
    is_intermediate_fix: bool
    is_final_approach_fix: bool

    def __init__(self):
        self.is_initial_approach_fix = False
        self.is_intermediate_fix = False
        self.is_final_approach_fix = False


@dataclass
class SegmentedPlate:
    approach_name: str
    airport_name: str
    approach_course: Tuple[pymupdf.Rect, str]

    has_dme_arc: bool

    waypoints: Dict[str, Waypoint]

    required_equipment: Optional[Tuple[pymupdf.Rect, str]]
    comments: PlateComments
    missed_approach_instructions: Tuple[pymupdf.Rect, str]

    approach_minimums: List[ApproachCategory]


def extract_text_from_segmented_plate(
    plate: pymupdf.Page, drawings, textpage, rectangles: List[pymupdf.Rect], debug=False
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
        rectangle_y = round(r.top_left.y, 1)
        if previous_y != rectangle_y:
            rectangle_layout.append([])
            previous_y = rectangle_y
        rectangle_layout[-1].append(r)

    approach_course_box = rectangle_layout[0][1]
    approach_text = (
        plate.get_textbox(approach_course_box, textpage=textpage)
        .replace("APP CRS", "")
        .strip()
    )

    # Approach title will be on the right side of the page, on the same line
    # as the approach course.
    approach_title_area = pymupdf.Rect(
        approach_course_box.top_right + pymupdf.Point(100, 0),
        pymupdf.Point(plate.rect.width, approach_course_box.bottom_right.y),
    )
    approach_title = plate.get_text(option="words", sort=True, clip=approach_title_area)
    approach_title = pymupdf_group_words_into_lines_based_on_vertical_position(
        approach_title
    )
    # First line is the approach title, then the airport name.
    approach_name, airport_name = approach_title

    # Get all the waypoints in the plan view.
    plan_view_box = find_plan_view_box(rectangle_layout, plate)
    waypoints = extract_all_waypoints_from_plan_view(plan_view_box, plate)
    _ = drawing_extraction.extract_approach_metadata(
        plan_view_box, plate, drawings, debug=debug
    )
    has_dme_arc = has_dme_arc_in_plan_view(plan_view_box, plate)

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
    missed_approach_text = pymupdf_extracted_words_to_string(missed_approach_text)

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
    comments_text = pymupdf_extracted_words_to_string(comments_text)

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
                and rect.top_left.y < comments_box.top_left.y
            ):
                required_equipment = rect
                break

    if required_equipment:
        required_equipment_text = plate.get_text(
            option="words", sort=True, clip=required_equipment
        )
        required_equipment = (
            required_equipment,
            pymupdf_extracted_words_to_string(required_equipment_text),
        )

    minimums = extract_minimums(rectangle_layout, plate=plate, textpage=textpage)

    return SegmentedPlate(
        approach_name=approach_name,
        airport_name=airport_name,
        approach_course=(approach_course_box, approach_text),
        has_dme_arc=has_dme_arc,
        waypoints=dict(waypoints),
        required_equipment=required_equipment,
        missed_approach_instructions=(missed_approach_rect, missed_approach_text),
        comments=comments,
        approach_minimums=minimums,
    )


CATEGORIES = "ABCD"


def extract_minimums(
    rectangle_layout, plate: pymupdf.Page, textpage
) -> List[ApproachCategory]:
    # Locate the rectangle that says "CATEGORY"
    category_rect = None
    for i in range(len(rectangle_layout) - 1, 0, -1):
        for j, rect in enumerate(rectangle_layout[i]):
            rect_text = plate.get_textbox(rect, textpage=textpage).strip()
            if "CATEGORY" in rect_text:
                category_rect = rect

    if category_rect is None:
        raise ValueError("Unable to find CATEGORY box")

    # Filter out any rectangles that are above or the left of the minimums.
    filtered_rectangles = []
    for row in rectangle_layout:
        filtered_row = []
        for rect in row:
            if (rect.top_left.x + 0.5) > category_rect.top_left.x and (
                rect.top_left.y + 0.5
            ) > category_rect.top_left.y:
                filtered_row.append(rect)
        if len(filtered_row) != 0:
            filtered_rectangles.append(filtered_row)

    rectangle_layout = filtered_rectangles

    # Verify that the boxes next to category are A, B, C, D like we expect.
    category_boxes = []
    for i, letter in enumerate(CATEGORIES):
        letter_rect = rectangle_layout[0][i + 1]
        letter_text = plate.get_textbox(letter_rect, textpage=textpage).strip()
        if letter_text != letter:
            raise ValueError(
                f"letter {i} after CATEGORY should be {letter}, was {letter_text}"
            )
        category_boxes.append(letter_rect)

    # Grab the first approach name.
    all_minimums = []
    # First set of minimums are the default, no conditions.
    condition = None

    for i in range(1, len(rectangle_layout)):
        approach_name_rect = rectangle_layout[i][0]
        # Should be the same size as the category cell.
        if int(approach_name_rect.width) != int(category_rect.width):
            break
        approach_name = plate.get_textbox(approach_name_rect, textpage=textpage)
        # Remove the Decision Altitude/Minimum Descent Altitude suffix, and fix
        # LNAV/VNAV being split over two lines.
        approach_name = approach_name.replace("MDA", "").replace("DA", "").strip()
        if "LNAV" in approach_name and "VNAV" in approach_name:
            approach_name = "LNAV/VNAV"

        # If this is Circling with an additional C in the box, denote that it's
        # circling with extended protected area.
        if "CIRCLING" in approach_name and (
            "C" in approach_name.replace("CIRCLING", "")
        ):
            approach_name = "CIRCLING (Expanded Radius)"

        minimums_per_category = []
        # Now iterate through the minimums values, up to 4 boxes.
        num_minimums = 0
        j = 0
        while num_minimums < 4:
            minimums_box = rectangle_layout[i][j + 1]
            minimums = extract_minimums_from_text_box(
                minimums_box, approach_name, plate
            )
            # Check the width of the minimums box to see how many categories it
            # covers.
            num_categories_covered = int(
                round(minimums_box.width / category_boxes[0].width, 0)
            )
            for _ in range(num_categories_covered):
                minimums_per_category.append(minimums)
                num_minimums += 1
            j += 1

        cat_a, cat_b, cat_c, cat_d = minimums_per_category
        all_minimums.append(
            ApproachCategory(
                approach_name, cat_a, cat_b, cat_c, cat_d, condition=condition
            )
        )

    return all_minimums


def extract_minimums_from_text_box(box, minimum_type, plate) -> ApproachMinimum:
    # For circling minimums, we expect a second line for the HAA
    # (Height Above Airport) during circling, but we don't really need that
    # information. So only get letters from one half of the rectangle, either
    # the bottom or left side depending on the width of the box.
    if "CIRCLING" in minimum_type and ((box.width / box.height) > 5):
        # Very horizontal box, HHA is on the right.
        box = pymupdf.Rect(
            box.top_left, box.bottom_right - pymupdf.Point(box.width * 0.5, 0)
        )
    elif "CIRCLING" in minimum_type and ((box.width / box.height) <= 5):
        # Regular box, HHA is on the bottom.
        box = pymupdf.Rect(
            box.top_left, box.bottom_right - pymupdf.Point(0, box.height * 0.6)
        )

    raw_text = plate.get_text(option="rawdict", clip=box)
    # We will iterate over the minimums character-by-character sorted by x
    # coordinate.
    letters = []
    for block in raw_text["blocks"]:
        for line in block["lines"]:
            for span in line["spans"]:
                for char in span["chars"]:
                    letters.append(char)

    # Sort by x-cordinate.
    letters.sort(key=lambda c: c["origin"][0])
    # Remove spaces.
    letters = [l for l in letters if l["c"] != " "]

    # Gets set to visibility or rvr depending on what we're expecting next.
    next_number = None
    altitude = ""
    # Scan for the altitude first.
    for i, letter in enumerate(letters):
        # Dash separates altitude from visibility
        if letter["c"] == "-":
            next_number = "visibility"
            break
        # Slash separates rvr from visibility
        if letter["c"] == "/":
            next_number = "rvr"
            break
        altitude += letter["c"]

    # Weird, no altitude or rvr seperator. something must have gone wrong.
    if next_number is None:
        print(minimum_type, letters)
        raise ValueError("No slash or dash in minimums box")

    rvr = None
    visibility = None

    if next_number == "visibility":
        # A visibility will either be a single digit like '1', a fraction like ½
        # or a mixed fraction like 1 ½.
        first_number = letters[i + 1]
        visibility = first_number["c"]
        # Check if the first number is a fraction numerator by checking its
        # size against the altitude number.
        first_number_bbox = pymupdf.Rect(first_number["bbox"])
        first_letter_bbox = pymupdf.Rect(letters[0]["bbox"])
        if first_number_bbox.height < first_letter_bbox.height * 0.8:
            visibility = f"{visibility}/{letters[i + 2]['c']}"
        elif len(letters) > (i + 2):
            # First number was not a fraction, so this could be a single number
            # or a mixed fraction. Check if the next number is a fraction.
            second_number_bbox = pymupdf.Rect(letters[i + 2]["bbox"])
            if second_number_bbox.height < first_letter_bbox.height * 0.8:
                # Okay, next should be a fraction since it's close to the first
                # number.
                visibility = f"{visibility} {letters[i + 2]['c']}/{letters[i + 3]['c']}"
    elif next_number == "rvr":
        # RVR could be up to two numbers
        pass
    else:
        raise NotImplemented()

    return ApproachMinimum(altitude=altitude, rvr=rvr, visibility=visibility)


def pymupdf_extracted_words_to_string(words):
    """Joins a list of extracted words from pymudpf which are a list of tuples
    of the form `(x0, y0, x1, y1, "word", block_no, line_no, word_no)`
    into a string of the words.
    """
    return " ".join([w[4].strip() for w in words])


def pymupdf_group_words_into_lines_based_on_vertical_position(words):
    """Joins a list of extracted words into lines as above but returns a list
    of lines, grouping them based on their y-coordinate."""
    words_grouped_by_y = collections.defaultdict(list)

    for w in words:
        y1 = int(w[3])
        words_grouped_by_y[y1].append(w[4].strip())

    lines = []
    for y in sorted(words_grouped_by_y.keys()):
        lines.append(" ".join(words_grouped_by_y[y]))
    return lines


# Distance threshold between the (IAF) text to WAYPOINT name text to consider
# it an IAF. Also used for FAF, IF.
FIX_TEXT_DISTANCE_THRESHOLD = 25


def is_waypoint_text_close_to_approach_type(waypoint_loc, approach_fixes):
    is_close = False
    for initial_appraoch_fix in approach_fixes:
        iaf_location = pymupdf.Point(initial_appraoch_fix[2], initial_appraoch_fix[3])
        distance = iaf_location.distance_to(waypoint_loc)
        if distance < FIX_TEXT_DISTANCE_THRESHOLD:
            is_close = True
    return is_close


def extract_all_waypoints_from_plan_view(plan_view_box, plate):
    words = plate.get_text(option="words", sort=True, clip=plan_view_box)

    initial_approach_fix_texts = []
    intermediate_fix_texts = []
    final_approach_fix_texts = []
    for w in words:
        word = w[4].strip()
        if (not word.startswith("(")) or (not word.endswith(")")):
            continue
        if "IAF" in word:
            initial_approach_fix_texts.append(w)
        if "IF" in word:
            intermediate_fix_texts.append(w)
        if "FAF" in word:
            final_approach_fix_texts.append(w)

    waypoints = collections.defaultdict(Waypoint)
    for w in words:
        word = w[4].strip()
        # Waypoints are generally 5 uppercase letters.
        if len(word) != 5 or (not word.isalpha()) or word.upper() != word:
            continue
        # See if this is an initial approach fix by looking for the text IAF
        # nearby.
        word_location = pymupdf.Point(w[0], w[1])

        is_initial_approach_fix = is_waypoint_text_close_to_approach_type(
            word_location, initial_approach_fix_texts
        )
        is_intermediate_fix = is_waypoint_text_close_to_approach_type(
            word_location, intermediate_fix_texts
        )
        is_final_approach_fix = is_waypoint_text_close_to_approach_type(
            word_location, final_approach_fix_texts
        )
        # Set if the fix is IAF/IF/FAF based on what we saw here, updating any
        # previous bools.
        waypoints[word].is_initial_approach_fix |= is_initial_approach_fix
        waypoints[word].is_intermediate_fix |= is_intermediate_fix
        waypoints[word].is_final_approach_fix |= is_final_approach_fix

    return waypoints


def has_dme_arc_in_plan_view(plan_view_box, plate):
    """Look for the words 'Arc' in the plan view, this is slightly complicated
    by the fact that the words can be curved. This means we can't just use
    pymupdf's word extaction directly to find it.
    """
    words = plate.get_text(option="rawdict", sort=True, clip=plan_view_box)

    letter_locations = collections.defaultdict(list)

    for block in words["blocks"]:
        for line in block["lines"]:
            for span in line["spans"]:
                for char in span["chars"]:
                    # Note the locations of all 'A', 'r' and 'c' characters.
                    if char["c"] in ("A", "r", "c"):
                        letter_locations[char["c"]].append(
                            pymupdf.Point(char["origin"])
                        )

    if len(letter_locations["r"]) == 0 or len(letter_locations["c"]) == 0:
        return False

    # Iterate through all the 'A' characters.
    for a_location in letter_locations["A"]:
        # Check distances to the closest 'r' character.
        closest_r = min([r.distance_to(a_location) for r in letter_locations["r"]])
        if closest_r > 8:
            continue
        closest_c = min([c.distance_to(a_location) for c in letter_locations["c"]])
        if closest_c > 13:
            continue
        return True

    return False


def find_plan_view_box(rectangle_layout, plate) -> pymupdf.Rect:
    """Find the plan view part of the plate"""
    # Largest rectangle is probably the plan view.
    largest_rect = rectangle_layout[0][0]

    for row in rectangle_layout:
        for rect in row:
            if rect.get_area() > largest_rect.get_area():
                largest_rect = rect

    # Just assert that the rectangle is around the middle of the plate, that's
    # where we expect it to be.
    assert largest_rect.top_left.y < (plate.rect.height / 2)
    assert largest_rect.bottom_right.y > (plate.rect.height / 2)
    assert largest_rect.top_left.x < (plate.rect.width / 2)
    assert largest_rect.bottom_right.x > (plate.rect.width / 2)

    return largest_rect
