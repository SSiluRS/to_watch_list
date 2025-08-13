import os
import mysql.connector
from mysql.connector import pooling

DB_CFG = dict(
    host=os.getenv("MYSQL_HOST", "db"),
    user=os.getenv("MYSQL_USER", "to_watch_list"),
    password=os.getenv("MYSQL_PASSWORD", "pass"),
    database=os.getenv("MYSQL_DATABASE", "to_watch_list"),
    charset="utf8mb4",
)

cnxpool = pooling.MySQLConnectionPool(pool_name="twl_pool", pool_size=5, **DB_CFG)

def get_conn():
    return cnxpool.get_connection()
