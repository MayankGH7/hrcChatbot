import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import mimetypes
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="college_website")

# Function to extract main content from HTML
def extract_text(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception:
        soup = BeautifulSoup(html, 'lxml')  # Fallback parser

    for script in soup(['script', 'style', 'header', 'footer', 'nav']):
        script.decompose()  # Remove unwanted tags

    return soup.get_text(separator=' ', strip=True)

# Recursive scraper
def scrape_website(base_url, max_depth=5):
    visited = set()
    results = []

    # File extensions to skip
    excluded_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}

    def crawl(url, depth):
        if depth > max_depth or url in visited:
            return

        # Check for excluded file extensions
        if any(url.lower().endswith(ext) for ext in excluded_extensions):
            print(f"Skipping excluded file: {url}")
            return

        if (url == "https://www.hansrajcollege.ac.in/#!" or url == "https://www.hansrajcollege.ac.in/?logout=true"):
            return

        print(f"Scraping: {url}")
        visited.add(url)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error: {e}")
            return

        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith("text/html"):
            print(f"Skipping non-HTML content: {url}")
            return

        html_content = response.text
        text_content = extract_text(html_content)

        # Store URL and content
        results.append({"url": url, "text": text_content})

        # Parse and find new links
        soup = BeautifulSoup(html_content, 'html.parser')
        for link in soup.find_all('a', href=True):
            next_url = urljoin(base_url, link['href'])
            if is_internal_link(base_url, next_url) and next_url not in visited:
                crawl(next_url, depth + 1)

        # time.sleep(1)  # Respectful crawling

    def is_internal_link(base, link):
        return urlparse(link).netloc == urlparse(base).netloc and link.startswith(base)

    crawl(base_url, 0)
    return results

# Store data in ChromaDB
def store_in_chroma(scraped_data):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    for i, page in enumerate(scraped_data):
        chunks = splitter.split_text(page['text'])
        for j, chunk in enumerate(chunks):
            collection.add(
                documents=[chunk],
                metadatas={"source": page['url']},
                ids=[f"doc_{i}_{j}"]
            )

# Usage
base_url = "https://www.hansrajcollege.ac.in/"
scraped_data = scrape_website(base_url, max_depth=2)

print(f"Total pages scraped: {len(scraped_data)}")

store_in_chroma(scraped_data)
print("Data stored in ChromaDB.")

# Example output
for page in scraped_data[:3]:
    print("URL:", page['url'])
    print("Text Snippet:", page['text'][:300], '\n')
