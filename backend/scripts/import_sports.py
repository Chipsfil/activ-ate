"""Import frontend/assets/data/sports.json into PostgreSQL.

Run from the repository root after applying schema.sql:
    python backend/scripts/import_sports.py
"""
import json
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).parents[1]))
from config import DATABASE_URL

source = Path(__file__).parents[2] / "frontend/assets/data/sports.json"
with source.open(encoding="utf-8") as handle:
    items = json.load(handle)["items"]

with psycopg.connect(DATABASE_URL) as db:
    with db.cursor() as cur:
        for item in items:
            cur.execute(
                """INSERT INTO sports(id,name,category,met,aliases)
                   VALUES(%s,%s,%s,%s,%s)
                   ON CONFLICT(id) DO UPDATE SET name=EXCLUDED.name,
                     category=EXCLUDED.category, met=EXCLUDED.met,
                     aliases=EXCLUDED.aliases""",
                (
                    item["id"],
                    item["name"],
                    item.get("category"),
                    item.get("met", 6),
                    item.get("aliases", []),
                ),
            )
    db.commit()
print(f"Imported {len(items)} sports.")
