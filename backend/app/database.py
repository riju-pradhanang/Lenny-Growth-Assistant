from sqlalchemy import create_engine
from app.config import get_settings


def get_engine():
    return create_engine(get_settings().database_url, pool_pre_ping=True)
