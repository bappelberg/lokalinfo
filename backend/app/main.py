import asyncio
import uuid as uuid_lib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlmodel import SQLModel, select

from config import settings
from database import AsyncSessionLocal, engine
from models import Comment, Post
from gdelt_master import gdelt_sync_loop
from police import police_sync_loop
from svt_nyheter_fetcher import svt_sync_loop
from routers import admin, comments, posts

SEED = [
    # (title, content, category, lat, lng, age, upvotes, downvotes)

    # ── Virala/högt upvotade ───────────────────────────────────────────────────
    ("Väpnat rån utanför Stureplan",
     "En person rånade en annan med kniv utanför Stureplan strax efter midnatt. Polisen grep en misstänkt på plats. Offret förd till sjukhus med lindriga skador.",
     "brott", 59.3355, 18.0752, timedelta(hours=3), 318, 12),

    ("STORT: Brand i flerbostadshus Södermalm",
     "Kraftig brand i ett flerbostadshus på Hornsgatan. Rök syns från stora delar av Södermalm. Räddningstjänsten uppmanar boende att hålla fönster stängda. Evakuering pågår.",
     "brand", 59.3178, 18.0498, timedelta(hours=5), 274, 8),

    ("Allvarlig olycka på E4 vid Haga Södra — kö på 14 km",
     "Frontalkrock mellan lastbil och personbil. Vägen helt avstängd i sydlig riktning. Räkna med minst 2 timmars fördröjning. Ta Essingeleden som alternativ.",
     "trafik", 59.3874, 18.0145, timedelta(hours=2), 241, 19),

    ("Polisinsats pågår — Medborgarplatsen avspärrad",
     "Stort polispådrag vid Medborgarplatsen. Flera polisbilar och hundpatrull på plats. Oklart vad som hänt. Undvik området tills vidare.",
     "brott", 59.3148, 18.0734, timedelta(minutes=45), 189, 7),

    ("Demonstation Sergels torg — trafiken påverkas",
     "Stor demonstration samlar flera tusen personer på Sergels torg och Sveavägen. Bussar omdirigerade. Fredlig stämning men räkna med trängsel.",
     "event", 59.3326, 18.0649, timedelta(hours=18), 156, 4),

    ("Vattenproblem Östermalm — brun/grumligt vatten",
     "Flera boende rapporterar missfärgat vatten från kranarna på Östermalm. Stockholm Vatten & Avfall utreder. Drick inte vattnet tills vidare.",
     "storning", 59.3418, 18.0877, timedelta(hours=6), 143, 3),

    ("Inbrott i källarförråd — Ringvägen 40-tal",
     "Någon har tagit sig in och stulit från minst 8 förråd i källaren. Polisanmälan gjord. Kontakta föreningen om du drabbats.",
     "brott", 59.3089, 18.0654, timedelta(hours=14), 112, 6),

    ("Takras på Götgatan — gata avspärrad",
     "Delar av ett tak har rasat ner på trottoaren vid Götgatan 78. Ingen skadad men gatan är avspärrad. Räkna med omledning.",
     "storning", 59.3134, 18.0726, timedelta(hours=8), 98, 2),

    # ── Normala / medelhöga ────────────────────────────────────────────────────
    ("Olycka vid Slussen — trafikkaos",
     "Trafikolycka i korsningen vid Slussen. Spårväg 2 och 3 försenade. Polis och ambulans på plats.",
     "trafik", 59.3193, 18.0719, timedelta(minutes=30), 67, 3),

    ("Bråk utanför krog på Stureplan",
     "Slagsmål utanför en krog. Ambulans tillkallad. En person verkar ha skadats.",
     "brott", 59.3352, 18.0745, timedelta(hours=1, minutes=20), 54, 8),

    ("Vattenläcka Kungsholmen — halv gata grävd upp",
     "Stor vattenläcka på Fleminggatan. Grävmaskiner på plats sedan tidigt i morse. Trottoar och en körbana blockerad.",
     "storning", 59.3318, 18.0185, timedelta(hours=7), 48, 1),

    ("Gatumusik Kungsträdgården — riktigt bra!",
     "Fantastisk gatumusiker spelar klassisk gitarr vid fontänen i Kungsträdgården. Passa på om du är i närheten!",
     "event", 59.3316, 18.0719, timedelta(hours=2), 44, 2),

    ("Cykelstöld utanför Centralen — var försiktig",
     "Min cykel stals utanför Stockholm Central trots lås. Tredje gången på en månad jag hör om detta. Använd två lås!",
     "brott", 59.3303, 18.0582, timedelta(hours=4), 39, 5),

    ("Skogsbrand Nacka naturreservat",
     "Rökutveckling synlig från Nacka naturreservat. Räddningstjänsten på plats. Håll dig borta från området.",
     "brand", 59.3142, 18.1612, timedelta(hours=11), 37, 1),

    ("Köbildning tunnelbana T-Centralen",
     "Signalfel på röda linjen gör att tågen går med kraftiga förseningar. Tunnelbanan råder resenärer att ta buss istället.",
     "trafik", 59.3310, 18.0589, timedelta(hours=1), 35, 2),

    ("Loppis Nytorget — massa fynd!",
     "Stor loppismarknad vid Nytorget med 40+ säljare. Böcker, kläder, elektronik och husgeråd. Pågår till kl 15.",
     "event", 59.3143, 18.0799, timedelta(hours=3), 31, 0),

    ("Misstänkt föremål Fridhemsplan",
     "Polisen spärrar av ett område vid Fridhemsplan efter rapport om misstänkt föremål. Troligen falskt alarm men undvik tills klartecken ges.",
     "brott", 59.3322, 18.0108, timedelta(hours=9), 28, 14),

    ("Bygge startar Hornstull — buller hela sommaren",
     "Nytt bostadsprojekt börjar byggas vid Hornstull. Störande ljud vardagar 07:00–18:00. Projektet beräknas pågå 18 månader.",
     "storning", 59.3161, 18.0348, timedelta(days=2), 26, 3),

    ("Gratis konsert Tantolunden ikväll kl 19",
     "Stockholms Stadsteater arrangerar gratis utomhusföreställning i Tantolunden. Ta med filt och korg!",
     "event", 59.3115, 18.0462, timedelta(hours=5), 24, 0),

    ("Inbrott bilarna på Lidingövägen",
     "Minst 6 bilar inbrutna på parkeringen vid Lidingövägen under natten. Fönsterrutor krossade. Polisanmält.",
     "brott", 59.3501, 18.0987, timedelta(hours=15), 22, 1),

    ("Röklukt i tunnelbanan Gamla Stan",
     "Kraftig röklukt rapporteras på T-baneperrongen vid Gamla Stan. SL undersöker. Kan vara tekniskt fel.",
     "storning", 59.3236, 18.0686, timedelta(minutes=50), 19, 2),

    ("Trafikljus ur funktion Sveavägen/Odengatan",
     "Trafikljusen i korsningen fungerar inte. Kör försiktigt och ge företräde åt höger. Trafikkontoret informerat.",
     "trafik", 59.3428, 18.0570, timedelta(hours=2, minutes=30), 17, 0),

    ("Räddningsinsats Djurgårdsbrunnsviken",
     "Räddningstjänstens båt på plats vid Djurgårdsbrunnsviken. Oklart om person i vattnet eller båtolycka.",
     "brand", 59.3410, 18.1180, timedelta(minutes=20), 16, 1),

    ("Marknad Hötorget hela veckan",
     "Säsongsmarknad på Hötorget med svenska råvaror, blommor och hantverk. Öppet 08:00–18:00 hela veckan.",
     "event", 59.3356, 18.0630, timedelta(days=1, hours=2), 15, 0),

    ("Strömavbrott Vasastan — hela kvarteret",
     "Strömavbrott drabbar flera kvarter i Vasastan. Elföretaget jobbar med felsökning. Oklart när det åtgärdas.",
     "storning", 59.3450, 18.0530, timedelta(hours=1, minutes=10), 14, 0),

    ("Farligt gods-transport E18 Bromma",
     "Lastbil med farligt gods har fått motorstopp på E18 vid Brommaplan. Räddningstjänst på plats som säkerhetsåtgärd.",
     "trafik", 59.3380, 17.9380, timedelta(hours=3, minutes=40), 13, 2),

    # ── Nyligen tillagda / låga upvotes ───────────────────────────────────────
    ("Misstänkt inbrott pågår just nu",
     "Ser en person som verkar försöka ta sig in i grannes lägenhet på Folkungagatan. Har ringt polisen.",
     "brott", 59.3132, 18.0801, timedelta(minutes=8), 9, 0),

    ("Trafikolycka Solnavägen",
     "Personbil och cyklist inblandade. Ambulans på väg.",
     "trafik", 59.3612, 18.0089, timedelta(minutes=12), 7, 0),

    ("Gratis yoga Rålambshovsparken nu",
     "Spontan yogagrupp i Rålambshovsparken. Alla välkomna, ta med matta!",
     "event", 59.3328, 18.0052, timedelta(minutes=25), 6, 0),

    ("Gaslukt Kungsholmen",
     "Kraftig gaslukt vid Scheelegatan. Har ringt SOS. Undvik området.",
     "storning", 59.3340, 18.0270, timedelta(minutes=15), 5, 0),

    ("Skadad fågel hittad Djurgården",
     "Hittade en skadad havsörn vid Djurgårdsvägen. Kontaktat Naturhistoriska museet. Vet någon vem man ska ringa?",
     "ovrigt", 59.3275, 18.1085, timedelta(minutes=35), 4, 1),

    ("Vägarbete startar imorgon Folkungagatan",
     "Enligt skylt börjar vägarbete på Folkungagatan 07:00 imorgon. Parkeringsförbud gäller.",
     "storning", 59.3128, 18.0752, timedelta(hours=1, minutes=45), 3, 0),

    ("Taggning på tunnelbanevagn",
     "Hela sidan av en tunnelbanevagn på gröna linjen är taggad med stora grafittimotiv.",
     "ovrigt", 59.3290, 18.0600, timedelta(minutes=55), 2, 3),

    ("Öppet hus Södermalms bibliotek",
     "Södermalms bibliotek har öppet hus med bokbytarbord och barnaktiviteter. Fri entré.",
     "event", 59.3120, 18.0610, timedelta(minutes=40), 2, 0),

    ("Bil utan registreringsskyltar Reimersholme",
     "Övergiven bil utan skyltar har stått här i 3 dagar. Polisanmält men ingen har kommit och tittat.",
     "ovrigt", 59.3168, 18.0195, timedelta(hours=2, minutes=15), 1, 0),

    ("Klotter på lekplats Vasaparken",
     "Klotter med otrevligt innehåll på lekplatsutrustningen i Vasaparken. Borde åtgärdas innan barn ser det.",
     "ovrigt", 59.3456, 18.0452, timedelta(minutes=18), 1, 0),
]

