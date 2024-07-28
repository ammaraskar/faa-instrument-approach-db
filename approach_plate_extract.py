from plate_analyzer import extract_information_from_plate
from plate_analyzer import scrape_faa_dtpp_zip


# extract_information_from_plate("../../Downloads/06065R8.PDF", debug=True)
# extract_information_from_plate("test_data/05222VT15.PDF", debug=True)

results = scrape_faa_dtpp_zip.analyze_dtpp_zips("../../Downloads/faa_dttp/")
with open("output.json", "w") as f:
    f.write(results.model_dump_json(indent=2))
