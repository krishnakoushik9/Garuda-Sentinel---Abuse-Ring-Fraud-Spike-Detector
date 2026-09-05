CHANNELS = {
    "UPI": {"limit_per_txn": 100000, "daily_limit": 200000, "real_time": True},
    "IMPS": {"limit_per_txn": 500000, "daily_limit": 1000000, "real_time": True},
    "NEFT": {"limit_per_txn": None, "settlement": "batch_hourly", "real_time": False},
    "RTGS": {"limit_per_txn_min": 200000, "real_time": True, "high_value": True},
    "CARD_POS": {"limit_per_txn": 200000, "real_time": True},
    "ATM": {"daily_limit": 50000, "real_time": True, "cash": True},
    "MOBILE_BANKING": {"limit_per_txn": 1000000, "real_time": True},
    "INTERNET_BANKING": {"limit_per_txn": None, "real_time": True}
}

# Suspicious channel combinations (mule laundering patterns)
SUSPICIOUS_CHANNEL_SEQUENCES = [
    ["NEFT_IN", "UPI_OUT_MULTIPLE"],       # Batch in, instant scatter
    ["UPI_IN", "ATM_OUT"],                 # Instant in, cash out
    ["IMPS_IN", "UPI_OUT", "ATM_OUT"],     # Rapid layering to cash
    ["RTGS_IN", "NEFT_OUT_MULTIPLE"],      # High value split
    ["MOBILE_IN", "CARD_POS_MULTIPLE"],    # Digital to merchant scatter
]
