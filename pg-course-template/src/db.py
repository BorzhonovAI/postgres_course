from typing import Final

import psycopg
import os
from psycopg import Connection

DB_NAME: Final[str] = os.environ["DB_NAME"]
DB_USER: Final[str] = os.environ["DB_USER"]
DB_PASSWORD: Final[str] = os.environ["DB_PASSWORD"]
DB_HOST: Final[str] = os.environ["DB_HOST"]
DB_PORT: Final[int] = int(os.environ["DB_PORT"])

_CONN: Connection | None = None


def connect(role: str | None = None, password: str | None = None) -> None:
    global _CONN

    if role is None and password is None:
        role = DB_USER
        password = DB_PASSWORD

    _CONN = psycopg.connect(
        dbname=DB_NAME,
        user=role,
        password=password,
        host=DB_HOST,
        port=DB_PORT,
        autocommit=True,
    )


def close() -> None:
    if _CONN is not None:
        _CONN.close()


def get_conn() -> Connection:
    if _CONN is None:
        raise RuntimeError("Database connection has not been established")
    return _CONN
