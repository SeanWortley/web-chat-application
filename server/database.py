import sqlite3
from threading import local
"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION
"""

class Database:
    DB_PATH = "chat_server.db"

    def __init__(self):
        self._local = local()
        self._initialise()
    
    def _initialise(self):
        connection = self._get_connection()
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users ()

        """)

    def _get_connection(self):
        if hasattr(self._local, "connection"):
            pass
        else:
            self._local.connection = sqlite3.connect(self.DB_PATH)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    