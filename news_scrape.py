#!/usr/bin/env python3
"""
Gold & Silver News Scraper - RSS Feed Based
Sources (all confirmed working):
  - Mining.com          (general mining, gold & silver)
  - Silver Institute    (silver market research & news)
  - Seeking Alpha Gold  (gold investment analysis)
  - Investing.com Gold  (gold market news)
  - Numismatic News     (precious metals & coins)

No Selenium, no API keys required. Pure RSS/requests.
"""

import logging
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from insert_queries import check_url_exists

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# RSS FEED DEFINITIONS  (confirmed working)
# ─────────────────────────────────────────────

RSS_FEEDS = [
    {
        "source": "Mining.com",
        "url": "https://www.mining.com/feed/",
        "limit": 10,
    },
    {
        "source": "Silver Institute",
        "url": "https://www.silverinstitute.org/feed/",
        "limit": 8,
    },
    {
        "source": "Seeking Alpha - Gold",
        "url": "https://seekingalpha.com/tag/gold.xml",
        "limit": 8,
    },
    {
        "source": "Investing.com - Commodities",
        "url": "https://www.investing.com/rss/news_11.rss",
        "limit": 8,
    },
    {
        "source": "Numismatic News",
        "url": "https://www.numismaticnews.net/feed",
        "limit": 6,
    },
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _clean_xml(content):
    """Fix unescaped HTML entities that break stdlib XML parser."""
    return re.sub(
        r'&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)([a-zA-Z]+);',
        r'&amp;\1;',
        content
    )


def _parse_date(date_str):
    """Parse RSS date string to YYYY-MM-DD. Returns today on failure."""
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


def _get_text(element, *tags):
    """Try multiple tag names and return first non-empty text found."""
    for tag in tags:
        child = element.find(tag)
        if child is not None and child.text and child.text.strip():
            return child.text.strip()
    return None


def _extract_image(item):
    """Extract image URL from media:content, media:thumbnail, or enclosure."""
    for ns in [
        "{http://search.yahoo.com/mrss/}content",
        "{http://search.yahoo.com/mrss/}thumbnail",
    ]:
        el = item.find(ns)
        if el is not None:
            url = el.get("url")
            if url:
                return url

    enclosure = item.find("enclosure")
    if enclosure is not None and "image" in enclosure.get("type", ""):
        return enclosure.get("url")

    return None


def _strip_html(text):
    """Remove HTML tags and decode common entities."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
    return text.strip()


def _fetch_rss(url):
    """Fetch and parse an RSS/Atom feed. Returns list of item elements."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
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


# ─────────────────────────────────────────────
# MAIN SCRAPER
# ─────────────────────────────────────────────

def scrape_rss_feeds(cursor):
    """
    Scrape all configured RSS feeds.
    Returns list of article dicts:
      source, title, url, content, summary, image_url, date
    """
    all_articles = []

    for feed in RSS_FEEDS:
        source  = feed["source"]
        feed_url = feed["url"]
        limit   = feed["limit"]

        logger.info(f"Fetching RSS: {source}")
        items = _fetch_rss(feed_url)

        if not items:
            logger.warning(f"  No items returned for {source}")
            continue

        count = 0
        for item in items:
            if count >= limit:
                break

            # ── URL ──────────────────────────────────────
            url = _get_text(item, "link")
            if not url:
                link_el = item.find("{http://www.w3.org/2005/Atom}link")
                if link_el is not None:
                    url = link_el.get("href")
            if not url:
                continue
            url = url.strip()

            # Skip duplicates
            if check_url_exists(cursor, url):
                logger.debug(f"  Already exists: {url}")
                continue

            # ── Title ────────────────────────────────────
            title = (
                _get_text(item, "title", "{http://www.w3.org/2005/Atom}title")
                or "No title"
            )
            title = _strip_html(title)

            # ── Description / Content ────────────────────
            raw_desc = (
                _get_text(item,
                    "description",
                    "{http://www.w3.org/2005/Atom}summary",
                    "{http://www.w3.org/2005/Atom}content",
                    "{http://purl.org/rss/1.0/modules/content/}encoded",
                )
                or ""
            )
            clean_content = _strip_html(raw_desc)

            # ── Date ─────────────────────────────────────
            pub_date = (
                _get_text(item,
                    "pubDate", "pubdate",
                    "{http://www.w3.org/2005/Atom}published",
                    "{http://www.w3.org/2005/Atom}updated",
                )
            )
            formatted_date = _parse_date(pub_date)

            # ── Image ────────────────────────────────────
            image_url = _extract_image(item)

            all_articles.append({
                "source":    source,
                "title":     title,
                "url":       url,
                "content":   clean_content,
                "summary":   clean_content[:500] if clean_content else None,
                "image_url": image_url,
                "date":      formatted_date,
            })
            count += 1
            logger.info(f"  [{source}] {title[:80]}")

        logger.info(f"  -> {count} new articles from {source}")

    logger.info(f"Total new articles from all RSS feeds: {len(all_articles)}")
    return all_articles


# ─────────────────────────────────────────────
# LEGACY STUBS (kept for import compatibility)
# ─────────────────────────────────────────────

def scrape_latest_articles_from_mining_site(cursor):
    return []

def scrape_mining_review_data(cursor):
    return []

def scrape_lppm_com_news(cursor):
    return []

def scrape_miningmx_articles(cursor):
    return []

def scrape_metaldaily_articles(cursor):
    return []

def scrape_articles_from_miningweekly(cursor, metal_name):
    return []
