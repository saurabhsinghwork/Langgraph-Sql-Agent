"""Inspect tables and data distributions in MCA and GST databases.

Authoritative diagnostic script checking schema, sample values, and states.
"""

# [Library Import: sqlite3]: Embedded relational database engine
import sqlite3
# [Library Import: pathlib.Path]: File system path manipulation
from pathlib import Path

# [Project-Defined Variable: Path]: Project workspace root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# [Project-Defined Function: check_db]: Inspect table details
def check_db(db_path: Path):
    """Print table schemas, row counts, and sample values."""
    print("=" * 60)
    print(f"DATABASE: {db_path.name}")
    print("=" * 60)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    for (tbl,) in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info({tbl})")
        cols = [col[1] for col in cur.fetchall()]
        print(f"\nTable '{tbl}': {cnt} total rows")
        print(f"Columns ({len(cols)}): {cols}")

        # Check distinct states if state column exists
        if "state" in cols:
            cur.execute(f"SELECT DISTINCT state, COUNT(*) FROM {tbl} GROUP BY state ORDER BY state")
            states = cur.fetchall()
            print(f"All distinct states in {tbl} ({len(states)} states): {states}")

        # Show first row
        cur.execute(f"SELECT * FROM {tbl} LIMIT 1")
        sample = cur.fetchone()
        print(f"Sample row: {sample}")
    conn.close()

if __name__ == "__main__":
    check_db(PROJECT_ROOT / "data" / "mca.db")
    check_db(PROJECT_ROOT / "data" / "gst.db")
