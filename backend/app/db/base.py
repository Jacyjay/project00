from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so they are registered with Base.metadata before create_all is called.
# These imports must come after Base is defined to avoid circular imports.
from app.models.social import Like, Comment  # noqa: E402, F401
