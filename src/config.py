import os
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

# Manually load .env if exists
env_path = os.path.join(ROOT, ".env")
if os.path.exists(env_path):
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                # set value if not already set in environment
                if k.strip() not in os.environ:
                    os.environ[k.strip()] = v.strip()

# SQLite
SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH")
if not SQLITE_DB_PATH:
    if os.path.exists("./database/ecosystem.db"):
        SQLITE_DB_PATH = "./database/ecosystem.db"
    elif os.path.exists("./database/banking.db"):
        SQLITE_DB_PATH = "./database/banking.db"
    else:
        SQLITE_DB_PATH = "./data/banking.db"


# Neo4j
NEO4J_URI = os.environ.get("NEO4J_URI", os.environ.get("NEO4J_URL", "bolt://localhost:7687"))
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "fraud_detection_2026")

# Redis
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

# Parse Redis host/port from URL for dependencies expecting separated properties
try:
    parsed_redis = urlparse(REDIS_URL)
    REDIS_HOST = parsed_redis.hostname or "localhost"
    REDIS_PORT = parsed_redis.port or 6379
except Exception:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379

# Kafka
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "localhost:9092")

# Government data ingestion
USE_REAL_GOVDATA = os.environ.get("USE_REAL_GOVDATA", "false").strip().lower() in {"1", "true", "yes", "on"}

# Cognee Cloud Settings
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY")
COGNEE_BASE_URL = os.environ.get("COGNEE_BASE_URL", "https://tenant-3d30d425-a5a1-488d-ad2c-a1444ffc2914.aws.cognee.ai").strip()
COGNEE_TENANT_ID = os.environ.get("COGNEE_TENANT_ID", "3d30d425-a5a1-488d-ad2c-a1444ffc2914").strip()
COGNEE_USER_ID = os.environ.get("COGNEE_USER_ID", "dd98b1ea-5f7e-4b56-b255-e96b98632d51").strip()

# API
API_PORT = int(os.environ.get("API_PORT", 8000))
API_HOST = os.environ.get("API_HOST", "0.0.0.0")

# Models
MODEL_DIR = os.environ.get("MODEL_DIR", "./models")
SEQ_LEN = int(os.environ.get("SEQ_LEN", 15))
