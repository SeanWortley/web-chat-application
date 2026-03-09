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
        pass