#!/usr/bin/env python3
"""Ingest DataSet.csv (real bank regulatory feed) into the banking ecosystem DB.

Usage:
    python scripts/ingest_dataset.py [--csv SETDATA/DataSet.csv] [--db database/ecosystem.db]
"""
from __future__ import annotations

import argparse
import random
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

# Occupation → estimated monthly income
INCOME_MAP = {
    "SALARIED": 50000, "SELFEMPLOYED": 40000, "STUDENT": 8000,
    "RETIRED": 20000, "HOUSEWIFE": 15000, "PROFESSIONAL": 60000,
}
DEFAULT_INCOME = 35000

# Channel assignment by segment/occupation
CHANNEL_MAP = {
    "CORPORATE": ["NEFT", "IMPS", "NEFT", "NEFT"],
    "RETAIL": ["UPI", "IMPS", "UPI", "MERCHANT"],
}
OCC_CHANNEL = {
    "STUDENT": ["UPI", "UPI", "MERCHANT"],
    "RETIRED": ["NEFT", "IMPS"],
    "SALARIED": ["SALARY", "UPI", "IMPS", "NEFT"],
    "SELFEMPLOYED": ["UPI", "IMPS", "TRANSFER", "NEFT"],
}


def _income_range(income: float) -> str:
    if income < 25000: return "low"
    if income < 100000: return "middle"
    if income < 350000: return "upper_middle"
    return "high"


def _parse_date(raw) -> str | None:
    """Parse D-M-YYYY → YYYY-MM-DD. Returns None on failure."""
    if pd.isna(raw) or not str(raw).strip():
        return None
    try:
        parts = str(raw).strip().split("-")
        if len(parts) == 3:
            d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, IndexError):
        pass
    return None


def safe_int(val, default=None):
    if pd.isna(val) or not str(val).strip():
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


