def insert_trade(conn, trade):
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO trades (symbol, price) VALUES (?, ?)",
        (trade.symbol, trade.price),
    )
    conn.commit()
