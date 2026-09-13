from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM metadata anchor; database structure is versioned in Alembic."""
    pass
