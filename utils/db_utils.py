# filename: utils/db_utils.py

import pandas as pd
from utils.db_connection import get_db_connection

def load_posts_dataframe():
    db = get_db_connection()
    query = """
        SELECT p.post_id, p.title, p.selftext, p.permalink, p.created_utc
        FROM posts p
    """
    df = pd.read_sql_query(query, db)
    db.close()
    return df
