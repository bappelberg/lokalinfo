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

# Koordinater för svenska kommuner (centrum). Källa: SCB/Lantmäteriet approximationer.
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
    # Östergötlands län
    "boxholm": (58.1967, 15.0559), "finspång": (58.7086, 15.7674),
    "kinda": (57.9833, 15.6167), "linköping": (58.4108, 15.6214),
    "mjölby": (58.3254, 15.1243), "motala": (58.5378, 15.0394),
    "norrköping": (58.5942, 16.1826), "söderköping": (58.4795, 16.3261),
    "vadstena": (58.4491, 14.8889), "valdemarsvik": (58.2042, 16.5984),
    "ydre": (57.8500, 15.2500), "åtvidaberg": (58.2027, 15.9985),
    "ödeshög": (58.2219, 14.6549),
    # Jönköpings län
    "aneby": (57.8370, 14.8104), "eksjö": (57.6636, 14.9713),
    "gislaved": (57.2999, 13.5408), "gnosjö": (57.3566, 13.7433),
    "habo": (57.9082, 14.0860), "jönköping": (57.7826, 14.1618),
    "mullsjö": (57.9161, 13.8837), "nässjö": (57.6528, 14.6944),
    "sävsjö": (57.4028, 14.6601), "tranås": (58.0377, 14.9797),
    "vaggeryd": (57.4973, 14.1453), "vetlanda": (57.4274, 15.0647),
    "värnamo": (57.1833, 14.0333),
    # Kronobergs län
    "alvesta": (56.8989, 14.5564), "lessebo": (56.7503, 15.2628),
    "ljungby": (56.8329, 13.9384), "markaryd": (56.4617, 13.5897),
    "tingsryd": (56.5268, 14.9735), "uppvidinge": (57.0981, 15.4778),
    "växjö": (56.8777, 14.8091), "älmhult": (56.5517, 14.1386),
    # Kalmar län
    "borgholm": (56.8790, 16.6562), "emmaboda": (56.6303, 15.5366),
    "hultsfred": (57.4882, 15.8439), "högsby": (57.1659, 16.0270),
    "kalmar": (56.6634, 16.3566), "mönsterås": (57.0359, 16.4414),
    "mörbylånga": (56.5254, 16.3777), "nybro": (56.7469, 15.9050),
    "oskarshamn": (57.2648, 16.4481), "torsås": (56.4103, 16.0000),
    "vimmerby": (57.6643, 15.8553), "västervik": (57.7574, 16.6372),
    # Gotlands län
    "gotland": (57.4684, 18.4867), "visby": (57.6348, 18.2948),
    # Blekinge län
    "karlshamn": (56.1706, 14.8639), "karlskrona": (56.1612, 15.5869),
    "olofström": (56.2786, 14.5283), "ronneby": (56.2095, 15.2773),
    "sölvesborg": (56.0508, 14.5739),
    # Skåne län
    "bjuv": (56.0833, 12.9167), "bromölla": (56.0768, 14.4672),
    "burlöv": (55.7364, 13.0844), "båstad": (56.4272, 12.8522),
    "eslöv": (55.8376, 13.3037), "helsingborg": (56.0465, 12.6945),
    "hässleholm": (56.1575, 13.7666), "höganäs": (56.1999, 12.5578),
    "hörby": (55.8568, 13.6618), "höör": (55.9378, 13.5424),
    "klippan": (56.1352, 13.1260), "kristianstad": (56.0294, 14.1567),
    "kävlinge": (55.7911, 13.1053), "landskrona": (55.8706, 12.8300),
    "lomma": (55.6718, 13.0720), "lund": (55.7047, 13.1910),
    "malmö": (55.6050, 13.0038), "osby": (56.3784, 13.9942),
    "perstorp": (56.1378, 13.3949), "simrishamn": (55.5561, 14.3553),
    "sjöbo": (55.6254, 13.7085), "skurup": (55.4759, 13.4992),
    "staffanstorp": (55.6426, 13.2075), "svalöv": (55.9166, 13.1090),
    "svedala": (55.5070, 13.2351), "tomelilla": (55.5422, 13.9487),
    "trelleborg": (55.3751, 13.1574), "vellinge": (55.4716, 13.0211),
    "ystad": (55.4297, 13.8205), "åstorp": (56.1330, 12.9427),
    "ängelholm": (56.2432, 12.8614), "örkelljunga": (56.2806, 13.2825),
    "östra göinge": (56.2618, 14.0988),
    # Hallands län
    "falkenberg": (56.9057, 12.4917), "halmstad": (56.6745, 12.8577),
    "hylte": (56.9970, 13.2254), "kungsbacka": (57.4877, 12.0763),
    "laholm": (56.5131, 13.0434), "varberg": (57.1055, 12.2508),
    # Västra Götalands län
    "ale": (57.9167, 12.0667), "alingsås": (57.9295, 12.5349),
    "bengtsfors": (59.0346, 12.2251), "bollebygd": (57.6667, 12.5667),
    "borås": (57.7210, 12.9401), "dals-ed": (58.9167, 11.9167),
    "essunga": (58.1667, 13.0000), "falköping": (58.1743, 13.5511),
    "färgelanda": (58.5682, 12.0087), "grästorp": (58.3310, 12.6878),
    "gullspång": (58.9833, 14.0833), "göteborg": (57.7089, 11.9746),
    "götene": (58.5334, 13.4896), "herrljunga": (58.0769, 13.0155),
    "hjo": (58.3007, 14.2936), "härryda": (57.6508, 12.2088),
    "karlsborg": (58.5333, 14.5000), "kungälv": (57.8704, 11.9808),
    "lerum": (57.7690, 12.2686), "lidköping": (58.5053, 13.1587),
    "lilla edet": (58.1379, 12.1352), "lysekil": (58.2741, 11.4374),
    "mariestad": (58.7093, 13.8248), "mark": (57.5191, 12.5671),
    "mellerud": (58.7017, 12.4617), "munkedal": (58.4718, 11.6793),
    "mölndal": (57.6554, 12.0137), "orust": (58.1000, 11.6500),
    "partille": (57.7388, 12.1100), "skara": (58.3866, 13.4382),
    "skövde": (58.3906, 13.8463), "sotenäs": (58.4236, 11.3050),
    "stenungsund": (57.9936, 11.8197), "strömstad": (58.9348, 11.1714),
    "svenljunga": (57.4962, 13.1107), "tanum": (58.7238, 11.3247),
    "tibro": (58.4240, 14.1624), "tidaholm": (58.1780, 13.9558),
    "tjörn": (57.9950, 11.6421), "tranemo": (57.4792, 13.3460),
    "trollhättan": (58.2840, 12.2883), "töreboda": (58.7059, 14.1199),
    "uddevalla": (58.3490, 11.9378), "ulricehamn": (57.7936, 13.4192),
    "vara": (58.2591, 12.9512), "vårgårda": (58.0290, 12.8077),
    "åmål": (59.0476, 12.7015), "öckerö": (57.7031, 11.6539),
    # Värmlands län
    "arvika": (59.6554, 12.5870), "eda": (59.8623, 12.1917),
    "filipstad": (59.7131, 14.1660), "forshaga": (59.5355, 13.4838),
    "grums": (59.3464, 13.1074), "hagfors": (60.0308, 13.6490),
    "hammarö": (59.3160, 13.5310), "karlstad": (59.3793, 13.5036),
    "kil": (59.4985, 13.3124), "kristinehamn": (59.3096, 14.1118),
    "munkfors": (59.8333, 13.5500), "storfors": (59.5330, 14.2666),
    "sunne": (59.8328, 13.1444), "säffle": (59.1327, 12.9228),
    "torsby": (60.1412, 12.9990), "årjäng": (59.3938, 12.1407),
    # Örebro län
    "askersund": (58.8783, 14.9014), "degerfors": (59.2333, 14.4333),
    "hallsberg": (59.0667, 15.1167), "hällefors": (59.7833, 14.5167),
    "karlskoga": (59.3274, 14.5216), "kumla": (59.1234, 15.1384),
    "laxå": (58.9840, 14.6162), "lekeberg": (59.1167, 15.1500),
    "lindesberg": (59.5912, 15.2283), "ljusnarsberg": (59.9000, 14.9333),
    "nora": (59.5218, 15.0375), "örebro": (59.2753, 15.2134),
    # Västmanlands län
    "arboga": (59.3973, 15.8344), "fagersta": (60.0047, 15.7940),
    "hallstahammar": (59.6153, 16.2250), "kungsör": (59.4253, 16.0985),
    "köping": (59.5136, 15.9892), "norberg": (60.0698, 15.9296),
    "sala": (59.9217, 16.6085), "skinnskatteberg": (59.8298, 15.6940),
    "surahammar": (59.7167, 16.2250), "västerås": (59.6099, 16.5448),
    # Dalarnas län
    "avesta": (60.1460, 16.1685), "borlänge": (60.4832, 15.4370),
    "falun": (60.6065, 15.6355), "gagnef": (60.5833, 14.9833),
    "hedemora": (60.2767, 15.9893), "leksand": (60.7305, 14.9980),
    "ludvika": (60.1493, 15.1895), "malung-sälen": (60.6833, 13.7167),
    "malung": (60.6833, 13.7167), "mora": (61.0082, 14.5387),
    "orsa": (61.1189, 14.6199), "rättvik": (60.8878, 15.1122),
    "smedjebacken": (60.1333, 15.4167), "säter": (60.3509, 15.7484),
    "vansbro": (60.1707, 14.2139), "älvdalen": (61.2250, 14.0376),
    # Gävleborgs län
    "bollnäs": (61.3478, 16.3934), "gävle": (60.6749, 17.1413),
    "hofors": (60.5521, 16.2927), "hudiksvall": (61.7278, 17.1040),
    "ljusdal": (61.8293, 16.0773), "nordanstig": (62.0000, 17.1000),
    "ockelbo": (60.8897, 16.7250), "ovanåker": (61.3500, 15.9333),
    "sandviken": (60.6169, 16.7685), "söderhamn": (61.3000, 17.0667),
    # Västernorrlands län
    "härnösand": (62.6325, 17.9387), "kramfors": (62.9296, 17.7992),
    "sollefteå": (63.1657, 17.2712), "sundsvall": (62.3908, 17.3069),
    "timrå": (62.4889, 17.3241), "ånge": (62.5285, 15.6558),
    "örnsköldsvik": (63.2908, 18.7148),
    # Jämtlands län
    "berg": (62.9833, 14.5000), "bräcke": (62.7472, 15.4264),
    "härjedalen": (62.1333, 14.2167), "krokom": (63.3333, 14.4667),
    "ragunda": (63.1000, 16.4000), "strömsund": (63.8603, 15.5547),
    "åre": (63.3987, 13.0825), "östersund": (63.1792, 14.6357),
    # Västerbottens län
    "bjurholm": (63.9333, 19.0000), "dorotea": (64.2574, 16.4119),
    "lycksele": (64.5942, 18.6699), "malå": (65.1833, 18.7500),
    "norsjö": (64.9106, 19.4853), "robertsfors": (64.1985, 20.8481),
    "skellefteå": (64.7495, 20.9527), "sorsele": (65.5333, 17.5333),
    "storuman": (65.0937, 17.1100), "umeå": (63.8258, 20.2630),
    "vilhelmina": (64.6253, 16.6568), "vindeln": (64.2014, 19.7206),
    "vännäs": (63.9083, 19.7500), "åsele": (64.1667, 17.3333),
    # Norrbottens län
    "arjeplog": (66.0500, 17.8833), "arvidsjaur": (65.5931, 19.1807),
    "boden": (65.8238, 21.6908), "gällivare": (67.1330, 20.6585),
    "haparanda": (65.8348, 24.1406), "jokkmokk": (66.6036, 19.8282),
    "kalix": (65.8549, 23.1382), "kiruna": (67.8557, 20.2253),
    "luleå": (65.5848, 22.1547), "pajala": (67.2099, 23.3670),
    "piteå": (65.3172, 21.4799), "älvsbyn": (65.6807, 21.0016),
    "överkalix": (66.3333, 22.8333), "övertorneå": (66.3906, 23.6678),
}


