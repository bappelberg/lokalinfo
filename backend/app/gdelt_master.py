import asyncio
import hashlib
import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import select

from database import AsyncSessionLocal
from models import Post

logger = logging.getLogger(__name__)

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
FETCH_INTERVAL_SECONDS = 60 * 60  # var 60:e minut
MAX_ARTICLES = 250

GEO_DB: dict[str, tuple[float, float]] = {
    "Venezuela": (6.4238, -66.5897),
    "Iran": (32.4279, 53.6880),
    "Italy": (41.8719, 12.5674),
    "Philippines": (12.8797, 121.7740),
    "Dubai": (25.2048, 55.2708),
    "United Arab Emirates": (23.4241, 53.8478),
    "India": (20.5937, 78.9629),
    "United Kingdom": (55.3781, -3.4360),
    "England": (52.3555, -1.1743),
    "USA": (37.0902, -95.7129),
    "United States": (37.0902, -95.7129),
    "Stockholm": (59.3293, 18.0686),
    "Sweden": (60.1282, 18.6435),
    "Ukraine": (48.3794, 31.1656),
    "Russia": (61.5240, 105.3188),
    "China": (35.8617, 104.1954),
    "France": (46.2276, 2.2137),
    "Germany": (51.1657, 10.4515),
    "Syria": (34.8021, 38.9968),
    "Israel": (31.0461, 34.8516),
    "Gaza": (31.3547, 34.3088),
    "Pakistan": (30.3753, 69.3451),
    "Afghanistan": (33.9391, 67.7100),
    "Brazil": (-14.2350, -51.9253),
    "Mexico": (23.6345, -102.5528),
    "Japan": (36.2048, 138.2529),
    "South Korea": (35.9078, 127.7669),
    "North Korea": (40.3399, 127.5101),
    "Turkey": (38.9637, 35.2433),
    "Saudi Arabia": (23.8859, 45.0792),
    "Iraq": (33.2232, 43.6793),
    "Egypt": (26.8206, 30.8025),
    "South Africa": (-30.5595, 22.9375),
    "Nigeria": (9.0820, 8.6753),
    "Ethiopia": (9.1450, 40.4897),
    "Sudan": (12.8628, 30.2176),
    "Libya": (26.3351, 17.2283),
    "Somalia": (5.1521, 46.1996),
    "Yemen": (15.5527, 48.5164),
}


def _fetch_article_text_sync(url: str) -> str:
    """Hämtar och extraherar brödtext från en artikel (sync, körs i executor)."""
    try:
        from newspaper import Article
        article = Article(url)
        article.download()
        article.parse()
        raw_text = article.text.replace("\n", " ").strip()
        return (raw_text[:300] + "...") if len(raw_text) > 300 else raw_text
    except Exception:
        return ""


def parse_gdelt_date(date_str: str) -> datetime | None:
    """Parsar GDELT:s datumformat: '20250410T123456Z'."""
    if not date_str:
        return None
    try:
        date_str = date_str.strip()
        if "T" in date_str:
            return datetime.strptime(date_str, "%Y%m%dT%H%M%SZ").replace(tzinfo=None)
        return datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=None)
    except Exception:
        return None


def resolve_location(title: str, summary: str) -> tuple[str, float, float] | None:
    """Hittar första kända plats i titel och sammanfattning."""
    text = f"{title} {summary}".lower()
    for place, (lat, lng) in GEO_DB.items():
        if place.lower() in text:
            return place, lat, lng
    return None


def map_gdelt_category(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    if any(w in text for w in ["fire", "explosion", "blast", "bomb"]):
        return "brand"
    if any(w in text for w in ["crash", "accident", "collision", "traffic"]):
        return "trafik"
    if any(w in text for w in ["arrest", "crime", "murder", "attack", "shooting", "killed", "war", "conflict"]):
        return "brott"
    return "ovrigt"


async def fetch_and_insert_gdelt_articles() -> int:
    """Hämtar GDELT-artiklar och sparar nya som posts. Returnerar antal nya posts."""
    params = {
        "query": "stability sourcelang:eng",
        "mode": "artlist",
        "maxrecords": str(MAX_ARTICLES),
        "format": "json",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(GDELT_API_URL, params=params, headers=headers)
        response.raise_for_status()
        articles = response.json().get("articles", [])

    inserted = 0
    async with AsyncSessionLocal() as session:
        for a in articles:
            url = a.get("url", "")
            if not url:
                continue

            external_id = hashlib.md5(url.encode()).hexdigest()[:50]

            existing = await session.exec(
                select(Post).where(Post.source == "gdelt", Post.external_id == external_id)
            )
            if existing.first():
                continue

            title = (a.get("title") or "")[:80]
            if not title:
                continue

            summary = await asyncio.to_thread(_fetch_article_text_sync, url)
            if not summary:
                continue

            location = resolve_location(title, summary)
            if not location:
                continue
            _, lat, lng = location

            created_at = datetime.now(timezone.utc).replace(tzinfo=None)

            category = map_gdelt_category(title, summary)
            domain = a.get("domain", "")
            footer = f"\n\nKälla: {domain} | {url}"
            max_body = 280 - len(footer)
            content = summary[:max(0, max_body)] + footer if max_body > 0 else summary[:280]

            session.add(Post(
                title=title,
                content=content,
                category=category,
                lat=lat,
                lng=lng,
                created_at=created_at,
                source="gdelt",
                external_id=external_id,
            ))
            inserted += 1

            await asyncio.sleep(0.5)

        await session.commit()

    return inserted


async def gdelt_sync_loop() -> None:
    """Bakgrundsloop som synkar GDELT-artiklar med jämna mellanrum."""
    logger.info("GDELT sync: startar bakgrundsloop (interval %ds)", FETCH_INTERVAL_SECONDS)
    while True:
        try:
            n = await fetch_and_insert_gdelt_articles()
            if n:
                logger.info("GDELT sync: lade till %d nya artiklar", n)
            else:
                logger.debug("GDELT sync: inga nya artiklar")
        except Exception as exc:
            logger.warning("GDELT sync misslyckades: %s", exc)
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)
