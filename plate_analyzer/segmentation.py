import pymupdf

import collections
import random


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


LINE_CLOSE_EPSILON = 0.5

def merge_close_lines(lines, vertical: bool):
    # Merge any vertical/horizontal lines that have similar points but are two
    # separate entries. e.g:
    #    l1      l2                            l3
    # |------|-------|     turns into   |--------------|
    merged_lines = []

    # Store lines with a particular x/y coordinate depending on the mode.
    line_buckets = collections.defaultdict(list)
    for line in lines:
        if vertical:
            line_buckets[line.top_left.x].append(line)
        else:
            line_buckets[line.top_left.y].append(line)

    # Sort vertical lines by y-coordinates and horizontal by x.
    for lines in line_buckets.values():
        if vertical:
            lines.sort(key=lambda line: line.top_left.y)
        else:
            lines.sort(key=lambda line: line.top_left.x)
    # Iterate over each bucket, merge any lines with similar end/start points.
    for lines in line_buckets.values():
        i = 0
        while i < len(lines) - 1:
            if vertical and lines[i].bottom_right.y >= (lines[i + 1].top_left.y - LINE_CLOSE_EPSILON):
                lines[i].include_point(lines.pop(i + 1).bottom_right)
            elif (not vertical) and lines[i].bottom_right.x >= (lines[i + 1].top_left.x - LINE_CLOSE_EPSILON):
                lines[i].include_point(lines.pop(i + 1).bottom_right)
            else:
                i += 1
        merged_lines.extend(lines)

    return merged_lines

def segment_plate_into_boxes(plate, drawings, debug=False):
    """
    Takes the plate pdf and returns a list of each Rectangle in the plate.

    If debug is true, outputs a `segmented.png` with each box in the pdf highlighted
    and marked with its index.
    """
    # Create a list of lines throughout the page. Internally these are
    # pymupdf.Rect instances. 
    vertical_lines = []
    horizontal_lines = []

    for path in drawings:
        # Very thick lines are usually arrows, not seperators.
        if path["width"] is not None and (path["width"] > 2.0):
            continue
        # The lines and rectangles only have one draw call.
        if len(path["items"]) != 1:
            continue
        item = path["items"][0]

        # If it's a quad with 4 points and they line up, treat it like a rectangle.
        if item[0] == "qu" and item[1].is_rectangular:
            item = ("re", pymupdf.Rect(item[1].ul, item[1].lr))

        if item[0] == "l":  # line
            if item[1].x == item[2].x:
                vertical_lines.append(line_segment_as_rect_from_points(item[1], item[2]))
            elif item[1].y == item[2].y:
                horizontal_lines.append(line_segment_as_rect_from_points(item[1], item[2]))
        elif item[0] == "re":  # rectangle
            # Rectangles have two vertical and two horizontal lines.
            vertical_lines.append(line_segment_as_rect_from_points(item[1].top_left, item[1].bottom_left))
            vertical_lines.append(line_segment_as_rect_from_points(item[1].top_right, item[1].bottom_right))
            horizontal_lines.append(line_segment_as_rect_from_points(item[1].top_left, item[1].top_right))
            horizontal_lines.append(line_segment_as_rect_from_points(item[1].bottom_left, item[1].bottom_right))
        else:
            continue

    horizontal_lines = merge_close_lines(horizontal_lines, vertical=False)
    vertical_lines = merge_close_lines(vertical_lines, vertical=True)

    # Find all intersections between the horizontal and vertical lines.
    intersections = []
    intersection_indexes = {}
    # Stores the set of all intersections on a line.
    all_intersections_on_line = collections.defaultdict(set)

    for horizontal_line in horizontal_lines:
        for vertical_line in vertical_lines:
            # Check if the lines overlap, the y of the horizontal line should be
            # between the y-range of the vertical line and the x of the vertical
            # line should be between the x-range of the horizontal line.
            horizontal_y = horizontal_line.top_left.y
            vertical_x = vertical_line.top_left.x

            if horizontal_y == 538:
                print("horizontal", horizontal_line)
                print("vertical", vertical_line)

            # Adjusted by 0.1 here to avoid near-misses on intersections.
            if (horizontal_y + 0.1) < vertical_line.top_left.y or (horizontal_y - 0.1) > vertical_line.bottom_right.y:
                continue
            if (vertical_x + 0.1) < horizontal_line.top_left.x or (vertical_x - 0.1) > horizontal_line.bottom_right.x:
                continue
            # If these are true then they overlap at horizontal-y and vertical-x
            intersection = (vertical_x, horizontal_y)

            # First see if we have this intersection already defined in the
            # intersections list. If not, add it along with a mapping to its idx
            # and the lines the intersection is found on.
            if intersection in intersection_indexes:
                intersection_idx = intersection_indexes[intersection]
                _, lines = intersections[intersection_idx]
            else:
                intersection_idx = len(intersections)
                lines = []
                intersections.append((intersection, lines))
                intersection_indexes[intersection] = intersection_idx

            all_intersections_on_line[horizontal_line].add(intersection)
            all_intersections_on_line[vertical_line].add(intersection)
            lines.extend([horizontal_line, vertical_line])

    lines = horizontal_lines + vertical_lines

    # We start the segmentation by building a table of each intersection and
    # which intersection it connects to. For example:
    #   0 -> 2, 1
    #   1 -> 0, 2
    intersection_graph = []

    for i, (intersection, lines) in enumerate(intersections):
        connected_intersections = set()
        # Find all the intersections on all the lines this intersection connects
        # to and add those as neighbors.
        for line in lines:
            for neighbor in all_intersections_on_line[line]:
                connected_intersections.add(intersection_indexes[neighbor])
        # Make sure we don't have a connection to ourselves :)
        connected_intersections.remove(i)
        intersection_graph.append(list(connected_intersections))

    for i, neighbors in enumerate(intersection_graph):
        print(i, sorted(neighbors))

    rectangles = find_all_rectangles_from_intersection_graph(intersection_graph, intersections)

    # Visually dump the segmented areas in debug mode.
    if debug:
        segmented = pymupdf.Document()
        outpage = segmented.new_page(width=plate.rect.width, height=plate.rect.height)

        shape = outpage.new_shape()

        for line in (horizontal_lines + vertical_lines):
            shape.draw_line(line.top_left, line.bottom_right)
            shape.finish(
                color=(random.random(), random.random(), random.random()),  # line color
            )

        for i, rect in enumerate(rectangles):
            shape.draw_rect(rect)
            shape.finish(
                color=(0.2, 0.2, 0.2),
                fill=(0.5, 0.5, 0.5),
            )
            outpage.insert_text(rect.top_left + pymupdf.Point(rect.width / 2.0, rect.height / 2.0), str(i))

        for i, inter in enumerate(intersections):
            shape.draw_circle(inter[0], radius=1)
            shape.finish(
                color=(1,0,0)
            )
            outpage.insert_text(inter[0], str(i))

        shape.commit()

        outpage.get_pixmap(dpi=800).save("segmented.png")

