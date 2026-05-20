#!/usr/bin/env python3
"""
PGM/Platinum Content Scraper — no Selenium required.

Replaces the old Selenium-based Substack scraper with a lightweight
requests + BeautifulSoup approach that pulls from multiple RSS feeds
and filters for PGM/platinum-relevant articles.

Sources:
  - Mining.com          (general mining RSS, filtered for PGM keywords)
  - Investing.com       (commodities RSS)
  - Stockhouse          (mining/metals RSS)
  - Business Wire       (press releases RSS, filtered for PGM)
  - PR Newswire metals  (metals press releases RSS)
"""

import logging
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

from database_operations import insert_substack_post, check_substack_url_exists
from database_config import get_curser

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PGM keyword filter
# ─────────────────────────────────────────────────────────────
PGM_KEYWORDS = [
    'platinum group', 'platinum mining', 'platinum price', 'platinum market',
    'platinum stocks', 'platinum investment', 'platinum etf', 'platinum demand',
    'platinum supply', 'platinum producer', 'platinum explorer', 'platinum output',
    'platinum ounce', 'platinum oz', 'platinum metal',
    'palladium', 'pgm', 'rhodium', 'iridium', 'ruthenium',
    'sibanye', 'stillwater', 'impala', 'implats',
    'amplats', 'anglo platinum', 'northam', 'valterra',
    'ivanhoe', 'platreef', 'bushveld', 'lifezone',
    'bravo mining', 'generation mining', 'clean air metals',
    'new age metals', 'chalice mining', 'zimplats',
    'southern palladium', 'autocatalyst', 'fuel cell platinum',
    'hydrogen fuel cell', 'pgm recycling', 'pgm demand',
    'pgm supply', 'pgm price', 'pgm market',
]

