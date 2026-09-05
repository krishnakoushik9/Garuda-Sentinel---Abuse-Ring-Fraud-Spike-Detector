REGULATORY_SOURCES = {
    "RBI_CAUTION_LIST": {
        "description": "Accounts cautioned by RBI/IBA",
        "update_frequency": "daily",
        "action": "flag_account_cautioned"
    },
    "NPCI_BLOCKED_VPA": {
        "description": "Blocked UPI Virtual Payment Addresses",
        "update_frequency": "real_time",
        "action": "block_transaction"
    },
    "FIU_IND_STR_PATTERNS": {
        "description": "Suspicious transaction patterns from FIU-IND",
        "update_frequency": "weekly",
        "action": "update_detection_rules"
    },
    "CRILC_FRAUD_ACCOUNTS": {
        "description": "Fraud accounts reported to CRILC (RBI)",
        "update_frequency": "daily", 
        "action": "auto_flag_account"
    },
    "I4C_CYBER_FRAUD_REGISTRY": {
        "description": "National Cyber Crime Reporting Portal accounts",
        "update_frequency": "real_time",
        "action": "investigate_immediately"
    }
}
