"""
Deals with scanning drawings and graphics on the profile/plan view to find extra
bits of information.
"""
import pymupdf


def extract_approach_metadata(plan_view_box, plate, drawings, debug=False):
    outpdf = pymupdf.open()
    outpage = outpdf.new_page(width=plate.rect.width, height=plate.rect.height)
    shape = outpage.new_shape()

    # Look for DME Arcs.
    for path in drawings:
        # Ignore stuff outside of plan view.
        if not plan_view_box.contains(path["rect"]):
            continue

        for item in path["items"]:
            if item[0] == "c":
                shape.draw_bezier(item[1], item[2], item[3], item[4])

        shape.finish(
            color=path["color"],
            closePath=path["closePath"]
        )

    shape.commit()
    outpage.get_pixmap(dpi=400).save("drawings.png")

def has_dme_arc(drawings, plan_view_box):
    pass
