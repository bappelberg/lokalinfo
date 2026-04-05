import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, SQLModel

AUTO_HIDE_THRESHOLD = 5


class Category(str, Enum):
    CRIME       = "brott"
    TRAFFIC     = "trafik"
    FIRE        = "brand"
    EVENT       = "event"
    DISTURBANCE = "storning"
    OTHER       = "ovrigt"


class Post(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(default="", max_length=80)
    content: str = Field(max_length=280)
    category: str = Field(max_length=20)
    lat: float
    lng: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    report_count: int = Field(default=0)
    is_hidden: bool = Field(default=False)
    is_deleted: bool = Field(default=False)


class PostCreate(SQLModel):
    title: str = Field(default="", max_length=80)
    content: str = Field(min_length=1, max_length=280)
    category: Category
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class PostOut(SQLModel):
    id: uuid.UUID
    title: str
    content: str
    category: Category
    lat: float
    lng: float
    created_at: datetime
    report_count: int
    is_hidden: bool

    model_config = {"from_attributes": True}


class PostAdminOut(PostOut):
    is_deleted: bool


class ReportOut(SQLModel):
    message: str
    auto_hidden: bool
