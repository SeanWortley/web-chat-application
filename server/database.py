import sqlite3
from threading import local
"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION

Arguements have aspecified type to prevent bad DB interactions.
"""

class Database:
    DB_PATH = "chat_server.db"

    def __init__(self):
        self._local = local()
        self._initialise()
    
    def _initialise(self): # Will not overwrite existing tables
        connection = self._get_connection()

        # Create users table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
        username        TEXT    PRIMARY KEY,
        hashed_password TEXT    NOT NULL
        );
        """)

        # Create groups table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS groups (
        group_name  TEXT    PRIMARY KEY,
        owner       TEXT    NOT NULL,
        FOREIGN KEY (owner) REFERENCES users(username)
        );
        """)

        # Create group_members table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS group_members (
        group_name  TEXT    NOT NULL,
        username    TEXT    NOT NULL,
        PRIMARY KEY (group_name, username),
        FOREIGN KEY (group_name)    REFERENCES groups(group_name),
        FOREIGN KEY (username)      REFERENCES users(username)
        );
        """)

        # Create offline_messages table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS offline_messages (
        msg_id      TEXT    NOT NULL,
        sender      TEXT    NOT NULL,
        chat_id     TEXT    NOT NULL,
        content     TEXT    NOT NULL,
        timestamp   TEXT    NOT NULL,
        PRIMARY KEY (msg_id, chat_id),
        FOREIGN KEY (sender) REFERENCES users(username)
        );
        """)

        # Create pending_recipients table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS pending_recipients (
        msg_id      TEXT    NOT NULL,
        chat_id     TEXT    NOT NULL,
        recipient   TEXT    NOT NULL  
        );
        """)
        connection.commit()

    def _get_connection(self):
        if hasattr(self._local, "connection"):
            pass
        else:
            self._local.connection = sqlite3.connect(self.DB_PATH)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    def create_user(self, username: str, hashed_password: str):
        try:
            self._get_connection().execute("INSERT INTO users (username, hashed_password) VALUES (?,?)", (username, hashed_password))
        
            self._get_connection().commit()
            return True
        except sqlite3.IntegrityError:
            return False
    
    def get_user(self, username: str):
        result = self._get_connection().execute("SELECT * FROM users WHERE username = ?", (username,))

        return result.fetchone()

    def validate_credentials(self, username: str, hashed_password: str):
        user = self.get_user(username)
        return (user is not None) and (user["hashed_password"] == hashed_password)

    