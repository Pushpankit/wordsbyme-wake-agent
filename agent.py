import asyncio
import os
import time
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
from bs4 import BeautifulSoup

BASE_URL = os.getenv("BASE_URL", "https://www.wordsbyme.in").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_PAGES = int(os.getenv("MAX_PAGES", "200"))
DELAY_BETWEEN_PAGES = float(os.getenv("DELAY_BETWEEN_PAGES", "0.5"))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140 Safari/537.36 WordsByMe-WakeAgent/2.0"
)

def normalize_url(url):
    url, _ = urldefrag(url)
    return url.rstrip("/") or url

def same_site(url):
    return urlparse(url).netloc == urlparse(BASE_URL).netloc

def is_http_url(url):
    return url.startswith(("http://", "https://"))

async def fetch(client, url):
    try:
        response = await client.get(url, follow_redirects=True)
        return response.status_code, str(response.url), response.text
    except Exception as exc:
        return None, url, str(exc)

async def discover_from_sitemap(client):
    urls = set()
    sitemap_url = f"{BASE_URL}/sitemap.xml"
    print(f"[sitemap] requesting {sitemap_url}")

    try:
        response = await client.get(sitemap_url, follow_redirects=True)
        print(f"[sitemap] HTTP {response.status_code}")
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "xml")
        for loc in soup.find_all("loc"):
            url = normalize_url(loc.get_text(strip=True))
            if same_site(url) and is_http_url(url):
                urls.add(url)

        print(f"[sitemap] discovered {len(urls)} URLs")
    except Exception as exc:
        print(f"[sitemap] ERROR: {type(exc).__name__}: {exc}")

    return urls

def discover_links(html):
    found = set()
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        url = normalize_url(urljoin(BASE_URL + "/", href))
        if same_site(url) and is_http_url(url):
            found.add(url)

    return found

async def crawl_once():
    started = time.time()
    discovered = set()
    visited = set()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT,
        headers=headers,
        follow_redirects=True,
    ) as client:
        discovered.update(await discover_from_sitemap(client))

        status, final_url, html = await fetch(client, BASE_URL)

        if status is None:
            print(f"[home] FAILED: {html}")
        else:
            print(f"[home] {status} {final_url}")
            if 200 <= status < 400:
                discovered.add(normalize_url(final_url))
                discovered.update(discover_links(html))

        queue = list(discovered)
        print(f"[crawl] queue={len(queue)}")

        while queue and len(visited) < MAX_PAGES:
            url = queue.pop(0)
            if url in visited:
                continue

            visited.add(url)
            page_started = time.time()
            status, final_url, html = await fetch(client, url)
            response_time = time.time() - page_started

            if status is None:
                print(f"[FAIL] {url} | {html}")
            elif 200 <= status < 400:
                print(f"[OK] {status} {url} | {response_time:.2f}s")

                for link in discover_links(html):
                    if (
                        link not in visited
                        and link not in discovered
                        and len(discovered) < MAX_PAGES
                    ):
                        discovered.add(link)
                        queue.append(link)
            else:
                print(f"[WARN] {status} {url} | {response_time:.2f}s")

            await asyncio.sleep(DELAY_BETWEEN_PAGES)

    elapsed = time.time() - started
    print(
        f"[crawl] visited={len(visited)} "
        f"discovered={len(discovered)} time={elapsed:.1f}s"
    )
    return elapsed

async def main():
    print("=================================")
    print("WordsByMe Wake Agent")
    print(f"BASE_URL = {BASE_URL}")
    print(f"MAX_PAGES = {MAX_PAGES}")
    print(f"REQUEST_TIMEOUT = {REQUEST_TIMEOUT}s")
    print("=================================")
    await crawl_once()

if __name__ == "__main__":
    asyncio.run(main())
