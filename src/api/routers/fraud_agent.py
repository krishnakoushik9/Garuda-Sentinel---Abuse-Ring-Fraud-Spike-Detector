from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sqlite3
import json
import os
import requests
from datetime import datetime

from src.api.deps import get_db
from src.config import SQLITE_DB_PATH
from src.agents.pdf_generator import generate_investigation_pdf
from src.services.memory_service import CogneeMemoryService
import asyncio

router = APIRouter(prefix="/agent-investigation", tags=["Fraud Investigation Agent"])

# Ensure exports directory exists
EXPORTS_DIR = "/home/krsna/Desktop/BOI/exports"
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Schema definitions
class AgentRequest(BaseModel):
    risk_score: float
    community: str
    graph_neighbors: List[Dict[str, Any]]
    recent_transactions: List[Dict[str, Any]]
    xgboost_features: Dict[str, Any]
    lstm_score: float
    gnn_score: float

class AgentResponse(BaseModel):
    report: str
    pdf_download_url: str
    rate_limit_remaining: int

def init_agent_db():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_rate_limit (
                date TEXT PRIMARY KEY,
                count INTEGER
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_reports (
                id TEXT PRIMARY KEY,
                community_id TEXT,
                report_text TEXT,
                pdf_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()

# Initialize DB on import
init_agent_db()

def check_and_increment_rate_limit() -> int:
    """Enforces absolute daily cap of 10 executions."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        row = conn.execute("SELECT count FROM agent_rate_limit WHERE date = ?", (today,)).fetchone()
        if row:
            count = row[0]
            if count >= 10:
                raise HTTPException(
                    status_code=429, 
                    detail="Daily rate limit exceeded. The Fraud Investigation Agent can only run 10 times per day."
                )
            new_count = count + 1
            conn.execute("UPDATE agent_rate_limit SET count = ? WHERE date = ?", (new_count, today))
        else:
            new_count = 1
            conn.execute("INSERT INTO agent_rate_limit (date, count) VALUES (?, 1)", (today,))
        conn.commit()
        return 10 - new_count
    finally:
        conn.close()

@router.post("/investigate", response_model=AgentResponse)
async def run_agent_investigation(req: AgentRequest):
    # 1. Rate Limit Enforcement
    remaining_runs = check_and_increment_rate_limit()

    # 2. Extract API Key
    groq_api_key = os.environ.get("GROQ_API_KEY", "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")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="Groq API key not configured on backend.")

    # 3. Call Groq API
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    # Format telemetry data for LLM
    neighbors_str = json.dumps(req.graph_neighbors[:15], indent=2)
    txns_str = json.dumps(req.recent_transactions[:10], indent=2)
    features_str = json.dumps(req.xgboost_features, indent=2)

    past_cases_context = await CogneeMemoryService.recall_past_cases(req.community, "layering loops structuring")

    prompt = f"""
You are the Lead Fraud Investigator AI Agent at Aegis Bank (Aegis Sentinel Intelligence Workstation).
You are analyzing a highly suspicious community cluster for potential mule account and money laundering activities.

Here is the telemetry data gathered from Graph analytics, GNN models, temporal anomalies, and XGBoost feature explainability:

[Historical Intelligence Memory (Cognee)]
{past_cases_context}

[Telemetry Data]
- Community Cluster: {req.community}
- Aggregated Risk Score: {req.risk_score:.2f}
- GNN Propagation Score: {req.gnn_score:.2f}
- LSTM Sequence Anomaly Score: {req.lstm_score:.2f}
- Suspected Neighbors: {neighbors_str}
- Recent Transaction Timeline: {txns_str}
- XGBoost Explainability SHAP Features: {features_str}

Your output MUST be a valid JSON object containing exactly two keys:
1. "summary_report": A rich, highly professional markdown formatted executive summary that will be displayed directly on the investigator's web portal.
2. "pdf_markdown": A highly structured, extremely detailed 4-page markdown report designed for automatic CAD compilation. You MUST use exactly three '---' dividers to separate this content into exactly 4 pages.

Do NOT include any surrounding codeblocks, markdown annotations, or introductory/explanatory text outside the JSON. Return only the raw JSON string.

Here is the required outline for the 4 PDF pages:

# Page 1: EXECUTIVE BRIEFING & CORE INTELLIGENCE
- Title: FINANCIAL SUSPICION REPORT: COMMUNITY {req.community}
- Include metadata table showing: Community ID, Aggregated Risk Level (HIGH), Recommendation Status (FREEZE CLUSTER), Detection Date (Today), Investigating Agency (DFIA - Aegis).
- Section: Executive Suspicion Statement (summarize the core findings).
- Section: Key Anomaly Summary (GNN: {req.gnn_score:.2f}, LSTM: {req.lstm_score:.2f}, Risk: {req.risk_score:.2f}).
- Section: Immediate Action Items (Freeze Cluster, Trigger STR, Escalate to Analyst).
---
# Page 2: NETWORK TOPOLOGY & CROSS-CHANNEL CORRELATION
- Title: GRAPH ANALYTICS & PROPAGATION METRICS
- Section: Peer Connection Summary (Discuss fan-out / fan-in degree of centrality, connections to other mule groups).
- Include table of suspected neighbors: Account ID, Pagerank, propagated_risk_score, status.
- Section: Velocity Indicators (rapid dispersal patterns).
---
# Page 3: MACHINE LEARNING FORENSICS & XGBOOST SHAP INSIGHTS
- Title: ALGORITHMIC COMPLIANCE AUDIT
- Section: XGBoost Classification Analysis (Explain the SHAP features like dormancy break flags, amount z-scores, velocity flags).
- Include Table of Top Features: Feature Name, SHAP Value, Risk Weight, Verdict.
- Section: Temporal Recurrent Analysis (Deep dive into the LSTM sequence pattern anomalies).
---
# Page 4: REGULATORY SAR COMPLIANCE & ESCALATION TIMELINE
- Title: LAW ENFORCEMENT & NPCI COMPLIANCE STRATEGIES
- Section: STR Filing Recommendations (Filing code, authority body, regulatory timeline).
- Section: Escalation Action Matrix (Analyst assignments, timeline, evidence lockers).
- Analyst signatures, badge numbers, and confidential stamping.
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a professional, clinical financial compliance and money laundering AI auditor. You output raw JSON strictly conforming to the requested schema."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=45)
        if res.status_code != 200:
            raise HTTPException(status_code=res.status_code, detail=f"Groq API returned error: {res.text}")
        
        response_json = res.json()
        content_str = response_json["choices"][0]["message"]["content"]
        
        try:
            parsed_data = json.loads(content_str)
        except Exception as e:
            # Fallback if LLM outputted JSON surrounded by markdown block
            cleaned = content_str.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            parsed_data = json.loads(cleaned.strip())

        summary_report = parsed_data.get("summary_report", "")
        pdf_markdown = parsed_data.get("pdf_markdown", "")

        if not pdf_markdown:
            pdf_markdown = summary_report

        # 4. Generate downloadable PDF
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{req.community}"
        pdf_filename = f"{report_id}.pdf"
        pdf_path = os.path.join(EXPORTS_DIR, pdf_filename)
        
        generate_investigation_pdf(pdf_markdown, pdf_path)
        
        asyncio.create_task(CogneeMemoryService.remember_investigation(report_id, req.community, summary_report, req.risk_score))

        # Save record in SQLite
        conn = sqlite3.connect(SQLITE_DB_PATH)
        try:
            conn.execute(
                "INSERT INTO agent_reports (id, community_id, report_text, pdf_path) VALUES (?, ?, ?, ?)",
                (report_id, req.community, summary_report, pdf_path)
            )
            conn.commit()
        finally:
            conn.close()

        # Build download path
        pdf_download_url = f"/api/v1/agent-investigation/download/{report_id}"

        return AgentResponse(
            report=summary_report,
            pdf_download_url=pdf_download_url,
            rate_limit_remaining=remaining_runs
        )

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Fraud Agent Investigation failed: {str(e)}")


@router.get("/download/{report_id}")
def download_pdf_report(report_id: str):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    try:
        row = conn.execute("SELECT pdf_path FROM agent_reports WHERE id = ?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Investigation PDF Report not found.")
        pdf_path = row[0]
    finally:
        conn.close()

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF Report file missing from disk.")

    return FileResponse(
        path=pdf_path, 
        media_type="application/pdf", 
        filename=os.path.basename(pdf_path)
    )

@router.get("/memory-graph/{community_id}")
async def get_memory_graph(community_id: str):
    data = await CogneeMemoryService.get_memory_graph_data(community_id)
    return data
