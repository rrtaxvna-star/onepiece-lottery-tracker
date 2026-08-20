"""Fetches ONE PIECE card game lottery roundup articles from nyuka-now.com.

nyuka-now.com's robots.txt (checked 2026-08-20) only disallows /wp-admin/ and
/campaign/, and imposes no bot-specific restrictions, so plain polite HTTP
polling is fine here. We deliberately avoid cardchusen.com, whose robots.txt
disallows scraping tools and AI crawlers outright.

Etiquette: identify ourselves with a real User-Agent, keep the poll interval
at 30-60 minutes (set by the caller/cron, not here), and sleep briefly
between requests when fetching multiple article pages in one run.
"""
import time

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "OnePieceLotteryTracker/1.0 (+personal, non-commercial hobby project; "
    "contact: rrtaxvna@gmail.com)"
)
BASE = "https://nyuka-now.com"
# Category (抽選情報) narrowed to the "ワンピースカードゲーム" tag via the site's
# own search form (method=get, action=nyuka-now.com, params: tag[]).
CATEGORY_URL = f"{BASE}/archives/category/chusen/?tag%5B%5D=one_piece_card"
REQUEST_TIMEOUT = 15
SLEEP_BETWEEN_REQUESTS = 2.0

TITLE_KEYWORDS = ("ワンピース", "ONE PIECE", "One Piece")

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})


def _get(url: str) -> str:
    resp = _session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def discover_article_urls() -> list[str]:
    """Find recent ONE PIECE-related roundup article URLs from the category index."""
    html = _get(CATEGORY_URL)
    soup = BeautifulSoup(html, "html.parser")

    urls: list[str] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a["href"]
        if "/archives/" not in href or href.rstrip("/").endswith("/category/chusen"):
            continue
        title_text = a.get_text(strip=True)
        if not title_text or not any(kw in title_text for kw in TITLE_KEYWORDS):
            continue
        full_url = href if href.startswith("http") else BASE + href
        if full_url not in seen:
            seen.add(full_url)
            urls.append(full_url)
    return urls


def fetch_article_text(url: str) -> str:
    """Fetch one article and return its main body text (nav/footer stripped)."""
    html = _get(url)
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.select("script, style, nav, header, footer, aside"):
        tag.decompose()

    content = (
        soup.select_one("article")
        or soup.select_one(".entry-content")
        or soup.select_one("main")
        or soup.body
    )
    if content is None:
        return ""
    return content.get_text("\n", strip=True)


def fetch_all(urls: list[str] | None = None) -> dict[str, str]:
    """Returns {article_url: article_text}. Discovers URLs if not given."""
    if urls is None:
        urls = discover_article_urls()

    results: dict[str, str] = {}
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        results[url] = fetch_article_text(url)
    return results
