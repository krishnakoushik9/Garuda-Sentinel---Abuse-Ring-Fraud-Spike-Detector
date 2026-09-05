#!/usr/bin/env python3
"""Graph-first synthetic banking ecosystem for PS2 mule-account research."""

from __future__ import annotations

import csv
import json
import os
import random
import sqlite3
import sys
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib import request


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOI_DB_PATH", str(ROOT / "database" / "ecosystem.db")))
SCHEMA_PATH = ROOT / "database" / "schema.sql"
EXPORT_DIR = ROOT / "exports"
RUNTIME_DIR = ROOT / "runtime"


CITIES = [
    ("Mumbai", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bengaluru", "Karnataka"),
    ("Hyderabad", "Telangana"),
    ("Chennai", "Tamil Nadu"),
    ("Kolkata", "West Bengal"),
    ("Pune", "Maharashtra"),
    ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
    ("Kochi", "Kerala"),
    ("Indore", "Madhya Pradesh"),
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Arjun", "Diya", "Ishaan", "Kavya", "Meera", "Neha",
    "Rohan", "Saanvi", "Vikram", "Ananya", "Rahul", "Priya", "Kabir", "Nisha",
]
LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Iyer", "Nair", "Gupta", "Das", "Reddy",
    "Mehta", "Joshi", "Khan", "Menon", "Agarwal", "Chatterjee", "Rao",
]
EMPLOYERS = [
    "Infosys", "TCS", "Reliance Retail", "HDFC Life", "Axis Services",
    "Metro Foods", "Bharat Logistics", "Apollo Health", "State Education Dept",
]
MERCHANT_CATEGORIES = [
    "grocery", "pharmacy", "electronics", "restaurant", "fuel", "travel",
    "education", "apparel", "utilities", "mobile_recharge",
]

SEGMENT_DISTRIBUTION = [
    ("employee", 0.36),
    ("student", 0.16),
    ("business", 0.13),
    ("merchant", 0.12),
    ("retired", 0.10),
    ("freelancer", 0.09),
    ("high_net_worth", 0.04),
]

REL_STRENGTH = {
    "family": 0.95,
    "friend": 0.80,
    "employer": 0.60,
    "merchant": 0.40,
    "local": 0.25,
    "stranger": 0.10,
    "mule": 0.92,
    "fraud_ring": 0.88,
}

SPEEDS = {"1x": 1, "10x": 10, "100x": 100, "1000x": 1000}


@dataclass
class Account:
    account_id: str
    name: str
    age: int
    city: str
    state: str
    occupation: str
    customer_segment: str
    monthly_income: float
    income_range: str
    account_open_date: str
    initial_balance: float
    balance: float
    risk_profile: str
    employer: str
    merchant_category: str
    cluster_id: str
    active: bool = False


@dataclass
class Relationship:
    source: str
    target: str
    relationship_type: str
    strength: float
    cluster_id: str


@dataclass
class MuleNetwork:
    network_id: str
    pattern_type: str
    accounts: list[str]
    next_fire_day: int
    amount_seed: float


@dataclass
class FraudCampaign:
    campaign_id: str
    fraud_type: str
    accounts: list[str]
    next_fire_day: int
    remaining_events: int


@dataclass
class Metrics:
    active_accounts: int = 0
    transactions: int = 0
    fraud_events: int = 0
    mule_networks: int = 0
    neo4j_nodes: int = 0
    neo4j_edges: int = 0
    started_at: float = field(default_factory=time.time)

    @property
    def tps(self) -> float:
        return self.transactions / max(time.time() - self.started_at, 1.0)


class CsvSink:
    def __init__(self, export_dir: Path):
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._writers: dict[str, csv.DictWriter] = {}
        self._files = {}

    def writer(self, name: str, fields: list[str]) -> csv.DictWriter:
        path = self.export_dir / name
        exists = path.exists() and path.stat().st_size > 0
        fh = path.open("a", newline="", encoding="utf-8")
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not exists:
            writer.writeheader()
        self._files[name] = fh
        self._writers[name] = writer
        return writer

    def close(self) -> None:
        for fh in self._files.values():
            fh.flush()
            fh.close()


