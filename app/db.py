import os
import mysql.connector
from mysql.connector import pooling

# Конфигурация берётся из .env
DB_CFG = dict(
    host=os.getenv("MYSQL_HOST", ""),  # IP хоста, где MariaDB
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER", ""),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", ""),
    charset="utf8mb4",
)

# Пул соединений
cnxpool = pooling.MySQLConnectionPool(pool_name="twl_pool", pool_size=5, **DB_CFG)

def get_conn():
    """Получить соединение с БД из пула"""
    return cnxpool.get_connection()
