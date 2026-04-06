from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, select

from config import settings
from database import AsyncSessionLocal, engine
from models import Post
from routers import admin, posts

SEED = [
    # (title, content, category, lat, lng, age)
    ("Olycka vid Slussen",         "Trafikolycka vid Slussen, undvik området.",                    "trafik",   59.3193, 18.0719, timedelta(minutes=30)),
    ("Polisinsats Medborgarplatsen","Polisen är på plats vid Medborgarplatsen.",                   "brott",    59.3148, 18.0734, timedelta(hours=2)),
    ("Gatumusik Sergels torg",     "Gatumusiker på Sergels torg — riktigt bra!",                  "event",    59.3326, 18.0649, timedelta(hours=1)),
    ("Brand Hornsgatan",           "Brand i soprum på Hornsgatan, brandkåren på plats.",          "brand",    59.3178, 18.0498, timedelta(days=1, hours=3)),
    ("Vattenläcka Götgatan",       "Vattenläcka på Götgatan, halv gata avspärrad.",               "storning", 59.3134, 18.0726, timedelta(days=1, hours=6)),
    ("Loppis Nytorget",            "Loppismarknad vid Nytorget hela dagen.",                      "event",    59.3143, 18.0799, timedelta(days=1, hours=8)),
    ("Inbrott Ringvägen",          "Inbrott i källarförråd på Ringvägen, polisen informerad.",    "brott",    59.3089, 18.0654, timedelta(days=3, hours=1)),
    ("Köer E4 Haga Södra",         "Vägtull på E4 vid Haga Södra — långa köer.",                 "trafik",   59.3874, 18.0145, timedelta(days=3, hours=4)),
    ("Bygge Hornstull",            "Störande ljud från bygge vid Hornstull, startar 07:00.",      "storning", 59.3161, 18.0348, timedelta(days=7, hours=2)),
    ("Filmvisning Tantolunden",    "Gratis filmvisning i Tantolunden ikväll kl 20.",              "event",    59.3115, 18.0462, timedelta(days=7, hours=5)),
    ("Skogsbrand Nacka",           "Skogsbrand vid Nacka naturreservat, evakuering pågår.",       "brand",    59.3142, 18.1612, timedelta(days=7, hours=9)),
    ("Rån Farsta",                 "Rånet på ICA Kvantum Farsta, två gripna.",                    "brott",    59.2426, 18.0897, timedelta(days=14, hours=1)),
    ("Vägarbete Lidingövägen",     "Vägarbete på Lidingövägen klart.",                            "trafik",   59.3501, 18.0987, timedelta(days=14, hours=3)),
    ("Filharmonikerna Humlegården","Öppen repetition med Stockholms Filharmoniker i Humlegården.","event",    59.3378, 18.0736, timedelta(days=14, hours=6)),
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with AsyncSessionLocal() as session:
        existing = await session.exec(select(Post).limit(1))
        if not existing.first():
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            for title, content, category, lat, lng, age in SEED:
                session.add(Post(title=title, content=content, category=category, lat=lat, lng=lng, created_at=now - age))
            await session.commit()

    yield


app = FastAPI(title="Lokalinfo API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.include_router(admin.router)
