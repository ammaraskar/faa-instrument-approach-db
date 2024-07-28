from plate_analyzer import extract_information_from_plate
from plate_analyzer import scrape_faa_dtpp_zip


# extract_information_from_plate("../../Downloads/00380HIL10-ocr.pdf", debug=True)
# extract_information_from_plate("test_data/05222VT15.PDF", debug=True)

scrape_faa_dtpp_zip.analyze_dtpp_zips("../../Downloads/faa_dttp/")
# verify_contents_of_zip_against_metadata("../../Downloads/faa_dttp/")
