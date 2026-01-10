# filename: utils/db_connection.py

import sqlite3
import pandas as pd
from utils.paths import DB_PATH

def get_db_connection(row_factory=None):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = row_factory
    return conn

