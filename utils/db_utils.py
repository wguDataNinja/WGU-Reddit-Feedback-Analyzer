# filename: utils/db_connection.py

import sqlite3
import pandas as pd
from utils.paths import DB_PATH

def get_db_connection(row_factory=None):
    conn = sqlite3.connect(DB_PATH)
    if row_factory:
        conn.row_factory = row_factory
    return conn

def load_posts_dataframe():
    db = get_db_connection()
    query = """
        SELECT p.post_id,
               p.title,
               p.selftext,
               p.permalink,
               p.created_utc   -- new field
        FROM posts p
    """
    df = pd.read_sql_query(query, db)
    db.close()
    return df