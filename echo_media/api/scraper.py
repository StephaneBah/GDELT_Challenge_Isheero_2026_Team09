import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; EchoMedia/1.0; research bot)",
    "Accept-Language": "fr,en;q=0.9",
}

async def fetch_article(url: str, max_chars: int = 1500) -> dict:
    """Retourne titre + extrait textuel d'un article. Silencieux si échec."""
    try:
        async with httpx.AsyncClient(timeout=8, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        # Extraire le texte principal (paragraphes)
        paragraphs = soup.find_all("p")
        text = " ".join(p.get_text(strip=True) for p in paragraphs)
        return {"url": url, "title": title, "excerpt": text[:max_chars]}
    except Exception as e:
        return {"url": url, "title": "", "excerpt": f"[Inaccessible: {type(e).__name__}]"}


async def fetch_articles(urls: list[str]) -> list[dict]:
    import asyncio
    return await asyncio.gather(*[fetch_article(u) for u in urls])
