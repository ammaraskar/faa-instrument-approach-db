import pymupdf
import numpy as np
import skimage

from typing import Optional


def line_segment_as_rect_from_points(point1, point2):
    """
    Creates a pymupdf.Rect instance from point1 and point2 representing a line
    segment.
    """
    x0, y0 = round(point1.x, 1), round(point1.y, 1)
    x1, y1 = round(point2.x, 1), round(point2.y, 1)
    rect = pymupdf.Rect(x0, y0, x1, y1)
    rect.normalize()
    return rect


def make_rectangle_from_quad(quad: pymupdf.Quad) -> Optional[pymupdf.Rect]:
    # Sort by y-then-x to get the upper left, upper right and then lower left
    # lower right points of the quad.
    points = [quad.ul, quad.ur, quad.ll, quad.lr]
    quad_points = [pymupdf.Point(round(p.x, 0), round(p.y, 0)) for p in points]
    quad_points_sorted = sorted(quad_points, key=lambda p: (p.y, p.x))
    ul, ur, ll, lr = quad_points_sorted
    # Check the top and bottom lines and see if they're straight.
    if ul.y != ur.y or ll.y != lr.y:
        return None
    # Check the left and right lines and see if they're straight.
    if ul.x != ll.x or ur.x != lr.x:
        print(ul, ur, ll, lr)
        return None
    return quad.rect


def segment_plate_into_rectangles(plate, drawings, debug=False):
    """
    Takes the plate pdf and returns a list of each Rectangle in the plate.

    If debug is true, outputs a `segmented.png` with each box in the pdf highlighted
    and marked with its index.
    """
    # Create a list of lines throughout the page. Internally these are
    # pymupdf.Rect instances.
    lines = []

    for path in drawings:
        # Very thick lines are usually arrows, not seperators.
        if path["width"] is not None and (path["width"] > 2.0):
            continue

        # If it's a quad and they line up, treat it like a rectangle.
        for item in path["items"]:
            if item[0] == "qu":
                as_rect = make_rectangle_from_quad(item[1])
                if as_rect is not None:
                    item = ("re", as_rect)

            if item[0] == "l":  # line
                if abs(item[1].x - item[2].x) < 2:
                    lines.append(line_segment_as_rect_from_points(item[1], item[2]))
                elif abs(item[1].y - item[2].y) < 2:
                    lines.append(line_segment_as_rect_from_points(item[1], item[2]))
            elif item[0] == "re":  # rectangle
                # Rectangles have two vertical and two horizontal lines.
                lines.append(
                    line_segment_as_rect_from_points(
                        item[1].top_left, item[1].bottom_left
                    )
                )
                lines.append(
                    line_segment_as_rect_from_points(
                        item[1].top_right, item[1].bottom_right
                    )
                )
                lines.append(
                    line_segment_as_rect_from_points(
                        item[1].top_left, item[1].top_right
                    )
                )
                lines.append(
                    line_segment_as_rect_from_points(
                        item[1].bottom_left, item[1].bottom_right
                    )
                )
            else:
                continue

    # Filter out short lines.
    lines = [line for line in lines if line.width > 6 or line.height > 6]

    # Create an image with just the horizontal and vertical lines so we can
    # segment out the rectangles.
    segmented = pymupdf.Document()
    outpage = segmented.new_page(width=plate.rect.width, height=plate.rect.height)
    shape = outpage.new_shape()
    for line in lines:
        rounded_tl = round(line.top_left.x, 0), round(line.top_left.y, 0)
        rounded_br = round(line.bottom_right.x, 0), round(line.bottom_right.y, 0)
        shape.draw_line(rounded_tl, rounded_br)
        shape.finish(color=(0, 0, 0))  # line color
    shape.commit()

    # Get pixmap in grayscale.
    pixmap = outpage.get_pixmap(colorspace=pymupdf.csGRAY)
    samples = pixmap.samples_mv
    # Threshold the image and then have scikit make labels.
    img = np.asarray(samples).reshape((pixmap.h, pixmap.w))
    if debug:
        skimage.io.imsave("lines.png", img)
    img_grayscale = img.copy()
    img_grayscale[img_grayscale < 10] = 0

    # Use scikit image to label different parts of the image.
    label_image = skimage.measure.label(img_grayscale, connectivity=1)

    segments = []
    for region in skimage.measure.regionprops(label_image):
        # Skip any small regions.
        if region.area < 30:
            continue

        (y0, x0, y1, x1) = region.bbox
        # Avoid the region that covers the whole page.
        if x0 == 0 and y0 == 0:
            continue
        rectangle = pymupdf.Rect((x0, y0, x1, y1))
        # Skip anything too narrow.
        if rectangle.height < 5 or rectangle.width < 5:
            continue
        segments.append(rectangle)

    # Visually dump the segmented areas in debug mode.
    if debug:
        import random

        shape = outpage.new_shape()
        # Draw all segmented boxes.
        for rect in segments:
            shape.draw_rect(rect)
            shape.finish(
                color=(1, 0, 0),
                fill=(random.random(), random.random(), random.random()),
            )
        shape.commit()
        # Label the center of all the rectangles.
        for i, rect in enumerate(segments):
            outpage.insert_text(
                rect.top_left + pymupdf.Point(rect.width / 2.0, rect.height / 2.0),
                str(i),
            )
        outpage.get_pixmap(dpi=400).save("segmented.png")

    return segments
