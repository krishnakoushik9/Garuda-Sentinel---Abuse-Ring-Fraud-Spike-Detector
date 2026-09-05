import argparse
import asyncio
import json
import logging
import os
import socket
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import aiohttp

from src.config import SQLITE_DB_PATH, USE_REAL_GOVDATA
from src.ingestion.kafka_client import KafkaPubSub

API_KEY = "579b464db66ec23bdd000001e55a2b7e099f45e96f171d7ee20c7b5a"
BASE_URL = "https://api.data.gov.in/resource"
HEADERS = {"Accept": "application/json"}
DATA_SOURCE = "REAL_GOVDATA_API"
IST = ZoneInfo("Asia/Kolkata")

logger = logging.getLogger("govdata_injector")


@dataclass(frozen=True)
class GovResource:
    key: str
    resource_id: str
    table: str
    kafka_topic: str
    normalizer: Callable[[dict, str], List[dict]]

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.resource_id}?api-key={API_KEY}&format=json&limit=100"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def use_real_govdata() -> bool:
    return os.environ.get("USE_REAL_GOVDATA", str(USE_REAL_GOVDATA)).strip().lower() in {"1", "true", "yes", "on"}


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).replace(",", "").replace("₹", "").strip())
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    return int(round(to_float(value, float(default))))


def first_value(record: dict, keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]
    return default


def normalize_upi(records: List[dict], ingested_at: str) -> List[dict]:
    rows = []
    for record in records:
        volume_crore = to_float(first_value(record, ("volume__in_crore_", "volume", "transaction_volume")))
        value_lakh_crore = to_float(first_value(record, ("value__in_lakh_crore_", "value", "transaction_value")))
        rows.append({
            "month": str(first_value(record, ("month", "_month", "period"), "UNKNOWN")),
            "volume_mn_transactions": volume_crore * 10.0,
            "value_cr_rupees": value_lakh_crore * 100000.0,
            "ingested_at": ingested_at,
            "source_resource_id": RESOURCES["upi"].resource_id,
            "data_source": DATA_SOURCE,
            "raw_record": json.dumps(record),
        })
    return rows


def normalize_rupay(records: List[dict], ingested_at: str) -> List[dict]:
    rows = []
    for record in records:
        rows.append({
            "period": str(first_value(record, ("_year", "year", "period"), "UNKNOWN")),
            "volume": to_float(first_value(record, ("volume__in_lakhs_", "volume", "transaction_volume"))),
            "value_cr": to_float(first_value(record, ("value__in_crore_", "value_cr", "transaction_value"))),
            "ingested_at": ingested_at,
            "source_resource_id": RESOURCES["rupay"].resource_id,
            "data_source": DATA_SOURCE,
            "raw_record": json.dumps(record),
        })
    return rows


def normalize_frauds(records: List[dict], ingested_at: str) -> List[dict]:
    rows = []
    for record in records:
        cases = to_int(first_value(record, ("mode_of_digital_payment___upi___count_of_cases", "num_cases", "cases")))
        amount_lakh = to_float(first_value(record, ("amount_lakh", "amount__lakh_", "amount")))
        fraud_ratio = to_float(first_value(record, ("mode_of_digital_payment___upi___fraud_to_sales_ratio__value_terms_",)))
        if amount_lakh == 0.0 and fraud_ratio > 0:
            amount_lakh = fraud_ratio
        rows.append({
            "year": str(first_value(record, ("financial_year", "_year", "year"), "UNKNOWN")),
            "fraud_category": str(first_value(record, ("fraud_category", "category"), "UPI_FRAUD")),
            "num_cases": cases,
            "amount_lakh": amount_lakh,
            "bank_type": str(first_value(record, ("bank_type", "bank_category"), "ALL_BANKS")),
            "ingested_at": ingested_at,
            "source_resource_id": RESOURCES["frauds"].resource_id,
            "data_source": DATA_SOURCE,
            "raw_record": json.dumps(record),
        })
    return rows


def normalize_cybercrime(records: List[dict], ingested_at: str) -> List[dict]:
    rows = []
    for record in records:
        state = str(first_value(record, ("state_ut", "state", "state_name"), "UNKNOWN"))
        if state.strip().lower() in {"total", "all india", "unknown"}:
            continue
        for key, value in record.items():
            if key.startswith("_") and key[1:].isdigit():
                rows.append({
                    "state": state,
                    "year": key[1:],
                    "total_cases": to_int(value),
                    "category": "CYBERCRIME_ABETMENT_OF_SUICIDE_ONLINE",
                    "ingested_at": ingested_at,
                    "source_resource_id": RESOURCES["cybercrime"].resource_id,
                    "data_source": DATA_SOURCE,
                    "raw_record": json.dumps(record),
                })
    return rows


