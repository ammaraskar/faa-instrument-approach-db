from plate_analyzer import extract_information_from_plate
from plate_analyzer import scrape_faa_dtpp_zip, cifp_analysis


if __name__ == "__main__":
    # extract_information_from_plate("../../Downloads/06065R8.PDF", debug=True)
    # extract_information_from_plate("test_data/05222VT15.PDF", debug=True)

    # cifp_analysis.analyze_cifp_file("../../Downloads/faa_dttp/FAACIFP18")

    results = scrape_faa_dtpp_zip.analyze_dtpp_zips("./", cifp_file="./FAACIFP18")
    with open("approaches.json", "w") as f:
        f.write(results.model_dump_json())
