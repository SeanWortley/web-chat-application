import sqlite3
from threading import local
from pathlib import Path

"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION PLS AND THANKS

Arguments have a specified type to prevent bad DB interactions.
"""

class Database:
    """SQLite-backed local storage for client chat history."""
    

    def __init__(self, username):
        """
        Creates a user-scoped local database and initializes tables.

        Args:
            username (str): Logged-in username used to name the DB file.
        """
        runtime_db_dir = Path(__file__).resolve().parents[2] / "runtime" / "db"
        runtime_db_dir.mkdir(parents=True, exist_ok=True)
        self.DB_PATH = str(runtime_db_dir / f"{username}.db")
        self.local = local()
        self.initialise()

    def initialise(self):
        """Creates required chat tables if they do not already exist."""
        connection = self.get_connection()
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS private_chats (
                chat_id     TEXT    NOT NULL,
                PRIMARY KEY (chat_id)
            );
            CREATE TABLE IF NOT EXISTS group_chats (
                chat_id     TEXT    NOT NULL,
                PRIMARY KEY (chat_id)
            );
            CREATE TABLE IF NOT EXISTS private_messages (
                msg_id      TEXT    NOT NULL,
                chat_id     TEXT    NOT NULL,
                from_user   TEXT    NOT NULL,
                msg_text    TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                PRIMARY KEY (msg_id),
                FOREIGN KEY (chat_id) REFERENCES private_chats(chat_id)
            );
            CREATE TABLE IF NOT EXISTS group_messages (
                msg_id      TEXT    NOT NULL,
                chat_id     TEXT    NOT NULL,
                from_user   TEXT    NOT NULL,
                msg_text    TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                PRIMARY KEY (msg_id),
                FOREIGN KEY (chat_id) REFERENCES group_chats(chat_id)
            );           
        """)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

    def get_connection(self):
        """Returns a thread-local SQLite connection configured for row access."""
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(self.DB_PATH)
            self.local.connection.row_factory = sqlite3.Row
            self.local.connection.execute("PRAGMA foreign_keys = ON")
        return self.local.connection
    
    def store_private_message(self, message, incoming = True):
        """
        Persists a private message and ensures its chat record exists.

        Args:
            message (dict): Message envelope containing payload data.
            incoming (bool): True for inbound messages, False for outbound.

        Returns:
            bool: True if write succeeded, otherwise False.
        """
        data = message.get("data")
        msg_id = data.get("msg_id")
        if incoming:
            chat_id = data.get("from")
        else: 
            chat_id = data.get("chat_id")
        from_user = data.get("from")
        msg_text = data.get("payload")
        timestamp = data.get("timestamp")

        try:
            self.get_connection().execute(
                "INSERT OR IGNORE INTO private_chats (chat_id) VALUES (?)",
                (chat_id,)
            )
            self.get_connection().commit()
            self.get_connection().execute(
                "INSERT INTO private_messages (msg_id, chat_id, from_user, msg_text, timestamp) VALUES (?, ?, ?, ?, ?)",
                (msg_id, chat_id, from_user, msg_text, timestamp)
            )
            self.get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False
    
    def store_group_message(self, message, incoming = True):
        """
        Persists a group message and ensures its group chat record exists.

        Args:
            message (dict): Message envelope containing payload data.
            incoming (bool): Included for API symmetry with private messages.

        Returns:
            bool: True if write succeeded, otherwise False.
        """
        data = message.get("data")
        msg_id = data.get("msg_id")
        chat_id = data.get("chat_id")
        from_user = data.get("from")
        msg_text = data.get("payload")
        timestamp = data.get("timestamp")

        try:
            self.get_connection().execute(
                "INSERT OR IGNORE INTO group_chats (chat_id) VALUES (?)",
                (chat_id,)
            )
            self.get_connection().commit()
            self.get_connection().execute(
                "INSERT INTO group_messages (msg_id, chat_id, from_user, msg_text, timestamp) VALUES (?, ?, ?, ?, ?)",
                (msg_id, chat_id, from_user, msg_text, timestamp)
            )
            self.get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    # THIS IS FOR INTERFACE IMPLEMENTATION
    def get_chat_history(self, chat_id, chat_type):
        """
        Retrieves ordered message history for a private or group chat.

        Args:
            chat_id (str): Username (private) or group name (group).
            chat_type (str): Either "private" or "group".

        Returns:
            list[dict]: Chronologically ordered message rows.
        """
        if chat_type == "private":
            command = """
                SELECT * FROM private_messages
                WHERE chat_id = ?
                ORDER BY CAST(timestamp AS REAL) ASC, msg_id ASC
            """
        elif chat_type == "group":
            command = """
                SELECT * FROM group_messages
                WHERE chat_id = ?
                ORDER BY CAST(timestamp AS REAL) ASC, msg_id ASC
            """
        else:
            return []

        chat_history = self.get_connection().execute(command, (chat_id,)).fetchall()
        return [dict(row) for row in chat_history]

    def delete_private_chat_logs(self, user_id):
        """
        Deletes all locally stored messages for a private chat.

        Args:
            user_id (str): Username of the private chat peer.
        """
        self.get_connection().execute(
            "DELETE FROM private_messages WHERE chat_id = ?", (user_id,)
        )
        self.get_connection().commit()
        self.get_connection().execute(
            "DELETE FROM private_chats WHERE chat_id = ?", (user_id,)
        )
        self.get_connection().commit()
        

    def delete_group_chat_logs(self, group_name):
        """
        Deletes all locally stored messages for a group chat.

        Args:
            group_name (str): Name of the group chat.
        """
        self.get_connection().execute(
            "DELETE FROM group_messages WHERE chat_id = ?", (group_name,)
        )
        self.get_connection().commit()
        self.get_connection().execute(
            "DELETE FROM group_chats WHERE chat_id = ?", (group_name,)
        )
        self.get_connection().commit()
        