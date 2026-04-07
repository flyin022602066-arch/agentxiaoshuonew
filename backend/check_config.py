import sqlite3
import json

conn = sqlite3.connect('data/novels.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print('Tables:', tables)

for table in tables:
    if 'config' in table.lower() or 'provider' in table.lower() or 'llm' in table.lower() or 'project' in table.lower():
        cur.execute(f'SELECT * FROM {table}')
        rows = [dict(r) for r in cur.fetchall()]
        print(f'\n{table}:')
        print(json.dumps(rows, ensure_ascii=False, indent=2))

conn.close()
