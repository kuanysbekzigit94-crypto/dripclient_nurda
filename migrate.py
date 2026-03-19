"""
Migration: adds all new columns that may be missing from an existing database.db
Safe to run multiple times — uses ALTER TABLE only when the column doesn't exist.
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "database.db")

if not os.path.exists(db_path):
    print("database.db not found — will be auto-created on bot start.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    # List of (column_name, column_definition)
    new_columns = [
        ("phone_number",   "TEXT"),
        ("language",       "TEXT DEFAULT 'kk'"),
        ("is_vip",         "INTEGER NOT NULL DEFAULT 0"),
        ("referred_by",    "INTEGER"),
        ("referral_count", "INTEGER NOT NULL DEFAULT 0"),
        ("referral_bonus", "REAL NOT NULL DEFAULT 0.0"),
    ]

    added = []
    for col_name, col_def in new_columns:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
            added.append(col_name)

    # products table checks
    cursor.execute("PRAGMA table_info(products)")
    existing_product_cols = {row[1] for row in cursor.fetchall()}
    if "vip_price" not in existing_product_cols:
        cursor.execute("ALTER TABLE products ADD COLUMN vip_price REAL")
        added.append("products.vip_price")

    # vip_codes table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vip_codes'")
    if not cursor.fetchone():
        cursor.execute("""
            CREATE TABLE vip_codes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT UNIQUE NOT NULL,
                is_used    INTEGER NOT NULL DEFAULT 0,
                used_by    INTEGER REFERENCES users(tg_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        added.append("vip_codes (table)")

    conn.commit()
    conn.close()

    if added:
        print(f"✅ Migration complete. Added: {', '.join(added)}")
    else:
        print("ℹ️  Database is already up to date — nothing to do.")