# (content, upvotes, downvotes, age, replies: [(content, upvotes, downvotes, age)])
COMMENT_SEEDS: dict[str, list] = {
    "Väpnat rån utanför Stureplan": [
        ("Var på plats, helt sjukt. Polisen kom på under 5 minuter.", 48, 0, timedelta(hours=2, minutes=50), [
            ("Bra att polisen var snabb! Hoppas offret mår bra.", 14, 0, timedelta(hours=2, minutes=35)),
            ("Femte rånet i det området på en månad... något måste göras.", 29, 1, timedelta(hours=2, minutes=20)),
        ]),
        ("Har det blivit värre på Stureplan på sistone? Känns som det händer saker hela tiden.", 22, 0, timedelta(hours=2, minutes=40), [
            ("Ja absolut, man undviker helst området sent på kvällen.", 11, 0, timedelta(hours=2, minutes=25)),
            ("Det är alkoholen + krogarna. Borde vara mer ordningsvakter.", 17, 2, timedelta(hours=2, minutes=10)),
            ("Eller så borde krogarna stänga tidigare.", 8, 3, timedelta(hours=1, minutes=55)),
        ]),
        ("Någon vet vilket sjukhus offret fördes till?", 3, 0, timedelta(hours=2), [
            ("Troligen Karolinska eller S:t Göran, de tar de flesta traumafall.", 6, 0, timedelta(hours=1, minutes=50)),
        ]),
        ("Polisen har nu bekräftat att en person är gripen. Följ SVT för uppdateringar.", 31, 0, timedelta(hours=1, minutes=30), []),
    ],

    "STORT: Brand i flerbostadshus Södermalm": [
        ("Bor i huset intill, det luktar rök överallt i trapphuset. Alla verkar ha evakuerats.", 67, 0, timedelta(hours=4, minutes=45), [
            ("Stanna inte inne om du inte måste! Täta under dörren med handdukar.", 22, 0, timedelta(hours=4, minutes=30)),
            ("Är du evakuerad nu? Mår du bra?", 9, 0, timedelta(hours=4, minutes=15)),
            ("Ja är ute på gatan nu. Tack för omtanken.", 18, 0, timedelta(hours=4)),
        ]),
        ("Såg det från Mariatorget, otroligt kraftig rök. Hoppas alla kom ut oskadda.", 41, 0, timedelta(hours=4, minutes=50), [
            ("Räddningstjänsten bekräftade att alla boende är redovisade.", 28, 0, timedelta(hours=3, minutes=30)),
        ]),
        ("Enligt Aftonbladet startade det i ett soprum i källaren. Troligen anlagd brand.", 35, 4, timedelta(hours=3, minutes=20), [
            ("Har du länk? Hittar inget på deras sajt.", 5, 0, timedelta(hours=3, minutes=10)),
            ("Sprid inte rykten utan källa.", 19, 1, timedelta(hours=2, minutes=55)),
        ]),
        ("Trafiken på Hornsgatan är helt stillastående, ta en annan väg.", 24, 0, timedelta(hours=4, minutes=40), []),
    ],

    "Allvarlig olycka på E4 vid Haga Södra — kö på 14 km": [
        ("Stod i kön i nästan 2 timmar. Inga uppdateringar från Trafikverket alls.", 55, 2, timedelta(hours=1, minutes=50), [
            ("Trafiken flödar nu via Essingeleden men det är också kö där nu.", 21, 0, timedelta(hours=1, minutes=30)),
            ("Trafikverkets app visade 'inga störningar' i 40 minuter. Helt värdelös.", 33, 1, timedelta(hours=1, minutes=15)),
        ]),
        ("Hörde att lastbilsföraren somnade vid ratten.", 18, 7, timedelta(hours=1, minutes=40), [
            ("Det är bara rykten, vänta på polisens presskonferens.", 24, 0, timedelta(hours=1, minutes=25)),
            ("Sluta spekulera innan fakta är klara.", 16, 2, timedelta(hours=1, minutes=10)),
        ]),
        ("Finns det något vettigt alternativ till Essingeleden söderut?", 12, 0, timedelta(hours=1, minutes=35), [
            ("Södertäljevägen via Skärholmen funkar, tog den precis.", 19, 0, timedelta(hours=1, minutes=20)),
            ("Pendelståget från Flemingsberg går bra om du kan parkera.", 8, 0, timedelta(hours=1, minutes=5)),
        ]),
        ("UPPDATERING: ett körfält öppnat igen. Kön minskar sakta.", 44, 0, timedelta(minutes=40), []),
    ],

    "Polisinsats pågår — Medborgarplatsen avspärrad": [
        ("Jobbar på ett kafé intill, polisen säger absolut ingenting om vad som hänt.", 34, 0, timedelta(minutes=40), [
            ("Tack för uppdatering! Fortsätt rapportera om du kan.", 12, 0, timedelta(minutes=35)),
            ("Har sett att de tar ut någon i handbojor.", 28, 3, timedelta(minutes=28)),
        ]),
        ("Var ute och sprang, fick vända vid avspärrningen. Ser allvarligt ut med 8+ polisbilar.", 21, 0, timedelta(minutes=38), [
            ("Ambulans också? Undrar om någon är skadad.", 7, 0, timedelta(minutes=30)),
            ("Ja, en ambulans kom för ca 15 min sen men åkte utan blåljus.", 14, 0, timedelta(minutes=22)),
        ]),
        ("Busslinje 4 och 59 är omledda, ta tunnelbanan istället.", 18, 0, timedelta(minutes=32), []),
    ],

    "Demonstation Sergels torg — trafiken påverkas": [
        ("Var med, fantastisk stämning och ett viktigt budskap. Uppskattningsvis 8 000 personer.", 42, 3, timedelta(hours=16), [
            ("Vilket budskap? Ingen info i inlägget.", 11, 0, timedelta(hours=15, minutes=30)),
            ("Klimatdemonstration, stod på plakaten. Google är din vän.", 19, 2, timedelta(hours=15)),
        ]),
        ("Satt fast på bussen i 45 minuter på grund av detta. Lite märkligt att inte SL informerade.", 28, 5, timedelta(hours=17), [
            ("De brukar lägga ut info i appen, såg inget om det heller.", 9, 0, timedelta(hours=16, minutes=30)),
            ("Demonstrationsrätten är viktigare än din pendling.", 15, 8, timedelta(hours=16)),
            ("Man kan tycka båda är viktiga...", 22, 0, timedelta(hours=15, minutes=30)),
        ]),
        ("Tack för att ni rapporterar! Kom precis hem med tunnelbanan, gick bra.", 8, 0, timedelta(hours=14), []),
    ],

    "Vattenproblem Östermalm — brun/grumligt vatten": [
        ("Fick brunt vatten ur kranen i morse, riktigt äckligt. Har beställt hem vatten.", 38, 0, timedelta(hours=5, minutes=30), [
            ("Samma hos oss på Storgatan. Stockholm Vatten svarar inte på telefon.", 17, 0, timedelta(hours=5)),
            ("Prova deras app, brukar gå snabbare att anmäla där.", 11, 0, timedelta(hours=4, minutes=40)),
        ]),
        ("Vet någon om det är farligt att duscha i det?", 14, 0, timedelta(hours=5), [
            ("Det beror på vad det är. Jag skulle vänta tills de gett klartecken.", 9, 0, timedelta(hours=4, minutes=45)),
            ("Missfärgning beror oftast på rost i rören, inte patogener. Men vänta ändå.", 21, 1, timedelta(hours=4, minutes=30)),
        ]),
        ("UPPDATERING från Stockholm Vatten: beror på tryckändring i ledningsnät. Spola 3 min, sedan OK.", 56, 0, timedelta(hours=2), [
            ("Tack! Spolat nu och det är klart igen.", 12, 0, timedelta(hours=1, minutes=45)),
        ]),
    ],

    "Inbrott i källarförråd — Ringvägen 40-tal": [
        ("Exakt samma sak hände i vår fastighet på Götgatan förra månaden. Tappade cykeln och skidor.", 31, 0, timedelta(hours=13), [
            ("Verkar vara organiserat, samma tillvägagångssätt som hos oss på Hornsgatan.", 18, 0, timedelta(hours=12, minutes=30)),
            ("Polisen sa att de sett ett mönster i Södermalm, flera anmälningar.", 24, 0, timedelta(hours=12)),
        ]),
        ("Kontakta bostadsrättsföreningen direkt och kräv bättre säkerhet.", 22, 0, timedelta(hours=12, minutes=30), [
            ("Vi har frågat men styrelsen säger att kameror kostar för mycket...", 15, 0, timedelta(hours=12)),
            ("Dags att byta styrelse isåfall. Säkerheten måste prioriteras.", 19, 1, timedelta(hours=11, minutes=30)),
            ("Det finns bidrag att söka för just detta hos kommunen.", 13, 0, timedelta(hours=11)),
        ]),
        ("Finns det kameraövervakning i huset? Kan vara viktigt för polisutredningen.", 8, 0, timedelta(hours=11), [
            ("Nej tyvärr, det är ju det som är problemet.", 5, 0, timedelta(hours=10, minutes=30)),
        ]),
    ],

    "Takras på Götgatan — gata avspärrad": [
        ("Passerade precis, otroligt att ingen skadades. Stora betongbitar på trottoaren.", 29, 0, timedelta(hours=7, minutes=30), [
            ("Skrämmande. Vad händer om det rasar på en person?", 11, 0, timedelta(hours=7)),
        ]),
        ("Det är tredje olyckan med den fastigheten på två år. Dags att ägaren tar ansvar.", 41, 1, timedelta(hours=7, minutes=45), [
            ("Stämmer, det var fuktskador i taket som aldrig åtgärdades ordentligt.", 22, 0, timedelta(hours=7, minutes=15)),
            ("Anmäl till stadsbyggnadskontoret, de kan tvinga fram åtgärder.", 17, 0, timedelta(hours=7)),
        ]),
        ("Cyklade förbi via Bondegatan istället, gick bra.", 7, 0, timedelta(hours=6), []),
    ],

    "Olycka vid Slussen — trafikkaos": [
        ("Tunnelbanan verkar gå OK, bara spårvagnen och en busslinje påverkas.", 18, 0, timedelta(minutes=25), [
            ("Bra info, tack! Tar tunnelbanan då.", 6, 0, timedelta(minutes=20)),
        ]),
        ("Vet någon hur lång tid det uppskattningsvis tar innan det är klart?", 9, 0, timedelta(minutes=22), [
            ("Polisen sa uppskattningsvis 30–45 minuter till.", 11, 0, timedelta(minutes=15)),
            ("UPPDATERING: spårvagnen kör igen nu!", 14, 0, timedelta(minutes=5)),
        ]),
    ],

    "Cykelstöld utanför Centralen — var försiktig": [
        ("Hände mig i februari, borta på 3 minuter trots hänglås. Använd alltid U-lås.", 24, 0, timedelta(hours=3, minutes=40), [
            ("U-lås + kedjlås kombinerat är svårast att knäcka.", 15, 0, timedelta(hours=3, minutes=20)),
            ("Och registrera cykeln i Stöldregistret om du inte gjort det.", 19, 0, timedelta(hours=3)),
        ]),
        ("Polisen verkar inte prioritera cykelstölder överhuvudtaget.", 22, 3, timedelta(hours=3, minutes=30), [
            ("Tyvärr sant, svårt att utreda utan övervakningskameror.", 13, 0, timedelta(hours=3, minutes=10)),
            ("Staden borde ha bättre övervakade cykelparkeringar vid Centralen.", 16, 0, timedelta(hours=2, minutes=50)),
        ]),
    ],

    "Gaslukt Kungsholmen": [
        ("Ring Stockholm Gas direkt! 08-671 78 00, de har jour dygnet runt.", 8, 0, timedelta(minutes=12), [
            ("Har ringt, de skickar bilar. Tack!", 5, 0, timedelta(minutes=8)),
        ]),
        ("Var i området nu, luktar STARKT. Håll er borta.", 4, 0, timedelta(minutes=10), []),
    ],

    "Misstänkt inbrott pågår just nu": [
        ("Ring 112 direkt om det pågår! Inte 114 14.", 7, 0, timedelta(minutes=6), [
            ("Har ringt 112, de är på väg.", 4, 0, timedelta(minutes=4)),
        ]),
        ("Ta inte risker, stå på säkert avstånd och fotografera bara om det är säkert.", 3, 0, timedelta(minutes=5), []),
    ],

    "Skadad fågel hittad Djurgården": [
        ("Ring Naturvårdsverkets havererade djurtelefon: 020-28 28 28 öppet vardagar.", 5, 0, timedelta(minutes=30), [
            ("Tack! Ringde precis, de kopplade mig vidare till en rehabiliterare.", 3, 0, timedelta(minutes=18)),
        ]),
        ("Havsörn? Det är en skyddad art, viktigt att det hanteras rätt.", 4, 0, timedelta(minutes=25), []),
    ],
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        # Migrera befintliga tabeller med nya kolumner
        await conn.execute(text("ALTER TABLE post ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)"))

    if settings.debug:
        async with AsyncSessionLocal() as session:
            existing = await session.exec(select(Post).limit(1))
            if not existing.first():
                now = datetime.now(timezone.utc).replace(tzinfo=None)

                # Pre-compute comment counts from seed data
                seeded_comment_counts = {
                    title: sum(1 + len(replies) for _, _, _, _, replies in thread)
                    for title, thread in COMMENT_SEEDS.items()
                }

                # Seed posts
                for title, content, category, lat, lng, age, upvotes, downvotes in SEED:
                    session.add(Post(
                        title=title,
                        content=content,
                        category=category,
                        lat=lat,
                        lng=lng,
                        created_at=now - age,
                        upvote_count=upvotes,
                        downvote_count=downvotes,
                        comment_count=seeded_comment_counts.get(title, 0),
                    ))
                await session.commit()

                # Seed comments
                result = await session.exec(select(Post))
                posts_by_title = {p.title: p for p in result.all()}

                for post_title, thread in COMMENT_SEEDS.items():
                    post = posts_by_title.get(post_title)
                    if not post:
                        continue
                    for content, upvotes, downvotes, age, replies in thread:
                        parent_id = uuid_lib.uuid4()
                        session.add(Comment(
                            id=parent_id,
                            post_id=post.id,
                            content=content,
                            upvote_count=upvotes,
                            downvote_count=downvotes,
                            created_at=now - age,
                        ))
                        for r_content, r_upvotes, r_downvotes, r_age in replies:
                            session.add(Comment(
                                post_id=post.id,
                                parent_id=parent_id,
                                content=r_content,
                                upvote_count=r_upvotes,
                                downvote_count=r_downvotes,
                                created_at=now - r_age,
                            ))
                await session.commit()

    # Starta bakgrundssynkar
    police_task = asyncio.create_task(police_sync_loop())
    gdelt_task = asyncio.create_task(gdelt_sync_loop())
    svt_task = asyncio.create_task(svt_sync_loop());
    yield
    for task in (police_task, gdelt_task, svt_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Lokalinfo API", lifespan=lifespan, redirect_slashes=False)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(posts.router)
app.include_router(admin.router)
app.include_router(comments.router)
