import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime


# Function to download the latest zip file from a fixed URL
def download_latest_zip():
    url = "https://aeronav.faa.gov/Upload_313-d/cifp/"

    try:
        print(f"Fetching page: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print("Page retrieved successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to retrieve page: {e}")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    print("Parsing HTML content...")

    # Extract all .zip links
    zip_links = [
        urljoin(url, link["href"])
        for link in soup.find_all("a", href=True)
        if link["href"].endswith(".zip")
    ]

    if not zip_links:
        print("No ZIP files found on the page.")
        return

    # Assuming the last file in the list is the latest one
    latest_zip_link = zip_links[-1]  # Choose the last link in the list

    print(f"Latest ZIP file found: {latest_zip_link}")

    # Download the latest zip file
    download_folder = "./"
    filename = os.path.join(download_folder, os.path.basename(latest_zip_link))
    os.makedirs(download_folder, exist_ok=True)

    try:
        print(f"Downloading {latest_zip_link}...")
        zip_response = requests.get(latest_zip_link, stream=True, timeout=10)
        zip_response.raise_for_status()
        with open(filename, "wb") as file:
            for chunk in zip_response.iter_content(chunk_size=1024):
                file.write(chunk)
        print(f"Downloaded: {filename}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {latest_zip_link}: {e}")


# Function to get the timestamp of a file using the 'Last-Modified' header
def get_file_timestamp(url):
    try:
        # Send a HEAD request to get the headers of the file
        response = requests.head(url)
        if response.status_code == 200 and "Last-Modified" in response.headers:
            # Return the timestamp from the 'Last-Modified' header
            return datetime.strptime(
                response.headers["Last-Modified"], "%a, %d %b %Y %H:%M:%S %Z"
            )
        else:
            return None
    except requests.RequestException:
        return None


# Function to download the latest 'num_files' zip files from any given URL
def download_latest_zip_files(url, num_files=5):
    # Send a request to the URL
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return

    # Parse the page content
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all links to zip files on the page
    zip_links = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.endswith(".zip"):
            zip_links.append(urljoin(url, href))  # Ensure we get the full URL

    if not zip_links:
        print("No zip files found on the page.")
        return

    # Get the timestamp for each zip file and store them in a list
    zip_files_with_timestamps = []
    for zip_url in zip_links:
        timestamp = get_file_timestamp(zip_url)
        if timestamp:
            zip_files_with_timestamps.append((zip_url, timestamp))

    # Sort the zip files by the timestamp (latest first)
    zip_files_with_timestamps.sort(key=lambda x: x[1], reverse=True)

    # Select the 5 most recent zip files
    latest_zip_files = zip_files_with_timestamps[:num_files]

    # Create a directory to store the downloaded files
    download_folder = "./"
    os.makedirs(download_folder, exist_ok=True)

    # Download each of the latest zip files
    for zip_url, timestamp in latest_zip_files:
        print(f"Downloading: {zip_url}")
        zip_name = os.path.join(download_folder, os.path.basename(zip_url))

        try:
            zip_response = requests.get(zip_url)
            zip_response.raise_for_status()  # Will raise an exception for bad responses
            with open(zip_name, "wb") as f:
                f.write(zip_response.content)
            print(f"Downloaded {zip_name}")
        except requests.RequestException as e:
            print(f"Failed to download {zip_url}: {e}")


if __name__ == "__main__":
    # First run Script 1 to download the latest file from the fixed URL
    download_latest_zip()

    # Then run Script 2 to download the latest zip files sorted by timestamp from the URL
    url = "https://aeronav.faa.gov/upload_313-d/terminal/"  # Hardcoded URL for Script 2
    download_latest_zip_files(url, num_files=5)
