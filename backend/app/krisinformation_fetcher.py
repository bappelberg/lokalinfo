import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import select

from database import AsyncSessionLocal
from models import Post

logger = logging.getLogger(__name__)

KRIS_API_URL = "https://api.krisinformation.se/v3/news"
FETCH_INTERVAL_SECONDS = 30 * 60  # var 30:e minut
MAX_EVENT_AGE_HOURS = 168  # 7 dagar — VMA-händelser är relevanta längre

# Koordinater för svenska kommuner/orter (samma som police.py)
MUNICIPALITY_COORDS: dict[str, tuple[float, float]] = {
    "stockholm": (59.3293, 18.0686), "göteborg": (57.7089, 11.9746),
    "malmö": (55.6050, 13.0038), "uppsala": (59.8594, 17.6383),
    "västerås": (59.6099, 16.5448), "örebro": (59.2753, 15.2134),
    "linköping": (58.4108, 15.6214), "helsingborg": (56.0465, 12.6945),
    "jönköping": (57.7826, 14.1618), "norrköping": (58.5942, 16.1826),
    "lund": (55.7047, 13.1910), "umeå": (63.8258, 20.2630),
    "gävle": (60.6749, 17.1413), "borås": (57.7210, 12.9401),
    "södertälje": (59.1955, 17.6253), "eskilstuna": (59.3710, 16.5099),
    "karlstad": (59.3793, 13.5036), "täby": (59.4436, 18.0697),
    "sundsvall": (62.3908, 17.3069), "luleå": (65.5848, 22.1547),
    "östersund": (63.1792, 14.6357), "trollhättan": (58.2840, 12.2883),
    "borlänge": (60.4832, 15.4370), "falun": (60.6065, 15.6355),
    "skellefteå": (64.7495, 20.9527), "kalmar": (56.6634, 16.3566),
    "karlskrona": (56.1612, 15.5869), "växjö": (56.8777, 14.8091),
    "halmstad": (56.6745, 12.8577), "kristianstad": (56.0294, 14.1567),
    "varberg": (57.1055, 12.2508), "skövde": (58.3906, 13.8463),
    "nyköping": (58.7527, 17.0073), "solna": (59.3601, 18.0010),
    "nacka": (59.3108, 18.1588), "huddinge": (59.2378, 17.9808),
    "haninge": (59.1668, 18.1436), "järfälla": (59.4267, 17.8346),
    "sollentuna": (59.4282, 17.9519), "upplands väsby": (59.5184, 17.9164),
    "sigtuna": (59.6174, 17.7239), "norrtälje": (59.7580, 18.7054),
    "enköping": (59.6369, 17.0775), "sandviken": (60.6169, 16.7685),
    "gavle": (60.6749, 17.1413), "hudiksvall": (61.7278, 17.1040),
    "härnösand": (62.6325, 17.9387), "örnsköldsvik": (63.2908, 18.7148),
    "kiruna": (67.8557, 20.2253), "gällivare": (67.1330, 20.6585),
    "piteå": (65.3172, 21.4799), "boden": (65.8238, 21.6908),
    # Skåne
    "trelleborg": (55.3751, 13.1574), "ystad": (55.4297, 13.8205),
    "landskrona": (55.8706, 12.8300), "ängelholm": (56.2432, 12.8614),
    "eslöv": (55.8376, 13.3037), "höganäs": (56.1999, 12.5578),
    "vellinge": (55.4716, 13.0211), "burlöv": (55.7364, 13.0844),
}


def lookup_municipality(text: str) -> tuple[float, float] | None:
    """Söker efter kommunnamn i text och returnerar koordinater."""
    t = text.lower()
    # Prova längre namn först för att undvika falska träffar
    for name in sorted(MUNICIPALITY_COORDS.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(name) + r'\b', t):
            return MUNICIPALITY_COORDS[name]
    return None


def parse_coordinate(coord_str: str) -> tuple[float, float] | None:
    """Parsar 'lat,lng'-sträng från krisinformation."""
    if not coord_str:
        return None
    try:
        parts = coord_str.split(",")
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng
    except (ValueError, AttributeError):
        pass
    return None


