import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'instance', 'concursos.db'))

print(f"Opening DB: {DB_PATH}")
if not os.path.exists(DB_PATH):
    print("ERROR: DB file not found")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Show columns in concursos table
cur.execute("PRAGMA table_info(concursos);")
cols = [row[1] for row in cur.fetchall()]
print("Concursos columns:", cols)

# Count rows
cur.execute("SELECT COUNT(*) AS c FROM concursos;")
count = cur.fetchone()[0]
print("Concursos count:", count)

# Show up to 10 rows basic info if any
if count:
    fields = [f for f in [
        'id','tipo','categoria','departamento_id','fecha_apertura_inscripcion','cierre_inscripcion','vencimiento'
    ] if f in cols]
    cur.execute(f"SELECT {', '.join(fields)} FROM concursos ORDER BY id LIMIT 10;")
    rows = cur.fetchall()
    for r in rows:
        values = {k: r[k] for k in fields}
        print(values)

conn.close()