def normalize_npci(records: List[dict], ingested_at: str) -> List[dict]:
    rows = []
    for record in records:
        period = str(first_value(record, ("_year", "year", "period"), "UNKNOWN"))
        volume = to_float(first_value(record, ("transaction_volume", "volume")))
        value = to_float(first_value(record, ("transaction_value__rs__", "transaction_value", "value")))
        for metric_name, metric_value in (("transaction_volume", volume), ("transaction_value_rs", value)):
            rows.append({
                "period": period,
                "metric_name": metric_name,
                "value": metric_value,
                "ingested_at": ingested_at,
                "source_resource_id": RESOURCES["npci"].resource_id,
                "data_source": DATA_SOURCE,
                "raw_record": json.dumps(record),
            })
    return rows


RESOURCES: Dict[str, GovResource] = {
    "upi": GovResource("upi", "a40ccebb-b1e7-4245-8801-a9f38eb8cab6", "gov_upi_stats", "gov.upi.stats", normalize_upi),
    "rupay": GovResource("rupay", "5c3d7a42-7f5e-4f1c-9e6d-1727caeda4c8", "gov_rupay_stats", "gov.rupay.stats", normalize_rupay),
    "frauds": GovResource("frauds", "3d50bf0b-52ed-4ef6-a113-5c4da9fba786", "gov_rbi_frauds", "gov.rbi.fraud_stats", normalize_frauds),
    "cybercrime": GovResource("cybercrime", "5116f39e-b323-46cb-bad5-bdc3a5d22610", "gov_cybercrime_state", "gov.cybercrime.state", normalize_cybercrime),
    "npci": GovResource("npci", "46b72197-0c1b-49ac-af93-d9b3b9ff3645", "gov_npci_stats", "gov.npci.stats", normalize_npci),
}


