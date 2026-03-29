import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"


def analyze_anomaly(detection: dict) -> dict:
    """
    Sends a detected anomaly to Groq LLM.
    Returns root cause, severity, and remediation steps.
    """
    service   = detection["service"]
    metrics   = detection["metrics"]
    reasons   = detection["reasons"]

    prompt = f"""You are an expert SRE (Site Reliability Engineer) and AIOps analyst.

A monitoring system has detected an anomaly in a production service. Analyze it and respond.

SERVICE: {service}
METRICS:
  - CPU Usage:       {metrics['cpu']:.1f}%
  - Memory Usage:    {metrics['memory']:.1f}%
  - Avg Response:    {metrics['response_ms']:.0f}ms
  - Error Rate:      {metrics['error_rate']:.1f}%

DETECTION REASONS:
{chr(10).join(f"  - {r}" for r in reasons)}

Respond in this EXACT format with no extra text:

SEVERITY: [CRITICAL / HIGH / MEDIUM / LOW]

ROOT_CAUSE:
[2-3 sentences explaining the most likely root cause of this anomaly]

IMPACT:
[1-2 sentences on what this means for users or the system]

REMEDIATION:
1. [First immediate action to take]
2. [Second action]
3. [Third action]

ESTIMATED_RECOVERY: [e.g. 5-10 minutes]
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=400
    )

    raw = response.choices[0].message.content.strip() 
    return parse_response(raw, service)


def parse_response(raw: str, service: str) -> dict:
    result = {
        "service":            service,
        "severity":           "UNKNOWN",
        "root_cause":         "",
        "impact":             "",
        "remediation":        [],
        "estimated_recovery": "",
        "raw":                raw
    }

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("SEVERITY:"):
            result["severity"] = line.replace("SEVERITY:", "").strip()

        elif line.startswith("ROOT_CAUSE:"):
            result["root_cause"] = line.replace("ROOT_CAUSE:", "").strip()

        elif line.startswith("IMPACT:"):
            result["impact"] = line.replace("IMPACT:", "").strip()

        elif line.startswith("ESTIMATED_RECOVERY:"):
            result["estimated_recovery"] = line.replace("ESTIMATED_RECOVERY:", "").strip()

        elif line and line[0].isdigit() and len(line) > 1 and line[1] in ".)":
            result["remediation"].append(line[2:].strip())

    return result
def print_analysis(analysis: dict):
    """Pretty-prints LLM analysis to terminal."""
    severity_icons = {
        "CRITICAL": "🔴",
        "HIGH":     "🟠",
        "MEDIUM":   "🟡",
        "LOW":      "🟢",
        "UNKNOWN":  "⚪"
    }
    icon = severity_icons.get(analysis["severity"], "⚪")

    print(f"\n{'▓'*65}")
    print(f"  {icon} [{analysis['severity']}] {analysis['service']}")
    print(f"{'▓'*65}")
    print(f"\n  ROOT CAUSE:")
    print(f"  {analysis['root_cause']}")
    print(f"\n  IMPACT:")
    print(f"  {analysis['impact']}")
    print(f"\n  REMEDIATION STEPS:")
    for i, step in enumerate(analysis["remediation"], 1):
        print(f"  {i}. {step}")
    print(f"\n  ⏱  Estimated recovery: {analysis['estimated_recovery']}")
    print(f"{'▓'*65}\n")


def analyze_all_anomalies(detections: list) -> list:
    """
    Takes a list of detection results, filters anomalies,
    sends each to Groq, returns list of analyses.
    """
    anomalies = [d for d in detections if d["is_anomaly"]]

    if not anomalies:
        print("  ✅ No anomalies to analyze.")
        return []

    print(f"\n🤖 Sending {len(anomalies)} anomalies to Groq LLM for analysis...\n")
    analyses = []

    for detection in anomalies:
        print(f"  Analyzing {detection['service']}...")
        try:
            analysis = analyze_anomaly(detection)
            print_analysis(analysis)
            analyses.append(analysis)
        except Exception as e:
            print(f"  ❌ Failed to analyze {detection['service']}: {e}")

    return analyses


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.ingestor import collect_snapshot
    from agent.detector import AnomalyDetector, print_detections

    print("🧠 Brain test — collecting snapshots and analyzing anomalies with Groq...\n")

    detector  = AnomalyDetector(contamination=0.1)
    snapshots = []

    # Collect enough data to train the model
    import time
    while len(snapshots) < 20:
        batch = collect_snapshot()
        for s in batch:
            detector.add_snapshot(s)
            snapshots.append(s)
        print(f"  Collected {len(snapshots)} snapshots so far...")
        if len(snapshots) < 20:
            time.sleep(5)

    detector.train()

    # Run detection on latest batch
    latest   = collect_snapshot()
    results  = [detector.predict(s) for s in latest]
    print_detections(results)

    # Send anomalies to Groq
    analyses = analyze_all_anomalies(results)
    print(f"\n✅ Brain analysis complete. Analyzed {len(analyses)} anomalies.")
