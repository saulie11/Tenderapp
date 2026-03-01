import feedparser
import requests
from datetime import datetime
from bs4 import BeautifulSoup


def fetch_rss_tenders(url: str, keywords: list = None) -> list:
    """Fetch tenders from an RSS feed."""
    tenders = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            description = entry.get("summary", entry.get("description", ""))
            link = entry.get("link", "")
            published = entry.get("published_parsed") or entry.get("updated_parsed")

            pub_date = None
            if published:
                try:
                    pub_date = datetime(*published[:6])
                except Exception:
                    pass

            if keywords:
                text_to_check = (title + " " + description).lower()
                if not any(kw.lower() in text_to_check for kw in keywords):
                    continue

            tenders.append({
                "title": title,
                "description": BeautifulSoup(description, "html.parser").get_text()[:500] if description else "",
                "source_url": link,
                "published_date": pub_date,
                "source_name": feed.feed.get("title", url),
            })
    except Exception as e:
        print(f"Error fetching RSS from {url}: {e}")

    return tenders


def fetch_website_tenders(url: str, keywords: list = None) -> list:
    """Attempt basic scraping of a tender website."""
    tenders = []
    try:
        headers = {"User-Agent": "TenderBot/1.0 (tender tracking application)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find tender listings - look for common patterns
        tender_links = []

        # Look for links containing tender keywords
        tender_keywords = ["tender", "rfp", "rfq", "bid", "procurement", "contract", "solicitation"]
        for link in soup.find_all("a", href=True):
            link_text = link.get_text().lower()
            href = link["href"].lower()
            if any(kw in link_text or kw in href for kw in tender_keywords):
                full_url = link["href"]
                if full_url.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    full_url = f"{parsed.scheme}://{parsed.netloc}{full_url}"
                tender_links.append({"title": link.get_text().strip(), "url": full_url})

        for item in tender_links[:20]:  # Limit to 20
            if keywords:
                if not any(kw.lower() in item["title"].lower() for kw in keywords):
                    continue
            tenders.append({
                "title": item["title"],
                "description": "",
                "source_url": item["url"],
                "published_date": None,
                "source_name": url,
            })

    except Exception as e:
        print(f"Error scraping website {url}: {e}")

    return tenders


def extract_text_from_html(html_content: str) -> str:
    """Extract clean text from HTML content."""
    soup = BeautifulSoup(html_content, "html.parser")
    for script in soup(["script", "style"]):
        script.decompose()
    return soup.get_text(separator="\n", strip=True)


def check_source_for_new_tenders(source, existing_urls: set) -> list:
    """Check a TenderSource for new tenders not already in the database."""
    keywords = [k.strip() for k in source.keywords.split(",")] if source.keywords else []

    if source.source_type == "rss":
        found = fetch_rss_tenders(source.url, keywords)
    elif source.source_type == "website":
        found = fetch_website_tenders(source.url, keywords)
    else:
        found = []

    new_tenders = [t for t in found if t.get("source_url") not in existing_urls]
    return new_tenders
