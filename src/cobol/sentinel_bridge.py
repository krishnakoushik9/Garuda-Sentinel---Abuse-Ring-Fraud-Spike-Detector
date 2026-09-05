import json
import os
import subprocess
import logging
from kafka import KafkaConsumer, KafkaProducer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("COBOL_Bridge")

KAFKA_BROKER = "localhost:9092"
RISK_TOPIC = "sentinel-risk-events"
DECISION_TOPIC = "sentinel-decisions"

def run_cobol_agent(account_id: str, cluster_id: str, risk: float, velocity: float, contam: float, amount: float, channel: str):
    # Formulate space-separated fixed length copybook packet to feed to GnuCOBOL
    # Pad or format numbers to 3 digits, amount to float string
    risk_pct = f"{int(risk * 100):03d}"
    vel_pct = f"{int(velocity * 100):03d}"
    contam_pct = f"{int(contam * 100):03d}"
    amt_str = f"{amount:010.2f}"
    
    # ACC007036 MULE00001 095 085 090 0044192.85 UPI
    input_str = f"{account_id[:10]} {cluster_id[:10]} {risk_pct} {vel_pct} {contam_pct} {amt_str} {channel[:5]}\n"
    
    try:
        binary_path = "/home/krsna/Desktop/BOI/build/sentinel_agent"
        if not os.path.exists(binary_path):
            raise FileNotFoundError("COBOL Binary build/sentinel_agent not found. Run scripts/build.sh first.")

        proc = subprocess.run(
            [binary_path],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=2.0
        )
        
        if proc.returncode != 0:
            logger.error(f"COBOL Agent failed with error: {proc.stderr}")
            return None

        # Parse output for DECISION_RESULT
        for line in proc.stdout.splitlines():
            if line.startswith("DECISION_RESULT:"):
                # Format: DECISION_RESULT: [action] [decision_code] [copybook_hex] [reason]
                parts = line.replace("DECISION_RESULT:", "").strip().split(maxsplit=3)
                if len(parts) >= 3:
                    action = parts[0].strip()
                    code = parts[1].strip()
                    hex_buf = parts[2].strip()
                    reason = parts[3].strip() if len(parts) == 4 else "APPROVED BY COBOL RUNTIME"
                    
                    return {
                        "action": action,
                        "decision_code": code,
                        "cobol_copybook_hex": hex_buf,
                        "explanation": f"[COBOL Runtime] {reason}"
                    }
        logger.error(f"Failed to find DECISION_RESULT in COBOL stdout: {proc.stdout}")
        return None
    except Exception as e:
        logger.error(f"Error executing COBOL agent: {str(e)}")
        return None

def main():
    logger.info("Initializing Kafka COBOL Bridge Daemon...")
    
    consumer = KafkaConsumer(
        RISK_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        group_id="cobol-group",
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda x: json.loads(x.decode("utf-8"))
    )
    
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    
    logger.info(f"COBOL Bridge fully listening to Kafka topic: {RISK_TOPIC}")
    
    for message in consumer:
        try:
            event = message.value
            logger.info(f"Ingested risk event from Kafka: {event}")
            
            account_id = event.get("account_id", "UNKNOWN")
            cluster_id = event.get("cluster_id", "NO_MULE_NETWORK")
            risk = float(event.get("risk_score", 0.0))
            velocity = float(event.get("velocity_score", 0.0))
            contam = float(event.get("contamination_score", 0.0))
            amount = float(event.get("amount", 0.0))
            channel = event.get("channel", "UPI")
            
            # Execute COBOL
            cobol_decision = run_cobol_agent(account_id, cluster_id, risk, velocity, contam, amount, channel)
            
            if cobol_decision:
                decision_payload = {
                    "account_id": account_id,
                    "action": cobol_decision["action"],
                    "decision_code": cobol_decision["decision_code"],
                    "cobol_copybook_hex": cobol_decision["cobol_copybook_hex"],
                    "explanation": cobol_decision["explanation"],
                    "decision_source": "COBOL Sentinel Runtime"
                }
                
                producer.send(DECISION_TOPIC, value=decision_payload)
                producer.flush()
                logger.info(f"Published decision to Kafka: {decision_payload}")
            else:
                logger.error("COBOL execution returned empty result, skipping publication.")
        except Exception as e:
            logger.error(f"Error handling consumer message: {str(e)}")

if __name__ == "__main__":
    main()
