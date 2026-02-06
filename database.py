# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Database module for session persistence using SQLite.
Provides robust session storage with retry logic and error handling.
"""

import sqlite3
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

# Database configuration
DB_PATH = Path("survey_sessions.db")
DB_TIMEOUT = 30.0  # SQLite timeout in seconds
MAX_RETRIES = 3
RETRY_DELAY = 0.5  # Initial retry delay in seconds


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


class SessionDatabase:
    """
    SQLite database manager for survey session persistence.
    Handles session storage, retrieval, and updates with retry logic.
    """
    
    def __init__(self, db_path: Path = DB_PATH):
        """
        Initialize the database connection and create tables if needed.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_database()
    
    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create sessions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        user_id TEXT NOT NULL PRIMARY KEY,
                        current_step TEXT NOT NULL,
                        answers TEXT NOT NULL,
                        step_history TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_audio_mode INTEGER DEFAULT 0,
                        session_data TEXT
                    )
                """)
                
                # Create session_history table for audit trail
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        step TEXT,
                        answer TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES sessions(user_id)
                    )
                """)
                
                # Create indexes for better query performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_updated_at 
                    ON sessions(updated_at)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_history_user_id 
                    ON session_history(user_id, timestamp)
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    @contextmanager
    def _get_connection(self):
        """
        Get a database connection with retry logic.
        Uses context manager for automatic connection cleanup.
        """
        retries = 0
        last_error = None
        
        while retries < MAX_RETRIES:
            try:
                conn = sqlite3.connect(
                    str(self.db_path),
                    timeout=DB_TIMEOUT,
                    check_same_thread=False  # Allow multi-threaded access
                )
                conn.row_factory = sqlite3.Row  # Enable dict-like access
                try:
                    yield conn
                    conn.commit()
                    return
                except Exception as e:
                    conn.rollback()
                    raise
                finally:
                    conn.close()
            except sqlite3.OperationalError as e:
                last_error = e
                retries += 1
                if retries < MAX_RETRIES:
                    wait_time = RETRY_DELAY * (2 ** (retries - 1))  # Exponential backoff
                    logger.warning(
                        f"Database operation failed (attempt {retries}/{MAX_RETRIES}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database operation failed after {MAX_RETRIES} attempts: {e}")
                    raise DatabaseError(f"Database connection failed after retries: {e}")
            except Exception as e:
                logger.error(f"Unexpected database error: {e}")
                raise DatabaseError(f"Database operation failed: {e}")
        
        raise DatabaseError(f"Database connection failed: {last_error}")
    
    def save_session(
        self,
        user_id: str,
        current_step: str,
        answers: Dict[str, Any],
        step_history: list,
        is_audio_mode: bool = False,
        session_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save or update a session in the database.
        
        Args:
            user_id: Unique identifier for the user/session
            current_step: Current step ID (e.g., "S1", "S2")
            answers: Dictionary of step_id -> answer mappings
            step_history: List of step IDs in order
            is_audio_mode: Whether the session is in audio mode
            session_data: Optional additional session data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Serialize complex data structures
                answers_json = json.dumps(answers, ensure_ascii=False)
                history_json = json.dumps(step_history, ensure_ascii=False)
                session_data_json = json.dumps(session_data or {}, ensure_ascii=False)
                
                # Use INSERT OR REPLACE for upsert operation
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions 
                    (user_id, current_step, answers, step_history, updated_at, 
                     is_audio_mode, session_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    current_step,
                    answers_json,
                    history_json,
                    datetime.utcnow().isoformat(),
                    int(is_audio_mode),
                    session_data_json
                ))
                
                logger.debug(f"Session saved for user {user_id} at step {current_step}")
                return True
        except Exception as e:
            logger.error(f"Failed to save session for user {user_id}: {e}")
            return False
    
    def load_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a session from the database.
        
        Args:
            user_id: Unique identifier for the user/session
            
        Returns:
            Dictionary with session data or None if not found
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT current_step, answers, step_history, is_audio_mode, session_data
                    FROM sessions
                    WHERE user_id = ?
                """, (user_id,))
                
                row = cursor.fetchone()
                if row is None:
                    logger.debug(f"No session found for user {user_id}")
                    return None
                
                # Deserialize JSON data
                session = {
                    "current_step": row["current_step"],
                    "answers": json.loads(row["answers"]),
                    "step_history": json.loads(row["step_history"]),
                    "is_audio_mode": bool(row["is_audio_mode"]),
                    "session_data": json.loads(row["session_data"]) if row["session_data"] else {}
                }
                
                logger.debug(f"Session loaded for user {user_id} at step {session['current_step']}")
                return session
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse session data for user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load session for user {user_id}: {e}")
            return None
    
    def update_session_state(
        self,
        user_id: str,
        current_step: Optional[str] = None,
        answers: Optional[Dict[str, Any]] = None,
        step_history: Optional[list] = None
    ) -> bool:
        """
        Update specific fields of a session without replacing the entire session.
        
        Args:
            user_id: Unique identifier for the user/session
            current_step: Optional new current step
            answers: Optional updated answers dictionary
            step_history: Optional updated step history
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing session first
            existing = self.load_session(user_id)
            if existing is None:
                logger.warning(f"Cannot update non-existent session for user {user_id}")
                return False
            
            # Merge updates
            new_step = current_step if current_step is not None else existing["current_step"]
            new_answers = answers if answers is not None else existing["answers"]
            new_history = step_history if step_history is not None else existing["step_history"]
            
            return self.save_session(
                user_id=user_id,
                current_step=new_step,
                answers=new_answers,
                step_history=new_history,
                is_audio_mode=existing.get("is_audio_mode", False),
                session_data=existing.get("session_data", {})
            )
        except Exception as e:
            logger.error(f"Failed to update session for user {user_id}: {e}")
            return False
    
    def add_history_entry(
        self,
        user_id: str,
        action: str,
        step: Optional[str] = None,
        answer: Optional[Any] = None
    ) -> bool:
        """
        Add an entry to the session history audit trail.
        
        Args:
            user_id: Unique identifier for the user/session
            action: Action type (e.g., "answer_saved", "step_changed", "back_navigation")
            step: Optional step ID
            answer: Optional answer value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO session_history (user_id, action, step, answer)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id,
                    action,
                    step,
                    json.dumps(answer) if answer is not None else None
                ))
                logger.debug(f"History entry added for user {user_id}: {action}")
                return True
        except Exception as e:
            logger.error(f"Failed to add history entry for user {user_id}: {e}")
            return False
    
    def get_session_history(self, user_id: str, limit: int = 100) -> list:
        """
        Get session history entries for a user.
        
        Args:
            user_id: Unique identifier for the user/session
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT action, step, answer, timestamp
                    FROM session_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit))
                
                rows = cursor.fetchall()
                return [
                    {
                        "action": row["action"],
                        "step": row["step"],
                        "answer": json.loads(row["answer"]) if row["answer"] else None,
                        "timestamp": row["timestamp"]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get session history for user {user_id}: {e}")
            return []
    
    def delete_session(self, user_id: str) -> bool:
        """
        Delete a session and its history from the database.
        
        Args:
            user_id: Unique identifier for the user/session
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                # Delete history first (foreign key constraint)
                cursor.execute("DELETE FROM session_history WHERE user_id = ?", (user_id,))
                # Delete session
                cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
                logger.info(f"Session deleted for user {user_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete session for user {user_id}: {e}")
            return False
    
    def list_sessions(self, limit: int = 100) -> list:
        """
        List all active sessions.
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of session summaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_id, current_step, updated_at, is_audio_mode
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [
                    {
                        "user_id": row["user_id"],
                        "current_step": row["current_step"],
                        "updated_at": row["updated_at"],
                        "is_audio_mode": bool(row["is_audio_mode"])
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []


# Global database instance
_db_instance: Optional[SessionDatabase] = None


def get_database() -> SessionDatabase:
    """
    Get or create the global database instance.
    Implements singleton pattern for database access.
    
    Returns:
        SessionDatabase instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = SessionDatabase()
    return _db_instance
