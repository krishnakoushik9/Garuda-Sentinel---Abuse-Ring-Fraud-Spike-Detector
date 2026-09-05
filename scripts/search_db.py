import sqlite3

conn = sqlite3.connect("database/ecosystem.db")
cursor = conn.cursor()

# Get all tables
tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

for table in tables:
    try:
        # Get text columns
        columns = [r[1] for r in cursor.execute(f"PRAGMA table_info({table})").fetchall() if r[2] in ('TEXT', 'VARCHAR')]
        for col in columns:
            query = f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE '%John Doe%'"
            count = cursor.execute(query).fetchone()[0]
            if count > 0:
                print(f"Found in table '{table}', column '{col}': {count} occurrences")
                # print a sample
                sample = cursor.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE '%John Doe%' LIMIT 1").fetchone()[0]
                print("Sample:", sample[:200])
    except Exception as e:
        print(f"Error checking table {table}: {e}")

conn.close()
