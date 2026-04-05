# Backend — Lokalinfo

## Stack

- **FastAPI** med async support
- **SQLModel** (SQLAlchemy 2.0 + Pydantic v2)
- **asyncpg** — async PostgreSQL-driver
- **Alembic** — databasmigreringar
- **Docker + PostgreSQL**

---

## Filstruktur

```
backend/
├── .env
├── requirements.txt
├── config.py
├── database.py
├── Dockerfile
└── app/
    ├── main.py
    ├── models.py
    ├── rate_limit.py
    └── routers/
        ├── __init__.py
        ├── posts.py
        └── admin.py
```

---

## Miljövariabler (.env)

```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/lokalinfo
ADMIN_TOKEN=change-this-to-a-secret-token
CORS_ORIGINS=http://localhost:3000
```

Inuti Docker Compose sätts `DATABASE_URL` automatiskt via `docker-compose.yml`.

---

## requirements.txt

```
fastapi[standard]
sqlmodel
uvicorn[standard]
asyncpg
pydantic-settings
alembic
```

---

## config.py

Läser miljövariabler med `pydantic-settings`.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str
    admin_token: str
    cors_origins: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

settings = Settings()
```

---

## database.py

Skapar async engine och session factory med SQLModel.

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from config import settings

engine = create_async_engine(settings.database_url)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

---

## app/models.py

Kombinerar databasmodell och API-scheman med SQLModel.

### Category (enum)

| Konstantnamn | Värde i databasen |
|---|---|
| `ACCIDENT` | `olycka` |
| `CRIME` | `brott` |
| `TRAFFIC` | `trafik` |
| `OUTAGE` | `driftstorning` |
| `NATURE` | `natur` |
| `ENVIRONMENT` | `miljo` |
| `EVENT` | `event` |
| `OTHER` | `ovrigt` |

### Post (tabell)

| Fält | Typ | Standard |
|---|---|---|
| `id` | UUID | auto (uuid4) |
| `content` | str (max 280) | — |
| `category` | str (max 20) | — |
| `lat` | float | — |
| `lng` | float | — |
| `created_at` | datetime (UTC) | auto |
| `report_count` | int | 0 |
| `is_hidden` | bool | False |
| `is_deleted` | bool | False |

`AUTO_HIDE_THRESHOLD = 5` — inlägg döljs automatiskt när `report_count` når detta värde.

### Scheman

| Klass | Används för |
|---|---|
| `PostCreate` | Input vid POST /posts (validerar category som enum, koordinater inom giltiga intervall) |
| `PostOut` | Svar till vanlig klient (döljer `is_deleted`) |
| `PostAdminOut` | Svar till admin (inkluderar `is_deleted`) |
| `ReportOut` | Svar vid rapportering (`message`, `auto_hidden`) |

---

## app/rate_limit.py

In-memory rate limiting per IP-adress. Lagras aldrig i databasen.

- Max **5 inlägg per timme** per IP
- **5 minuters cooldown** mellan inlägg

---

## app/main.py

- Skapar databastabeller vid uppstart via `SQLModel.metadata.create_all`
- Registrerar CORS-middleware med origins från `settings.cors_origins_list`
- Monterar routrarna `/posts` och `/admin`

---

## Endpoints

### Publika

| Metod | URL | Beskrivning |
|---|---|---|
| `GET` | `/posts?lat=&lng=&radius=` | Hämta synliga inlägg inom radien (km, standard 5.0) |
| `POST` | `/posts` | Skapa nytt inlägg |
| `POST` | `/posts/{id}/report` | Rapportera inlägg |

### Admin (kräver header `X-Admin-Token`)

| Metod | URL | Beskrivning |
|---|---|---|
| `GET` | `/admin/posts` | Lista rapporterade inlägg, sorterade efter antal rapporter |
| `DELETE` | `/admin/posts/{id}` | Mjukradera inlägg (`is_deleted = true`) |
| `POST` | `/admin/posts/{id}/restore` | Återställ inlägg (`is_hidden = false`, `report_count = 0`) |

---

## Docker

### Starta hela stacken

```bash
docker compose up --build
```

### Endast backend (om databasen redan körs)

```bash
docker compose up --build backend
```

Volymmount `./backend:/app` gör att kodändringar reflekteras direkt i dev-läge utan rebuild.

API-dokumentation: [http://localhost:8000/docs](http://localhost:8000/docs)
