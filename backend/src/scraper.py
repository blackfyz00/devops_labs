"""Scraper using Cloudflare Browser Rendering API only."""

import logging

import httpx
from bs4 import BeautifulSoup

from .config import get_settings
from .models import Quote, ScrapingResult

logger = logging.getLogger(__name__)


async def scrape_url(url: str) -> ScrapingResult:
    """Scrape any URL via Cloudflare Browser Rendering."""
    settings = get_settings()
    endpoint = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{settings.cf_account_id}/browser-run/content"
    )
    headers = {
        "Authorization": f"Bearer {settings.cf_browser_api_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "gotoOptions": {"waitUntil": "networkidle0"},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(endpoint, headers=headers, json=payload)

    if response.status_code == 429:
        raise RuntimeError("Browser quota exceeded")

    response.raise_for_status()

    data = response.json()
    html = data.get("result", "")

    if not html:
        raise RuntimeError("Cloudflare returned empty HTML")

    return _parse_page(url, html)


def _parse_page(url: str, html: str) -> ScrapingResult:
    """Extract quotes using specific selectors if present, otherwise fallback to generic text."""
    soup = BeautifulSoup(html, "html.parser")
    
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    result = ScrapingResult(total_count=0)
    
    quote_elements = soup.select(".quote")
    
    if quote_elements:
        logger.info("Found %d quote elements via CSS selectors", len(quote_elements))
        for el in quote_elements:
            text_el = el.select_one(".text")
            author_el = el.select_one(".author")
            tags_els = el.find_all(class_="tag")
            
            text = text_el.get_text(strip=True) if text_el else ""
            author = author_el.get_text(strip=True) if author_el else "Unknown"
            tags = [t.get_text(strip=True) for t in tags_els]
            
            if text:
                quote_obj = Quote(text=text, author=author, tags=tags)
                result.add_quote(quote_obj)
    else:
        logger.warning("No .quote elements found, falling back to generic extraction for %s", url)
        title = soup.title.get_text(strip=True) if soup.title else url
        paragraphs = soup.find_all("p")
        
        count = 0
        for p in paragraphs:
            text = p.get_text(strip=True)
            if len(text) > 50:
                quote_obj = Quote(text=text, author=title, tags=["generic"])
                result.add_quote(quote_obj)
                count += 1
                if count >= 5:
                    break
                    
    return result