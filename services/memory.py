"""
Deterministic Memory Manager service based on SQLite.

Implements Least Privilege context retrieval as defined in Agent Decision Policy v0.2:
- get_coach_context: Climbing history, movement restrictions, weight trend; NO nutrition/meal logs.
- get_nutritionist_context: Nutrition logs, dietary restrictions, weight/BF% trend, enriched training load summary (type, duration, RPE); Task-scoped access for injury restrictions.
- get_supervisor_context: High-level summaries, active goals, all active restrictions; NO raw set-by-set or meal-by-meal data.
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
                    category TEXT NOT NULL, -- 'movement', 'training', 'dietary', 'medical'
                    description TEXT NOT NULL,
                    severity TEXT NOT NULL, -- 'WARNING', 'RESTRICTION', 'CRITICAL_ESCALATION'
                    affected_area TEXT,
                    restricted_actions TEXT, -- JSON array of strings
                    status TEXT DEFAULT 'active', -- 'active', 'resolved', 'archived'
                    source TEXT DEFAULT 'user_reported', -- 'confirmed', 'user_reported', 'agent_detected'
                    verification_status TEXT DEFAULT 'unverified_medical',
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

                CREATE TABLE IF NOT EXISTS weight_logs (
                    log_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    log_date TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    body_fat_pct REAL,
                    measurement_method TEXT,
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
            # Add initial weight record
            conn.execute(
                """
                INSERT INTO weight_logs (log_id, user_id, log_date, weight_kg, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"w_{user_id}_{now}", user_id, now[:10], weight_kg, now),
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
        affected_area: Optional[str] = None,
        restricted_actions: Optional[List[str]] = None,
        status: str = "active",
        source: str = "user_reported",
        verification_status: str = "unverified_medical",
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        actions_json = json.dumps(restricted_actions or [])
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO restrictions (
                    restriction_id, user_id, category, description, severity,
                    affected_area, restricted_actions, status, source, verification_status, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    restriction_id,
                    user_id,
                    category,
                    description,
                    severity,
                    affected_area,
                    actions_json,
                    status,
                    source,
                    verification_status,
                    now,
                ),
            )

    def add_weight_log(
        self,
        log_id: str,
        user_id: str,
        log_date: str,
        weight_kg: float,
        body_fat_pct: Optional[float] = None,
        measurement_method: Optional[str] = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO weight_logs (log_id, user_id, log_date, weight_kg, body_fat_pct, measurement_method, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (log_id, user_id, log_date, weight_kg, body_fat_pct, measurement_method, now),
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
        - Weight trend (for power-to-weight analysis as permitted in Policy v0.2).
        - ABSOLUTELY NO NUTRITION/MEAL LOGS.
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
                {
                    "restriction_id": row["restriction_id"],
                    "description": row["description"],
                    "severity": row["severity"],
                    "affected_area": row["affected_area"],
                    "restricted_actions": json.loads(row["restricted_actions"]) if row["restricted_actions"] else [],
                    "status": row["status"],
                    "verification_status": row["verification_status"],
                }
                for row in conn.execute(
                    "SELECT * FROM restrictions WHERE user_id = ? AND is_active = 1 AND category IN ('movement', 'training')",
                    (user_id,),
                ).fetchall()
            ]

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

            weight_trend = [
                {"date": row["log_date"], "weight_kg": row["weight_kg"]}
                for row in conn.execute(
                    "SELECT log_date, weight_kg FROM weight_logs WHERE user_id = ? ORDER BY log_date DESC LIMIT 14",
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
                "weight_trend": weight_trend,
            }

    def get_nutritionist_context(
        self,
        user_id: str,
        limit_days: int = 14,
        granted_scopes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieves context strictly allowed for General Nutritionist:
        - Basic profile.
        - Active goals.
        - Dietary restrictions ONLY.
        - Detailed nutrition logs.
        - Enriched training load summary: count, total duration, avg RPE, and recent session overviews (session type, duration, RPE) WITHOUT raw climbing/bouldering move-by-move logs.
        - Weight and BF% trend with measurement method.
        - Task-scoped access: if granted_scopes contains 'active_injury_restrictions_summary' or 'relevant_injury_restrictions', includes injury restriction summary.
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

            dietary_restrictions = [
                {
                    "restriction_id": row["restriction_id"],
                    "description": row["description"],
                    "severity": row["severity"],
                    "status": row["status"],
                }
                for row in conn.execute(
                    "SELECT * FROM restrictions WHERE user_id = ? AND is_active = 1 AND category = 'dietary'",
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

            # Enriched training load summary (as required by Policy v0.2 Section 2)
            t_summary = conn.execute(
                """
                SELECT COUNT(*) as session_count, AVG(rpe) as avg_rpe, SUM(duration_min) as total_duration
                FROM training_logs WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

            recent_sessions = [
                {
                    "date": row["session_date"],
                    "session_type": row["session_type"],
                    "type": row["session_type"],
                    "duration_min": row["duration_min"],
                    "rpe": row["rpe"],
                }
                for row in conn.execute(
                    "SELECT session_date, session_type, duration_min, rpe FROM training_logs WHERE user_id = ? ORDER BY session_date DESC LIMIT 10",
                    (user_id,),
                ).fetchall()
            ]

            weight_body_composition = [
                {
                    "date": row["log_date"],
                    "weight_kg": row["weight_kg"],
                    "body_fat_pct": row["body_fat_pct"],
                    "measurement_method": row["measurement_method"],
                }
                for row in conn.execute(
                    "SELECT log_date, weight_kg, body_fat_pct, measurement_method FROM weight_logs WHERE user_id = ? ORDER BY log_date DESC LIMIT 30",
                    (user_id,),
                ).fetchall()
            ]

            result: Dict[str, Any] = {
                "profile": {
                    "age": user["age"],
                    "gender": user["gender"],
                    "height_cm": user["height_cm"],
                    "weight_kg": user["weight_kg"],
                },
                "goals": goals,
                "dietary_restrictions": dietary_restrictions,
                "nutrition_logs": n_logs,
                "weight_body_composition_trend": weight_body_composition,
                "training_load_summary": {
                    "session_count": t_summary["session_count"] if t_summary else 0,
                    "avg_rpe": round(t_summary["avg_rpe"], 1) if (t_summary and t_summary["avg_rpe"]) else 0.0,
                    "total_duration_min": t_summary["total_duration"] if (t_summary and t_summary["total_duration"]) else 0,
                    "recent_sessions_overview": recent_sessions,
                },
            }

            # Task-scoped access check (Section 3 of Agent Decision Policy v0.2)
            scopes = granted_scopes or []
            if "active_injury_restrictions_summary" in scopes or "relevant_injury_restrictions" in scopes:
                injuries = [
                    {
                        "restriction_id": row["restriction_id"],
                        "affected_area": row["affected_area"],
                        "description": row["description"],
                        "severity": row["severity"],
                        "restricted_actions": json.loads(row["restricted_actions"]) if row["restricted_actions"] else [],
                    }
                    for row in conn.execute(
                        "SELECT * FROM restrictions WHERE user_id = ? AND is_active = 1 AND category IN ('movement', 'training')",
                        (user_id,),
                    ).fetchall()
                ]
                result["task_scoped_injury_restrictions"] = injuries

            return result

    def get_supervisor_context(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves high-level summary context for Supervisor:
        - Basic profile.
        - Active goals.
        - All active restrictions (movement, training, dietary).
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
                {
                    "restriction_id": row["restriction_id"],
                    "category": row["category"],
                    "description": row["description"],
                    "severity": row["severity"],
                    "affected_area": row["affected_area"],
                    "restricted_actions": json.loads(row["restricted_actions"]) if row["restricted_actions"] else [],
                    "status": row["status"],
                    "verification_status": row["verification_status"],
                }
                for row in conn.execute(
                    "SELECT * FROM restrictions WHERE user_id = ? AND is_active = 1",
                    (user_id,),
                ).fetchall()
            ]

            last_training = conn.execute(
                "SELECT session_date, session_type, duration_min, rpe FROM training_logs WHERE user_id = ? ORDER BY session_date DESC LIMIT 1",
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
