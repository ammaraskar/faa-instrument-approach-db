"""
Deals with scanning drawings and graphics on the profile/plan view to find extra
bits of information.
"""

import random

import pymupdf
import numpy as np


def extract_approach_metadata(plan_view_box, plate, drawings, debug=False):
    # Return vals.
    has_hold_in_lieu = False
    has_procedure_turn = False

    # Bezier curves and lines to draw in debug mode.
    debug_curves = []
    debug_lines = []
    debug_barbs = []

    bezier_curve_locations = set()
    arc_diameter_lines = []
    # Looking for hold-in-lieu of procedure turns are a little difficult. We are
    # trying to identify the race track on the chart.
    #
    # Unfortunately, the race track is not fully complete, two curves and two
    # lines like we would expect. It usually has cut-outs to put in outbound
    # and inbound courses as well as areas for waypoints.
    #
    # We deal with this by:
    # 1. Looking for the two arcs on each side of the race-track.
    # 2. Connecting a line between the two arcs to get a semi-circle.
    # 3. Project a line perpendicular from the semi-circle diameter line and
    #    see if it intersects with another arc somewhere close by.
    for path in drawings:
        # Ignore stuff outside of plan view.
        if not plan_view_box.contains(path["rect"]):
            continue
        # For a charted hold, the arc on either side is typically made
        # of 4 bezier curves.
        if len(path["items"]) != 4:
            continue
        # Look for paths that only have bezier curves.
        has_curves_only = True
        for item in path["items"]:
            if item[0] != "c":
                has_curves_only = False
                break
        if not has_curves_only:
            continue

        # Draw a line between the start point of the first bezier curve and then
        # the final point of the last bezier curve.
        curve_start = path["items"][0][1]
        curve_end = path["items"][3][4]
        # Filter out any arcs that are too small.
        if curve_start.distance_to(curve_end) < 3:
            continue
        arc_diameter_lines.append((curve_start, curve_end))

        # Also add a rounded version of the curve start and end points for when
        # we check the interception.
        bezier_curve_locations.add(
            pymupdf.Point(round(curve_start.x, 1), round(curve_start.y, 1))
        )
        bezier_curve_locations.add(
            pymupdf.Point(round(curve_end.x, 1), round(curve_end.y, 1))
        )
        if debug:
            debug_curves.extend(path["items"])
    # Draw out a perpendicular line from each end of the arc-diameter lines and
    # check if they intercept any other bezier_curve_locations.
    for line in arc_diameter_lines:
        perp_line_1, perp_line_2 = get_i_beam_from_line(line)

        # Calculate shortest distance from perp_line_1 and perp_line_2 to
        # every bezier_curve_location. If it intercepts a bezier curve location
        # then we consider it to be a race-track.
        for curve_loc in bezier_curve_locations:
            # Ignore the curve locations that are on this arc line itself.
            if curve_loc.distance_to(line[0]) < 2 or curve_loc.distance_to(line[1]) < 2:
                continue
            # Calculate distance between perp lines and the point.
            curve_loc_array = np.array([curve_loc.x, curve_loc.y])
            perp_line_1_distance = line_distance_to_point(perp_line_1, curve_loc_array)
            perp_line_2_distance = line_distance_to_point(perp_line_2, curve_loc_array)
            if perp_line_1_distance < 1 or perp_line_2_distance < 1:
                has_hold_in_lieu = True

        if debug:
            debug_lines.append(perp_line_1)
            debug_lines.append(perp_line_2)

    # Next look for the procedure turn barb.
    #     l
    #   -----
    #   \
    #    \
    #  h  \
    #      \
    # We are basically looking for the flat base of the triangle and the long
    # hypotenus that makes up the barb. We then check the angle between these
    # lines to make sure it's what we expect.
    base_candidates = []
    # Dict of rounded hypotenuse coordinates to hypotenuse line, so we can check
    # it fast against all possible base lines.
    hypotenuse_candidates = {}
    for path in drawings:
        # Ignore stuff outside of plan view.
        if not plan_view_box.contains(path["rect"]):
            continue

        # Look for paths that only have lines.
        has_lines_only = True
        for item in path["items"]:
            if item[0] != "l":
                has_lines_only = False
                break
        if not has_lines_only:
            continue

        for item in path["items"]:
            line = (item[1], item[2])
            line_distance = item[1].distance_to(item[2])

            # Barb triangle base between around 4.8
            if abs(line_distance - 4.8) < 0.6:
                base_candidates.append(line)
                if debug:
                    arc_diameter_lines.append(line)
            # Barb triangle hypotenuse around 9
            if abs(line_distance - 9) < 1:
                p1 = (round(item[1].x, 0), round(item[1].y, 0))
                p2 = (round(item[2].x, 0), round(item[2].y, 0))

                hypotenuse_candidates[p1] = line
                hypotenuse_candidates[p2] = line

                if debug:
                    debug_lines.append(line)
    # Iterate over the bases and see if they intersect with any hypotenus.
    for base_p1, base_p2 in base_candidates:
        rounded_base_p1 = (round(base_p1.x, 0), round(base_p1.y, 0))
        rounded_base_p2 = (round(base_p2.x, 0), round(base_p2.y, 0))

        hypotenuse = None
        if rounded_base_p1 in hypotenuse_candidates:
            hypotenuse = hypotenuse_candidates[rounded_base_p1]
        elif rounded_base_p2 in hypotenuse_candidates:
            hypotenuse = hypotenuse_candidates[rounded_base_p1]
        else:
            continue

        base_line = np.array([base_p2.x - base_p1.x, base_p2.y - base_p1.y])
        hypotenuse_line = np.array(
            [hypotenuse[1].x - hypotenuse[0].x, hypotenuse[1].y - hypotenuse[0].y]
        )

        # Calculate angle between hypotenuse and base line.
        angle = angle_between_lines(base_line, hypotenuse_line)
        angle = np.rad2deg(angle)
        if angle > 90:
            angle = 180 - angle
        if debug:
            debug_barbs.append(
                (
                    (hypotenuse),
                    (base_p1, base_p2),
                    angle,
                )
            )
        # Around a 55 degree angle for the barb.
        if abs(angle - 55) < 10:
            has_procedure_turn = True

    if debug:
        outpdf = pymupdf.open()
        outpage = outpdf.new_page(width=plate.rect.width, height=plate.rect.height)
        shape = outpage.new_shape()

        for loc in bezier_curve_locations:
            shape.draw_circle(loc, 1)
            shape.finish(color=(1, 0, 0))

        for item in debug_curves:
            shape.draw_bezier(item[1], item[2], item[3], item[4])
            shape.finish(
                color=(
                    random.random(),
                    random.random(),
                    random.random(),
                    random.random(),
                ),
                closePath=False,
            )

        for line in arc_diameter_lines:
            shape.draw_line(line[0], line[1])
            shape.finish(color=(0, 1, 0))

        for line in debug_lines:
            shape.draw_line(line[0], line[1])
            shape.finish(color=(0, 0, 1), dashes="[3 4] 0")

        for base, hypotenuse, angle in debug_barbs:
            shape.draw_line(base[0], base[1])
            shape.finish(color=(1, 0.5, 0.5))
            shape.draw_line(hypotenuse[0], hypotenuse[1])
            shape.finish(color=(0.5, 0.5, 1))
            outpage.insert_text(base[0] + pymupdf.Point(2, 2), "A: " + str(int(angle)))

        shape.commit()
        outpage.get_pixmap(dpi=400).save("drawings.png")

    return (has_hold_in_lieu, has_procedure_turn)


