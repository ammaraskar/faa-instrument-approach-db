from plate_analyzer import segmentation

import pymupdf


def extract_information_from_plate(plate_path, debug=False):
    pdf = pymupdf.open(plate_path)
    plate = pdf[0]

    drawings = plate.get_drawings()
    segmentation.segment_plate_into_boxes(plate, drawings, debug=debug)
    return

    drawing_clusters = plate.cluster_drawings(drawings=drawings)

    print(drawing_clusters)

    for cluster in drawing_clusters:
        plate.draw_rect(cluster, color=(1,0,0))

    # Get all the text on the page so we can exclude any paths corresponding
    # to fonts.
    text_bboxes = []
    raw_text_blocks = plate.get_text(option="rawdict")["blocks"]
    for block in raw_text_blocks:
        # Type 0 = text
        if block["type"] != 0:
            continue

        for line in block["lines"]:
            for span in line["spans"]:
                for char in span["chars"]:
                    # Draw the bbox
                    text_bboxes.append(char["bbox"])
                    #outpage.draw_rect(char["bbox"], color=(0,1,0))

    outpage = pdf.new_page(width=plate.rect.width, height=plate.rect.height)

    # Draw just the lines that split up the plate.
    shape = outpage.new_shape()
    for i, path in enumerate(drawings):
        # Very thick lines are usually arrows, not seperators.
        if path["width"] is not None and (path["width"] > 1.0):
            continue

        # The lines and rectangles only have one draw-call.
        if len(path["items"]) != 1:
            continue
        item = path["items"][0]

        if item[0] == "l":  # line
            # Check if it's a straight line.
            if item[1][0] != item[2][0] and item[1][1] != item[2][1]:
                continue
            shape.draw_line(item[1], item[2])
        elif item[0] == "re":  # rectangle
            shape.draw_rect(item[1])
        elif item[0] == "qu":  # quad
            shape.draw_quad(item[1])
        else:
            continue

        #outpage.insert_text(shape.rect.tl, str(i))

        shape.finish(
            fill=path["fill"],  # fill color
            color=path["color"],  # line color
        )
    shape.commit()

    """
    for i, path in enumerate(drawings):
        shape = outpage.new_shape()

        if i == 1530:
            print(path)

        if i not in [1560, 1530, 1532]:
            continue

        # if the bbox is close to that of a text character, do not draw
        # the shape!
        rect = path["rect"]
        is_text = False
        for text_bbox in text_bboxes:
            if bbox_close(text_bbox, rect):
                is_text = True
        if is_text:
            continue

        for item in path["items"]:
            if item[0] == "l":  # line
                shape.draw_line(item[1], item[2])
            elif item[0] == "re":  # rectangle
                shape.draw_rect(item[1])
            elif item[0] == "qu":  # quad
                shape.draw_quad(item[1])
            elif item[0] == "c":  # curve
                shape.draw_bezier(item[1], item[2], item[3], item[4])
            else:
                raise ValueError("unhandled drawing", item)

        if i % 3 == 0:    
            color = (1, 0, 0)
        elif i % 3 == 1:
            color = (0, 1, 0)
        else:
            color = (0, 0, 1)


        # ------------------------------------------------------
        # all items are drawn, now apply the common properties
        # to finish the path
        # ------------------------------------------------------
        stroke_opacity = path.get("stroke_opacity", 1)
        fill_opacity = path.get("fill_opacity", 1)
        #outpage.draw_rect(shape.rect, color=(0,0,1))
        shape.finish(
            fill=path["fill"],  # fill color
            color=path["color"],  # line color
        )

        # Write which shape number this is.
        outpage.insert_text(shape.rect.tl, str(i), color=color)
        
        shape.commit()
    """


    outpage.get_pixmap(dpi=800).save("copied-shapes.png")

    """
    table_finder = plate.find_tables()
    for table in table_finder.tables:
        print(table)
        plate.draw_rect(table.bbox, color=(0,1,0))

    pix = plate.get_pixmap()
    pix.save("page.png")
    """

def bbox_close(bbox1, bbox2):
    return abs(bbox2.x0 - bbox1[0]) < 4 and \
           abs(bbox2.y0 - bbox1[1]) < 4 and \
           abs(bbox2.x1 - bbox1[2]) < 4 and \
           abs(bbox2.y1 - bbox1[3]) < 4


extract_information_from_plate('test_data/05035R7.PDF', debug=True)
