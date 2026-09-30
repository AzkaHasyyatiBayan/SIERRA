import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class DatabaseManager:
    def __init__(self, db_path: str = "sierra.db"):
        self.db_path = db_path
        self._init_database()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Creates tables if they do not exist."""
        with self._connection() as conn:
            cursor = conn.cursor()

            # Sessions table for local session analytics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    safe_duration_seconds INTEGER DEFAULT 0,
                    warning_duration_seconds INTEGER DEFAULT 0,
                    danger_duration_seconds INTEGER DEFAULT 0,
                    posture_score REAL DEFAULT 100.0,
                    avg_neck_angle REAL DEFAULT 0.0,
                    avg_shoulder_angle REAL DEFAULT 0.0
                )
            """)

            # Calibration table for personalized baseline
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    neck_baseline_deg REAL DEFAULT 12.0,
                    shoulder_baseline_deg REAL DEFAULT 0.0,
                    calibrated_at TEXT
                )
            """)

            # System settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    max_dimming_opacity REAL DEFAULT 0.65,
                    dimming_color TEXT DEFAULT '#111827',
                    game_mode_enabled INTEGER DEFAULT 1,
                    sound_alert_enabled INTEGER DEFAULT 0
                )
            """)

            # Seed default settings if empty
            cursor.execute("SELECT id FROM settings WHERE id = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO settings (id, max_dimming_opacity, dimming_color, game_mode_enabled, sound_alert_enabled)
                    VALUES (1, 0.65, '#111827', 1, 0)
                """)

            # Seed default baseline if empty
            cursor.execute("SELECT id FROM calibration WHERE id = 1")
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO calibration (id, neck_baseline_deg, shoulder_baseline_deg, calibrated_at)
                    VALUES (1, 10.0, 0.0, ?)
                """, (datetime.now().isoformat(),))

            conn.commit()

    # --- Calibration Methods ---
    def get_calibration(self) -> Tuple[float, float]:
        """Returns (neck_baseline_deg, shoulder_baseline_deg)."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT neck_baseline_deg, shoulder_baseline_deg FROM calibration WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return float(row["neck_baseline_deg"]), float(row["shoulder_baseline_deg"])
            return 10.0, 0.0

    def save_calibration(self, neck_deg: float, shoulder_deg: float):
        """Saves new personalized baseline calibration."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO calibration (id, neck_baseline_deg, shoulder_baseline_deg, calibrated_at)
                VALUES (1, ?, ?, ?)
            """, (round(neck_deg, 2), round(shoulder_deg, 2), datetime.now().isoformat()))
            conn.commit()

    # --- Settings Methods ---
    def get_settings(self) -> Dict:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {"max_dimming_opacity": 0.65, "dimming_color": "#111827", "game_mode_enabled": 1}

    def update_settings(self, opacity: float, color: str, game_mode: bool):
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE settings
                SET max_dimming_opacity = ?, dimming_color = ?, game_mode_enabled = ?
                WHERE id = 1
            """, (opacity, color, 1 if game_mode else 0))
            conn.commit()

    # --- Session Analytics Methods ---
    def start_session(self) -> int:
        """Starts a new tracking session and returns session_id."""
        with self._connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO sessions (start_time, end_time, duration_seconds)
                VALUES (?, ?, 0)
            """, (now, now))
            conn.commit()
            return cursor.lastrowid

    def update_session(self, session_id: int, duration_sec: int,
                       safe_sec: int, warning_sec: int, danger_sec: int,
                       avg_neck: float, avg_shoulder: float):
        """Updates active session progress in real time."""
        total = max(1, safe_sec + warning_sec + danger_sec)
        score = max(0.0, min(100.0, ((safe_sec * 100.0) + (warning_sec * 50.0)) / total))
        now = datetime.now().isoformat()

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?,
                    duration_seconds = ?,
                    safe_duration_seconds = ?,
                    warning_duration_seconds = ?,
                    danger_duration_seconds = ?,
                    posture_score = ?,
                    avg_neck_angle = ?,
                    avg_shoulder_angle = ?
                WHERE id = ?
            """, (now, duration_sec, safe_sec, warning_sec, danger_sec,
                  round(score, 1), round(avg_neck, 1), round(avg_shoulder, 1), session_id))
            conn.commit()

    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Retrieves history of recent sessions for dashboard analytics."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sessions
                WHERE duration_seconds >= 5
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_aggregate_stats(self) -> Dict:
        """Returns cumulative statistics across all sessions."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(id) as total_sessions,
                    COALESCE(SUM(duration_seconds), 0) as total_duration,
                    COALESCE(SUM(safe_duration_seconds), 0) as total_safe,
                    COALESCE(SUM(warning_duration_seconds), 0) as total_warning,
                    COALESCE(SUM(danger_duration_seconds), 0) as total_danger,
                    COALESCE(AVG(posture_score), 100.0) as overall_avg_score
                FROM sessions
                WHERE duration_seconds >= 5
            """)
            row = cursor.fetchone()
            return dict(row) if row else {
                "total_sessions": 0, "total_duration": 0,
                "total_safe": 0, "total_warning": 0, "total_danger": 0,
                "overall_avg_score": 100.0
            }

    def delete_session(self, session_id: int):
        """Deletes a specific session from the history."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
