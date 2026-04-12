import asyncio
import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import httpx
from sqlmodel import select

from database import AsyncSessionLocal
from models import Post

logger = logging.getLogger(__name__)

SVT_RSS_URL = "https://www.svt.se/rss.xml"
FETCH_INTERVAL_SECONDS = 20 * 60  # Var 20:e minut
MAX_EVENT_AGE_HOURS = 24

# --- KOORDINATER & MAPPING ---

MUNICIPALITY_COORDS: dict[str, tuple[float, float]] = {
    # Stockholms län
    "botkyrka": (59.2087, 17.8254), "danderyd": (59.4008, 18.0333),
    "ekerö": (59.2950, 17.8128), "haninge": (59.1668, 18.1436),
    "huddinge": (59.2378, 17.9808), "järfälla": (59.4267, 17.8346),
    "lidingö": (59.3636, 18.1536), "nacka": (59.3108, 18.1588),
    "norrtälje": (59.7580, 18.7054), "nykvarn": (59.1839, 17.4282),
    "nynäshamn": (58.9024, 17.9479), "salem": (59.2167, 17.7667),
    "sigtuna": (59.6174, 17.7239), "sollentuna": (59.4282, 17.9519),
    "solna": (59.3601, 18.0010), "stockholm": (59.3293, 18.0686),
    "sundbyberg": (59.3611, 17.9706), "södertälje": (59.1955, 17.6253),
    "tyresö": (59.2447, 18.2289), "täby": (59.4436, 18.0697),
    "upplands väsby": (59.5184, 17.9164), "upplands-bro": (59.5273, 17.6367),
    "vallentuna": (59.5380, 18.0803), "vaxholm": (59.4019, 18.3331),
    "värmdö": (59.3167, 18.5167), "österåker": (59.4833, 18.2833),
    # Uppsala län
    "enköping": (59.6369, 17.0775), "heby": (59.9280, 16.8816),
    "knivsta": (59.7248, 17.7825), "tierp": (60.3439, 17.5142),
    "uppsala": (59.8594, 17.6383), "älvkarleby": (60.5667, 17.4500),
    "östhammar": (60.2597, 18.3717),
    # Södermanlands län
    "eskilstuna": (59.3710, 16.5099), "flen": (59.0582, 16.5887),
    "gnesta": (59.0449, 17.3069), "katrineholm": (58.9960, 16.2069),
    "nyköping": (58.7527, 17.0073), "oxelösund": (58.6758, 17.1068),
    "strängnäs": (59.3773, 17.0300), "trosa": (58.8975, 17.5502),
    "vingåker": (59.0500, 15.8667),
    # Dalarna & Övriga
    "borlänge": (60.4832, 15.4370), "falun": (60.6065, 15.6355),
    "göteborg": (57.7089, 11.9746), "västerås": (59.6099, 16.5448),
    
    # --- SVT REGIONALA SLUGS (Fallback till centralorter) ---
    "dalarna": (60.6065, 15.6355), "vastmanland": (59.6099, 16.5448),
    "sormland": (58.7527, 17.0073), "vast": (57.7089, 11.9746),
    "skane": (55.6050, 13.0038), "smaland": (56.8777, 14.8091),
    "jonkoping": (57.7826, 14.1618), "ost": (58.4108, 15.6214),
    "orebro": (59.2753, 15.2134), "varmland": (59.3793, 13.5036),
    "gavleborg": (60.6749, 17.1413), "vasternorrland": (62.6325, 17.9387),
    "jamtland": (63.1792, 14.6357), "vasterbotten": (63.8258, 20.2630),
    "norrbotten": (65.5848, 22.1547), "halland": (56.6745, 12.8577),
    "blekinge": (56.1612, 15.5869),
}