I_BEAM_PERPENDICULAR_LENGTH = 80


def get_i_beam_from_line(line):
    """Calculate two lines from the line segment `line`. The lines are
    perpendicular to `line` and have midpoints at the start of the line segment
    and end of line segment. This makes an i-beam sort of shape like this:

        ret[0]
        ───┬───
           │
           │ line
           │
           │
        ───┴───
        ret[1]
    """
    (point1, point2) = line
    point1_vec = np.array([point1.x, point1.y])
    point2_vec = np.array([point2.x, point2.y])

    vec = point2_vec - point1_vec

    perp_vec = np.empty_like(vec)
    perp_vec[0] = -vec[1]
    perp_vec[1] = vec[0]

    perp_norm = perp_vec / np.linalg.norm(perp_vec)

    perp_line_1 = (point1_vec + (perp_norm * I_BEAM_PERPENDICULAR_LENGTH)), (
        point1_vec + (perp_norm * -I_BEAM_PERPENDICULAR_LENGTH)
    )
    perp_line_2 = (point2_vec + (perp_norm * I_BEAM_PERPENDICULAR_LENGTH)), (
        point2_vec + (perp_norm * -I_BEAM_PERPENDICULAR_LENGTH)
    )

    return perp_line_1, perp_line_2


def line_distance_to_point(line, point):
    """Calculate perpendicular from a tuple of points defining `line` and `point`"""
    return np.linalg.norm(
        np.cross(line[0] - line[1], line[1] - point)
    ) / np.linalg.norm(line[1] - line[0])


def unit_vector(vector):
    """Returns the unit vector of the vector."""
    return vector / np.linalg.norm(vector)


def angle_between_lines(line1, line2):
    """Calculate the angle between line1 and line2."""
    v1_u = unit_vector(line1)
    v2_u = unit_vector(line2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))
