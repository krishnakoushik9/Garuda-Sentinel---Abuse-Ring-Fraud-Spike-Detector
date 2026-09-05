from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import sqlite3
import json
import random

from src.config import SQLITE_DB_PATH
from src.regulatory.watchlist_manager import WatchlistManager
from src.regulatory.str_generator import STRGenerator
from src.regulatory.rfa_tracker import RFATracker
from src.regulatory.feed_simulator import RegulatoryFeedSimulator
from src.regulatory.news_feed import RegulatoryNewsFeed
from src.ingestion.govdata_injector import GovDataInjector

router = APIRouter(prefix="/regulatory", tags=["Regulatory Intelligence"])
govdata_router = APIRouter(prefix="/govdata", tags=["Government Data"])

# Instantiate controllers
watchlist_mgr = WatchlistManager()
str_gen = STRGenerator()
rfa_track = RFATracker()
news_aggregator = RegulatoryNewsFeed()
govdata_injector = GovDataInjector()

@router.get("/news", response_model=List[Dict[str, Any]])
def get_regulatory_news(query: Optional[str] = None):
    """Fetches real-time, unified Google News RSS and Reddit bank fraud feeds."""
    try:
        if query:
            google_items = news_aggregator.fetch_google_news(query)
            reddit_items = news_aggregator.fetch_reddit_news(query)
            items = google_items + reddit_items
            items.sort(key=lambda x: x["risk_score"], reverse=True)
            return items
        return news_aggregator.get_unified_feed()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch real-time news circulars: {e}")

@router.get("/watchlist", response_model=Dict[str, Any])
def get_watchlist():
    """Returns the current watchlist and breakdown statistics."""
    try:
        stats = watchlist_mgr.get_watchlist_stats()
        
        # Pull watchlist accounts
        accounts = []
        # Fallback to local SQLite pull
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT account_id, name, customer_segment, risk_profile, city, status FROM accounts WHERE status = 'GOVT_FLAGGED'"
        ).fetchall()
        conn.close()
        
        for r in rows:
            meta = watchlist_mgr.is_on_watchlist(r["account_id"]) or {}
            accounts.append({
                "account_id": r["account_id"],
                "name": r["name"],
                "customer_segment": r["customer_segment"],
                "risk_profile": r["risk_profile"] or "HIGH",
                "city": r["city"],
                "source": meta.get("source", "NCRP/I4C Portal"),
                "reason": meta.get("reason", "Government complaint ticket logged against account.")
            })
            
        return {
            "stats": stats,
            "watchlist": accounts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch watchlist: {e}")

@router.get("/strs", response_model=List[Dict[str, Any]])
def get_pending_strs():
    """Returns all pending Suspicious Transaction Reports (STRs)."""
    try:
        return str_gen.get_pending_strs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending STRs: {e}")

@router.post("/strs/{str_id}/file", response_model=Dict[str, str])
def file_str(str_id: str, analyst_id: str = Query("ANALYST_001")):
    """Marks a Suspicious Transaction Report as filed to FIU-IND."""
    try:
        str_gen.mark_str_filed(str_id, analyst_id)
        return {"status": "success", "message": f"STR {str_id} filed to FIU-IND successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to file STR: {e}")

@router.get("/rfa", response_model=Dict[str, Any])
def get_rfa_accounts():
    """Returns all Red-Flagged Accounts (RFA) with compliance timelines."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT a.account_id, a.name, a.risk_profile, r.reason, r.evidence, 
                   r.flagged_date, r.crilc_report_deadline, r.crilc_reported, 
                   r.fraud_classification_deadline, r.classification 
            FROM accounts a 
            JOIN rfa_accounts r ON a.account_id = r.account_id
            """
        ).fetchall()
        conn.close()
        
        rfa_list = []
        for r in rows:
            rfa_list.append(dict(r))
            
        overdue_crilc = rfa_track.get_overdue_crilc_reports()
        pending_class = rfa_track.get_pending_classifications()
        
        return {
            "rfa_accounts": rfa_list,
            "overdue_crilc_count": len(overdue_crilc),
            "pending_classifications_count": len(pending_class),
            "overdue_crilc_accounts": overdue_crilc,
            "pending_classifications_accounts": pending_class
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch RFA list: {e}")

@router.get("/alerts/feed", response_model=List[Dict[str, Any]])
def get_regulatory_feed_recent():
    """Returns recent regulatory warnings logged in the DB."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT event_id as id, transaction_id, account_id, fraud_type, severity, timestamp FROM fraud_events ORDER BY timestamp DESC LIMIT 20"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch regulatory alert feed: {e}")

@router.post("/simulate", response_model=Dict[str, Any])
def trigger_regulatory_simulation():
    """Triggers one round of simulated NCRP tickets and CRILC daily updates."""
    try:
        simulator = RegulatoryFeedSimulator()
        
        # 1. Simulate 1 NCRP ticket
        ncrp = simulator.simulate_i4c_realtime_ticket()
        watchlist_mgr.add_to_watchlist(
            account_id=ncrp["accused_accounts"][0],
            source="I4C_NCRP",
            reason=f"Govt ticket {ncrp['ticket_id']} category: {ncrp['category']}",
            severity="CRITICAL"
        )
        
        # 2. Simulate 3 CRILC reports
        crilcs = simulator.simulate_crilc_daily_update()[:3]
        for c in crilcs:
            watchlist_mgr.add_to_watchlist(
                account_id=c["account_id"],
                source="RBI_CRILC",
                reason=f"CRILC daily fraud report: {c['fraud_type']}",
                severity="HIGH"
            )
            
        # 3. Simulate 1 RFA flagging
        rfa_acc = random.choice(simulator.accounts)
        rfa_track.flag_account(
            account_id=rfa_acc,
            reason="Simulated High Risk Velocity Flag",
            evidence={"score": 0.94, "pattern": "STRUCTURING"}
        )
            
        return {
            "status": "success",
            "message": "Regulatory simulation round triggered successfully.",
            "simulated_data": {
                "ncrp_ticket": ncrp,
                "crilc_reports": crilcs,
                "red_flagged_account": rfa_acc
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Regulatory feed simulation failed: {e}")


@govdata_router.get("/status", response_model=Dict[str, Any])
def get_govdata_status():
    """Returns ingestion freshness, table counts, and live data source status."""
    try:
        return govdata_injector.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch govdata status: {e}")


@govdata_router.get("/upi-baseline", response_model=Dict[str, Any])
def get_govdata_upi_baseline():
    """Returns latest UPI national velocity baseline metrics."""
    try:
        return govdata_injector.get_upi_baseline()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch UPI baseline: {e}")


@govdata_router.get("/fraud-context", response_model=Dict[str, Any])
def get_govdata_fraud_context(
    fraud_category: Optional[str] = Query("UPI_FRAUD"),
    amount: Optional[float] = Query(0.0),
):
    """Returns RBI fraud stats for STR enrichment."""
    try:
        return govdata_injector.get_fraud_context(fraud_category=fraud_category, amount=amount)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch RBI fraud context: {e}")


@govdata_router.get("/geo-risk", response_model=Dict[str, Any])
def get_govdata_geo_risk():
    """Returns state cybercrime rankings and geo-risk deltas."""
    try:
        return govdata_injector.get_geo_risk()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch geo-risk: {e}")


@govdata_router.post("/refresh", response_model=Dict[str, Any])
async def refresh_govdata():
    """Manually triggers re-ingestion of all five data.gov.in sources."""
    try:
        return await govdata_injector.ingest_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Govdata refresh failed: {e}")
