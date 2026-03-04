import sqlite3
from threading import local
from threading import Lock
"""
DO NOT ACCESS FUNCTIONS OR VARIABLES 
BEGINNING WITH '_' OUTSIDE OF THIS FUNCTION

Arguements have aspecified type to prevent bad DB interactions.
"""

class Database:
    DB_PATH = "chat_server.db"

    def __init__(self):
        self._lock = Lock()
        self._connection = sqlite3.connect(self.DB_PATH, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialise()
    
    def _initialise(self): # Will not overwrite existing tables
        connection = self._connection

        # Create users table
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS users (
        username        TEXT    PRIMARY KEY,
        hashed_password TEXT    NOT NULL
        );
        """)

        # Create chat_groups table (groups is protected apparently......)
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS chat_groups (
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
        FOREIGN KEY (group_name)    REFERENCES chat_groups(group_name),
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

        connection.execute("PRAGMA foreign_keys = ON")
        print(f"Foreign keys enabled: {connection.execute('PRAGMA foreign_keys').fetchone()[0]}")

    def _get_connection(self):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(self.DB_PATH, check_same_thread=False)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    def get_user(self, username):
        result = self._connection.execute("SELECT * FROM users WHERE username = ?", (username,))

        return result.fetchone()

    def create_user(self, username, hashed_password):
        try:
            with self._lock:
                self._connection.execute(
                    "INSERT INTO users (username, hashed_password) VALUES (?,?)", 
                    (username, hashed_password)
                )
                self._connection.commit()
                
                # Verify
                check = self._connection.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
                print(f"User verify: {dict(check) if check else 'NOT FOUND'}")
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False
    
    def get_group(self, group_name):
        result = self._connection.execute(
            "SELECT * FROM chat_groups WHERE group_name = ?", (group_name,)
        )
        return result.fetchone()

    def create_group(self, group_name, owner):
        try:
            with self._lock:
                print("Inserting into chat_groups...")
                self._connection.execute(
                    "INSERT INTO chat_groups (group_name, owner) VALUES (?, ?)", 
                    (group_name, owner)
                )
                print("Inserting into group_members...")
                self._connection.execute(
                    "INSERT INTO group_members (group_name, username) VALUES (?,?)",
                    (group_name, owner)
                )
                self._connection.commit()
                rows = self._connection.execute("SELECT * FROM chat_groups").fetchall()
                print(f"All groups after commit: {[dict(r) for r in rows]}")
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False
    

    def validate_credentials(self, username, hashed_password):
        user = self.get_user(username)
        return (user is not None) and (user["hashed_password"] == hashed_password)

    