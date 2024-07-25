from plate_analyzer.drawing_extraction import (
    line_distance_to_point,
    get_i_beam_from_line,
    I_BEAM_PERPENDICULAR_LENGTH,
)

import pymupdf
import numpy as np


def test_get_i_beam_from_line_returns_horizontal_line_for_vertical():
    # Make sure if we give a vertical line, it provides two horizontal lines.
    point1 = pymupdf.Point(10, 10)
    point2 = pymupdf.Point(10, 0)

    i_beam_top, i_beam_bottom = get_i_beam_from_line((point1, point2))

    i_beam_top = pymupdf.Point(i_beam_top[0]), pymupdf.Point(i_beam_top[1])
    assert i_beam_top[0].x == 10 + I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_top[0].y == 10
    assert i_beam_top[1].x == 10 - I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_top[1].y == 10

    i_beam_bottom = pymupdf.Point(i_beam_bottom[0]), pymupdf.Point(i_beam_bottom[1])
    assert i_beam_bottom[0].x == 10 + I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_bottom[0].y == 0
    assert i_beam_bottom[1].x == 10 - I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_bottom[1].y == 0


def test_get_i_beam_from_line_returns_horizontal_line_for_vertical():
    # Make sure if we give a horizontal line, it provides two vertical lines.
    point1 = pymupdf.Point(0, 0)
    point2 = pymupdf.Point(20, 0)

    i_beam_top, i_beam_bottom = get_i_beam_from_line((point1, point2))

    i_beam_top = pymupdf.Point(i_beam_top[0]), pymupdf.Point(i_beam_top[1])
    assert i_beam_top[0].x == 0
    assert i_beam_top[0].y == I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_top[1].x == 0
    assert i_beam_top[1].y == -I_BEAM_PERPENDICULAR_LENGTH

    i_beam_bottom = pymupdf.Point(i_beam_bottom[0]), pymupdf.Point(i_beam_bottom[1])
    assert i_beam_bottom[0].x == 20
    assert i_beam_bottom[0].y == I_BEAM_PERPENDICULAR_LENGTH
    assert i_beam_bottom[1].x == 20
    assert i_beam_bottom[1].y == -I_BEAM_PERPENDICULAR_LENGTH


def calculate_perpendicular_distance_from_horizontal_line():
    line = np.array([0, 0]), np.array([10, 0])
    point = np.array([5, 1])

    distance = line_distance_to_point(line, point)
    assert distance == 5