def find_all_rectangles_from_intersection_graph(intersection_graph, intersections):
    """Takes an intersection graph built from horizontal and vertical lines and
    finds all rectangles from it by finding 4-length cycles."""
    rectangles = set()
    used_top_left_corners = set()
    rectangle_objects = []

    for i in range(len(intersection_graph)):
        candidate_rectangles = find_rectangles_from_intersections(
            starting_intersection=i, current_intersection=i,
            intersection_graph=intersection_graph, path=[i])

        # Sort the edge nodes for deduplication, since order doesn't matter.
        smallest_rectangle, smallest_rect_nodes = None, None
        for rectangle in candidate_rectangles:
            # Always pick the smallest rectangle from any given starting point, as a
            # heuristic to avoid selecting large rectangles that encompass other
            # rectangles.
            intersection_points = [intersections[i][0] for i in rectangle]
            intersection_points.sort()
            rect_object = pymupdf.Rect(intersection_points[0], intersection_points[-1])

            # Avoid reusing a top left corner of a previous rectangle.
            if rect_object.top_left in used_top_left_corners:
                continue
            # Avoid any previously selected rectangles.
            if tuple(sorted(rectangle)) in rectangles:
                continue
            # Avoid selecting a "rectangle" that is basically just a path of
            # straight lines.
            if rect_object.get_area() < 1:
                continue

            if smallest_rectangle is None or smallest_rectangle.get_area() > rect_object.get_area():
                smallest_rectangle, smallest_rect_nodes = rect_object, rectangle

        if smallest_rectangle is None:
            continue

        # If we overlap an existing rectangle, avoid.
        overlaps = False
        for previous_rect in rectangle_objects:
            if previous_rect.intersects(smallest_rectangle):
                overlaps = True
        if overlaps:
            continue

        rectangle = tuple(sorted(smallest_rect_nodes))
        rectangles.add(rectangle)
        rectangle_objects.append(smallest_rectangle)
        used_top_left_corners.add(smallest_rectangle.top_left)

    return rectangle_objects

def find_rectangles_from_intersections(starting_intersection, current_intersection, intersection_graph, path, num_edges=0):
    """Takes an intersection, and follows all intersections out from it until it
    creates a cycle back to the original with at-most 4 edges to find a rectangle.
    """
    if num_edges > 3:
        return []

    paths = []

    for intersection in intersection_graph[current_intersection]:
        if intersection == starting_intersection and num_edges == 3:
            return [path]
        # Ignore any intersections already in the path.
        if intersection in path:
            continue

        paths.extend(
            find_rectangles_from_intersections(starting_intersection, intersection, intersection_graph, path + [intersection], num_edges + 1)
        )
    return paths