class DataSetIngester:
    def __init__(self, csv_path: str, db_path: str, batch_size: int = 500):
        self.csv_path = Path(csv_path)
        self.db_path = Path(db_path)
        self.batch_size = batch_size
        self.df: pd.DataFrame | None = None
        self.dense_features: list[str] = []
        self.skip_features: list[str] = []
        self.mule_ids: list[str] = []
        self.all_account_ids: list[str] = []
        self.stats: dict = {}
        self.rng = random.Random(42)
        self._start = time.time()

    # ------------------------------------------------------------------
    def run(self):
        print("=" * 60)
        print("  DataSet.csv → Banking Ecosystem Ingestion Pipeline")
        print("=" * 60)
        self.apply_schema_v2()
        self._load_csv()
        self.analyse_features()
        self.ingest_accounts()
        self.ingest_features()
        self.synthesise_transactions()
        self.populate_account_profiles()
        self.populate_mule_accounts()
        self.populate_graph_analytics()
        self.register_data_source()
        self.print_summary()

    # ------------------------------------------------------------------
    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _load_csv(self):
        print(f"\n→ Loading {self.csv_path} ...")
        self.df = pd.read_csv(self.csv_path, low_memory=False)
        print(f"  Loaded {len(self.df):,} rows × {len(self.df.columns):,} columns")

    # ------------------------------------------------------------------
    def apply_schema_v2(self):
        print("\n→ Applying schema_v2.sql ...")
        schema_path = ROOT / "database" / "schema_v2.sql"
        sql = schema_path.read_text(encoding="utf-8")
        with self._conn() as conn:
            conn.executescript(sql)
        print("  Schema V2 applied (IF NOT EXISTS — safe to re-run)")

    # ------------------------------------------------------------------
    def analyse_features(self):
        print("\n→ Analysing feature sparsity (F1–F3885) ...")
        feature_cols = [c for c in self.df.columns if c.startswith("F") and c[1:].isdigit()]
        feature_cols = [c for c in feature_cols if 1 <= int(c[1:]) <= 3885]
        n = len(self.df)
        na_rates = self.df[feature_cols].isna().sum() / n

        self.dense_features = [c for c in feature_cols if na_rates[c] < 0.50]
        self.skip_features = [c for c in feature_cols if na_rates[c] >= 0.90]
        mid = [c for c in feature_cols if 0.50 <= na_rates[c] < 0.90]

        print(f"  Dense (<50% NA):    {len(self.dense_features):,} features → stored")
        print(f"  Mid (50-90% NA):    {len(mid):,} features → stored")
        print(f"  Sparse (≥90% NA):   {len(self.skip_features):,} features → skipped")
        # Include mid-range too in dense for storage
        self.dense_features = [c for c in feature_cols if na_rates[c] < 0.90]

    # ------------------------------------------------------------------
    def ingest_accounts(self):
        print("\n→ Ingesting accounts ...")
        df = self.df
        now = datetime.now().isoformat(timespec="seconds")
        conn = self._conn()

        # Identify the unnamed index column
        idx_col = df.columns[0]  # First column is the unnamed index

        ds_rows = []
        acc_rows = []
        count = 0

        for _, row in df.iterrows():
            row_idx = safe_int(row[idx_col], count)
            account_id = f"REAL{row_idx:06d}"
            self.all_account_ids.append(account_id)

            # Parse fields
            reg_date = _parse_date(row.get("F3888"))
            occ_raw = str(row.get("F3891", "")).strip().upper() if pd.notna(row.get("F3891")) else "UNKNOWN"
            gender = str(row.get("F3892", "")).strip().upper() if pd.notna(row.get("F3892")) and str(row.get("F3892")).strip() else "UNKNOWN"
            segment = str(row.get("F3893", "RETAIL")).strip().upper() if pd.notna(row.get("F3893")) else "RETAIL"
            acct_type = str(row.get("F3886", "")).strip() if pd.notna(row.get("F3886")) else None
            scheme = str(row.get("F3889", "")).strip() if pd.notna(row.get("F3889")) else None
            region = str(row.get("F3890", "")).strip() if pd.notna(row.get("F3890")) else None
            f3887 = safe_int(row.get("F3887"))
            is_mule = safe_int(row.get("F3924"), 0)

            if is_mule == 1:
                self.mule_ids.append(account_id)

            # Risk profile
            if is_mule == 1:
                risk = "HIGH"
            elif segment == "CORPORATE":
                risk = "MEDIUM"
            else:
                risk = "LOW"

            # F3894-F3923 (30 behavioral columns)
            behav = []
            for fi in range(3894, 3924):
                v = row.get(f"F{fi}")
                behav.append(safe_int(v))

            ds_rows.append((
                account_id, row_idx, acct_type, reg_date, scheme, region,
                occ_raw, gender, segment, f3887, *behav,
                is_mule, risk, "ACTIVE", "REGULATORY_FEED", now
            ))

            # Mirror row for main accounts table
            monthly_income = INCOME_MAP.get(occ_raw, DEFAULT_INCOME)
            if reg_date:
                try:
                    reg_year = int(reg_date[:4])
                    age = max(18, min(80, datetime.now().year - reg_year))
                except ValueError:
                    age = 30
            else:
                age = 30

            acc_rows.append((
                account_id, f"Customer {row_idx}", age, "UNKNOWN",
                region if region else "UNKNOWN",
                occ_raw, segment, float(monthly_income),
                _income_range(monthly_income),
                reg_date if reg_date else now[:10],
                0.0, 0.0, risk, None, None,
                f"CLUSTER_REAL_{segment}", "ACTIVE", now, now
            ))

            count += 1
            if len(ds_rows) >= self.batch_size:
                self._flush_accounts(conn, ds_rows, acc_rows)
                ds_rows, acc_rows = [], []
                if count % 1000 == 0:
                    print(f"  {count:,} / {len(df):,} rows ingested")

        self._flush_accounts(conn, ds_rows, acc_rows)
        conn.close()
        self.stats["accounts"] = count
        self.stats["mules"] = len(self.mule_ids)
        print(f"  ✓ {count:,} accounts ingested ({len(self.mule_ids)} confirmed mules)")

    def _flush_accounts(self, conn, ds_rows, acc_rows):
        if not ds_rows:
            return
        placeholders_ds = ",".join(["?"] * 45)  # 10 base + 30 behav + 5 tail
        conn.executemany(
            f"INSERT OR REPLACE INTO dataset_accounts VALUES ({placeholders_ds})",
            ds_rows
        )
        conn.executemany(
            "INSERT OR REPLACE INTO accounts "
            "(account_id,name,age,city,state,occupation,customer_segment,"
            "monthly_income,income_range,account_open_date,initial_balance,"
            "balance,risk_profile,employer,merchant_category,cluster_id,"
            "status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            acc_rows
        )
        conn.commit()

    # ------------------------------------------------------------------
    def ingest_features(self):
        print("\n→ Ingesting sparse features (vectorised) ...")
        df = self.df
        idx_col = df.columns[0]
        conn = self._conn()
        
        print("  Melting dense features...")
        melted = pd.melt(
            df,
            id_vars=[idx_col],
            value_vars=self.dense_features,
            var_name='feature_name',
            value_name='feature_value'
        )
        
        print("  Filtering nulls...")
        melted = melted.dropna(subset=['feature_value'])
        
        print("  Converting values to numeric (dropping strings)...")
        melted['feature_value'] = pd.to_numeric(melted['feature_value'], errors='coerce')
        melted = melted.dropna(subset=['feature_value'])
        
        print("  Mapping account IDs...")
        melted['account_id'] = melted[idx_col].apply(lambda x: f"REAL{safe_int(x, 0):06d}" if pd.notna(x) else "REAL000000")
        
        rows = list(melted[['account_id', 'feature_name', 'feature_value']].itertuples(index=False, name=None))
        total = len(rows)
        
        print(f"  Inserting {total:,} features into SQLite...")
        for i in range(0, total, 10000):
            batch = rows[i:i+10000]
            conn.executemany(
                "INSERT OR REPLACE INTO dataset_features (account_id, feature_name, feature_value) VALUES (?,?,?)",
                batch
            )
            conn.commit()
            if (i // 10000) % 10 == 0:
                print(f"    {min(i + 10000, total):,} / {total:} features inserted")
                
        conn.close()
        self.stats["features"] = total
        print(f"  ✓ {total:,} feature values stored")

    # ------------------------------------------------------------------
    def synthesise_transactions(self):
        print("\n→ Synthesising transactions from behavioral aggregates ...")
        conn = self._conn()
        df = self.df
        idx_col = df.columns[0]
        txn_seq = 0
        txn_rows = []
        mule_txn_count = 0
        mule_set = set(self.mule_ids)
        base_date = datetime(2025, 1, 1)

        for _, row in df.iterrows():
            row_idx = safe_int(row[idx_col], 0)
            account_id = f"REAL{row_idx:06d}"
            is_mule = safe_int(row.get("F3924"), 0)
            segment = str(row.get("F3893", "RETAIL")).strip().upper() if pd.notna(row.get("F3893")) else "RETAIL"
            occ = str(row.get("F3891", "")).strip().upper() if pd.notna(row.get("F3891")) else "UNKNOWN"

            # Use F3895 as tx count hint, F3894 as age-in-days hint
            f3895 = safe_int(row.get("F3895"), 10)
            f3894 = safe_int(row.get("F3894"), 30)
            n_txns = max(3, min(20, f3895 // 30 if f3895 > 60 else 5))

            # Channel selection
            channels = OCC_CHANNEL.get(occ, CHANNEL_MAP.get(segment, ["UPI", "IMPS"]))

            for ti in range(n_txns):
                txn_seq += 1
                txn_id = f"RTXN{txn_seq:010d}"
                day_offset = self.rng.randint(0, max(f3894, 1))
                ts = (base_date + timedelta(days=day_offset, hours=self.rng.randint(8, 22),
                      minutes=self.rng.randint(0, 59))).isoformat(timespec="seconds")
                channel = self.rng.choice(channels)

                if is_mule and len(self.mule_ids) > 1:
                    # Cross-link mule accounts
                    receiver = self.rng.choice([m for m in self.mule_ids if m != account_id] or self.mule_ids)
                    amount = round(self.rng.uniform(5000, 95000), 2)
                    rel_type = "mule"
                    desc = self.rng.choice(["Fan-Out distribution", "Relay mule chain", "Layering transfer"])
                    risk = round(self.rng.uniform(0.65, 0.95), 4)
                    mule_txn_count += 1
                else:
                    # Normal — pick nearby account
                    offset = self.rng.randint(1, min(50, len(self.all_account_ids) - 1))
                    r_idx = (self.all_account_ids.index(account_id) + offset) % len(self.all_account_ids)
                    receiver = self.all_account_ids[r_idx]
                    amount = round(self.rng.uniform(100, 25000), 2)
                    rel_type = "stranger"
                    desc = f"{channel} payment"
                    risk = round(self.rng.uniform(0.01, 0.35), 4)

                txn_rows.append((
                    txn_id, ts, account_id, receiver, amount, channel,
                    "COMPLETED", desc, rel_type, day_offset, risk, "REGULATORY_FEED"
                ))

            if len(txn_rows) >= 2000:
                self._flush_txns(conn, txn_rows)
                txn_rows = []

        self._flush_txns(conn, txn_rows)
        conn.close()
        self.stats["transactions"] = txn_seq
        self.stats["mule_transactions"] = mule_txn_count
        print(f"  ✓ {txn_seq:,} transactions generated ({mule_txn_count:,} mule-linked)")

    def _flush_txns(self, conn, rows):
        if not rows:
            return
        # Insert into dataset_transactions_synthetic
        conn.executemany(
            "INSERT OR REPLACE INTO dataset_transactions_synthetic "
            "(transaction_id,timestamp,sender_account,receiver_account,amount,"
            "channel,status,description,relationship_type,simulated_day,risk_score,data_source) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            rows
        )
        # Also mirror into main transactions table
        conn.executemany(
            "INSERT OR REPLACE INTO transactions "
            "(transaction_id,timestamp,sender_account,receiver_account,amount,"
            "channel,status,description,relationship_type,simulated_day,risk_score) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[9], r[10]) for r in rows]
        )
        conn.commit()

    # ------------------------------------------------------------------
    def populate_account_profiles(self):
        print("\n→ Populating account_profiles ...")
        conn = self._conn()
        now = datetime.now().isoformat(timespec="seconds")
        mule_set = set(self.mule_ids)

        profiles = conn.execute("""
            SELECT sender_account, AVG(amount) avg_amt, COUNT(*) cnt, MAX(timestamp) last_ts
            FROM transactions WHERE sender_account LIKE 'REAL%'
            GROUP BY sender_account
        """).fetchall()

        rows = []
        for p in profiles:
            aid = p["sender_account"]
            is_m = aid in mule_set
            risk = round(0.9 + self.rng.uniform(-0.05, 0.05), 4) if is_m else round(0.1 + self.rng.uniform(0, 0.15), 4)
            # Lookup occupation/income from dataset_accounts
            da = conn.execute("SELECT occupation, segment FROM dataset_accounts WHERE account_id=?", (aid,)).fetchone()
            occ = da["occupation"] if da else "UNKNOWN"
            income = INCOME_MAP.get(occ, DEFAULT_INCOME)
            rows.append((aid, round(p["avg_amt"], 2), p["cnt"], p["last_ts"], risk, "VERIFIED", occ, float(income)))

        conn.executemany(
            "INSERT OR REPLACE INTO account_profiles "
            "(account_id,avg_transaction_amt,transaction_count,last_active,"
            "risk_score,kyc_status,occupation,monthly_income) VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        conn.close()
        self.stats["profiles"] = len(rows)
        print(f"  ✓ {len(rows):,} account profiles populated")

    # ------------------------------------------------------------------
    def populate_mule_accounts(self):
        print("\n→ Registering confirmed mule accounts ...")
        conn = self._conn()
        now = datetime.now().isoformat(timespec="seconds")
        n_chains = 10

        mule_rows = []
        network_ids = set()
        for i, aid in enumerate(self.mule_ids):
            chain_idx = i % n_chains + 1
            chain_id = f"REAL_CHAIN_{chain_idx}"
            layer = (i // n_chains) + 1
            # linked_account: next mule in the same chain
            same_chain = [m for j, m in enumerate(self.mule_ids) if j % n_chains + 1 == chain_idx and m != aid]
            linked = same_chain[0] if same_chain else None

            mule_rows.append((aid, "REGULATORY_CONFIRMED", chain_id, layer, linked, now))
            network_ids.add(chain_id)

        conn.executemany(
            "INSERT OR REPLACE INTO mule_accounts "
            "(account_id,pattern_type,chain_id,layer,linked_account,detected_at) "
            "VALUES (?,?,?,?,?,?)",
            mule_rows
        )

        for nid in sorted(network_ids):
            first_mule = next(m for i, m in enumerate(self.mule_ids) if i % n_chains + 1 == int(nid.split("_")[-1]))
            conn.execute(
                "INSERT OR REPLACE INTO mule_networks "
                "(network_id,pattern_type,source_account,created_at,active) VALUES (?,?,?,?,1)",
                (nid, "REGULATORY_CONFIRMED", first_mule, now)
            )

        conn.commit()
        conn.close()
        self.stats["mule_chains"] = len(network_ids)
        print(f"  ✓ {len(self.mule_ids)} mule accounts registered in {len(network_ids)} chains")

    # ------------------------------------------------------------------
    def populate_graph_analytics(self):
        print("\n→ Populating graph_analytics placeholders ...")
        conn = self._conn()
        now = datetime.now().isoformat(timespec="seconds")
        mule_set = set(self.mule_ids)

        rows = []
        for aid in self.all_account_ids:
            is_m = aid in mule_set
            da = conn.execute("SELECT segment FROM dataset_accounts WHERE account_id=?", (aid,)).fetchone()
            seg = da["segment"] if da else "RETAIL"
            rows.append((
                aid,
                1.0 if is_m else 0.1,
                0.0, 0.0,
                f"CLUSTER_REAL_{seg}",
                0.9 if is_m else 0.05,
                now
            ))

        conn.executemany(
            "INSERT OR REPLACE INTO graph_analytics "
            "(account_id,pagerank,degree_centrality,betweenness,community_id,"
            "propagated_risk_score,updated_at) VALUES (?,?,?,?,?,?,?)",
            rows
        )
        conn.commit()
        conn.close()
        self.stats["graph_nodes"] = len(rows)
        print(f"  ✓ {len(rows):,} graph analytics nodes populated")

    # ------------------------------------------------------------------
    def register_data_source(self):
        print("\n→ Registering data source ...")
        conn = self._conn()
        now = datetime.now().isoformat(timespec="seconds")

        # Deactivate all existing sources
        conn.execute("UPDATE data_source_registry SET is_active = 0")

        source_id = f"REGULATORY_{now.replace(':', '').replace('-', '')}"
        conn.execute(
            "INSERT OR REPLACE INTO data_source_registry "
            "(source_id,source_name,source_type,file_path,row_count,mule_count,ingested_at,is_active) "
            "VALUES (?,?,?,?,?,?,?,1)",
            (source_id, "Bank of India Regulatory Feed", "REGULATORY_FEED",
             str(self.csv_path), self.stats["accounts"], self.stats["mules"], now)
        )

        # Update simulation_control for dashboard API
        for key, val in [
            ("data_source", "REGULATORY_FEED"),
            ("status", "finished"),
            ("regulatory_row_count", str(self.stats["accounts"])),
            ("regulatory_mule_count", str(self.stats["mules"])),
        ]:
            conn.execute(
                "INSERT OR REPLACE INTO simulation_control (key, value, updated_at) VALUES (?,?,?)",
                (key, val, now)
            )

        conn.commit()
        conn.close()
        print("  ✓ Data source registered as REGULATORY_FEED (active)")

    # ------------------------------------------------------------------
    def print_summary(self):
        elapsed = time.time() - self._start
        print()
        print("┌──────────────────────────────────────────────┐")
        print("│  DataSet.csv Ingestion Summary               │")
        print("├───────────────────────────┬──────────────────┤")
        print(f"│  Total accounts           │ {self.stats.get('accounts', 0):>12,}   │")
        print(f"│  Confirmed mule accounts  │ {self.stats.get('mules', 0):>12,}   │")
        print(f"│  Dense features stored    │ {self.stats.get('features', 0):>12,}   │")
        print(f"│  Skipped sparse features  │ {len(self.skip_features):>12,}   │")
        print(f"│  Synthetic transactions   │ {self.stats.get('transactions', 0):>12,}   │")
        print(f"│  Mule transactions        │ {self.stats.get('mule_transactions', 0):>12,}   │")
        print(f"│  Graph nodes populated    │ {self.stats.get('graph_nodes', 0):>12,}   │")
        print(f"│  Active data source       │ {'REGULATORY_FEED':>16} │")
        print(f"│  Time elapsed             │ {elapsed:>11.1f}s   │")
        print("└───────────────────────────┴──────────────────┘")


def main():
    parser = argparse.ArgumentParser(description="Ingest DataSet.csv into banking ecosystem DB")
    parser.add_argument("--csv", default=str(ROOT / "SETDATA" / "DataSet.csv"), help="Path to DataSet.csv")
    parser.add_argument("--db", default=str(ROOT / "database" / "ecosystem.db"), help="Path to banking SQLite DB")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows per commit batch")
    args = parser.parse_args()

    ingester = DataSetIngester(args.csv, args.db, args.batch_size)
    ingester.run()


if __name__ == "__main__":
    main()