class Neo4jSink:
    def __init__(self) -> None:
        self.url = os.environ.get("NEO4J_URL", "http://localhost:7474")
        self.user = os.environ.get("NEO4J_USER", "neo4j")
        self.password = os.environ.get("NEO4J_PASSWORD", "password")
        self.db = os.environ.get("NEO4J_DATABASE", "neo4j")
        self.enabled = os.environ.get("NEO4J_ENABLED", "0") == "1"
        self.nodes = 0
        self.edges = 0

    def cypher(self, statements: list[dict]) -> None:
        if not self.enabled:
            return
        payload = json.dumps({"statements": statements}).encode("utf-8")
        url = f"{self.url}/db/{self.db}/tx/commit"
        req = request.Request(url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        import base64

        token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
        try:
            with request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("errors"):
                print(f"Neo4j warning: {data['errors'][0].get('message')}", file=sys.stderr)
        except Exception as exc:
            self.enabled = False
            print(f"Neo4j disabled: {exc}", file=sys.stderr)

    def write_accounts(self, accounts: list[Account]) -> None:
        if not accounts:
            return
        rows = [a.__dict__ for a in accounts]
        self.cypher([
            {
                "statement": (
                    "UNWIND $rows AS row MERGE (a:Account {account_id: row.account_id}) "
                    "SET a.name=row.name, a.segment=row.customer_segment, a.city=row.city, "
                    "a.state=row.state, a.risk_profile=row.risk_profile, a.cluster_id=row.cluster_id"
                ),
                "parameters": {"rows": rows},
            }
        ])
        self.nodes += len(rows)

    def write_transactions(self, rows: list[dict]) -> None:
        if not rows:
            return
        self.cypher([
            {
                "statement": (
                    "UNWIND $rows AS row "
                    "MATCH (s:Account {account_id: row.sender_account}) "
                    "MATCH (r:Account {account_id: row.receiver_account}) "
                    "CREATE (s)-[:SENT_TO {amount: row.amount, timestamp: row.timestamp, "
                    "channel: row.channel, risk_score: row.risk_score, tx: row.transaction_id}]->(r)"
                ),
                "parameters": {"rows": rows},
            }
        ])
        self.edges += len(rows)


class Ecosystem:
    def __init__(self) -> None:
        self.account_count = int(os.environ.get("BOI_ACCOUNTS", "100000"))
        self.account_count = max(1000, min(100000, self.account_count))
        self.target_transactions = int(os.environ.get("BOI_TRANSACTIONS", "1000000"))
        self.speed = os.environ.get("BOI_SPEED", "100x")
        self.speed_factor = SPEEDS.get(self.speed, 100)
        self.initial_relationship_limit = int(os.environ.get("BOI_INITIAL_RELATIONSHIPS", "350000"))
        self.seed = int(os.environ.get("BOI_SEED", "20260101"))
        self.rng = random.Random(self.seed)
        self.sim_time = datetime.fromisoformat(os.environ.get("BOI_START_TIME", "2026-01-01T09:00:00"))
        self.stop_file = Path(os.environ.get("BOI_STOP_FILE", str(RUNTIME_DIR / "guard.stop")))
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self.accounts: list[Account] = []
        self.account_by_id: dict[str, Account] = {}
        self.relationships: dict[str, list[Relationship]] = defaultdict(list)
        self.active_ids: list[str] = []
        self.metrics = Metrics()
        self.csv = CsvSink(EXPORT_DIR)
        self.neo4j = Neo4jSink()
        self.txn_seq = 0
        self.event_seq = 0
        self.mule_networks: list[MuleNetwork] = []
        self.fraud_campaigns: list[FraudCampaign] = []
        self.recent_stream: deque[str] = deque(maxlen=12)
        self.relationship_seq = 0
        self._prepare()

    def _prepare(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA cache_size=-200000")
        self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.conn.commit()
        self.accounts_csv = self.csv.writer(
            "accounts.csv",
            ["account_id", "name", "age", "city", "state", "occupation", "customer_segment",
             "monthly_income", "income_range", "account_open_date", "initial_balance",
             "risk_profile", "employer", "merchant_category", "cluster_id"],
        )
        self.transactions_csv = self.csv.writer(
            "transactions.csv",
            ["transaction_id", "timestamp", "sender_account", "receiver_account", "amount",
             "channel", "status", "description", "relationship_type", "simulated_day", "risk_score"],
        )
        self.relationships_csv = self.csv.writer(
            "relationships.csv",
            ["source_account", "target_account", "relationship_type", "strength", "cluster_id", "created_at"],
        )
        self.mule_labels_csv = self.csv.writer(
            "mule_labels.csv",
            ["account_id", "network_id", "pattern_type", "role", "label_timestamp"],
        )
        self.fraud_labels_csv = self.csv.writer(
            "fraud_labels.csv",
            ["transaction_id", "account_id", "campaign_id", "fraud_type", "label_timestamp"],
        )

    def run(self) -> None:
        print(f"Preparing ecosystem: accounts={self.account_count:,}, target_transactions={self.target_transactions:,}, speed={self.speed}")
        self.generate_accounts()
        self.generate_relationships()
        self.seed_mule_networks()
        self.seed_fraud_campaigns()
        self.activate_accounts(10)
        print("Phase 2 Banking Ecosystem started. Press Ctrl+C or create runtime/guard.stop to stop.")
        try:
            while self.metrics.transactions < self.target_transactions and not self.stop_file.exists():
                self.tick()
        except KeyboardInterrupt:
            pass
        finally:
            self.csv.close()
            self.conn.commit()
            self.conn.close()

    def weighted_segment(self) -> str:
        x = self.rng.random()
        acc = 0.0
        for name, weight in SEGMENT_DISTRIBUTION:
            acc += weight
            if x <= acc:
                return name
        return "employee"

    def generate_accounts(self) -> None:
        existing = self.conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        if existing >= self.account_count:
            print(f"Loaded existing accounts: {existing:,}")
            self.load_accounts()
            return
        print(f"Generating realistic accounts: {self.account_count:,}")
        rows = []
        csv_rows = []
        account_chunk = []
        for i in range(1, self.account_count + 1):
            segment = self.weighted_segment()
            city, state = self.rng.choice(CITIES)
            age = self.age_for(segment)
            income = self.income_for(segment)
            risk = self.risk_for(segment)
            account_id = f"ACC{i:06d}"
            opened = self.sim_time.date() - timedelta(days=self.rng.randint(0, 3650))
            initial_balance = round(max(500, income * self.rng.uniform(0.15, 2.2)), 2)
            employer = self.rng.choice(EMPLOYERS) if segment in {"employee", "high_net_worth"} else ""
            merchant_category = self.rng.choice(MERCHANT_CATEGORIES) if segment in {"merchant", "business"} else ""
            account = Account(
                account_id=account_id,
                name=f"{self.rng.choice(FIRST_NAMES)} {self.rng.choice(LAST_NAMES)}",
                age=age,
                city=city,
                state=state,
                occupation=self.occupation_for(segment),
                customer_segment=segment,
                monthly_income=income,
                income_range=self.income_range(income),
                account_open_date=opened.isoformat(),
                initial_balance=initial_balance,
                balance=initial_balance,
                risk_profile=risk,
                employer=employer,
                merchant_category=merchant_category,
                cluster_id=f"{city[:3].upper()}-{self.rng.randint(1, 900):03d}",
            )
            if i == 1:
                account.name = "Central Settlement Account"
                account.occupation = "Settlement Treasury"
                account.customer_segment = "business"
                account.monthly_income = 50000000
                account.income_range = "high"
                account.initial_balance = 100000000000
                account.balance = 100000000000
            self.accounts.append(account)
            self.account_by_id[account_id] = account
            account_chunk.append(account)
            csv_row = account.__dict__.copy()
            csv_row.pop("active")
            csv_row.pop("balance")
            rows.append((
                account.account_id, account.name, account.age, account.city, account.state,
                account.occupation, account.customer_segment, account.monthly_income,
                account.income_range, account.account_open_date, account.initial_balance,
                account.balance, account.risk_profile, account.employer,
                account.merchant_category, account.cluster_id,
                self.sim_time.isoformat(timespec="seconds"),
            ))
            csv_rows.append(csv_row)
            if len(rows) >= 5000:
                self.insert_accounts(rows, csv_rows)
                self.neo4j.write_accounts(account_chunk)
                print(f"  accounts seeded: {i:,}/{self.account_count:,}", flush=True)
                rows, csv_rows = [], []
                account_chunk = []
        self.insert_accounts(rows, csv_rows)
        self.neo4j.write_accounts(account_chunk)
        print(f"  accounts seeded: {self.account_count:,}/{self.account_count:,}", flush=True)

    def load_accounts(self) -> None:
        for row in self.conn.execute("SELECT * FROM accounts ORDER BY account_id"):
            account = Account(
                account_id=row["account_id"], name=row["name"], age=row["age"], city=row["city"],
                state=row["state"], occupation=row["occupation"], customer_segment=row["customer_segment"],
                monthly_income=row["monthly_income"], income_range=row["income_range"],
                account_open_date=row["account_open_date"], initial_balance=row["initial_balance"],
                balance=row["balance"], risk_profile=row["risk_profile"], employer=row["employer"] or "",
                merchant_category=row["merchant_category"] or "", cluster_id=row["cluster_id"],
                active=bool(row["activated_at"]),
            )
            self.accounts.append(account)
            self.account_by_id[account.account_id] = account
            if account.active:
                self.active_ids.append(account.account_id)

    def insert_accounts(self, rows: list[tuple], csv_rows: list[dict]) -> None:
        if not rows:
            return
        self.conn.executemany(
            "INSERT OR IGNORE INTO accounts "
            "(account_id,name,age,city,state,occupation,customer_segment,monthly_income,income_range,"
            "account_open_date,initial_balance,balance,risk_profile,employer,merchant_category,"
            "cluster_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )
        for row in csv_rows:
            self.accounts_csv.writerow(row)
        self.conn.commit()

    def age_for(self, segment: str) -> int:
        ranges = {
            "student": (18, 25), "employee": (23, 58), "business": (28, 62),
            "merchant": (25, 60), "retired": (60, 82), "freelancer": (22, 50),
            "high_net_worth": (35, 72),
        }
        lo, hi = ranges[segment]
        return self.rng.randint(lo, hi)

    def income_for(self, segment: str) -> float:
        ranges = {
            "student": (3000, 18000), "employee": (30000, 180000), "business": (60000, 500000),
            "merchant": (35000, 300000), "retired": (15000, 90000), "freelancer": (20000, 220000),
            "high_net_worth": (400000, 2500000),
        }
        lo, hi = ranges[segment]
        return round(self.rng.triangular(lo, hi, lo + (hi - lo) * 0.35), 2)

    def income_range(self, income: float) -> str:
        if income < 25000:
            return "low"
        if income < 100000:
            return "middle"
        if income < 350000:
            return "upper_middle"
        return "high"

    def risk_for(self, segment: str) -> str:
        weights = {
            "student": [("low", .75), ("medium", .23), ("high", .02)],
            "employee": [("low", .82), ("medium", .17), ("high", .01)],
            "business": [("low", .50), ("medium", .42), ("high", .08)],
            "merchant": [("low", .55), ("medium", .38), ("high", .07)],
            "retired": [("low", .86), ("medium", .13), ("high", .01)],
            "freelancer": [("low", .62), ("medium", .33), ("high", .05)],
            "high_net_worth": [("low", .55), ("medium", .35), ("high", .10)],
        }
        x = self.rng.random()
        acc = 0.0
        for label, weight in weights[segment]:
            acc += weight
            if x <= acc:
                return label
        return "medium"

    def occupation_for(self, segment: str) -> str:
        return {
            "student": "Student",
            "employee": "Salary Employee",
            "business": "Small Business",
            "merchant": "Merchant",
            "retired": "Retired Person",
            "freelancer": "Freelancer",
            "high_net_worth": "High Net Worth Individual",
        }[segment]

    def add_relationship(self, source: str, target: str, rel_type: str, cluster_id: str) -> None:
        if source == target:
            return
        rel = Relationship(source, target, rel_type, REL_STRENGTH[rel_type], cluster_id)
        self.relationships[source].append(rel)

    def generate_relationships(self) -> None:
        existing = self.conn.execute("SELECT COUNT(*) FROM account_relationships").fetchone()[0]
        if existing > 0:
            print(f"Loaded existing relationship seed graph: {existing:,} edges")
            self.load_relationships()
            return
        print(f"Generating bounded relationship seed graph: up to {self.initial_relationship_limit:,} edges")
        by_city: dict[str, list[Account]] = defaultdict(list)
        by_employer: dict[str, list[Account]] = defaultdict(list)
        merchants: list[Account] = []
        for acct in self.accounts:
            by_city[acct.city].append(acct)
            if acct.employer:
                by_employer[acct.employer].append(acct)
            if acct.customer_segment in {"merchant", "business"}:
                merchants.append(acct)
        rows = []
        created = 0
        for city_accounts in by_city.values():
            self.rng.shuffle(city_accounts)
            for idx in range(0, len(city_accounts), 6):
                if created >= self.initial_relationship_limit:
                    break
                family = city_accounts[idx:idx + 6]
                if len(family) < 2:
                    continue
                for pos, a in enumerate(family):
                    peers = [p for p in family if p.account_id != a.account_id]
                    for b in self.rng.sample(peers, min(2, len(peers))):
                        self.queue_relationship(rows, a.account_id, b.account_id, "family", a.cluster_id)
                        created += 1
                    friend_pool = city_accounts[max(0, idx - 50):idx] + city_accounts[idx + 6:idx + 56]
                    if friend_pool:
                        b = self.rng.choice(friend_pool)
                        self.queue_relationship(rows, a.account_id, b.account_id, "friend", a.cluster_id)
                        created += 1
                    if merchants:
                        m = self.rng.choice(merchants)
                        self.queue_relationship(rows, a.account_id, m.account_id, "merchant", a.cluster_id)
                        created += 1
                    if created % 50000 == 0:
                        print(f"  relationships seeded: {created:,}", flush=True)
                    if created >= self.initial_relationship_limit:
                        break
            if created >= self.initial_relationship_limit:
                break
        for employer, employees in by_employer.items():
            if created >= self.initial_relationship_limit:
                break
            employer_acct = self.rng.choice(employees)
            for emp in employees[:1000]:
                self.queue_relationship(rows, employer_acct.account_id, emp.account_id, "employer", employer)
                created += 1
                if created >= self.initial_relationship_limit:
                    break
        self.flush_relationships(rows)
        print(f"  relationships seeded: {created:,}", flush=True)

    def queue_relationship(self, rows: list, source: str, target: str, rel_type: str, cluster_id: str) -> None:
        if source == target:
            return
        self.relationship_seq += 1
        rel_id = f"REL{self.relationship_seq:012d}"
        strength = REL_STRENGTH[rel_type]
        rows.append((rel_id, source, target, rel_type, strength, cluster_id, self.sim_time.isoformat(timespec="seconds")))
        self.add_relationship(source, target, rel_type, cluster_id)
        self.relationships_csv.writerow({
            "source_account": source, "target_account": target, "relationship_type": rel_type,
            "strength": strength, "cluster_id": cluster_id, "created_at": self.sim_time.isoformat(timespec="seconds"),
        })
        if len(rows) >= 50000:
            self.flush_relationships(rows)
            rows.clear()

    def flush_relationships(self, rows: list) -> None:
        if not rows:
            return
        self.conn.executemany(
            "INSERT OR IGNORE INTO account_relationships "
            "(relationship_id,source_account,target_account,relationship_type,strength,cluster_id,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            rows,
        )
        self.conn.commit()

    def load_relationships(self) -> None:
        for row in self.conn.execute("SELECT * FROM account_relationships"):
            self.add_relationship(row["source_account"], row["target_account"], row["relationship_type"], row["cluster_id"])

    def activate_accounts(self, target: int) -> None:
        target = min(target, len(self.accounts))
        while len(self.active_ids) < target:
            acct = self.accounts[len(self.active_ids)]
            acct.active = True
            self.active_ids.append(acct.account_id)
        self.metrics.active_accounts = len(self.active_ids)
        self.conn.executemany(
            "UPDATE accounts SET activated_at = COALESCE(activated_at, ?) WHERE account_id = ?",
            [(self.sim_time.isoformat(timespec="seconds"), aid) for aid in self.active_ids[-target:]],
        )
        self.conn.commit()

    def growth_target(self) -> int:
        day = max((self.sim_time - datetime(2026, 1, 1, 9)).days, 0)
        if day < 1:
            return 10
        if day < 3:
            return 100
        if day < 10:
            return 1000
        if day < 30:
            return 10000
        return self.account_count

    def tick(self) -> None:
        self.sim_time += timedelta(days=self.speed_factor / 1000)
        self.activate_accounts(self.growth_target())
        batch = []
        day = (self.sim_time - datetime(2026, 1, 1, 9)).days
        normal_count = max(1, int(len(self.active_ids) * 0.0025))
        for _ in range(normal_count):
            batch.append(self.behavior_transaction())
        batch.extend(self.mule_transactions(day))
        batch.extend(self.fraud_transactions(day))
        batch = [tx for tx in batch if tx]
        self.persist_transactions(batch)
        if self.metrics.transactions % 5000 < len(batch):
            self.compute_graph_analytics()
        self.print_live(batch)
        time.sleep(0.05)

    def choose_sender(self) -> Account:
        candidates = [self.account_by_id[aid] for aid in self.rng.sample(self.active_ids, min(200, len(self.active_ids)))]
        weights = []
        for a in candidates:
            base = {
                "student": 0.35, "employee": 1.0, "business": 2.2, "merchant": 2.6,
                "retired": 0.45, "freelancer": 1.1, "high_net_worth": 1.5,
            }[a.customer_segment]
            weights.append(base)
        return self.rng.choices(candidates, weights=weights, k=1)[0]

    def choose_receiver(self, sender: Account) -> tuple[Account, str]:
        rels = [r for r in self.relationships.get(sender.account_id, []) if r.target in self.account_by_id]
        if rels and self.rng.random() < 0.9:
            rel = self.rng.choices(rels, weights=[r.strength for r in rels], k=1)[0]
            return self.account_by_id[rel.target], rel.relationship_type
        receiver = self.account_by_id[self.rng.choice(self.active_ids)]
        return receiver, "stranger"

    def behavior_transaction(self) -> dict | None:
        sender = self.choose_sender()
        receiver, rel_type = self.choose_receiver(sender)
        segment = sender.customer_segment
        channel = "UPI"
        desc = "UPI transfer"
        amount = 500.0
        if segment == "student":
            channel = self.rng.choice(["UPI", "RECHARGE", "MERCHANT"])
            amount = self.rng.triangular(50, 2500, 250)
            desc = "Student recharge/payment"
        elif segment == "employee":
            if self.sim_time.day in {1, 2} and self.rng.random() < 0.08:
                treasury = self.account_by_id["ACC000001"]
                return self.make_tx(treasury, sender, sender.monthly_income, "SALARY", "Salary Credit", "employer")
            channel = self.rng.choice(["UPI", "RENT", "BILLPAY", "MERCHANT"])
            amount = self.rng.triangular(200, sender.monthly_income * 0.45, 2500)
            desc = "Employee household payment"
        elif segment == "business":
            channel = self.rng.choice(["NEFT", "IMPS", "PAYROLL", "VENDOR"])
            amount = self.rng.triangular(1000, sender.monthly_income * 1.8, 35000)
            desc = "Business operating payment"
        elif segment == "merchant":
            if self.rng.random() < 0.65:
                customer = self.account_by_id[self.rng.choice(self.active_ids)]
                return self.make_tx(customer, sender, self.rng.triangular(80, 9000, 650), "MERCHANT", "Customer receipt", "merchant")
            amount = self.rng.triangular(500, sender.monthly_income * 0.7, 12000)
            desc = "Merchant vendor settlement"
        elif segment == "retired":
            if self.sim_time.day == 5 and self.rng.random() < 0.06:
                treasury = self.account_by_id["ACC000001"]
                return self.make_tx(treasury, sender, sender.monthly_income, "PENSION", "Pension Credit", "employer")
            amount = self.rng.triangular(100, 9000, 900)
            desc = "Retired low-volume payment"
        elif segment == "freelancer":
            amount = self.rng.triangular(300, sender.monthly_income, 6000)
            channel = self.rng.choice(["UPI", "IMPS", "BILLPAY"])
            desc = "Freelancer payment"
        else:
            amount = self.rng.triangular(5000, sender.monthly_income, 50000)
            channel = self.rng.choice(["NEFT", "IMPS", "UPI"])
            desc = "HNI transfer"
        return self.make_tx(sender, receiver, amount, channel, desc, rel_type)

    def make_tx(self, sender: Account, receiver: Account, amount: float, channel: str, desc: str, rel_type: str, risk_boost: float = 0) -> dict:
        if sender.account_id == receiver.account_id and len(self.active_ids) > 1:
            alternatives = [aid for aid in self.active_ids if aid != sender.account_id]
            receiver = self.account_by_id[self.rng.choice(alternatives)]
        self.txn_seq += 1
        amount = round(max(10, amount), 2)
        if sender.balance >= amount:
            sender.balance -= amount
            receiver.balance += amount
            status = "COMPLETED"
        else:
            status = "REJECTED"
        risk = min(1.0, {"low": .1, "medium": .35, "high": .65, "critical": .85}.get(sender.risk_profile.lower(), .85) + risk_boost)
        return {
            "transaction_id": f"TXN{self.txn_seq:012d}",
            "timestamp": self.sim_time.isoformat(timespec="seconds"),
            "sender_account": sender.account_id,
            "receiver_account": receiver.account_id,
            "amount": amount,
            "channel": channel,
            "status": status,
            "description": desc,
            "relationship_type": rel_type,
            "simulated_day": (self.sim_time - datetime(2026, 1, 1, 9)).days,
            "risk_score": round(risk, 4),
        }

    def seed_mule_networks(self) -> None:
        for idx in range(1, 151):
            pattern = self.rng.choice(["relay", "fan_out", "layering", "cash_out", "fraud_ring"])
            size = 25 if pattern == "fan_out" else 5
            accounts = [f"ACC{n:06d}" for n in self.rng.sample(range(2, self.account_count + 1), size)]
            network = MuleNetwork(f"MULE{idx:05d}", pattern, accounts, self.rng.randint(2, 60), self.rng.uniform(5000, 95000))
            self.mule_networks.append(network)
            source = accounts[0]
            self.conn.execute(
                "INSERT OR IGNORE INTO mule_networks(network_id,pattern_type,source_account,created_at,active) VALUES (?,?,?,?,1)",
                (network.network_id, pattern, source, self.sim_time.isoformat(timespec="seconds")),
            )
            for pos, account_id in enumerate(accounts):
                self.conn.execute(
                    "INSERT INTO mule_accounts(account_id,pattern_type,chain_id,layer,linked_account,detected_at) VALUES (?,?,?,?,?,?)",
                    (account_id, pattern, network.network_id, pos, accounts[pos - 1] if pos else "", self.sim_time.isoformat(timespec="seconds")),
                )
                self.mule_labels_csv.writerow({
                    "account_id": account_id, "network_id": network.network_id,
                    "pattern_type": pattern, "role": "mule" if pos else "source",
                    "label_timestamp": self.sim_time.isoformat(timespec="seconds"),
                })
        self.conn.commit()
        self.metrics.mule_networks = len(self.mule_networks)

    def mule_transactions(self, day: int) -> list[dict]:
        rows = []
        for network in self.mule_networks:
            if day < network.next_fire_day or self.rng.random() > 0.08:
                continue
            accts = [self.account_by_id[a] for a in network.accounts if a in self.account_by_id]
            if len(accts) < 2:
                continue
            if network.pattern_type == "fan_out":
                source, mule = accts[0], accts[1]
                rows.append(self.make_tx(source, mule, network.amount_seed, "IMPS", "Fan-Out funding", "mule", .25))
                for dest in accts[2:22]:
                    rows.append(self.make_tx(mule, dest, network.amount_seed / 22 * self.rng.uniform(.7, 1.05), "UPI", "Fan-Out distribution", "mule", .35))
            elif network.pattern_type in {"relay", "layering"}:
                amount = network.amount_seed
                for a, b in zip(accts, accts[1:]):
                    rows.append(self.make_tx(a, b, amount, "IMPS", f"{network.pattern_type.title()} mule chain", "mule", .35))
                    amount *= self.rng.uniform(.82, .97)
            elif network.pattern_type == "cash_out":
                rows.append(self.make_tx(accts[0], accts[-1], network.amount_seed, "CASHOUT", "Cash-Out mule endpoint", "mule", .40))
            else:
                for _ in range(8):
                    a, b = self.rng.sample(accts, 2)
                    rows.append(self.make_tx(a, b, self.rng.triangular(5000, 60000, 15000), "UPI", "Fraud ring circulation", "fraud_ring", .45))
            network.next_fire_day = day + self.rng.randint(1, 5)
            self.recent_stream.append("Potential Mule Chain Created")
        return rows

    def seed_fraud_campaigns(self) -> None:
        types = ["dormancy_break", "rapid_in_out", "velocity_spike", "night_activity", "structured_splitting", "synthetic_scam"]
        for idx in range(1, 121):
            size = self.rng.randint(3, 18)
            accounts = [f"ACC{n:06d}" for n in self.rng.sample(range(2, self.account_count + 1), size)]
            self.fraud_campaigns.append(FraudCampaign(f"FRDNET{idx:05d}", self.rng.choice(types), accounts, self.rng.randint(2, 90), self.rng.randint(10, 80)))

    def fraud_transactions(self, day: int) -> list[dict]:
        rows = []
        for campaign in self.fraud_campaigns:
            if campaign.remaining_events <= 0 or day < campaign.next_fire_day or self.rng.random() > 0.12:
                continue
            accts = [self.account_by_id[a] for a in campaign.accounts if a in self.account_by_id]
            if len(accts) < 2:
                continue
            count = {"structured_splitting": 12, "velocity_spike": 18, "rapid_in_out": 8}.get(campaign.fraud_type, 4)
            emitted = 0
            for _ in range(min(count, campaign.remaining_events)):
                a, b = self.rng.sample(accts, 2)
                amount = 9900 if campaign.fraud_type == "structured_splitting" else self.rng.triangular(1200, 125000, 18000)
                tx = self.make_tx(a, b, amount, self.rng.choice(["UPI", "IMPS", "NEFT"]), campaign.fraud_type.replace("_", " ").title(), "fraud_ring", .50)
                rows.append(tx)
                self.event_seq += 1
                self.conn.execute(
                    "INSERT OR IGNORE INTO fraud_events(event_id,transaction_id,account_id,fraud_type,description,severity,detected_at) VALUES (?,?,?,?,?,?,?)",
                    (f"FE{self.event_seq:010d}", tx["transaction_id"], a.account_id, campaign.fraud_type, tx["description"], "HIGH", tx["timestamp"]),
                )
                self.fraud_labels_csv.writerow({
                    "transaction_id": tx["transaction_id"], "account_id": a.account_id,
                    "campaign_id": campaign.campaign_id, "fraud_type": campaign.fraud_type,
                    "label_timestamp": tx["timestamp"],
                })
                emitted += 1
            campaign.remaining_events -= emitted
            campaign.next_fire_day = day + self.rng.randint(1, 4)
            self.metrics.fraud_events += emitted
            self.recent_stream.append(f"{campaign.fraud_type.replace('_', ' ').title()} Fraud Campaign Active")
        return rows

    def persist_transactions(self, rows: list[dict]) -> None:
        if not rows:
            return
        self.conn.executemany(
            "INSERT OR IGNORE INTO transactions(transaction_id,timestamp,sender_account,receiver_account,amount,channel,status,description,relationship_type,simulated_day,risk_score) "
            "VALUES (:transaction_id,:timestamp,:sender_account,:receiver_account,:amount,:channel,:status,:description,:relationship_type,:simulated_day,:risk_score)",
            rows,
        )
        for tx in rows:
            self.transactions_csv.writerow(tx)
            self.relationships_csv.writerow({
                "source_account": tx["sender_account"], "target_account": tx["receiver_account"],
                "relationship_type": "SENT_TO", "strength": tx["risk_score"],
                "cluster_id": tx["relationship_type"], "created_at": tx["timestamp"],
            })
        self.conn.commit()
        self.neo4j.write_transactions(rows[-1000:])
        self.metrics.transactions += len(rows)
        self.metrics.neo4j_nodes = self.neo4j.nodes
        self.metrics.neo4j_edges = self.neo4j.edges

    def compute_graph_analytics(self) -> None:
        rows = self.conn.execute(
            "SELECT sender_account, receiver_account, AVG(risk_score) risk, COUNT(*) c "
            "FROM transactions GROUP BY sender_account, receiver_account"
        ).fetchall()
        out_degree = Counter()
        in_degree = Counter()
        risk = defaultdict(float)
        for row in rows:
            out_degree[row["sender_account"]] += row["c"]
            in_degree[row["receiver_account"]] += row["c"]
            risk[row["sender_account"]] += row["risk"] * row["c"]
            risk[row["receiver_account"]] += row["risk"] * row["c"] * 0.5
        total = max(sum(out_degree.values()) + sum(in_degree.values()), 1)
        now = self.sim_time.isoformat(timespec="seconds")
        analytics = []
        for aid in set(out_degree) | set(in_degree):
            degree = out_degree[aid] + in_degree[aid]
            pagerank = (in_degree[aid] + 1) / total
            betweenness = min(1.0, (out_degree[aid] * in_degree[aid]) / max(total, 1))
            propagated = min(1.0, risk[aid] / max(degree, 1))
            community = self.account_by_id.get(aid).cluster_id if aid in self.account_by_id else "unknown"
            analytics.append((aid, pagerank, degree / total, betweenness, community, propagated, now))
        self.conn.executemany(
            "INSERT OR REPLACE INTO graph_analytics(account_id,pagerank,degree_centrality,betweenness,community_id,propagated_risk_score,updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            analytics[:50000],
        )
        self.conn.commit()

    def print_live(self, batch: list[dict]) -> None:
        if batch:
            tx = batch[-1]
            self.recent_stream.append(f"{tx['sender_account']} -> {tx['receiver_account']} | INR {tx['amount']:.2f} | {tx['channel']}")
        sys.stdout.write("\033[2J\033[H")
        print(f"[{self.sim_time.isoformat(timespec='seconds')}] speed={self.speed}")
        for line in list(self.recent_stream)[-6:]:
            print(line)
        print()
        print(f"Accounts:        {self.metrics.active_accounts:,}/{self.account_count:,}")
        print(f"Transactions:    {self.metrics.transactions:,}")
        print(f"TPS:             {self.metrics.tps:,.2f}")
        print(f"Fraud Events:    {self.metrics.fraud_events:,}")
        print(f"Mule Networks:   {self.metrics.mule_networks:,}")
        print(f"Neo4j Nodes:     {self.metrics.neo4j_nodes:,}")
        print(f"Neo4j Edges:     {self.metrics.neo4j_edges:,}")
        sys.stdout.flush()


def main() -> None:
    Ecosystem().run()


if __name__ == "__main__":
    main()
