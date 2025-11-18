"""
SQLite database wrapper for BuildRunner

Provides simple interface for database operations.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite database wrapper"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file (default: .buildrunner/data.db)
        """
        if db_path is None:
            db_path = Path(".buildrunner/data.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self._init_connection()
        logger.info(f"Database initialized at {self.db_path}")

    def _init_connection(self):
        """Initialize database connection with proper settings"""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        self.cursor = self.conn.cursor()

    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        try:
            yield self.cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute SQL statement

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Cursor with results
        """
        try:
            cursor = self.conn.execute(sql, params)
            self.conn.commit()
            return cursor
        except sqlite3.Error as e:
            logger.error(f"SQL error: {e}")
            logger.error(f"Query: {sql}")
            logger.error(f"Params: {params}")
            raise

    def query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute SELECT query and return results

        Args:
            sql: SELECT statement
            params: Query parameters

        Returns:
            List of rows as dictionaries
        """
        cursor = self.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute SELECT query and return first result

        Args:
            sql: SELECT statement
            params: Query parameters

        Returns:
            First row as dictionary or None
        """
        cursor = self.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert row into table

        Args:
            table: Table name
            data: Column values as dictionary

        Returns:
            ID of inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        cursor = self.execute(sql, tuple(data.values()))
        return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, params: tuple = ()) -> int:
        """
        Update rows in table

        Args:
            table: Table name
            data: Column values to update
            where: WHERE clause (without WHERE keyword)
            params: Parameters for WHERE clause

        Returns:
            Number of rows updated
        """
        set_clause = ", ".join(f"{col} = ?" for col in data.keys())
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"

        all_params = tuple(data.values()) + params
        cursor = self.execute(sql, all_params)
        return cursor.rowcount

    def delete(self, table: str, where: str, params: tuple = ()) -> int:
        """
        Delete rows from table

        Args:
            table: Table name
            where: WHERE clause (without WHERE keyword)
            params: Parameters for WHERE clause

        Returns:
            Number of rows deleted
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(sql, params)
        return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        """
        Check if table exists

        Args:
            table_name: Name of table

        Returns:
            True if table exists
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.query_one(sql, (table_name,))
        return result is not None

    def run_migration(self, migration_sql: str):
        """
        Run database migration

        Args:
            migration_sql: SQL statements to execute
        """
        with self.transaction():
            # Split on semicolons and execute each statement
            statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
            for statement in statements:
                self.cursor.execute(statement)

        logger.info(f"Migration executed successfully")

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
