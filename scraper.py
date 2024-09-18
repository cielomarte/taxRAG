import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import PyPDF2
import time

# Directory to store downloaded PDFs
PDF_DIR = 'pdfs'
if not os.path.exists(PDF_DIR):
    os.makedirs(PDF_DIR)

# Set the headers with a User-Agent string
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# Function to check if the link is part of the base domain
def is_internal_link(url, base_url):
    return urlparse(url).netloc == urlparse(base_url).netloc

# Function to clean up URL fragments
def clean_url(url):
    parsed_url = urlparse(url)
    return parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

# Function to scrape all internal and PDF links
def get_internal_links(base_url, visited_urls=None):
    if visited_urls is None:
        visited_urls = set()

    print(f"Scraping URL: {base_url}")
    try:
        response = requests.get(base_url, headers=headers, timeout=30)  # Set a timeout of 30 seconds
        if response.status_code != 200:
            print(f"Failed to retrieve {base_url}, status code: {response.status_code}")
            return set()
    except Exception as e:
        print(f"Error during request to {base_url}: {e}")
        return set()

    soup = BeautifulSoup(response.content, "html.parser")
    links = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag['href']
        full_url = urljoin(base_url, href)
        clean_full_url = clean_url(full_url)

        if clean_full_url not in visited_urls and is_internal_link(full_url, base_url):
            visited_urls.add(clean_full_url)
            print(f"Discovered link: {clean_full_url}")

            if href.endswith(".pdf"):
                links.add(clean_full_url)
            elif base_url in full_url:
                # Recursively scrape the new page
                print(f"Recursively scraping: {clean_full_url}")
                links.update(get_internal_links(clean_full_url, visited_urls))

    return links

# Function to download and extract text from PDF files with retry logic
def download_and_extract_pdf(url, save_dir, retries=3):
    for i in range(retries):  # Retry up to 3 times
        try:
            response = requests.get(url, headers=headers, timeout=30)  # Set a 30-second timeout
            if response.status_code == 200:
                break
            else:
                print(f"Attempt {i+1} failed with status code: {response.status_code}")
                time.sleep(2)  # Delay before retry
        except Exception as e:
            print(f"Attempt {i+1} error during downloading PDF {url}: {e}")
            time.sleep(2)  # Delay before retry
    else:
        print(f"Failed to download PDF {url} after {retries} attempts.")
        return ""

    pdf_path = os.path.join(save_dir, url.split("/")[-1])
    try:
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(response.content)
        print(f"Downloaded PDF: {pdf_path}")
    except Exception as e:
        print(f"Error saving PDF {pdf_path}: {e}")
        return ""

    # Extract text from the downloaded PDF
    return extract_text_from_pdf(pdf_path)

# Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        print(f"Extracted text from PDF: {pdf_path}")
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

# Main scraping function with incremental data saving
def scrape_website(base_url):
    all_data = []
    links = get_internal_links(base_url)

    for link in links:
        if link.endswith('.pdf'):
            print(f"Downloading and extracting PDF: {link}")
            pdf_text = download_and_extract_pdf(link, PDF_DIR)
            if pdf_text:
                entry = {"url": link, "content": pdf_text}
                all_data.append(entry)
                # Save incrementally to avoid losing data
                save_data_incrementally(entry)
        else:
            print(f"Scraping HTML page: {link}")
            try:
                response = requests.get(link, headers=headers, timeout=30)
                if response.status_code != 200:
                    print(f"Failed to retrieve {link}, status code: {response.status_code}")
                    continue
            except Exception as e:
                print(f"Error during request to {link}: {e}")
                continue
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text().strip()
            if text:
                print(f"Extracted text from {link}")
                entry = {"url": link, "content": text}
                all_data.append(entry)
                # Save incrementally to avoid losing data
                save_data_incrementally(entry)
            else:
                print(f"No text found on {link}")

        time.sleep(5)  # Be courteous and avoid overwhelming the server with requests

    return all_data

# Function to save data incrementally
def save_data_incrementally(entry):
    with open('cdtfa_data.txt', 'a', encoding='utf-8') as f:
        f.write(f"URL: {entry['url']}\nContent:\n{entry['content']}\n\n")
        print(f"Data saved for {entry['url']}")

if __name__ == "__main__":
    base_url = "https://www.cdtfa.ca.gov/"  # Replace with the correct base URL
    print("Starting the scraping process...")
    scrape_website(base_url)
    print("Scraping process completed.")
