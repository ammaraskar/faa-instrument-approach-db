from plate_analyzer import extract_information_from_plate
from plate_analyzer.scrape_faa_dtpp_zip import scan_dtpp_file


#extract_information_from_plate("../../Downloads/05538VDA.PDF", debug=True)
#extract_information_from_plate("test_data/00983ILD27.PDF", debug=True)

scan_dtpp_file("../../Downloads/DDTPPC_240711.zip")
