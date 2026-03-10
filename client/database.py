import sqlite3
from threading import local

"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION PLS AND THANKS

Arguments have a specified type to prevent bad DB interactions.
"""

class Database:
    

    def __init__(self, username):
        self.DB_PATH = f"client/{username}.db"
        self.local = local()
        self.initialise()

    def initialise(self):
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
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(self.DB_PATH)
            self.local.connection.row_factory = sqlite3.Row
            self.local.connection.execute("PRAGMA foreign_keys = ON")
        return self.local.connection
    
    def store_private_message(self, message, incoming = True):
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

    def get_chat_history(self, chat_id):
        pass