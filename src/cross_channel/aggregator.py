import sqlite3
import logging
import time
from typing import Optional, Dict, Any, List
from src.config import SQLITE_DB_PATH
from src.api.deps import get_redis

logger = logging.getLogger("cross_channel_aggregator")

class CrossChannelAggregator:
    """
    Maintains rolling cross-channel statistics per account.
    Detects channel hopping anomalies and computes multi-channel velocity metrics.
    """
    def __init__(self, db_path=None):
        self.db_path = db_path or SQLITE_DB_PATH
        self.redis_client = None
        self.redis_failed = False

    def get_channel_profile(self, account_id: str, window_days: int = 30) -> dict:
        """
        Queries SQLite transactions grouped by channel to construct a multi-channel usage profile.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        profile = {}
        dominant_channel = "None"
        max_amount = -1.0
        channels_used = set()

        try:
            # Group active usage in window_days
            cursor.execute(
                """
                SELECT channel, 
                       COUNT(*) as count, 
                       SUM(amount) as total_amount, 
                       AVG(amount) as avg_amount,
                       CAST(strftime('%H', timestamp) as INTEGER) as peak_hour
                FROM transactions
                WHERE sender_account = ?
                  AND timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY channel
                """,
                (account_id, window_days)
            )
            rows = cursor.fetchall()
            
            # Fallback to ALL historical transactions if none in last 30 days
            if not rows:
                cursor.execute(
                    """
                    SELECT channel, 
                           COUNT(*) as count, 
                           SUM(amount) as total_amount, 
                           AVG(amount) as avg_amount,
                           CAST(strftime('%H', timestamp) as INTEGER) as peak_hour
                    FROM transactions
                    WHERE sender_account = ?
                    GROUP BY channel
                    """,
                    (account_id,)
                )
                rows = cursor.fetchall()
            
            for r in rows:
                ch = r["channel"] or "UPI"
                amt = r["total_amount"]
                # Handle possible COMP-3 cent division
                if amt > 100000000:
                    amt = amt / 100.0
                avg = r["avg_amount"]
                if avg > 100000000:
                    avg = avg / 100.0
                    
                profile[ch] = {
                    "count": r["count"],
                    "total_amount": round(amt, 2),
                    "avg_amount": round(avg, 2),
                    "peak_hour": r["peak_hour"]
                }
                
                channels_used.add(ch)
                if amt > max_amount:
                    max_amount = amt
                    dominant_channel = ch

            # Calculate channel diversity score (used channels / 8 total available channels)
            diversity = round(len(channels_used) / 8.0, 2)

            # Discover channels used in the last 7 days that were NEVER used prior to that
            cursor.execute(
                """
                SELECT DISTINCT channel FROM transactions
                WHERE sender_account = ?
                  AND timestamp > datetime('now', '-7 days')
                  AND channel NOT IN (
                      SELECT DISTINCT channel FROM transactions
                      WHERE sender_account = ?
                        AND timestamp <= datetime('now', '-7 days')
                  )
                """,
                (account_id, account_id)
            )
            new_channels = [r["channel"] or "UPI" for r in cursor.fetchall()]
            
            if not new_channels and channels_used:
                # Fallback: list the most recent channels used historically
                new_channels = list(channels_used)[:1]

        except Exception as e:
            logger.error(f"Failed to fetch cross-channel profile for {account_id}: {e}")
            diversity = 0.0
            new_channels = []
        finally:
            conn.close()

        return {
            "profile": profile,
            "dominant_channel": dominant_channel,
            "channel_diversity_score": diversity,
            "recent_new_channels": new_channels
        }

    def detect_channel_hop(self, account_id: str, time_window_minutes: int = 60) -> Optional[dict]:
        """
        Detects rapid channel hopping within a sliding time window.
        Leverages Redis zsets with an in-memory/SQLite BFS correlation fallback.
        """
        # Try Redis correlation
        redis_online = False
        if self.redis_client is None and not self.redis_failed:
            try:
                self.redis_client = next(get_redis())
                if self.redis_client is None:
                    self.redis_failed = True
            except Exception:
                self.redis_failed = True

        if self.redis_client:
            try:
                key = f"channels:{account_id}"
                now = time.time()
                self.redis_client.zremrangebyscore(key, 0, now - time_window_minutes * 60)
                records = self.redis_client.zrange(key, 0, -1)
                
                channels = set()
                txns = []
                for r in records:
                    if isinstance(r, bytes):
                        r = r.decode('utf-8')
                    ch, tid, amt = r.split(':')
                    channels.add(ch)
                    txns.append({"channel": ch, "transaction_id": tid, "amount": float(amt)})
                
                if len(channels) >= 3:
                    return {
                        "account_id": account_id,
                        "rapid_hopping_detected": True,
                        "unique_channels_count": len(channels),
                        "channels_involved": list(channels),
                        "time_window_minutes": time_window_minutes,
                        "transactions": txns
                    }
                redis_online = True
            except Exception:
                pass

        # Fallback to local SQLite analysis
        if not redis_online:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                # First check relative to last transaction timestamp
                cursor.execute(
                    "SELECT timestamp FROM transactions WHERE sender_account = ? ORDER BY timestamp DESC LIMIT 1",
                    (account_id,)
                )
                last_tx = cursor.fetchone()
                
                base_time_expr = "datetime('now')"
                if last_tx:
                    base_time_expr = f"'{last_tx['timestamp']}'"
                
                cursor.execute(
                    f"""
                    SELECT channel, transaction_id, amount, timestamp 
                    FROM transactions
                    WHERE sender_account = ?
                      AND timestamp > datetime({base_time_expr}, '-' || ? || ' minutes')
                      AND timestamp <= datetime({base_time_expr})
                    """,
                    (account_id, time_window_minutes)
                )
                rows = cursor.fetchall()
                channels = set()
                txns = []
                for r in rows:
                    ch = r["channel"] or "UPI"
                    amt = r["amount"]
                    if amt > 100000000:
                        amt = amt / 100.0
                    channels.add(ch)
                    txns.append({
                        "channel": ch,
                        "transaction_id": r["transaction_id"],
                        "amount": round(amt, 2),
                        "timestamp": r["timestamp"]
                    })
                
                if len(channels) >= 3:
                    return {
                        "account_id": account_id,
                        "rapid_hopping_detected": True,
                        "unique_channels_count": len(channels),
                        "channels_involved": list(channels),
                        "time_window_minutes": time_window_minutes,
                        "transactions": txns
                    }
            except Exception as e:
                logger.error(f"Local SQLite channel-hop lookup failed: {e}")
            finally:
                conn.close()

        return None

    def get_cross_channel_velocity(self, account_id: str) -> dict:
        """
        Computes combined velocity indicators across all aggregate channels.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        v1h, v24h, v7d = 0, 0, 0
        a1h, a24h, a7d = 0.0, 0.0, 0.0
        
        try:
            # Check relative to last transaction timestamp
            cursor.execute(
                "SELECT timestamp FROM transactions WHERE sender_account = ? ORDER BY timestamp DESC LIMIT 1",
                (account_id,)
            )
            last_tx = cursor.fetchone()
            
            base_time_expr = "datetime('now')"
            if last_tx:
                base_time_expr = f"'{last_tx['timestamp']}'"
                
            cursor.execute(
                f"""
                SELECT 
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-1 hour') AND timestamp <= datetime({base_time_expr}) THEN 1 ELSE 0 END) as c1h,
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-1 hour') AND timestamp <= datetime({base_time_expr}) THEN amount ELSE 0 END) as a1h,
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-24 hours') AND timestamp <= datetime({base_time_expr}) THEN 1 ELSE 0 END) as c24h,
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-24 hours') AND timestamp <= datetime({base_time_expr}) THEN amount ELSE 0 END) as a24h,
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-7 days') AND timestamp <= datetime({base_time_expr}) THEN 1 ELSE 0 END) as c7d,
                    SUM(CASE WHEN timestamp >= datetime({base_time_expr}, '-7 days') AND timestamp <= datetime({base_time_expr}) THEN amount ELSE 0 END) as a7d
                FROM transactions
                WHERE sender_account = ?
                """,
                (account_id,)
            )
            row = cursor.fetchone()
            if row:
                v1h = row["c1h"] or 0
                a1h = row["a1h"] or 0.0
                v24h = row["c24h"] or 0
                a24h = row["a24h"] or 0.0
                v7d = row["c7d"] or 0
                a7d = row["a7d"] or 0.0
                
                # COMP-3 cent conversion
                if a1h > 100000000: a1h /= 100.0
                if a24h > 100000000: a24h /= 100.0
                if a7d > 100000000: a7d /= 100.0
                
        except Exception as e:
            logger.error(f"Failed to fetch cross-channel velocity for {account_id}: {e}")
        finally:
            conn.close()

        return {
            "account_id": account_id,
            "velocity_1h": {"count": v1h, "amount": round(a1h, 2)},
            "velocity_24h": {"count": v24h, "amount": round(a24h, 2)},
            "velocity_7d": {"count": v7d, "amount": round(a7d, 2)}
        }
