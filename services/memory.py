"""
Deterministic Memory Manager service based on SQLite.

Implements Least Privilege context retrieval as defined in Agent Decision Policy v0.1:
- get_coach_context: Climbing history, movement restrictions; NO nutrition/meal logs.
- get_nutritionist_context: Nutrition logs, dietary restrictions, weight trend, training load summary; NO raw climb logs.
- get_supervisor_context: High-level summaries, active goals, active restrictions; NO raw set-by-set or meal-by-meal data.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any, Dict, Generator, List, Optional


class MemoryManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:")
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        if self._shared_conn is not None:
            with self._shared_conn:
                yield self._shared_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            try:
                with conn:
                    yield conn
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    age INTEGER,
                    gender TEXT,
                    height_cm REAL,
                    weight_kg REAL,
                    experience_level TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS goals (
                    goal_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    target_grade TEXT,
                    deadline TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS restrictions (
                    restriction_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL, -- 'movement', 'dietary', 'medical'
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL, -- 'WARNING', 'RESTRICTION', 'CRITICAL_ESCALATION'
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS training_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    details TEXT, -- JSON string
                    rpe REAL,
                    duration_min INTEGER,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS nutrition_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    log_date TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    calories REAL,
                    protein_g REAL,
                    carbs_g REAL,
                    fat_g REAL,
                    is_complete INTEGER DEFAULT 1,
                    is_estimated INTEGER DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    domain TEXT NOT NULL, -- 'training', 'nutrition'
                    phase TEXT NOT NULL,
                    details TEXT, -- JSON string
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    status TEXT NOT NULL, -- 'CREATED', 'PENDING_REVIEW', 'ACCEPTED', etc.
                    current_state TEXT, -- JSON string
                    proposed_change TEXT, -- JSON string
                    reason TEXT,
                    evidence TEXT, -- JSON string
                    risk TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                );
                """
            )

    # -------------------------------------------------------------
    # Write / Seed operations
    # -------------------------------------------------------------
    def create_user(
        self,
        user_id: str,
        name: str,
        age: int,
        gender: str,
        height_cm: float,
        weight_kg: float,
        experience_level: str = "intermediate",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, name, age, gender, height_cm, weight_kg, experience_level, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, name, age, gender, height_cm, weight_kg, experience_level, now),
            )

    def add_goal(self, goal_id: str, user_id: str, title: str, target_grade: str, deadline: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO goals (goal_id, user_id, title, target_grade, deadline, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (goal_id, user_id, title, target_grade, deadline, now),
            )

    def add_restriction(
        self,
        restriction_id: str,
        user_id: str,
        category: str,
        description: str,
        severity: str = "RESTRICTION",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO restrictions (restriction_id, user_id, category, description, severity, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (restriction_id, user_id, category, description, severity, now),
            )

    def add_training_log(
        self,
        log_id: str,
        user_id: str,
        session_date: str,
        session_type: str,
        details: Dict[str, Any],
        rpe: float,
        duration_min: int,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO training_logs (log_id, user_id, session_date, session_type, details, rpe, duration_min, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, user_id, session_date, session_type, json.dumps(details), rpe, duration_min, now),
            )

    def add_nutrition_log(
        self,
        log_id: str,
        user_id: str,
        log_date: str,
        meal_type: str,
        description: str,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        is_complete: bool = True,
        is_estimated: bool = False,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO nutrition_logs (log_id, user_id, log_date, meal_type, description, calories, protein_g, carbs_g, fat_g, is_complete, is_estimated, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    user_id,
                    log_date,
                    meal_type,
                    description,
                    calories,
                    protein_g,
                    carbs_g,
                    fat_g,
                    1 if is_complete else 0,
                    1 if is_estimated else 0,
                    now,
                ),
            )

    # -------------------------------------------------------------
    # Least Privilege Context Retrieval
    # -------------------------------------------------------------
    def get_coach_context(self, user_id: str, limit_days: int = 14) -> Dict[str, Any]:
        """
        Retrieves context strictly allowed for Climbing Coach:
        - Basic profile (age, weight, height, experience).
        - Active goals.
        - Movement restrictions ONLY (no dietary/general medical).
        - Detailed training logs.
        - ABSOLUTELY NO NUTRITION/MEAL LOGS.
        """
        with self._get_connection() as conn:
            # User profile
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user:
                raise ValueError(f"User {user_id} not found")

            # Goals
            goals = [
                dict(row)
                for row in conn.execute(
                    "SELECT goal_id, title, target_grade, deadline FROM goals WHERE user_id = ? AND is_active = 1",
                    (user_id,),
                ).fetchall()
            ]

            # Movement restrictions only
            restrictions = [
                dict(row)
                for row in conn.execute(
                    "SELECT restriction_id, description, severity FROM restrictions WHERE user_id = ? AND is_active = 1 AND category = 'movement'",
                    (user_id,),
                ).fetchall()
            ]

            # Training logs
            t_logs = [
                {
                    "log_id": row["log_id"],
                    "session_date": row["session_date"],
                    "session_type": row["session_type"],
                    "details": json.loads(row["details"]) if row["details"] else {},
                    "rpe": row["rpe"],
                    "duration_min": row["duration_min"],
                }
                for row in conn.execute(
                    "SELECT * FROM training_logs WHERE user_id = ? ORDER BY session_date DESC LIMIT 20",
                    (user_id,),
                ).fetchall()
            ]

            return {
                "profile": {
                    "age": user["age"],
                    "gender": user["gender"],
                    "height_cm": user["height_cm"],
                    "weight_kg": user["weight_kg"],
                    "experience_level": user["experience_level"],
                },
                "goals": goals,
                "movement_restrictions": restrictions,
                "training_logs": t_logs,
            }

    def get_nutritionist_context(self, user_id: str, limit_days: int = 14) -> Dict[str, Any]:
        """
        Retrieves context strictly allowed for General Nutritionist:
        - Basic profile.
        - Active goals.
        - Dietary restrictions ONLY.
        - Detailed nutrition logs.
        - High-level training volume estimate (count of sessions, avg RPE) WITHOUT raw route/climbing logs.
        """
        with self._get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user:
                raise ValueError(f"User {user_id} not found")

            goals = [
                dict(row)
                for row in conn.execute(
                    "SELECT goal_id, title, deadline FROM goals WHERE user_id = ? AND is_active = 1",
                    (user_id,),
                ).fetchall()
            ]

            restrictions = [
                dict(row)
                for row in conn.execute(
                    "SELECT restriction_id, description, severity FROM restrictions WHERE user_id = ? AND is_active = 1 AND category = 'dietary'",
                    (user_id,),
                ).fetchall()
            ]

            n_logs = [
                {
                    "log_id": row["log_id"],
                    "log_date": row["log_date"],
                    "meal_type": row["meal_type"],
                    "description": row["description"],
                    "calories": row["calories"],
                    "protein_g": row["protein_g"],
                    "carbs_g": row["carbs_g"],
                    "fat_g": row["fat_g"],
                    "is_complete": bool(row["is_complete"]),
                    "is_estimated": bool(row["is_estimated"]),
                }
                for row in conn.execute(
                    "SELECT * FROM nutrition_logs WHERE user_id = ? ORDER BY log_date DESC LIMIT 30",
                    (user_id,),
                ).fetchall()
            ]

            # High-level training volume summary only (NO raw climb/hangboard logs)
            t_summary = conn.execute(
                """
                SELECT COUNT(*) as session_count, AVG(rpe) as avg_rpe, SUM(duration_min) as total_duration
                FROM training_logs WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            return {
                "profile": {
                    "age": user["age"],
                    "gender": user["gender"],
                    "height_cm": user["height_cm"],
                    "weight_kg": user["weight_kg"],
                },
                "goals": goals,
                "dietary_restrictions": restrictions,
                "nutrition_logs": n_logs,
                "training_load_summary": {
                    "session_count": t_summary["session_count"] if t_summary else 0,
                    "avg_rpe": round(t_summary["avg_rpe"], 1) if (t_summary and t_summary["avg_rpe"]) else 0.0,
                    "total_duration_min": t_summary["total_duration"] if (t_summary and t_summary["total_duration"]) else 0,
                },
            }

    def get_supervisor_context(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves high-level summary context for Supervisor:
        - Basic profile.
        - Active goals.
        - All active restrictions (movement and dietary).
        - Status of active plans and proposals.
        - NO raw sets/reps and NO raw individual meal logs.
        """
        with self._get_connection() as conn:
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user:
                raise ValueError(f"User {user_id} not found")

            goals = [
                dict(row)
                for row in conn.execute(
                    "SELECT goal_id, title, target_grade, deadline FROM goals WHERE user_id = ? AND is_active = 1",
                    (user_id,),
                ).fetchall()
            ]

            restrictions = [
                dict(row)
                for row in conn.execute(
                    "SELECT restriction_id, category, description, severity FROM restrictions WHERE user_id = ? AND is_active = 1",
                    (user_id,),
                ).fetchall()
            ]

            last_training = conn.execute(
                "SELECT session_date, session_type, rpe FROM training_logs WHERE user_id = ? ORDER BY session_date DESC LIMIT 1",
                (user_id,),
            ).fetchone()

            return {
                "profile": {
                    "user_id": user["user_id"],
                    "name": user["name"],
                    "age": user["age"],
                    "weight_kg": user["weight_kg"],
                    "experience_level": user["experience_level"],
                },
                "goals": goals,
                "active_restrictions": restrictions,
                "last_workout_summary": dict(last_training) if last_training else None,
            }