def lookup_municipality(city: str) -> tuple[float, float] | None:
    """Slår upp koordinater för en svensk kommun. Case-insensitiv."""
    return MUNICIPALITY_COORDS.get(city.lower().strip())


def extract_city_from_title(title: str) -> str | None:
    """Extraherar stadsnamn från polisens titlar, t.ex. '10 april 08.22, Arbetsplatsolycka, Järfälla' → 'Järfälla'."""
    parts = [p.strip() for p in title.split(",")]
    if len(parts) >= 3:
        return parts[-1]
    return None


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
        normalized = dt_str.strip().replace(" +", "+").replace(" -", "-")
        if "T" not in normalized:
            normalized = normalized.replace(" ", "T", 1)
        dt = datetime.fromisoformat(normalized)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def resolve_coords(title: str, fallback_gps: str) -> tuple[float, float] | None:
    """Returnerar bästa tillgängliga koordinater: kommunuppslag → läns-GPS → None."""
    city = extract_city_from_title(title)
    if city:
        coords = lookup_municipality(city)
        if coords:
            return coords
    return parse_gps(fallback_gps)


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

            if should_skip(event):
                continue

            created_at = parse_datetime(event.get("datetime", ""))
            if created_at is None or created_at < cutoff:
                continue

            title = (event.get("name") or "")[:80]
            summary = (event.get("summary") or "").strip()
            content = summary[:280] if summary else title[:280]
            if not content:
                continue

            fallback_gps = event.get("location", {}).get("gps", "")
            coords = resolve_coords(title, fallback_gps)
            if not coords:
                continue
            lat, lng = coords

            # Uppdatera koordinater om händelsen redan finns med oprecis läns-GPS
            existing = await session.exec(
                select(Post).where(Post.source == "polisen", Post.external_id == external_id)
            )
            existing_post = existing.first()
            if existing_post:
                if existing_post.lat != lat or existing_post.lng != lng:
                    existing_post.lat = lat
                    existing_post.lng = lng
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
