import json
import random
import time
from datetime import datetime, timezone
from elasticsearch import Elasticsearch
from dotenv import load_dotenv
import os

load_dotenv()

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"))
INDEX = os.getenv("LOG_INDEX", "aiops-logs")

SERVICES = ["api-gateway", "auth-service", "db-worker", "cache-service", "notification-service"]
LOG_LEVELS = ["INFO", "INFO", "INFO", "INFO", "WARNING", "ERROR"]
ERROR_MESSAGES = [
    "Connection timeout after 30s",
    "Database query exceeded 5000ms",
    "Memory usage above 90%",
    "Disk usage critical: 95% full",
    "Failed to authenticate request",
    "Upstream service unreachable",
    "CPU spike detected: 98%",
]
INFO_MESSAGES = [
    "Request processed successfully",
    "Health check passed",
    "Cache hit ratio: 94%",
    "Scheduled job completed",
    "User session started",
    "Config reloaded",
]

def generate_log(inject_anomaly=False):
    service = random.choice(SERVICES)
    level = "ERROR" if inject_anomaly else random.choice(LOG_LEVELS)
    message = random.choice(ERROR_MESSAGES) if level == "ERROR" else random.choice(INFO_MESSAGES)
    return {
        "@timestamp": datetime.now(timezone.utc).isoformat(),
        "service": service,
        "level": level,
        "message": message,
        "response_time_ms": random.randint(800, 5000) if inject_anomaly else random.randint(10, 200),
        "cpu_percent": random.uniform(70, 99) if inject_anomaly else random.uniform(5, 40),
        "memory_percent": random.uniform(80, 95) if inject_anomaly else random.uniform(20, 60),
        "error_count": random.randint(10, 50) if inject_anomaly else random.randint(0, 2),
        "host": f"server-{random.randint(1, 5)}",
    }

def create_index():
    try:
        es.indices.create(index=INDEX, mappings={
            "properties": {
                "@timestamp":       {"type": "date"},
                "service":          {"type": "keyword"},
                "level":            {"type": "keyword"},
                "message":          {"type": "text"},
                "response_time_ms": {"type": "float"},
                "cpu_percent":      {"type": "float"},
                "memory_percent":   {"type": "float"},
                "error_count":      {"type": "integer"},
                "host":             {"type": "keyword"},
            }
        })
        print(f"✅ Created index: {INDEX}")
    except Exception as e:
        if "resource_already_exists_exception" in str(e).lower():
            print(f"ℹ️  Index '{INDEX}' already exists, skipping creation.")
        else:
            raise
def ship_logs(count=100, anomaly_rate=0.1):
    create_index()
    print(f"Shipping {count} logs to Elasticsearch...\n")
    for i in range(count):
        inject = random.random() < anomaly_rate
        log = generate_log(inject_anomaly=inject)
        es.index(index=INDEX, document=log)
        status = "⚠️  ANOMALY" if inject else "✓ normal"
        print(f"  [{i+1:03d}] {log['service']:25s} {log['level']:8s} {status}")
        time.sleep(0.05)
    print(f"\n✅ Done. {count} logs in '{INDEX}'")
    print("👉 Open Kibana → http://localhost:5601 → Discover → aiops-logs")

if __name__ == "__main__":
    ship_logs(count=100, anomaly_rate=0.1)