class GovDataInjector:
    def __init__(self, db_path: Optional[str] = None, pubsub_client: Optional[KafkaPubSub] = None):
        self.db_path = db_path or SQLITE_DB_PATH
        self.pubsub = pubsub_client or KafkaPubSub()
        self.scheduler = None
        self.init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS gov_upi_stats (
                    month TEXT,
                    volume_mn_transactions REAL,
                    value_cr_rupees REAL,
                    ingested_at TEXT,
                    source_resource_id TEXT,
                    data_source TEXT,
                    raw_record TEXT
                );
                CREATE TABLE IF NOT EXISTS gov_rupay_stats (
                    period TEXT,
                    volume REAL,
                    value_cr REAL,
                    ingested_at TEXT,
                    source_resource_id TEXT,
                    data_source TEXT,
                    raw_record TEXT
                );
                CREATE TABLE IF NOT EXISTS gov_rbi_frauds (
                    year TEXT,
                    fraud_category TEXT,
                    num_cases INTEGER,
                    amount_lakh REAL,
                    bank_type TEXT,
                    ingested_at TEXT,
                    source_resource_id TEXT,
                    data_source TEXT,
                    raw_record TEXT
                );
                CREATE TABLE IF NOT EXISTS gov_cybercrime_state (
                    state TEXT,
                    year TEXT,
                    total_cases INTEGER,
                    category TEXT,
                    ingested_at TEXT,
                    source_resource_id TEXT,
                    data_source TEXT,
                    raw_record TEXT
                );
                CREATE TABLE IF NOT EXISTS gov_npci_stats (
                    period TEXT,
                    metric_name TEXT,
                    value REAL,
                    ingested_at TEXT,
                    source_resource_id TEXT,
                    data_source TEXT,
                    raw_record TEXT
                );
                CREATE TABLE IF NOT EXISTS gov_derived_signals (
                    signal_type TEXT,
                    value REAL,
                    computed_at TEXT,
                    source_resource TEXT,
                    description TEXT
                );
            """)

    async def fetch_resource(self, session: aiohttp.ClientSession, resource: GovResource) -> List[dict]:
        if not use_real_govdata():
            logger.warning("USE_REAL_GOVDATA=false; using cached rows for %s", resource.key)
            return self._cached_rows(resource)

        try:
            async with session.get(resource.url, headers=HEADERS) as response:
                if response.status >= 400:
                    logger.warning("GovData HTTP %s for %s", response.status, resource.key)
                    return self._cached_rows(resource)
                payload = await response.json(content_type=None)
        except Exception as exc:
            logger.warning("GovData fetch failed for %s: %r", resource.key, exc)
            return self._cached_rows(resource)

        records = payload.get("records") or []
        if not records:
            logger.warning("GovData returned empty records for %s", resource.key)
            return self._cached_rows(resource)
        return records

    def _cached_rows(self, resource: GovResource) -> List[dict]:
        try:
            with self._conn() as conn:
                rows = conn.execute(
                    f"SELECT raw_record FROM {resource.table} WHERE raw_record IS NOT NULL ORDER BY ingested_at DESC LIMIT 100"
                ).fetchall()
            return [json.loads(row["raw_record"]) for row in rows if row["raw_record"]]
        except Exception as exc:
            logger.warning("GovData cache fallback failed for %s: %s", resource.key, exc)
            return []

    async def ingest_resource(self, key: str) -> Dict[str, Any]:
        resource = RESOURCES[key]
        timeout = aiohttp.ClientTimeout(total=10)
        connector = aiohttp.TCPConnector(family=socket.AF_INET)
        session_headers = {"User-Agent": "curl/8.5.0"}
        async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=session_headers) as session:
            raw_records = await self.fetch_resource(session, resource)
        if not raw_records:
            return {"resource": key, "records": 0, "status": "empty"}

        ingested_at = utc_now_iso()
        rows = resource.normalizer(raw_records, ingested_at)
        self._store_rows(resource, rows)
        for row in rows:
            self.pubsub.publish(resource.kafka_topic, row)
        signals = self.compute_derived_signals(key)
        return {"resource": key, "records": len(rows), "signals": len(signals), "status": "ok"}

    async def ingest_all(self) -> Dict[str, Any]:
        results = await asyncio.gather(*(self.ingest_resource(key) for key in RESOURCES), return_exceptions=True)
        output: Dict[str, Any] = {}
        for key, result in zip(RESOURCES.keys(), results):
            if isinstance(result, Exception):
                logger.warning("GovData ingest failed for %s: %s", key, result)
                output[key] = {"resource": key, "records": 0, "status": "failed", "error": str(result)}
            else:
                output[key] = result
        return output

    async def ingest_all_if_empty(self) -> Dict[str, Any]:
        if not self.tables_are_empty():
            return {"status": "skipped", "reason": "govdata tables already contain records"}
        return await self.ingest_all()

    def _store_rows(self, resource: GovResource, rows: List[dict]) -> None:
        if not rows:
            return
        columns = list(rows[0].keys())
        placeholders = ",".join(["?"] * len(columns))
        sql = f"INSERT INTO {resource.table} ({','.join(columns)}) VALUES ({placeholders})"
        with self._conn() as conn:
            conn.execute(
                f"DELETE FROM {resource.table} WHERE source_resource_id = ? AND data_source = ?",
                (resource.resource_id, DATA_SOURCE),
            )
            conn.executemany(sql, [[row.get(column) for column in columns] for row in rows])

    def tables_are_empty(self) -> bool:
        with self._conn() as conn:
            for resource in RESOURCES.values():
                count = conn.execute(f"SELECT COUNT(*) AS c FROM {resource.table}").fetchone()["c"]
                if count:
                    return False
        return True

    def compute_derived_signals(self, resource_key: str) -> List[dict]:
        computed_at = utc_now_iso()
        signals: List[dict] = []
        with self._conn() as conn:
            if resource_key == "upi":
                row = conn.execute(
                    "SELECT AVG(volume_mn_transactions) AS avg_monthly FROM gov_upi_stats WHERE data_source = ?",
                    (DATA_SOURCE,),
                ).fetchone()
                avg_monthly = row["avg_monthly"] or 0.0
                daily_baseline = avg_monthly / 30.0
                signals.append({
                    "signal_type": "UPI_DAILY_VELOCITY_BASELINE",
                    "value": daily_baseline,
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["upi"].resource_id,
                    "description": "National daily UPI transaction-count baseline in million transactions.",
                })
                signals.append({
                    "signal_type": "VELOCITY_SPIKE_THRESHOLD_3_5X",
                    "value": daily_baseline * 3.5,
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["upi"].resource_id,
                    "description": "Flag VELOCITY_SPIKE when account 24h UPI count exceeds 3.5x daily baseline.",
                })
            elif resource_key == "rupay":
                row = conn.execute(
                    "SELECT SUM(value_cr) AS value_cr, SUM(volume) AS volume FROM gov_rupay_stats WHERE data_source = ?",
                    (DATA_SOURCE,),
                ).fetchone()
                avg_card_txn = ((row["value_cr"] or 0.0) * 10000000.0) / max(row["volume"] or 0.0, 1.0)
                signals.append({
                    "signal_type": "CARD_AVG_TXN_RUPEES",
                    "value": avg_card_txn,
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["rupay"].resource_id,
                    "description": "National RuPay credit-card linked UPI average transaction value.",
                })
            elif resource_key == "frauds":
                row = conn.execute(
                    "SELECT SUM(num_cases) AS cases, AVG(amount_lakh) AS avg_amount FROM gov_rbi_frauds WHERE data_source = ?",
                    (DATA_SOURCE,),
                ).fetchone()
                signals.append({
                    "signal_type": "RBI_FRAUD_CASE_VOLUME",
                    "value": float(row["cases"] or 0.0),
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["frauds"].resource_id,
                    "description": "Total RBI-reported fraud cases available from data.gov.in source.",
                })
            elif resource_key == "cybercrime":
                row = conn.execute(
                    "SELECT AVG(total_cases) AS avg_cases FROM gov_cybercrime_state WHERE data_source = ?",
                    (DATA_SOURCE,),
                ).fetchone()
                signals.append({
                    "signal_type": "STATE_CYBERCRIME_AVG_CASES",
                    "value": float(row["avg_cases"] or 0.0),
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["cybercrime"].resource_id,
                    "description": "Average state cybercrime case volume for geo-risk calibration.",
                })
            elif resource_key == "npci":
                row = conn.execute(
                    "SELECT AVG(value) AS avg_value FROM gov_npci_stats WHERE metric_name = 'transaction_volume' AND data_source = ?",
                    (DATA_SOURCE,),
                ).fetchone()
                signals.append({
                    "signal_type": "NPCI_INTEROP_AVG_VOLUME",
                    "value": float(row["avg_value"] or 0.0),
                    "computed_at": computed_at,
                    "source_resource": RESOURCES["npci"].resource_id,
                    "description": "Average NPCI/cross-border UPI interoperability volume.",
                })

            conn.executemany(
                """
                INSERT INTO gov_derived_signals (signal_type, value, computed_at, source_resource, description)
                VALUES (:signal_type, :value, :computed_at, :source_resource, :description)
                """,
                signals,
            )
        return signals

    def get_status(self) -> dict:
        with self._conn() as conn:
            last_ingested = {}
            record_counts = {}
            freshness_minutes = {}
            now = datetime.now(timezone.utc)
            for key, resource in RESOURCES.items():
                row = conn.execute(
                    f"SELECT COUNT(*) AS c, MAX(ingested_at) AS last_at FROM {resource.table}"
                ).fetchone()
                record_counts[key] = row["c"] or 0
                last_ingested[key] = row["last_at"]
                if row["last_at"]:
                    parsed = datetime.fromisoformat(row["last_at"])
                    freshness_minutes[key] = round((now - parsed).total_seconds() / 60.0, 2)
                else:
                    freshness_minutes[key] = None
        return {
            "last_ingested": last_ingested,
            "record_counts": record_counts,
            "freshness_minutes": freshness_minutes,
            "data_source": DATA_SOURCE,
            "use_real_govdata": use_real_govdata(),
        }

    def get_upi_baseline(self) -> dict:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT AVG(volume_mn_transactions) AS monthly_avg_mn,
                       AVG(value_cr_rupees) AS monthly_value_cr,
                       MAX(ingested_at) AS last_ingested
                FROM gov_upi_stats
                WHERE data_source = ?
                """,
                (DATA_SOURCE,),
            ).fetchone()
            rows = conn.execute(
                """
                SELECT month, volume_mn_transactions, value_cr_rupees, ingested_at
                FROM gov_upi_stats
                WHERE data_source = ?
                ORDER BY rowid
                """,
                (DATA_SOURCE,),
            ).fetchall()
        monthly_avg = row["monthly_avg_mn"] or 0.0
        daily_avg = monthly_avg / 30.0
        series = []
        previous_volume = None
        for item in rows:
            volume = float(item["volume_mn_transactions"] or 0.0)
            mom_change = 0.0
            if previous_volume and previous_volume > 0:
                mom_change = ((volume - previous_volume) / previous_volume) * 100.0
            series.append({
                "month": item["month"],
                "volume_mn_transactions": round(volume, 4),
                "value_cr_rupees": round(float(item["value_cr_rupees"] or 0.0), 4),
                "mom_change_pct": round(mom_change, 2),
                "ingested_at": item["ingested_at"],
            })
            previous_volume = volume
        return {
            "monthly_avg_mn_transactions": round(monthly_avg, 4),
            "daily_avg_mn_transactions": round(daily_avg, 4),
            "velocity_spike_threshold_mn_transactions": round(daily_avg * 3.5, 4),
            "monthly_avg_value_cr_rupees": round(row["monthly_value_cr"] or 0.0, 4),
            "series": series,
            "last_ingested": row["last_ingested"],
            "source_resource": RESOURCES["upi"].resource_id,
        }

    def get_fraud_context(self, fraud_category: Optional[str] = None, amount: Optional[float] = None) -> dict:
        category = fraud_category or "UPI_FRAUD"
        amount_lakh = (amount or 0.0) / 100000.0
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT year, fraud_category, num_cases, amount_lakh, bank_type
                FROM gov_rbi_frauds
                WHERE data_source = ? AND (fraud_category = ? OR ? = 'UPI_FRAUD')
                ORDER BY year DESC
                """,
                (DATA_SOURCE, category, category),
            ).fetchall()

        amounts = [float(row["amount_lakh"] or 0.0) for row in rows]
        positive_amounts = [value for value in amounts if value > 0]
        avg_lakh = sum(positive_amounts) / len(positive_amounts) if positive_amounts else 0.0
        percentile = 0.0
        if positive_amounts and amount_lakh > 0:
            percentile = 100.0 * sum(1 for value in positive_amounts if value <= amount_lakh) / len(positive_amounts)
        latest = rows[0] if rows else {}
        return {
            "fraud_category": category,
            "year": latest["year"] if latest else None,
            "num_cases_this_year": latest["num_cases"] if latest else 0,
            "national_avg_fraud_amount_lakh": round(avg_lakh, 4),
            "national_avg_fraud_amount_rupees": round(avg_lakh * 100000.0, 2),
            "transaction_amount_rupees": amount or 0.0,
            "percentile_rank": round(percentile, 2),
            "source": "RBI official fraud data, data.gov.in",
            "source_resource": RESOURCES["frauds"].resource_id,
            "records": [dict(row) for row in rows],
        }

    def get_geo_risk(self) -> dict:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT state, MAX(year) AS latest_year, SUM(total_cases) AS total_cases
                FROM gov_cybercrime_state
                WHERE data_source = ? AND LOWER(state) NOT IN ('total', 'all india', 'unknown')
                GROUP BY state
                ORDER BY total_cases DESC
                """,
                (DATA_SOURCE,),
            ).fetchall()
        rankings = []
        for rank, row in enumerate(rows, start=1):
            rankings.append({
                "rank": rank,
                "state": row["state"],
                "latest_year": row["latest_year"],
                "total_cases": row["total_cases"],
                "risk_delta": 0.08 if rank <= 5 else 0.0,
            })
        return {
            "rankings": rankings,
            "top_5_states": [row["state"] for row in rankings[:5]],
            "source_resource": RESOURCES["cybercrime"].resource_id,
        }

    def start_scheduler(self) -> bool:
        if self.scheduler and self.scheduler.running:
            return True
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from apscheduler.triggers.cron import CronTrigger
            from apscheduler.triggers.interval import IntervalTrigger
        except Exception as exc:
            logger.warning("APScheduler unavailable; govdata scheduler disabled: %s", exc)
            return False

        self.scheduler = AsyncIOScheduler(timezone=IST)
        for key in ("upi", "rupay", "npci"):
            self.scheduler.add_job(
                self.ingest_resource,
                IntervalTrigger(hours=6),
                args=[key],
                id=f"govdata_{key}_6h",
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )
        self.scheduler.add_job(
            self.ingest_resource,
            CronTrigger(hour=2, minute=0, timezone=IST),
            args=["frauds"],
            id="govdata_frauds_daily",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.add_job(
            self.ingest_resource,
            CronTrigger(hour=3, minute=0, timezone=IST),
            args=["cybercrime"],
            id="govdata_cybercrime_daily",
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self.scheduler.start()
        return True

    def shutdown_scheduler(self) -> None:
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)


async def _run_test() -> None:
    logging.basicConfig(level=logging.INFO)
    injector = GovDataInjector()
    result = await injector.ingest_all()
    print(json.dumps(result, indent=2))
    print(json.dumps(injector.get_status(), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Garuda Sentinel data.gov.in ingestion service")
    parser.add_argument("--test", action="store_true", help="Fetch all five live resources and write to SQLite")
    args = parser.parse_args()
    if args.test:
        os.environ["USE_REAL_GOVDATA"] = "true"
        asyncio.run(_run_test())
    else:
        parser.print_help()
