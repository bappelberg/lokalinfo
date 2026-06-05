# Backend — Lokalinfo

## Stack

- **FastAPI** med async support
- **SQLModel** (SQLAlchemy 2.0 + Pydantic v2)
- **asyncpg** — async PostgreSQL-driver
- **Alembic** — databasmigreringar
- **argon2-cffi** — lösenordshashning
- **Docker + PostgreSQL**

---

## Filstruktur

```
backend/
├── requirements.txt
├── Dockerfile / Dockerfile.prod
└── app/
    ├── main.py                    # FastAPI-app, startup, seed-data
    ├── models.py                  # Databas-modeller (SQLModel)
    ├── config.py                  # Miljövariabler (pydantic-settings)
    ├── database.py                # Async engine + session factory
    ├── rate_limit.py              # In-memory rate limiting per IP
    ├── utils.py                   # Hjälpfunktioner
    ├── police.py                  # Synkar Polisens händelse-API
    ├── svt_nyheter_fetcher.py     # Synkar SVT Nyheter RSS
    ├── krisinformation_fetcher.py # Synkar Krisinformation API
    ├── gdelt_master.py            # Synkar GDELT globala nyheter
    └── routers/
        ├── posts.py               # Inlägg (CRUD, röstning, rapportering)
        ├── comments.py            # Kommentarer + trådar
        ├── auth.py                # Registrering + inloggning
        └── admin.py               # Adminpanel (moderering)
```

---

## Miljövariabler (.env)

```
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/lokalinfo
ADMIN_TOKEN=change-this-to-a-secret-token
CORS_ORIGINS=http://localhost:3000
DEBUG=true
```

---

## Modeller

### Category (enum)

| Värde | Beskrivning |
|---|---|
| `brott` | Brott & polishändelser |
| `trafik` | Trafikolyckor & störningar |
| `brand` | Brand & räddningsinsatser |
| `event` | Evenemang |
| `storning` | Driftstörningar & störningar |
| `natur` | Naturhändelser |
| `ovrigt` | Övrigt |

### Post (tabell)

| Fält | Typ | Standard |
|---|---|---|
| `id` | UUID | auto (uuid4) |
| `title` | str (max 80) | "" |
| `content` | str (max 600) | — |
| `category` | str (max 20) | — |
| `lat` / `lng` | float | — |
| `created_at` | datetime (UTC) | auto |
| `upvote_count` / `downvote_count` | int | 0 |
| `comment_count` | int | 0 |
| `report_count` | int | 0 |
| `is_hidden` / `is_deleted` | bool | False |
| `source` | str? (max 20) | None |
| `external_id` | str? (max 50) | None |
| `image_url` | str? (max 500) | None |
| `user_id` | UUID? | None |
| `author_username` | str? (max 50) | None |
| `author_avatar_url` | str? (max 500) | None |

`AUTO_HIDE_THRESHOLD = 1` — inlägg döljs automatiskt när `report_count` når detta värde.

---

## Endpoints

### Inlägg

| Metod | URL | Beskrivning |
|---|---|---|
| `GET` | `/posts` | Hämta synliga inlägg (lat, lng, radius, category, from_date, to_date) |
| `POST` | `/posts` | Skapa nytt inlägg |
| `POST` | `/posts/{id}/vote` | Rösta (upvote/downvote) |
| `POST` | `/posts/{id}/report` | Rapportera inlägg |

### Kommentarer

| Metod | URL | Beskrivning |
|---|---|---|
| `GET` | `/posts/{id}/comments` | Hämta kommentarer (med trådar) |
| `POST` | `/posts/{id}/comments` | Skapa kommentar (stöder parent_id för svar) |
| `POST` | `/comments/{id}/vote` | Rösta på kommentar |

### Auth

| Metod | URL | Beskrivning |
|---|---|---|
| `POST` | `/auth/register` | Registrera ny användare |
| `POST` | `/auth/login` | Logga in (returnerar session) |
| `GET` | `/users/me` | Hämta inloggad användare |

### Admin (kräver header `X-Admin-Token`)

| Metod | URL | Beskrivning |
|---|---|---|
| `GET` | `/admin/posts` | Lista rapporterade inlägg |
| `DELETE` | `/admin/posts/{id}` | Mjukradera inlägg |
| `POST` | `/admin/posts/{id}/restore` | Återställ inlägg |
| `POST` | `/admin/posts/{id}/reply` | Svara på inlägg som admin |

---

## Externa datakällor

Bakgrundslooparna startar automatiskt vid uppstart och körs parallellt:

| Källa | Fil | Intervall |
|---|---|---|
| Polismyndigheten | `police.py` | 15 min |
| SVT Nyheter (RSS) | `svt_nyheter_fetcher.py` | 20 min |
| Krisinformation | `krisinformation_fetcher.py` | 30 min |
| GDELT | `gdelt_master.py` | 60 min |

---

## Rate limiting

In-memory per IP-adress — lagras aldrig i databasen.

- Max **5 inlägg per timme** per IP
- **5 minuters cooldown** mellan inlägg

---

## Docker

```bash
# Dev (med hot reload)
docker compose -f docker-compose.dev.yml up --build

# Produktion
docker compose up --build
```

API-dokumentation: [http://localhost:8000/docs](http://localhost:8000/docs)
