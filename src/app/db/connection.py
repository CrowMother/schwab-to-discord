import sqlite3

def get_connection(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def close_connection(conn: sqlite3.Connection) -> None:
    conn.close()

