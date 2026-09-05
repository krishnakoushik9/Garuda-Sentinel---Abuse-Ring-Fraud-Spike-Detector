import sqlite3
try:
    import redis
except Exception:
    redis = None
try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None
from typing import Generator
from src.config import SQLITE_DB_PATH, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, REDIS_HOST, REDIS_PORT

def get_db():
    """Dependency for SQLite connection."""
    conn = sqlite3.connect(SQLITE_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_neo4j():
    """Dependency for Neo4j driver."""
    if GraphDatabase is None:
        yield None
        return
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        # Check connectivity
        driver.verify_connectivity()
        yield driver
    except Exception:
        yield None
    finally:
        driver.close()

def get_redis():
    """Dependency for Redis connection."""
    if redis is None:
        yield None
        return
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=0.5)
    try:
        r.ping()
        yield r
    except Exception:
        yield None
