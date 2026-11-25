"""SQLAlchemy models.

Import every model module here so that `Base.metadata` is complete for Alembic.
"""

from app.db.base import Base

__all__ = ["Base"]
