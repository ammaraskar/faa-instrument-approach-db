import pymupdf

from plate_analyzer import segmentation


def test_merge_close_lines_does_not_merge_far_away_lines():
    #     l1             l2
    # |---------|    |--------|
    l1 = pymupdf.Rect(0, 0, 20, 0)
    l2 = pymupdf.Rect(30, 0, 50, 0)
    
    joined = segmentation.merge_close_lines([l1, l2], vertical=False)
    assert joined == [l1, l2]


def test_merge_close_lines_merges_overlapping_horizontal():
    #     l1     l2
    # |--------|
    #        |-------|
    l1 = pymupdf.Rect(0, 0, 20, 0)
    l2 = pymupdf.Rect(15, 0, 35, 0)

    joined = segmentation.merge_close_lines([l1, l2], vertical=False)
    assert len(joined) == 1
    assert joined[0].top_left.x == 0
    assert joined[0].bottom_right.x == 35


def test_merge_close_lines_merges_lines_nearby():
    #     l1        l2
    # |---------||--------|
    l1 = pymupdf.Rect(0, 0, 19.8, 0)
    l2 = pymupdf.Rect(19.9, 0, 35, 0)

    joined = segmentation.merge_close_lines([l1, l2], vertical=False)
    assert len(joined) == 1
    assert joined[0].top_left.x == 0
    assert joined[0].bottom_right.x == 35

def test_merge_close_lines_multiple_vertical_segments():
    # A combination test of overlaps/close in vertical mode.
    #   -+-                -+-  
    #    |                  |   
    #    |                  | l4
    # l1 |                  |   
    #    | -+-             -+-  
    #   -+- |               |   
    #       | l2            | l5
    #       |               |   
    #      -+-             -+-  
    #       |                   
    #       | l3                
    #      -+-                 
    l1 = pymupdf.Rect(0, 0, 0, 21)
    l2 = pymupdf.Rect(0, 20, 0, 25.9)
    l3 = pymupdf.Rect(0, 26.0, 0, 30)

    l4 = pymupdf.Rect(10, 0, 10, 5)
    l5 = pymupdf.Rect(10, 5, 10, 10)

    joined = segmentation.merge_close_lines([l1, l2, l3, l4, l5], vertical=True)
    assert len(joined) == 2
    assert joined[0].top_left == pymupdf.Point(0, 0)
    assert joined[0].bottom_right == pymupdf.Point(0, 30)
    assert joined[1].top_left == pymupdf.Point(0, 0)
    assert joined[1].top_left == pymupdf.Point(0, 0)
