from typing import List
import sqlite3





def get_unposted_trade_ids(conn: sqlite3.Connection) -> List[str]:
    """
    Returns all trade_ids that are marked as unposted in trade_state.
    """
    rows = conn.execute(
        """
        SELECT s.trade_id
        FROM trade_state s
        WHERE s.posted = 0
        ORDER BY s.updated_at ASC;
        """
    ).fetchall()

    return [r[0] for r in rows]
