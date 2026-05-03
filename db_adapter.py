import json
import sqlite3
from pathlib import Path
from threading import RLock
from datetime import datetime, date


class SQLiteHabitStore:
    def __init__(self, db_path="data/atomic_habits.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        self._init_schema()

    def _now_iso(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_schema(self):
        with self.lock:
            cur = self.conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS water_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    logged_at TEXT NOT NULL,
                    amount_ml INTEGER NOT NULL,
                    daily_goal_ml INTEGER,
                    source TEXT DEFAULT 'manual'
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    task_text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    deleted_at TEXT
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    snapshot_date TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_water_logs_user_logged_at
                ON water_logs(user_id, logged_at)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_created_at
                ON tasks(user_id, created_at)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user_status
                ON tasks(user_id, status)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_settings_snapshots_user_date
                ON settings_snapshots(user_id, snapshot_date)
            """)

            self.conn.commit()

    def add_water_log(self, amount_ml, user_id=1, daily_goal_ml=None, logged_at=None, source="manual"):
        logged_at = logged_at or self._now_iso()
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO water_logs (user_id, logged_at, amount_ml, daily_goal_ml, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, logged_at, int(amount_ml), daily_goal_ml, source),
            )
            self.conn.commit()

    def get_water_logs(self, user_id=1, start_date=None, end_date=None):
        query = """
            SELECT id, user_id, logged_at, amount_ml, daily_goal_ml, source
            FROM water_logs
            WHERE user_id = ?
        """
        params = [user_id]

        if start_date:
            query += " AND date(logged_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(logged_at) <= date(?)"
            params.append(end_date)

        query += " ORDER BY logged_at DESC"

        with self.lock:
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_water_total(self, user_id=1, start_date=None, end_date=None):
        query = """
            SELECT COALESCE(SUM(amount_ml), 0) AS total_ml
            FROM water_logs
            WHERE user_id = ?
        """
        params = [user_id]

        if start_date:
            query += " AND date(logged_at) >= date(?)"
            params.append(start_date)
        if end_date:
            query += " AND date(logged_at) <= date(?)"
            params.append(end_date)

        with self.lock:
            cur = self.conn.execute(query, params)
            row = cur.fetchone()
            return int(row["total_ml"] or 0)

    def add_task(self, task_text, user_id=1, created_at=None):
        created_at = created_at or self._now_iso()
        with self.lock:
            cur = self.conn.execute(
                """
                INSERT INTO tasks (user_id, task_text, status, created_at)
                VALUES (?, ?, 'open', ?)
                """,
                (user_id, task_text.strip(), created_at),
            )
            self.conn.commit()
            task_id = cur.lastrowid
            return self.get_task_by_id(task_id)

    def get_task_by_id(self, task_id):
        with self.lock:
            cur = self.conn.execute(
                """
                SELECT id, user_id, task_text, status, created_at, completed_at, deleted_at
                FROM tasks
                WHERE id = ?
                """,
                (task_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def get_tasks(self, user_id=1, status=None, include_deleted=False, created_start=None, created_end=None):
        query = """
            SELECT id, user_id, task_text, status, created_at, completed_at, deleted_at
            FROM tasks
            WHERE user_id = ?
        """
        params = [user_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        if not include_deleted:
            query += " AND deleted_at IS NULL"

        if created_start:
            query += " AND date(created_at) >= date(?)"
            params.append(created_start)

        if created_end:
            query += " AND date(created_at) <= date(?)"
            params.append(created_end)

        query += " ORDER BY created_at DESC, id DESC"

        with self.lock:
            cur = self.conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_open_tasks_for_today(self, user_id=1):
        today = date.today().isoformat()
        return self.get_tasks(user_id=user_id, status="open", include_deleted=False, created_start=today, created_end=today)

    def toggle_task(self, task_id):
        task = self.get_task_by_id(task_id)
        if not task or task["deleted_at"] is not None:
            return None

        new_status = "completed" if task["status"] != "completed" else "open"
        completed_at = self._now_iso() if new_status == "completed" else None

        with self.lock:
            self.conn.execute(
                """
                UPDATE tasks
                SET status = ?, completed_at = ?
                WHERE id = ?
                """,
                (new_status, completed_at, task_id),
            )
            self.conn.commit()

        return self.get_task_by_id(task_id)

    def delete_task(self, task_id):
        deleted_at = self._now_iso()
        with self.lock:
            self.conn.execute(
                """
                UPDATE tasks
                SET status = 'deleted', deleted_at = ?
                WHERE id = ?
                """,
                (deleted_at, task_id),
            )
            self.conn.commit()
        return self.get_task_by_id(task_id)

    def snapshot_settings(self, user_id=1, snapshot_date=None, settings=None):
        snapshot_date = snapshot_date or date.today().isoformat()
        settings = settings or {}
        payload = json.dumps(settings, ensure_ascii=False)

        with self.lock:
            self.conn.execute(
                """
                INSERT INTO settings_snapshots (user_id, snapshot_date, settings_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, snapshot_date, payload, self._now_iso()),
            )
            self.conn.commit()

    def get_settings_snapshots(self, user_id=1, start_date=None, end_date=None):
        query = """
            SELECT id, user_id, snapshot_date, settings_json, created_at
            FROM settings_snapshots
            WHERE user_id = ?
        """
        params = [user_id]

        if start_date:
            query += " AND date(snapshot_date) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(snapshot_date) <= date(?)"
            params.append(end_date)

        query += " ORDER BY snapshot_date DESC, id DESC"

        with self.lock:
            cur = self.conn.execute(query, params)
            rows = cur.fetchall()

        results = []
        for row in rows:
            item = dict(row)
            try:
                item["settings_json"] = json.loads(item["settings_json"])
            except Exception:
                pass
            results.append(item)

        return results
