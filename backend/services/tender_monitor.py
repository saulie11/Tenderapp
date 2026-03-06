import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from bs4 import BeautifulSoup


def _parse_rss_date(date_str: str):
    """Parse RSS/Atom date strings."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def fetch_rss_tenders(url: str, keywords: list = None) -> list:
    """Fetch tenders from an RSS feed using stdlib XML parser."""
    tenders = []
    try:
        headers = {"User-Agent": "TenderBot/1.0 (tender tracking application)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        # Detect RSS vs Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        feed_title = ""

        # RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            feed_title = (channel.findtext("title") or "").strip()
            for item in channel.findall("item"):
                title = (item.findtext("title") or "").strip()
                description = (item.findtext("description") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date = _parse_rss_date(item.findtext("pubDate") or "")
                if keywords:
                    text = (title + " " + description).lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue
                tenders.append({
                    "title": title,
                    "description": BeautifulSoup(description, "html.parser").get_text()[:500],
                    "source_url": link,
                    "published_date": pub_date,
                    "source_name": feed_title or url,
                })
        else:
            # Atom feed
            feed_title_el = root.find("atom:title", ns)
            feed_title = feed_title_el.text.strip() if feed_title_el is not None else ""
            for entry in root.findall("atom:entry", ns):
                title_el = entry.find("atom:title", ns)
                title = title_el.text.strip() if title_el is not None else ""
                summary_el = entry.find("atom:summary", ns) or entry.find("atom:content", ns)
                description = summary_el.text.strip() if summary_el is not None else ""
                link_el = entry.find("atom:link", ns)
                link = link_el.get("href", "") if link_el is not None else ""
                date_el = entry.find("atom:published", ns) or entry.find("atom:updated", ns)
                pub_date = _parse_rss_date(date_el.text if date_el is not None else "")
                if keywords:
                    text = (title + " " + description).lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue
                tenders.append({
                    "title": title,
                    "description": BeautifulSoup(description, "html.parser").get_text()[:500],
                    "source_url": link,
                    "published_date": pub_date,
                    "source_name": feed_title or url,
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