def extract_coords(areas: list, headline: str) -> tuple[float, float] | None:
    """Extraherar koordinater: försöker Area-listan, faller tillbaka på ortsnamn i rubriken."""
    for area in areas:
        coord = area.get("Coordinate") or ""
        result = parse_coordinate(coord)
        if result:
            return result
        # Area kan också ha Description med ortnamn
        desc = area.get("Description") or ""
        result = lookup_municipality(desc)
        if result:
            return result
    # Fallback: leta efter ortnamn i rubriken
    return lookup_municipality(headline)


def parse_published(dt_str: str) -> datetime | None:
    """Parsar ISO 8601-datum från krisinformations API."""
    if not dt_str:
        return None
    try:
        normalized = dt_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def map_category(event_type: str) -> str:
    """Mappar krisinformations händelsetyp till lokal kategori."""
    t = (event_type or "").lower()
    if any(x in t for x in ["brand", "eld", "fire"]):
        return "brand"
    if any(x in t for x in ["trafik", "väg", "järnväg", "transport"]):
        return "trafik"
    if any(x in t for x in ["brott", "polis", "hot", "angrepp"]):
        return "brott"
    if any(x in t for x in ["störning", "avbrott", "el", "vatten", "gas", "it"]):
        return "storning"
    if any(x in t for x in ["natur", "översvämning", "storm", "väder", "jordskred", "ras"]):
        return "natur"
    return "ovrigt"


async def fetch_and_insert_kris_events() -> int:
    """Hämtar krisinformation och sparar nya som posts. Returnerar antal nya."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(KRIS_API_URL)
        response.raise_for_status()
        items = response.json()

    if not isinstance(items, list):
        logger.warning("Krisinformation: oväntat svar-format")
        return 0

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=MAX_EVENT_AGE_HOURS)
    inserted = 0

    async with AsyncSessionLocal() as session:
        for item in items:
            if item.get("Language", "").lower() != "sv":
                continue

            external_id = str(item.get("Identifier") or "")
            if not external_id:
                continue

            created_at = parse_published(item.get("Published") or "")
            if created_at is None or created_at < cutoff:
                continue

            headline = (item.get("Headline") or "")[:80]

            areas = item.get("Area") or []
            coords = extract_coords(areas, headline)
            if not coords:
                logger.debug("Kris sync: ingen plats för item %s ('%s'), skippar", external_id, headline)
                continue
            lat, lng = coords

            # Kolla dubblett
            existing = await session.exec(
                select(Post).where(Post.source == "krisinformation", Post.external_id == external_id)
            )
            if existing.first():
                continue

            preamble = (item.get("Preamble") or "").strip()
            web = (item.get("Web") or "").strip()

            source_line = "\nKälla: Krisinformation.se"
            if web:
                source_line += f"\n{web}"
            content = preamble[:600 - len(source_line)] + source_line

            # Event är antingen en sträng eller ett dict beroende på API-version
            event = item.get("Event") or ""
            if isinstance(event, dict):
                event_type = event.get("EventTypeName") or ""
            else:
                event_type = str(event)
            category = map_category(event_type)

            session.add(Post(
                title=headline,
                content=content,
                category=category,
                lat=lat,
                lng=lng,
                created_at=created_at,
                source="krisinformation",
                external_id=external_id,
            ))
            inserted += 1
            logger.info("Kris sync: lade till '%s' (lat=%.4f, lng=%.4f)", headline, lat, lng)

        await session.commit()

    return inserted


async def kris_sync_loop() -> None:
    """Bakgrundsloop för Krisinformation."""
    logger.info("Kris sync: startar bakgrundsloop (intervall %ds)", FETCH_INTERVAL_SECONDS)
    while True:
        try:
            n = await fetch_and_insert_kris_events()
            if n:
                logger.info("Kris sync: lade till %d nya posts", n)
            else:
                logger.debug("Kris sync: inga nya händelser")
        except Exception as exc:
            logger.warning("Kris sync misslyckades: %s", exc)
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)
