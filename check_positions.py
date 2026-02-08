import sqlite3
conn = sqlite3.connect('/data/trades.db')

cursor = conn.execute('''
    SELECT symbol, instruction, SUM(filled_quantity) as total_qty
    FROM trades
    GROUP BY symbol, instruction
    ORDER BY symbol
''')

positions = {}
for symbol, instruction, qty in cursor.fetchall():
    if symbol not in positions:
        positions[symbol] = {'bought': 0, 'sold': 0}
    
    if 'BUY' in instruction.upper():
        positions[symbol]['bought'] += qty
    elif 'SELL' in instruction.upper():
        positions[symbol]['sold'] += qty

print('Symbol     | Bought | Sold | Remaining')
print('-' * 45)
total_remaining = 0
for symbol, pos in sorted(positions.items()):
    remaining = pos['bought'] - pos['sold']
    if remaining != 0:
        print(f"{symbol:10} | {pos['bought']:6.0f} | {pos['sold']:4.0f} | {remaining:9.0f}")
        total_remaining += remaining

print('-' * 45)
print(f'Total open positions: {total_remaining:.0f}')
conn.close()
