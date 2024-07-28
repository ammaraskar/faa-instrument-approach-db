from plate_analyzer import extract_information_from_plate
from plate_analyzer.scrape_faa_dtpp_zip import scan_dtpp_file, verify_contents_of_zip_against_metadata


# extract_information_from_plate("../../Downloads/03214R5.PDF", debug=True)
# extract_information_from_plate("test_data/05222VT15.PDF", debug=True)

scan_dtpp_file("../../Downloads/faa_dttp/DDTPPC_240711.zip")
#verify_contents_of_zip_against_metadata("../../Downloads/faa_dttp/")
