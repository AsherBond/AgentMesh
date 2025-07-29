import sqlite3
from typing import Generator, Optional
from contextlib import contextmanager
import os
from pathlib import Path


class DatabaseManager:
    """Database manager for SQLite with extensible design"""
    
    def __init__(self, db_path: str = "agentmesh.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database and create tables if they don't exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tasks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    task_status TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    task_content TEXT NOT NULL,
                    submit_time TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(task_status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_submit_time ON tasks(submit_time)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(task_name)
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable row factory for named access
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_query(self, query: str, params: tuple = ()) -> list:
        """Execute a query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an update query and return affected rows"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount


# Global database manager instance
db_manager = DatabaseManager() 