# ─────────────────────────────────────────────────────────────
# RSS feed sources (all confirmed working)
# ─────────────────────────────────────────────────────────────
RSS_SOURCES = [
    {
        "name": "Mining.com",
        "url": "https://www.mining.com/feed/",
        "limit": 15,
    },
    {
        "name": "Investing.com - Commodities",
        "url": "https://www.investing.com/rss/news_11.rss",
        "limit": 15,
    },
    {
        "name": "Stockhouse",
        "url": "https://stockhouse.com/rss/news",
        "limit": 15,
    },
    {
        "name": "Business Wire - Mining",
        "url": "https://feed.businesswire.com/rss/home/?rss=G22",
        "limit": 15,
    },
    {
        "name": "PR Newswire - Metals",
        "url": "https://www.prnewswire.com/rss/news-releases-list.rss",
        "limit": 15,
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _is_pgm_relevant(text: str) -> bool:
    """Return True if text contains at least one PGM keyword."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in PGM_KEYWORDS)


def _clean_xml(content: str) -> str:
    """Fix unescaped HTML entities that break stdlib XML parser."""
    return re.sub(
        r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)([a-zA-Z]+);',
        r'&amp;\1;',
        content,
    )


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode common entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = (text
            .replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return text.strip()


def _parse_date(date_str: str) -> str:
    """Parse RSS date string → YYYY-MM-DD. Returns today on failure."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str[:19], fmt[:19]).strftime("%Y-%m-%d")
        except Exception:
            continue
    return datetime.now().strftime("%Y-%m-%d")


def _get_text(element, *tags) -> str:
    """Try multiple tag names, return first non-empty text found."""
    for tag in tags:
        child = element.find(tag)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _extract_image(item) -> str:
    """Extract image URL from media:content, media:thumbnail, or enclosure."""
    for ns in [
        "{http://search.yahoo.com/mrss/}content",
        "{http://search.yahoo.com/mrss/}thumbnail",
    ]:
        el = item.find(ns)
        if el is not None:
            url = el.get("url", "")
            if url:
                return url
    enclosure = item.find("enclosure")
    if enclosure is not None and "image" in enclosure.get("type", ""):
        return enclosure.get("url", "")
    return ""


def _fetch_feed(url: str):
    """Fetch and parse an RSS feed. Returns list of <item> elements."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        cleaned = _clean_xml(response.text)
        root = ET.fromstring(cleaned.encode("utf-8"))
        items = root.findall(".//item")
        if not items:
            items = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        return items
    except requests.exceptions.RequestException as e:
        logger.warning(f"HTTP error fetching {url}: {e}")
    except ET.ParseError as e:
        logger.warning(f"XML parse error for {url}: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error fetching {url}: {e}")
    return []


# ─────────────────────────────────────────────────────────────
# Main scraper
# ─────────────────────────────────────────────────────────────

def scrape_substack_nickel_posts(cursor=None, max_posts: int = 10) -> list:
    """
    Scrapes PGM/platinum-related articles from multiple RSS feeds
    using requests + BeautifulSoup (no Selenium required).

    Parameters:
        cursor: psycopg2 cursor for duplicate-URL checking (optional)
        max_posts: maximum total posts to return

    Returns:
        list of dicts with keys: title, url, content, subtitle, image_url, date
    """
    all_posts = []
    seen_urls: set = set()

    for source in RSS_SOURCES:
        if len(all_posts) >= max_posts:
            break

        name = source["name"]
        url  = source["url"]
        limit = source["limit"]

        logger.info(f"Fetching feed: {name}")
        items = _fetch_feed(url)

        if not items:
            logger.warning(f"  No items from {name}")
            continue

        found = 0
        for item in items:
            if len(all_posts) >= max_posts:
                break

            # Extract fields
            title = _strip_html(
                _get_text(item, "title", "{http://www.w3.org/2005/Atom}title")
            )
            link = _get_text(item, "link")
            if not link:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    link = link_el.get("href", "")
            link = link.strip() if link else ""

            description = _strip_html(
                _get_text(
                    item,
                    "description",
                    "{http://www.w3.org/2005/Atom}summary",
                    "{http://purl.org/rss/1.0/modules/content/}encoded",
                )
            )

            pub_date = _get_text(
                item,
                "pubDate", "pubdate",
                "{http://www.w3.org/2005/Atom}published",
                "{http://www.w3.org/2005/Atom}updated",
            )
            date = _parse_date(pub_date)
            image_url = _extract_image(item)

            # Skip if missing essentials
            if not title or not link:
                continue

            # PGM relevance filter
            combined = f"{title} {description}"
            if not _is_pgm_relevant(combined):
                continue

            # Skip duplicates (in-memory)
            if link in seen_urls:
                continue

            # Skip if already in DB
            if cursor:
                try:
                    if check_substack_url_exists(cursor, link):
                        logger.debug(f"  Already in DB: {link}")
                        continue
                except Exception:
                    pass

            seen_urls.add(link)
            all_posts.append({
                "title":     title,
                "url":       link,
                "content":   description[:2000] if description else title,
                "subtitle":  f"via {name}",
                "image_url": image_url,
                "date":      date,
            })
            found += 1
            logger.info(f"  [{name}] {title[:70]}")

        logger.info(f"  → {found} PGM articles from {name}")

    logger.info(f"Total PGM articles scraped: {len(all_posts)}")
    return all_posts[:max_posts]


# ─────────────────────────────────────────────────────────────
# DB helpers (unchanged interface — called from app.py)
# ─────────────────────────────────────────────────────────────

def insert_substack_posts_to_db(cursor, connection, posts: list) -> None:
    """Insert scraped posts into the database, skipping duplicates."""
    successful = 0
    for post in posts:
        try:
            if not check_substack_url_exists(cursor, post["url"]):
                insert_substack_post(
                    cursor=cursor,
                    connection=connection,
                    **post,
                )
                successful += 1
                print(f"Inserted: {post['title'][:60]}...")
            else:
                print(f"Skipping duplicate: {post['title'][:60]}...")
        except Exception as e:
            print(f"Error inserting '{post['title'][:50]}': {e}")
            continue
    print(f"Inserted {successful} of {len(posts)} posts")


def ensure_table_exists(cursor, connection) -> None:
    """Ensure the api_app_coppersubstack table exists."""
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_app_coppersubstack (
                id         VARCHAR(255) PRIMARY KEY,
                title      TEXT NOT NULL,
                url        TEXT UNIQUE NOT NULL,
                content    TEXT,
                subtitle   TEXT,
                image_url  TEXT,
                date       DATE NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
        print("Table api_app_coppersubstack is ready")
    except Exception as e:
        print(f"Error ensuring table exists: {e}")
        raise


# ─────────────────────────────────────────────────────────────
# Standalone run
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    connection, cursor = get_curser()
    try:
        ensure_table_exists(cursor, connection)
        print("Starting PGM/platinum content scraping...")
        posts = scrape_substack_nickel_posts(cursor, max_posts=20)
        if posts:
            print(f"Found {len(posts)} posts. Inserting into database...")
            insert_substack_posts_to_db(cursor, connection, posts)
        else:
            print("No PGM posts found")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cursor.close()
        connection.close()
        print("Done")
