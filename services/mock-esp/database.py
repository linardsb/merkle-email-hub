"""SQLite database manager for mock ESP server."""

import json
import os
from pathlib import Path

import aiosqlite

DB_PATH = os.environ.get("MOCK_ESP_DB_PATH", "/app/data/mock_esp.db")


class DatabaseManager:
    """Async SQLite database manager."""

    def __init__(self, db_path: str = DB_PATH) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def _get_db(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
        return self._db

    async def init_tables(self) -> None:
        """Create all ESP tables if they don't exist."""
        db = await self._get_db()
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS braze_content_blocks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sfmc_assets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                category_id INTEGER DEFAULT 0,
                customer_key TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS adobe_deliveries (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                label TEXT DEFAULT '',
                folder_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS taxi_templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                syntax_version TEXT DEFAULT '2',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        await db.commit()

    async def seed_from_json(self, table: str, data_path: str) -> None:
        """Load seed data into a table if it's empty."""
        db = await self._get_db()
        cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        row = await cursor.fetchone()
        if row and row[0] > 0:
            return

        path = Path(data_path)
        if not path.exists():
            return

        data: list[dict] = json.loads(path.read_text())
        if not data:
            return

        columns = list(data[0].keys())
        # Serialize list/dict fields to JSON strings
        for record in data:
            for col in columns:
                if isinstance(record[col], (list, dict)):
                    record[col] = json.dumps(record[col])

        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"  # noqa: S608

        for record in data:
            values = [record[col] for col in columns]
            await db.execute(sql, values)

        await db.commit()

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        db = await self._get_db()
        return await db.execute(sql, params)

    async def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        db = await self._get_db()
        cursor = await db.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        db = await self._get_db()
        cursor = await db.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def commit(self) -> None:
        if self._db:
            await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
