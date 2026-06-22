from dataclasses import dataclass
from psycopg.rows import class_row
from db import get_conn


@dataclass
class User:
    id: int
    username: str
    role: str


def find_user_by_login_and_pass(username: str, password: str) -> User | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(User)) as cur:
        cur.execute(
            """SELECT id, username, role FROM auth.users "
            "WHERE username = %s AND password = crypt(%s, password)""",
            (username, password)
        )
        user: User | None = cur.fetchone()

    return user


def get_user(_id: int) -> User | None:
    conn = get_conn()
    with conn.cursor(row_factory=class_row(User)) as cur:
        cur.execute(
            "SELECT id, username, role FROM auth.users WHERE id = %s",
            (_id,)
        )
        user: User | None = cur.fetchone()

    return user
