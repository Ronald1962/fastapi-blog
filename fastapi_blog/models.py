import datetime
from pathlib import Path
from typing import List, Mapping, Optional

import databases
import markdown2
import sqlalchemy
from pydantic import BaseModel
from sqlalchemy import desc, func, select

# SQLAlchemy specific code, as with any other app
# DATABASE_URL = "sqlite:///" + str(Path(__file__).parent / "blog.db")
DATABASE_URL = "postgresql:///db"

database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()

tags = sqlalchemy.Table(
    "tags",
    metadata,
    sqlalchemy.Column("tag_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("description", sqlalchemy.String, nullable=False),
)

posts = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("post_id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("subtitle", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("author", sqlalchemy.String, nullable=False, default="smetam"),
    sqlalchemy.Column(
        "date", sqlalchemy.DateTime, nullable=False, default=datetime.datetime.now
    ),
    sqlalchemy.Column("content", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("completed", sqlalchemy.Boolean, nullable=False, default=False),
)

post_tags = sqlalchemy.Table(
    "post_tags",
    metadata,
    sqlalchemy.Column(
        "post_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("posts.post_id"),
        primary_key=True,
    ),
    sqlalchemy.Column(
        "tag_id",
        sqlalchemy.Integer,
        sqlalchemy.ForeignKey("tags.tag_id"),
        primary_key=True,
    ),
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)


class PostInput(BaseModel):
    title: str
    subtitle: str
    content: str
    completed: bool


class Post(BaseModel):
    post_id: int
    title: str
    subtitle: str
    author: str
    date: datetime.datetime
    content: str
    completed: bool


async def fetch_last_post_id() -> int:
    query = (
        select([posts.c.post_id])
        .select_from(posts)
        .order_by(desc(posts.c.date))
        .limit(1)
    )
    return await database.fetch_val(query=query)


async def fetch_post(post_id: int = None) -> Optional[Mapping]:
    post_id = post_id or await fetch_last_post_id()
    query = (
        select([posts])
        .select_from(posts)
        .where(posts.c.post_id == post_id)
    )
    post = await database.fetch_one(query)
    post = dict(post.items())
    post["tag_list"] = []
    post["content"] = markdown2.markdown(post["content"])
    return post


async def fetch_posts(
    post_ids: List[int] = None, offset: int = 0, limit: int = 3
) -> List[Mapping]:
    query = (
        select([posts])
        .select_from(posts)
    )
    if post_ids:
        query = query.where(posts.c.post_id.in_(post_ids))
    else:
        query = query.limit(limit).offset(offset)
    fetched_posts = []
    for row in await database.fetch_all(query):
        post = dict(row.items())
        post["tag_list"] = []
        fetched_posts.append(post)
    return fetched_posts


async def fetch_posts_by_tag(
    tag_id: int, offset: int = 0, limit: int = 5
) -> List[Mapping]:
    query = (
        select([post_tags.c.post_id])
        .select_from(post_tags)
        .where(post_tags.c.tag_id == tag_id)
        .limit(limit)
        .offset(offset)
    )
    post_ids = [item["post_id"] for item in await database.fetch_all(query)]
    return await fetch_posts(post_ids) if post_ids else []


async def fetch_most_popular_tag_id() -> int:
    query = (
        select([post_tags.c.tag_id, func.count(post_tags.c.post_id).label("n_posts")])
        .select_from(post_tags)
        .group_by(post_tags.c.tag_id)
        .order_by(desc("n_posts"))
        .limit(1)
    )
    return await database.fetch_val(query=query)


async def fetch_tag(tag_id: int = None) -> Optional[Mapping]:
    tag_id = tag_id or await fetch_most_popular_tag_id()
    query = (
        select([tags])
        .select_from(tags)
        .where(tags.c.tag_id == tag_id)
    )
    tag = await database.fetch_one(query)
    tag = dict(tag.items())
    tag["post_list"] = []
    return tag


async def fetch_tags(offset: int = 0, limit: int = 5) -> List[Mapping]:
    query = (
        select([tags])
        .select_from(tags)
        .limit(limit)
        .offset(offset)
    )
    fetched_tags = []
    for row in await database.fetch_all(query):
        tag = dict(row.items())
        tag["post_list"] = []
        fetched_tags.append(tag)
    return fetched_tags