FOREIGN_COORDS: dict[str, tuple[float, float]] = {
    # Europa
    "albanien": (41.1533, 20.1683), "belgien": (50.5039, 4.4699),
    "bosnien": (43.9159, 17.6791), "bulgarien": (42.7339, 25.4858),
    "cypern": (35.1264, 33.4299), "Danmark": (56.2639, 9.5018),
    "danmark": (56.2639, 9.5018), "estland": (58.5953, 25.0136),
    "finland": (61.9241, 25.7482), "frankrike": (46.2276, 2.2137),
    "paris": (48.8566, 2.3522), "grekland": (39.0742, 21.8243),
    "aten": (37.9838, 23.7275), "irland": (53.4129, -8.2439),
    "island": (64.9631, -19.0208), "italien": (41.8719, 12.5674),
    "rom": (41.9028, 12.4964), "kroatien": (45.1, 15.2),
    "lettland": (56.8796, 24.6032), "litauen": (55.1694, 23.8813),
    "luxembourg": (49.8153, 6.1296), "malta": (35.9375, 14.3754),
    "moldavien": (47.4116, 28.3699), "nederländerna": (52.1326, 5.2913),
    "amsterdam": (52.3676, 4.9041), "nordmakedonien": (41.6086, 21.7453),
    "norge": (60.4720, 8.4689), "oslo": (59.9139, 10.7522),
    "poland": (51.9194, 19.1451), "portugal": (39.3999, -8.2245),
    "rumänien": (45.9432, 24.9668), "schweiz": (46.8182, 8.2275),
    "serbien": (44.0165, 21.0059), "slovakien": (48.6690, 19.6990),
    "slovenien": (46.1512, 14.9955), "spanien": (40.4637, -3.7492),
    "madrid": (40.4168, -3.7038), "tjeckien": (49.8175, 15.4730),
    "turkiet": (38.9637, 35.2433), "istanbul": (41.0082, 28.9784),
    "ankara": (39.9334, 32.8597), "tyskland": (51.1657, 10.4515),
    "berlin": (52.5200, 13.4050), "ungern": (47.1625, 19.5033),
    "budapest": (47.4979, 19.0402), "ukraina": (48.3794, 31.1656),
    "kyiv": (50.4501, 30.5234), "österrike": (47.5162, 14.5501),
    "wien": (48.2082, 16.3738),
    # Ryssland & fd Sovjet
    "ryssland": (61.5240, 105.3188), "moskva": (55.7558, 37.6173),
    "belarus": (53.7098, 27.9534), "georgien": (42.3154, 43.3569),
    "armenien": (40.0691, 45.0382), "azerbajdzjan": (40.1431, 47.5769),
    "kazakstan": (48.0196, 66.9237),
    # Mellanöstern
    "iran": (32.4279, 53.6880), "tehran": (35.6892, 51.3890),
    "irak": (33.2232, 43.6793), "bagdad": (33.3152, 44.3661),
    "israel": (31.0461, 34.8516), "jerusalem": (31.7683, 35.2137),
    "tel aviv": (32.0853, 34.7818), "gaza": (31.3547, 34.3088),
    "libanon": (33.8547, 35.8623), "beirut": (33.8938, 35.5018),
    "syrien": (34.8021, 38.9968), "damaskus": (33.5138, 36.2765),
    "saudiarabien": (23.8859, 45.0792), "jemen": (15.5527, 48.5164),
    "förenade arabemiraten": (23.4241, 53.8478), "dubai": (25.2048, 55.2708),
    "jordanien": (30.5852, 36.2384), "kuwait": (29.3117, 47.4818),
    "qatar": (25.3548, 51.1839), "oman": (21.5126, 55.9233),
    "pakistan": (30.3753, 69.3451), "islamabad": (33.7294, 73.0931),
    "afghanistan": (33.9391, 67.7100), "kabul": (34.5553, 69.2075),
    # Asien
    "indien": (20.5937, 78.9629), "new delhi": (28.6139, 77.2090),
    "kina": (35.8617, 104.1954), "peking": (39.9042, 116.4074),
    "shanghai": (31.2304, 121.4737), "japan": (36.2048, 138.2529),
    "tokyo": (35.6762, 139.6503), "sydkorea": (35.9078, 127.7669),
    "nordkorea": (40.3399, 127.5101), "taiwan": (23.6978, 120.9605),
    "thailand": (15.8700, 100.9925), "vietnam": (14.0583, 108.2772),
    "indonesien": (0.7893, 113.9213), "malaysia": (4.2105, 101.9758),
    "filippinerna": (12.8797, 121.7740), "bangladesh": (23.6850, 90.3563),
    "myanmar": (21.9162, 95.9560), "nepal": (28.3949, 84.1240),
    # Afrika
    "egypten": (26.8206, 30.8025), "kairo": (30.0444, 31.2357),
    "nigeria": (9.0820, 8.6753), "sydafrika": (-30.5595, 22.9375),
    "etiopien": (9.1450, 40.4897), "kenya": (0.0236, 37.9062),
    "ghana": (7.9465, -1.0232), "tanzania": (-6.3690, 34.8888),
    "marocko": (31.7917, -7.0926), "algeriet": (28.0339, 1.6596),
    "libyen": (26.3351, 17.2283), "somalia": (5.1521, 46.1996),
    "sudan": (12.8628, 30.2176), "tunisien": (33.8869, 9.5375),
    "congo": (-4.0383, 21.7587), "senegal": (14.4974, -14.4524),
    # Amerika
    "usa": (37.0902, -95.7129), "washington": (38.9072, -77.0369),
    "new york": (40.7128, -74.0060), "los angeles": (34.0522, -118.2437),
    "kanada": (56.1304, -106.3468), "mexiko": (23.6345, -102.5528),
    "brasilien": (-14.2350, -51.9253), "argentina": (-38.4161, -63.6167),
    "colombia": (4.5709, -74.2973), "venezuela": (6.4238, -66.5897),
    "chile": (-35.6751, -71.5430), "peru": (-9.1900, -75.0152),
    "cuba": (21.5218, -77.7812),
    # Oceanien
    "australien": (-25.2744, 133.7751), "new zealand": (-40.9006, 174.8860),
}

