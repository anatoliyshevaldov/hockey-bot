import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "hockey.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('training', 'game')),
                title TEXT NOT NULL,
                description TEXT,
                event_date DATE NOT NULL,
                event_time TEXT NOT NULL,
                location TEXT,
                max_players INTEGER NOT NULL DEFAULT 20,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'cancelled')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'waitlist', 'cancelled')),
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, user_id),
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ── Teams ──────────────────────────────────────────────────────────────

async def create_team(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO teams (name) VALUES (?)", (name,))
        await db.commit()
        return cursor.lastrowid

async def get_teams() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM teams ORDER BY name")
        return await cursor.fetchall()

async def delete_team(team_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        await db.commit()

# ── Events ─────────────────────────────────────────────────────────────

async def create_event(team_id, type_, title, description, event_date, event_time, location, max_players) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO events (team_id, type, title, description, event_date, event_time, location, max_players)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (team_id, type_, title, description, event_date, event_time, location, max_players))
        await db.commit()
        return cursor.lastrowid

async def get_upcoming_events(team_id: int = None) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if team_id:
            cursor = await db.execute("""
                SELECT e.*, t.name as team_name,
                    (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'confirmed') as confirmed_count,
                    (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'waitlist') as waitlist_count
                FROM events e JOIN teams t ON e.team_id = t.id
                WHERE e.team_id = ? AND e.status = 'active' AND e.event_date >= DATE('now')
                ORDER BY e.event_date, e.event_time
            """, (team_id,))
        else:
            cursor = await db.execute("""
                SELECT e.*, t.name as team_name,
                    (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'confirmed') as confirmed_count,
                    (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'waitlist') as waitlist_count
                FROM events e JOIN teams t ON e.team_id = t.id
                WHERE e.status = 'active' AND e.event_date >= DATE('now')
                ORDER BY e.event_date, e.event_time
            """)
        return await cursor.fetchall()

async def get_event(event_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT e.*, t.name as team_name,
                (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'confirmed') as confirmed_count,
                (SELECT COUNT(*) FROM registrations r WHERE r.event_id = e.id AND r.status = 'waitlist') as waitlist_count
            FROM events e JOIN teams t ON e.team_id = t.id
            WHERE e.id = ?
        """, (event_id,))
        return await cursor.fetchone()

async def cancel_event(event_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE events SET status = 'cancelled' WHERE id = ?", (event_id,))
        await db.commit()

async def get_events_for_reminder(days_ahead: int = 1) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT e.*, t.name as team_name
            FROM events e JOIN teams t ON e.team_id = t.id
            WHERE e.status = 'active' AND e.event_date = DATE('now', '+' || ? || ' days')
        """, (days_ahead,))
        return await cursor.fetchall()

# ── Registrations ──────────────────────────────────────────────────────

async def get_user_registration(event_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM registrations WHERE event_id = ? AND user_id = ? AND status != 'cancelled'
        """, (event_id, user_id))
        return await cursor.fetchone()

async def register_user(event_id: int, user_id: int, username: str, full_name: str) -> str:
    """Returns: 'confirmed', 'waitlist', or 'already_registered'"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        existing = await db.execute(
            "SELECT status FROM registrations WHERE event_id = ? AND user_id = ?",
            (event_id, user_id)
        )
        existing = await existing.fetchone()
        if existing and existing["status"] != "cancelled":
            return "already_registered"

        event = await db.execute(
            "SELECT max_players FROM events WHERE id = ?", (event_id,)
        )
        event = await event.fetchone()

        count = await db.execute(
            "SELECT COUNT(*) as cnt FROM registrations WHERE event_id = ? AND status = 'confirmed'",
            (event_id,)
        )
        count = await count.fetchone()

        status = "confirmed" if count["cnt"] < event["max_players"] else "waitlist"

        if existing:
            await db.execute(
                "UPDATE registrations SET status = ?, username = ?, full_name = ?, registered_at = CURRENT_TIMESTAMP WHERE event_id = ? AND user_id = ?",
                (status, username, full_name, event_id, user_id)
            )
        else:
            await db.execute(
                "INSERT INTO registrations (event_id, user_id, username, full_name, status) VALUES (?, ?, ?, ?, ?)",
                (event_id, user_id, username, full_name, status)
            )
        await db.commit()
        return status

async def cancel_registration(event_id: int, user_id: int) -> str | None:
    """Cancel registration and promote from waitlist. Returns promoted user_id or None."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        reg = await db.execute(
            "SELECT status FROM registrations WHERE event_id = ? AND user_id = ? AND status != 'cancelled'",
            (event_id, user_id)
        )
        reg = await reg.fetchone()
        if not reg:
            return None

        was_confirmed = reg["status"] == "confirmed"
        await db.execute(
            "UPDATE registrations SET status = 'cancelled' WHERE event_id = ? AND user_id = ?",
            (event_id, user_id)
        )

        promoted_user_id = None
        if was_confirmed:
            next_waitlist = await db.execute("""
                SELECT user_id FROM registrations
                WHERE event_id = ? AND status = 'waitlist'
                ORDER BY registered_at ASC LIMIT 1
            """, (event_id,))
            next_waitlist = await next_waitlist.fetchone()
            if next_waitlist:
                promoted_user_id = next_waitlist["user_id"]
                await db.execute(
                    "UPDATE registrations SET status = 'confirmed' WHERE event_id = ? AND user_id = ?",
                    (event_id, promoted_user_id)
                )

        await db.commit()
        return promoted_user_id

async def get_event_registrations(event_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        confirmed = await db.execute(
            "SELECT * FROM registrations WHERE event_id = ? AND status = 'confirmed' ORDER BY registered_at",
            (event_id,)
        )
        waitlist = await db.execute(
            "SELECT * FROM registrations WHERE event_id = ? AND status = 'waitlist' ORDER BY registered_at",
            (event_id,)
        )
        return {
            "confirmed": await confirmed.fetchall(),
            "waitlist": await waitlist.fetchall()
        }

async def get_confirmed_user_ids(event_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM registrations WHERE event_id = ? AND status = 'confirmed'",
            (event_id,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

async def get_all_registered_user_ids(event_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM registrations WHERE event_id = ? AND status != 'cancelled'",
            (event_id,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]

# ── Admins ─────────────────────────────────────────────────────────────

async def is_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        return await cursor.fetchone() is not None

async def add_admin(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        await db.commit()

async def get_admins() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM admins")
        return await cursor.fetchall()
