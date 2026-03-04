import sqlite3
from threading import local

"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION

Arguments have a specified type to prevent bad DB interactions.
"""

class Database:
    DB_PATH = "chat_server.db"

    def __init__(self):
        self._local = local()
        self._initialise()
    
    def _initialise(self):
        connection = self._get_connection()

        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username        TEXT    PRIMARY KEY,
            hashed_password TEXT    NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chat_groups (
            group_name  TEXT    PRIMARY KEY,
            owner       TEXT    NOT NULL,
            FOREIGN KEY (owner) REFERENCES users(username)
        );
        CREATE TABLE IF NOT EXISTS group_members (
            group_name  TEXT    NOT NULL,
            username    TEXT    NOT NULL,
            PRIMARY KEY (group_name, username),
            FOREIGN KEY (group_name) REFERENCES chat_groups(group_name),
            FOREIGN KEY (username)   REFERENCES users(username)
        );
        CREATE TABLE IF NOT EXISTS offline_messages (
            msg_id      TEXT    NOT NULL,
            sender      TEXT    NOT NULL,
            chat_id     TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL,
            PRIMARY KEY (msg_id, chat_id),
            FOREIGN KEY (sender) REFERENCES users(username)
        );
        CREATE TABLE IF NOT EXISTS pending_recipients (
            msg_id      TEXT    NOT NULL,
            chat_id     TEXT    NOT NULL,
            recipient   TEXT    NOT NULL
        );
        """)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

    def _get_connection(self):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(self.DB_PATH)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection

    def get_user(self, username: str):
        return self._get_connection().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    def create_user(self, username: str, hashed_password: str):
        try:
            self._get_connection().execute(
                "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
                (username, hashed_password)
            )
            self._get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_group(self, group_name: str):
        return self._get_connection().execute(
            "SELECT * FROM chat_groups WHERE group_name = ?", (group_name,)
        ).fetchone()

    def create_group(self, group_name: str, owner: str):
        try:
            self._get_connection().execute("PRAGMA defer_foreign_keys = ON")
            self._get_connection().execute(
                "INSERT INTO chat_groups (group_name, owner) VALUES (?, ?)",
                (group_name, owner)
            )
            self._get_connection().execute(
                "INSERT INTO group_members (group_name, username) VALUES (?, ?)",
                (group_name, owner)
            )
            self._get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_group_members(self, group_name: str):
        return self._get_connection().execute(
            "SELECT username FROM group_members WHERE group_name = ?", (group_name,)
        ).fetchall()

    def add_group_member(self, group_name: str, username: str):
        try:
            self._get_connection().execute(
                "INSERT INTO group_members (group_name, username) VALUES (?, ?)",
                (group_name, username)
            )
            self._get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def store_offline_message(self, msg_id: str, sender: str, chat_id: str, content: str, timestamp: str):
        try:
            self._get_connection().execute(
                "INSERT INTO offline_messages (msg_id, sender, chat_id, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (msg_id, sender, chat_id, content, timestamp)
            )
            self._get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_offline_messages(self, username: str):
        return self._get_connection().execute(
            "SELECT * FROM offline_messages WHERE chat_id = ?", (username,)
        ).fetchall()

    def validate_credentials(self, username: str, hashed_password: str):
        user = self.get_user(username)
        return (user is not None) and (user["hashed_password"] == hashed_password)