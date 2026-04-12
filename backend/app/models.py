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
    RECREATION  = "rekreation"
    NATURE      = "natur"
    HELP        = "hjalp"
    CULTURE     = "kultur"
    FOOD        = "mat"
    OTHER       = "ovrigt"


class Post(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(default="", max_length=80)
    content: str = Field(max_length=600)
    category: str = Field(max_length=20)
    lat: float
    lng: float
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    upvote_count: int = Field(default=0)
    downvote_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    report_count: int = Field(default=0)
    is_hidden: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    source: str | None = Field(default=None, max_length=20)
    external_id: str | None = Field(default=None, max_length=50, index=True)
    image_url: str | None = Field(default=None, max_length=500)
    user_id: uuid.UUID | None = Field(default=None, foreign_key="user.id")
    author_username: str | None = Field(default=None, max_length=50)
    author_avatar_url: str | None = Field(default=None, max_length=500)


class PostCreate(SQLModel):
    title: str = Field(default="", max_length=80)
    content: str = Field(min_length=1, max_length=280)
    category: Category
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    image_url: str | None = Field(default=None, max_length=500)


class PostOut(SQLModel):
    id: uuid.UUID
    title: str
    content: str
    category: Category
    lat: float
    lng: float
    created_at: datetime
    upvote_count: int
    downvote_count: int
    comment_count: int
    report_count: int
    is_hidden: bool
    image_url: str | None
    author_username: str | None
    author_avatar_url: str | None

    model_config = {"from_attributes": True}


class PostAdminOut(PostOut):
    is_deleted: bool


class VoteOut(SQLModel):
    upvote_count: int
    downvote_count: int
    direction: str | None  # "up", "down", eller None om rösten togs bort


class ReportOut(SQLModel):
    message: str
    auto_hidden: bool

# Comments

class Comment(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id: uuid.UUID = Field(foreign_key="post.id")
    parent_id: uuid.UUID | None = Field(default=None, foreign_key="comment.id")
    content: str = Field(max_length=500)
    upvote_count: int = Field(default=0)
    downvote_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    is_deleted: bool = Field(default=False)
    author_username: str | None = Field(default=None, max_length=50)
    author_avatar_url: str | None = Field(default=None, max_length=500)

class CommentCreate(SQLModel):
    content: str = Field(min_length=1, max_length=500)
    parent_id: uuid.UUID | None = None

class CommentOut(SQLModel):
    id: uuid.UUID
    post_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: str
    upvote_count: int
    downvote_count: int
    created_at: datetime
    author_username: str | None
    author_avatar_url: str | None

    model_config = {"from_attributes": True}


class PostVote(SQLModel, table=True):
    post_id: uuid.UUID = Field(foreign_key="post.id", primary_key=True)
    ip: str = Field(primary_key=True, max_length=45)
    direction: str = Field(max_length=4)  # "up" | "down"


class CommentVote(SQLModel, table=True):
    comment_id: uuid.UUID = Field(foreign_key="comment.id", primary_key=True)
    ip: str = Field(primary_key=True, max_length=45)
    direction: str = Field(max_length=4)  # "up" | "down"

class UserRole(str, Enum):
    user = "user"
    moderator = "moderator"
    admin = "admin"


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(unique=True, max_length=50, index=True)
    email: str = Field(unique=True, max_length=255, index=True)
    hashed_password: str = Field(max_length=255)
    role: UserRole = Field(default=UserRole.user, sa_column_kwargs={"server_default": "user"})
    is_active: bool = Field(default=True)
    avatar_url: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class UserCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=100)


class UserOut(SQLModel):
    id: uuid.UUID
    username: str
    email: str
    role: UserRole
    is_active: bool
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(SQLModel):
    identifier: str  # e-post eller användarnamn
    password: str

