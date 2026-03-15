import sqlite3
from threading import local
from pathlib import Path


class Database:
    """SQLite-backed persistence layer for server user, group, and offline message data."""

    def __init__(self):
        """Creates the server database file and initializes required tables."""
        runtime_db_dir = Path(__file__).resolve().parents[2] / "runtime" / "db"
        runtime_db_dir.mkdir(parents=True, exist_ok=True)
        self.DB_PATH = str(runtime_db_dir / "server.db")
        self.local = local()
        self.initialise()

    def initialise(self):
        """Creates server-side tables for users, groups, memberships, and offline messages."""
        connection = self.get_connection()
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
                chat_type   TEXT    NOT NULL,
                group_id    TEXT,
                msg_text    TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                PRIMARY KEY (msg_id, chat_id),
                FOREIGN KEY (sender) REFERENCES users(username)
            );
        """)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.commit()

    def get_connection(self):
        """Returns a thread-local SQLite connection configured with row objects."""
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(self.DB_PATH)
            self.local.connection.row_factory = sqlite3.Row
            self.local.connection.execute("PRAGMA foreign_keys = ON")
        return self.local.connection

    def get_user(self, username):
        """
        Fetches a user row by username.

        Args:
            username (str): Username to look up.

        Returns:
            sqlite3.Row | None: Matching user row if found.
        """
        return self.get_connection().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

    def create_user(self, username, hashed_password):
        """
        Creates a new user account.

        Args:
            username (str): Username for the account.
            hashed_password (str): Password hash to store.

        Returns:
            bool: True if insert succeeded, otherwise False.
        """
        try:
            self.get_connection().execute(
                "INSERT INTO users (username, hashed_password) VALUES (?, ?)",
                (username, hashed_password)
            )
            self.get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_group(self, group_name):
        """
        Fetches a group row by name.

        Args:
            group_name (str): Group name to look up.

        Returns:
            sqlite3.Row | None: Matching group row if found.
        """
        return self.get_connection().execute(
            "SELECT * FROM chat_groups WHERE group_name = ?", (group_name,)
        ).fetchone()

    def get_group_members(self, group_name):
        """
        Returns all members in a group.

        Args:
            group_name (str): Name of the group.

        Returns:
            list[sqlite3.Row]: Rows containing usernames.
        """
        return self.get_connection().execute(
            "SELECT username FROM group_members WHERE group_name = ?", (group_name,)
        ).fetchall()

    def create_group(self, group_name, owner):
        """
        Creates a group and adds the owner as its first member.

        Args:
            group_name (str): New group name.
            owner (str): Username of the group owner.

        Returns:
            bool: True if creation succeeded, otherwise False.
        """
        try:
            self.get_connection().execute("PRAGMA defer_foreign_keys = ON")
            self.get_connection().execute(
                "INSERT INTO chat_groups (group_name, owner) VALUES (?, ?)",
                (group_name, owner)
            )

            self.get_connection().execute(
                "INSERT INTO group_members (group_name, username) VALUES (?, ?)",
                (group_name, owner)
            )

            self.get_connection().commit()
            return True

        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def is_group_member(self, group_name, username):
        """
        Checks whether a user belongs to a group.

        Args:
            group_name (str): Group name.
            username (str): Username to check.

        Returns:
            bool: True if the user is a member.
        """
        return self.get_connection().execute(
            "SELECT 1 FROM group_members WHERE group_name = ? AND username = ?",
            (group_name, username)
        ).fetchone() is not None

    def add_group_member(self, group_name, username):
        """
        Adds a user to an existing group.

        Args:
            group_name (str): Group name.
            username (str): User to add.

        Returns:
            bool: True if insert succeeded, otherwise False.
        """
        try:
            self.get_connection().execute(
                "INSERT INTO group_members (group_name, username) VALUES (?, ?)",
                (group_name, username)
            )
            self.get_connection().commit()
            return True
        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_user_groups(self, username):
        """
        Returns the groups a user belongs to.

        Args:
            username (str): Username to look up.

        Returns:
            list[sqlite3.Row]: Rows containing group names.
        """
        result = self.get_connection().execute(
            "SELECT group_name FROM group_members WHERE username = ?",
            (username,)
        )
        return result.fetchall()

    def store_offline_message(self, msg_id, sender, chat_id, chat_type, group_id=None, msg_text="", timestamp=""):
        """
        Stores a message for later delivery when recipients are offline.

        Args:
            msg_id (str): Message identifier.
            sender (str): Sender username.
            chat_id (str): Recipient username or group name.
            chat_type (str): Either "private" or "group".
            group_id (str | None): Group key used for grouping unsent batches.
            msg_text (str): Message content.
            timestamp (str): Message timestamp.

        Returns:
            bool: True if insert succeeded, otherwise False.
        """
        try:
            self.get_connection().execute(
                "INSERT INTO offline_messages (msg_id, sender, chat_id, chat_type, group_id, msg_text, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (msg_id, sender, chat_id, chat_type, group_id, msg_text, timestamp)
            )

            self.get_connection().commit()
            return True

        except sqlite3.IntegrityError as e:
            print(f"DB error: {e}")
            return False

    def get_offline_messages(self, username):
        """
        Retrieves offline messages deliverable to a given user.

        Args:
            username (str): Username requesting unsent messages.

        Returns:
            list[sqlite3.Row]: Offline message rows in timestamp order.
        """
        return self.get_connection().execute("""
            SELECT om.* FROM offline_messages om
            WHERE om.chat_id = ?
            OR (om.chat_type = 'group' AND EXISTS (
                SELECT 1 FROM group_members gm
                WHERE gm.group_name = om.chat_id
                AND gm.username = ?
            ))
            ORDER BY om.timestamp ASC
            """, (username, username)).fetchall()

    def delete_offline_messages(self, username):
        """
        Deletes delivered offline messages for a user-recipient chat_id.

        Args:
            username (str): Recipient username.
        """
        self.get_connection().execute(
            "DELETE FROM offline_messages WHERE chat_id = ?", (username,)
        )

        self.get_connection().commit()
