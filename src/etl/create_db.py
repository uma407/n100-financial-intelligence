import sqlite3

conn = sqlite3.connect("nifty100.db")

with open("db/schema.sql", "r", encoding="utf-8") as f:
    schema = f.read()

conn.executescript(schema)

print("Database created successfully!")

conn.close()