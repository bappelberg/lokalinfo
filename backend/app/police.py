import asyncio
import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlmodel import select

from database import AsyncSessionLocal
from models import Post

logger = logging.getLogger(__name__)

POLICE_API_URL = "https://polisen.se/api/events"
FETCH_INTERVAL_SECONDS = 15 * 60  # var 15:e minut
MAX_EVENT_AGE_HOURS = 24  # skippa händelser äldre än så

# Händelsetyper som är redaktionella sammanfattningar, inte faktiska incidents
SKIP_TYPES = {
    "sammanfattning",
    "övrigt",
}


def should_skip(event: dict) -> bool:
    """Returnerar True för redaktionella händelser som inte ska visas som posts."""
    event_type = (event.get("type") or "").lower().strip()
    if event_type in SKIP_TYPES:
        return True
    name = (event.get("name") or "").lower()
    if "sammanfattning" in name:
        return True
    return False


def map_category(police_type: str) -> str:
    p = police_type.lower()
    if "brand" in p:
        return "brand"
    if any(x in p for x in ["trafik", "trafikolycka", "vårdslöshet i trafik", "olovlig körning", "fordon"]):
        return "trafik"
    if any(x in p for x in ["rån", "stöld", "inbrott", "misshandel", "mord", "mordförsök",
                              "bedrägeri", "skadegörelse", "olaga hot", "rattfylleri", "narkotika"]):
        return "brott"
    if any(x in p for x in ["fylleri", "bråk", "förargelseväckande", "ofredande", "störning", "ordningsstörning"]):
        return "storning"
    return "ovrigt"


def parse_gps(gps_str: str) -> tuple[float, float] | None:
    """Parsar 'lat,lng'-sträng från Polisens API."""
    try:
        parts = gps_str.split(",")
        if len(parts) == 2:
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lng <= 180:
                return lat, lng
    except (ValueError, AttributeError):
        pass
    return None


def parse_datetime(dt_str: str) -> datetime | None:
    """Parsar datetime från polisens API. Returnerar None om strängen inte kan tolkas."""
    if not dt_str:
        return None
    try:
        # Polisens format: "2025-03-28 00:33:00 +01:00"
        # Python <3.11 hanterar inte mellanslag före timezone — ersätt med T och ta bort extra mellanslag
        normalized = dt_str.strip().replace(" +", "+").replace(" -", "-")
        if "T" not in normalized:
            normalized = normalized.replace(" ", "T", 1)
        dt = datetime.fromisoformat(normalized)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


async def fetch_and_insert_police_events() -> int:
    """Hämtar polishändelser och sparar nya som posts. Returnerar antal nya posts."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(POLICE_API_URL)
        response.raise_for_status()
        events = response.json()

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=MAX_EVENT_AGE_HOURS)

    inserted = 0
    async with AsyncSessionLocal() as session:
        for event in events:
            external_id = str(event.get("id", ""))
            if not external_id:
                continue

            # Skippa sammanfattningar och redaktionellt innehåll
            if should_skip(event):
                continue

            # Parsa och validera tidpunkt innan vi gör något annat
            created_at = parse_datetime(event.get("datetime", ""))
            if created_at is None or created_at < cutoff:
                continue

            # Skippa om vi redan har den här händelsen
            existing = await session.exec(
                select(Post).where(
                    Post.source == "polisen",
                    Post.external_id == external_id,
                )
            )
            if existing.first():
                continue

            # GPS-koordinater krävs
            gps_str = event.get("location", {}).get("gps", "")
            coords = parse_gps(gps_str)
            if not coords:
                continue
            lat, lng = coords

            # Bygg title och content
            title = (event.get("name") or "")[:80]
            summary = (event.get("summary") or "").strip()
            content = summary[:280] if summary else title[:280]
            if not content:
                continue

            category = map_category(event.get("type", ""))

            session.add(Post(
                title=title,
                content=content,
                category=category,
                lat=lat,
                lng=lng,
                created_at=created_at,
                source="polisen",
                external_id=external_id,
            ))
            inserted += 1

        if inserted:
            await session.commit()

    return inserted


async def police_sync_loop() -> None:
    """Bakgrundsloop som synkar polishändelser med jämna mellanrum."""
    logger.info("Police sync: startar bakgrundsloop (interval %ds)", FETCH_INTERVAL_SECONDS)
    while True:
        try:
            n = await fetch_and_insert_police_events()
            if n:
                logger.info("Police sync: lade till %d nya posts", n)
            else:
                logger.debug("Police sync: inga nya händelser")
        except Exception as exc:
            logger.warning("Police sync misslyckades: %s", exc)
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)
