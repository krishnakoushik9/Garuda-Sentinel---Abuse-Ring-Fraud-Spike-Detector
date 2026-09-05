import json
import logging
import sqlite3
from typing import Optional
from src.config import SQLITE_DB_PATH
from src.api.deps import get_redis, get_neo4j

logger = logging.getLogger("watchlist_manager")

class WatchlistManager:
    """
    Redis-backed high-speed regulatory watchlist.
    Guarantees O(1) watchlist evaluation for live transaction monitoring.
    Syncs with Neo4j and SQLite database states.
    """
    WATCHLIST_KEY = "watchlist:accounts"
    GOVT_FLAG_KEY = "watchlist:govt_flagged"

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self.redis_failed = False
        self.fallback_store = {}  # In-memory failsafe cache if Redis is offline

    def add_to_watchlist(self, account_id: str, source: str, reason: str, severity: str):
        logger.info(f"Adding account {account_id} to watchlist. Source: {source}, Severity: {severity}")
        
        # 1. Update SQLite local cache
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            conn.execute(
                "UPDATE accounts SET status = 'GOVT_FLAGGED', risk_profile = ? WHERE account_id = ?",
                (severity, account_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to update SQLite watchlist account {account_id} ({e})")

        # 2. Update Redis Watchlist
        metadata = {
            "account_id": account_id,
            "source": source,
            "reason": reason,
            "severity": severity,
            "added_at": float(sqlite3.connect(SQLITE_DB_PATH).execute("SELECT strftime('%s', 'now')").fetchone()[0]) if sqlite3 else 0.0
        }
        
        redis_online = False
        if self.redis is None and not self.redis_failed:
            try:
                self.redis = next(get_redis())
                if self.redis is None:
                    self.redis_failed = True
            except Exception:
                self.redis_failed = True

        if self.redis:
            try:
                # Store structured JSON metadata in Redis Hash
                self.redis.hset(self.WATCHLIST_KEY, account_id, json.dumps(metadata))
                # Add to set for quick key matching
                self.redis.sadd(self.GOVT_FLAG_KEY, account_id)
                redis_online = True
            except Exception as ex:
                logger.warning(f"Redis watchlist storage failed ({ex}). Falling back to memory.")

        if not redis_online:
            self.fallback_store[account_id] = metadata

        # 3. Update Neo4j Node Properties
        self._sync_node_to_neo4j(account_id, source)

    def is_on_watchlist(self, account_id: str) -> Optional[dict]:
        """Provides O(1) evaluation on live transactions."""
        redis_online = False
        if self.redis is None and not getattr(self, 'redis_failed', False):
            try:
                self.redis = next(get_redis())
                if self.redis is None:
                    self.redis_failed = True
            except Exception:
                self.redis_failed = True

        if self.redis:
            try:
                res = self.redis.hget(self.WATCHLIST_KEY, account_id)
                if res:
                    if isinstance(res, bytes):
                        res = res.decode('utf-8')
                    return json.loads(res)
                redis_online = True
            except Exception:
                pass

        if not redis_online:
            # Fallback to local memory cache
            if account_id in self.fallback_store:
                return self.fallback_store[account_id]
                
            # Fallback to SQLite query
            try:
                conn = sqlite3.connect(SQLITE_DB_PATH)
                row = conn.execute(
                    "SELECT account_id, risk_profile, status FROM accounts WHERE account_id = ?",
                    (account_id,)
                ).fetchone()
                conn.close()
                if row and row[2] == "GOVT_FLAGGED":
                    return {
                        "account_id": account_id,
                        "source": "SQLITE_FALLBACK",
                        "reason": "SQLite Watchlist Match",
                        "severity": row[1] or "HIGH",
                        "added_at": 0.0
                    }
            except Exception:
                pass
                
        return None

    def get_watchlist_stats(self) -> dict:
        """Returns aggregate metrics from the watchlist."""
        total = 0
        breakdown = {"CRILC": 0, "I4C": 0, "NPCI": 0, "INTERNAL": 0, "OTHER": 0}
        
        # Pull from Redis if online
        redis_online = False
        if self.redis is None and not getattr(self, 'redis_failed', False):
            try:
                self.redis = next(get_redis())
                if self.redis is None:
                    self.redis_failed = True
            except Exception:
                self.redis_failed = True

        if self.redis:
            try:
                data = self.redis.hgetall(self.WATCHLIST_KEY)
                for aid, val in data.items():
                    total += 1
                    if isinstance(val, bytes):
                        val = val.decode('utf-8')
                    meta = json.loads(val)
                    src = meta.get("source", "OTHER").upper()
                    if "CRILC" in src: breakdown["CRILC"] += 1
                    elif "I4C" in src or "NCRP" in src: breakdown["I4C"] += 1
                    elif "NPCI" in src: breakdown["NPCI"] += 1
                    elif "INTERNAL" in src: breakdown["INTERNAL"] += 1
                    else: breakdown["OTHER"] += 1
                redis_online = True
            except Exception:
                pass

        if not redis_online:
            # Aggregate from in-memory fallback + SQLite
            for aid, meta in self.fallback_store.items():
                total += 1
                src = meta.get("source", "OTHER").upper()
                if "CRILC" in src: breakdown["CRILC"] += 1
                elif "I4C" in src or "NCRP" in src: breakdown["I4C"] += 1
                elif "NPCI" in src: breakdown["NPCI"] += 1
                elif "INTERNAL" in src: breakdown["INTERNAL"] += 1
                else: breakdown["OTHER"] += 1
                
            try:
                conn = sqlite3.connect(SQLITE_DB_PATH)
                rows = conn.execute("SELECT count(*) FROM accounts WHERE status = 'GOVT_FLAGGED'").fetchone()
                total = max(total, rows[0])
                conn.close()
            except Exception:
                pass

        return {
            "total_flagged": total,
            "source_breakdown": breakdown
        }

    def sync_to_neo4j(self):
        """Batch synchronizes watchlist properties into Neo4j graph nodes."""
        logger.info("Batch synchronizing watchlist accounts to Neo4j graph nodes...")
        try:
            driver = next(get_neo4j())
            if not driver:
                return
                
            # Fetch all from SQLite
            conn = sqlite3.connect(SQLITE_DB_PATH)
            rows = conn.execute("SELECT account_id FROM accounts WHERE status = 'GOVT_FLAGGED'").fetchall()
            conn.close()
            
            with driver.session() as session:
                for r in rows:
                    session.run(
                        "MATCH (a:Account {id: $aid}) SET a.govt_flagged = true, a.status = 'GOVT_FLAGGED'",
                        aid=r[0]
                    )
            logger.info(f"Successfully synced {len(rows)} nodes to Neo4j.")
        except Exception as e:
            logger.warning(f"Neo4j batch sync failed ({e})")

    def _sync_node_to_neo4j(self, account_id: str, source: str):
        try:
            driver = next(get_neo4j())
            if driver:
                with driver.session() as session:
                    session.run(
                        "MATCH (a:Account {id: $aid}) SET a.govt_flagged = true, a.watchlist_source = $src, a.status = 'GOVT_FLAGGED'",
                        aid=account_id,
                        src=source
                    )
        except Exception:
            pass
