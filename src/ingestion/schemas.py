from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class TransactionAlert(BaseModel):
    alert_id: str
    source: Literal["FMS", "TMS", "GOVT_CYBER", "INTERNAL"]
    alert_type: str  # VELOCITY_BREACH, STRUCTURING, MULE_SUSPECTED, CYBER_FRAUD_TICKET
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    account_id: str
    related_accounts: List[str]
    amount: Optional[float] = None
    timestamp: datetime
    raw_payload: dict
    channel: Optional[str] = None # UPI, IMPS, NEFT, RTGS, CARD
    govt_ticket_id: Optional[str] = None # for I4C/NCRP tickets
    description: str

class NationalCyberAlert(BaseModel):
    ticket_id: str           # NCRP complaint number format: XXXXX/YYYY
    complainant_account: str
    fraudulent_accounts: List[str]
    fraud_type: str          # OTP_FRAUD, VISHING, PHISHING, SIM_SWAP, UPI_FRAUD
    amount_lost: float
    reported_at: datetime
    status: str              # OPEN, INVESTIGATING, RESOLVED
    source_portal: Literal["NCRP", "I4C", "CFCFRMS", "CYBERCRIME_GOV"]

class TMSAlert(BaseModel):
    tms_alert_id: str
    rule_triggered: str      # e.g. "RULE_047_STRUCTURING", "RULE_012_VELOCITY"
    account_id: str
    risk_score: float
    transaction_ids: List[str]
    alert_timestamp: datetime
    analyst_notes: Optional[str] = None
    disposition: Optional[str] = None  # SAR_FILED, FALSE_POSITIVE, PENDING

class CrossChannelEvent(BaseModel):
    event_id: str
    primary_account: str
    channels_involved: List[str]  # multiple channels = higher risk
    total_amount: float
    time_window_minutes: int
    transaction_count: int
    pattern: str  # CHANNEL_HOPPING, RAPID_LAYERING, CROSS_BANK_RELAY