def lookup_location(name: str) -> tuple[float, float] | None:
    if not name:
        return None
    key = name.lower().strip()
    return MUNICIPALITY_COORDS.get(key) or FOREIGN_COORDS.get(key)

def extract_location_from_url(url: str) -> str | None:
    parts = url.split('/')
    if "lokalt" in parts:
        idx = parts.index("lokalt")
        if len(parts) > idx + 1:
            return parts[idx + 1]
    return None

def map_svt_category(url: str, title: str) -> str:
    u, t = url.lower(), title.lower()
    if any(x in t for x in ["brand", "eld", "rök"]): return "brand"
    if any(x in t for x in ["trafik", "olycka", "krock", "väg"]): return "trafik"
    if any(x in t for x in ["rån", "mord", "skjutning", "polis", "gripen", "åtal", "våldtäkt"]): return "brott"
    return "ovrigt"

def parse_rss_datetime(dt_str: str) -> datetime | None:
    try:
        dt = datetime.strptime(dt_str, '%a, %d %b %Y %H:%M:%S %z')
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None

async def fetch_and_insert_svt_events() -> int:
    """Hämtar SVT-nyheter och sparar nya som posts."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(SVT_RSS_URL)
        response.raise_for_status()
        xml_content = response.text

    root = ET.fromstring(xml_content)
    items = root.findall(".//item")
    
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=MAX_EVENT_AGE_HOURS)
    inserted = 0

    async with AsyncSessionLocal() as session:
        for item in items:
            title = (item.findtext("title") or "")[:80]
            link = (item.findtext("link") or "").strip()
            description = (item.findtext("description") or "").strip()
            pub_date_str = item.findtext("pubDate") or ""
            guid = hashlib.md5((item.findtext("guid") or link).encode()).hexdigest()[:50]

            created_at = parse_rss_datetime(pub_date_str)
            if not created_at or created_at < cutoff:
                continue

            # --- PLATS-IDENTIFIERING ---
            search_text = f"{title} {description}"
            coords = None

            # 1. Kolla alla kända platser mot titeln + beskrivning (längre namn först)
            all_locations = sorted(
                list(MUNICIPALITY_COORDS.keys()) + list(FOREIGN_COORDS.keys()),
                key=len, reverse=True
            )
            for place in all_locations:
                if place.title() in search_text:
                    coords = lookup_location(place)
                    break

            # 2. Fallback: URL-slug för lokala nyheter (/nyheter/lokalt/vasterbotten/...)
            if not coords:
                loc_slug = extract_location_from_url(link)
                coords = lookup_location(loc_slug)

            if not coords:
                continue

            lat, lng = coords

            # Kolla dubblett
            existing = await session.exec(
                select(Post).where(Post.source == "svt", Post.external_id == guid)
            )
            if existing.first():
                continue

            category = map_svt_category(link, title)
            source_line = f"\nKälla: SVT Nyheter\n{link}"
            content = description[:600 - len(source_line)] + source_line

            session.add(Post(
                title=title,
                content=content[:600],
                category=category,
                lat=lat,
                lng=lng,
                created_at=created_at,
                source="svt",
                external_id=guid,
            ))
            inserted += 1

        await session.commit()
    return inserted

async def svt_sync_loop() -> None:
    """Bakgrundsloop för SVT."""
    logger.info("SVT sync: startar bakgrundsloop (intervall %ds)", FETCH_INTERVAL_SECONDS)
    while True:
        try:
            n = await fetch_and_insert_svt_events()
            if n:
                logger.info("SVT sync: lade till %d nya posts", n)
        except Exception as exc:
            logger.warning("SVT sync misslyckades: %s", exc)
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)