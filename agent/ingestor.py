import os
import time
from datetime import datetime, timezone, timedelta
from elasticsearch import Elasticsearch
from dotenv import load_dotenv

load_dotenv()

es = Elasticsearch(os.getenv("ELASTICSEARCH_URL"))
LOG_INDEX = os.getenv("LOG_INDEX", "aiops-logs")


def get_metrics_for_service(service: str, minutes: int = 2) -> dict:
    """
    Pulls last N minutes of logs for a service and
    returns aggregated metrics as a flat dict.
    """
    now = datetime.now(timezone.utc)
    since = (now - timedelta(minutes=minutes)).isoformat()

    result = es.search(index=LOG_INDEX, query={
        "bool": {
            "must": [
                {"term":  {"service": service}},
                {"range": {"@timestamp": {"gte": since}}}
            ]
        }
    }, aggs={
        "avg_response_time": {"avg": {"field": "response_time_ms"}},
        "avg_cpu":           {"avg": {"field": "cpu_percent"}},
        "avg_memory":        {"avg": {"field": "memory_percent"}},
        "avg_error_count":   {"avg": {"field": "error_count"}},
        "error_rate": {
            "filter": {"term": {"level": "ERROR"}}
        }
    }, size=0)

    total_logs = result["hits"]["total"]["value"]
    aggs       = result["aggregations"]

    if total_logs == 0:
        return None

    error_count = aggs["error_rate"]["doc_count"]
    error_rate  = (error_count / total_logs * 100) if total_logs > 0 else 0.0

    return {
        "service":          service,
        "timestamp":        now.isoformat(),
        "total_logs":       total_logs,
        "avg_response_ms":  round(aggs["avg_response_time"]["value"] or 0, 2),
        "avg_cpu":          round(aggs["avg_cpu"]["value"]            or 0, 2),
        "avg_memory":       round(aggs["avg_memory"]["value"]         or 0, 2),
        "avg_error_count":  round(aggs["avg_error_count"]["value"]    or 0, 2),
        "error_rate_pct":   round(error_rate, 2),
    }


def get_all_services() -> list:
    """Returns all unique service names found in the index."""
    result = es.search(index=LOG_INDEX, aggs={
        "services": {
            "terms": {"field": "service", "size": 50}
        }
    }, size=0)
    return [b["key"] for b in result["aggregations"]["services"]["buckets"]]


def collect_snapshot() -> list:
    """
    Collects one metric snapshot for every service.
    Returns a list of metric dicts.
    """
    services = get_all_services()
    snapshots = []

    for service in services:
        metrics = get_metrics_for_service(service)
        if metrics:
            snapshots.append(metrics)

    return snapshots


def print_snapshot(snapshots: list):
    """Pretty-prints a snapshot to the terminal."""
    print(f"\n{'─'*65}")
    print(f"  SNAPSHOT @ {datetime.now().strftime('%H:%M:%S')}  |  {len(snapshots)} services")
    print(f"{'─'*65}")
    print(f"  {'SERVICE':<25} {'CPU%':>6} {'MEM%':>6} {'ERR%':>6} {'AVG_MS':>8}")
    print(f"  {'─'*24} {'─'*5} {'─'*5} {'─'*5} {'─'*7}")
    for m in snapshots:
        flag = "  ⚠️ " if m["error_rate_pct"] > 10 or m["avg_cpu"] > 70 else ""
        print(
            f"  {m['service']:<25}"
            f"  {m['avg_cpu']:>5.1f}"
            f"  {m['avg_memory']:>5.1f}"
            f"  {m['error_rate_pct']:>5.1f}"
            f"  {m['avg_response_ms']:>7.0f}"
            f"{flag}"
        )
    print(f"{'─'*65}")


def run_ingestor(interval_seconds: int = 15):
    """
    Main loop — collects and prints snapshots every N seconds.
    In the full agent, this feeds into the detector.
    """
    print("🔍 Ingestor started — polling Elasticsearch every "
          f"{interval_seconds}s\n")
    while True:
        try:
            snapshots = collect_snapshot()
            if snapshots:
                print_snapshot(snapshots)
            else:
                print("⚠️  No data found — run log_generator.py first")
        except Exception as e:
            print(f"❌ Ingestor error: {e}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_ingestor(interval_seconds=15)
