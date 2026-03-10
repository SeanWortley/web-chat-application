import sqlite3
from threading import local

"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION PLS AND THANKS

Arguments have a specified type to prevent bad DB interactions.
"""

class Database:
    DB_PATH = "client/client.db"

    def __init__(self):
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
                msg_text    TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                PRIMARY KEY (msg_id),
                FOREIGN KEY (chat_id) REFERENCES private_chats(chat_id)
            );
            CREATE TABLE IF NOT EXISTS group_messages (
            msg_id          TEXT    NOT NULL,
                chat_id     TEXT    NOT NULL,
                from_user   TEXT    NOT NULL,
                msg_text    TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL
                PRIMARY KEY (msg_id),
                FOREIGN KEY (chat_id) REFERENCES group_chats(chat_id)
            );           
        """)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

    def get_connection(self):
        if not hasattr(self.local, "connection"):
            self.local.connection - sqlite3.connect(self.DB_PATH)
            self.local.connection.row_factory = sqlite3.Row
            self.local.connection.execute("PRAGMA foreign_keys = ON")
        return self.local.connection
    
    