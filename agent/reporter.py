import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")
REPORTS_DIR   = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports"
)


class IncidentReporter:
    def __init__(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        self.slack_enabled = bool(SLACK_WEBHOOK and
                                  SLACK_WEBHOOK != "your_slack_webhook_here")
        if self.slack_enabled:
            print("  ✅ Slack alerts enabled")
        else:
            print("  ℹ️  Slack webhook not configured — skipping Slack alerts")

    # ── SLACK ─────────────────────────────────────────────────────

    def send_slack_alert(self, analyses: list, actions: list):
        """Sends a concise Slack summary of the incident."""
        if not self.slack_enabled:
            return

        anomaly_count = len(analyses)
        action_count  = len(actions)
        services      = ", ".join(a["service"] for a in analyses)

        severity_counts = {}
        for a in analyses:
            s = a.get("severity", "UNKNOWN")
            severity_counts[s] = severity_counts.get(s, 0) + 1

        severity_text = "  ".join(
            f"{s}: {c}" for s, c in severity_counts.items()
        )

        # Build Slack blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 AIOps Autopilot — {anomaly_count} Anomalies Detected"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Services:*\n{services}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity_text}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Healing Actions:*\n{action_count} executed"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            },
            {"type": "divider"}
        ]

        # Add per-service details
        for a in analyses[:3]:   # max 3 to keep Slack clean
            service_actions = [
                x["action"] for x in actions
                if x["service"] == a["service"]
            ]
            action_text = ", ".join(service_actions) if service_actions \
                else "no action taken"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{a['service']}* — _{a.get('severity', 'UNKNOWN')}_\n"
                        f">*Root cause:* {a.get('root_cause', 'N/A')[:120]}...\n"
                        f">*Healing:* {action_text}"
                    )
                }
            })

        payload = {"blocks": blocks}

        try:
            resp = requests.post(
                SLACK_WEBHOOK,
                json=payload,
                timeout=10
            )
            if resp.status_code == 200:
                print("  ✅ Slack alert sent successfully")
            else:
                print(f"  ⚠️  Slack returned {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"  ❌ Slack alert failed: {e}")

    # ── HTML REPORT ───────────────────────────────────────────────

    def generate_html_report(self, analyses: list,
                             actions: list,
                             detections: list) -> str:
        """Generates a full HTML incident report and saves to disk."""
        timestamp  = datetime.now(timezone.utc)
        report_id  = timestamp.strftime("%Y%m%d_%H%M%S")
        filename   = f"incident_{report_id}.html"
        filepath   = os.path.join(REPORTS_DIR, filename)

        anomaly_count = len(analyses)
        action_count  = len(actions)
        success_count = len([a for a in actions if a["success"]])

        severity_colors = {
            "CRITICAL": "#e74c3c",
            "HIGH":     "#e67e22",
            "MEDIUM":   "#f39c12",
            "LOW":      "#27ae60",
            "UNKNOWN":  "#95a5a6"
        }

        # Build service cards HTML
        service_cards = ""
        for analysis in analyses:
            service  = analysis["service"]
            severity = analysis.get("severity", "UNKNOWN")
            color    = severity_colors.get(severity, "#95a5a6")

            # Find matching detection metrics
            detection = next(
                (d for d in detections if d["service"] == service), {}
            )
            metrics = detection.get("metrics", {})

            # Find healing actions for this service
            svc_actions = [a for a in actions if a["service"] == service]
            actions_html = "".join(
                f'<div class="action-item">⚙️ {a["action"]}'
                f'{"✅" if a["success"] else "❌"}</div>'
                for a in svc_actions
            ) or "<div class='action-item'>ℹ️ No actions taken</div>"

            remediation_html = "".join(
                f"<li>{step}</li>"
                for step in analysis.get("remediation", [])
            )

            service_cards += f"""
            <div class="service-card">
                <div class="card-header" style="border-left: 4px solid {color}">
                    <div>
                        <span class="service-name">{service}</span>
                        <span class="severity-badge"
                              style="background:{color}">
                            {severity}
                        </span>
                    </div>
                    <span class="recovery-time">
                        ⏱ {analysis.get("estimated_recovery", "N/A")}
                    </span>
                </div>

                <div class="metrics-row">
                    <div class="metric">
                        <span class="metric-val">
                            {metrics.get("cpu", 0):.1f}%
                        </span>
                        <span class="metric-lbl">CPU</span>
                    </div>
                    <div class="metric">
                        <span class="metric-val">
                            {metrics.get("memory", 0):.1f}%
                        </span>
                        <span class="metric-lbl">Memory</span>
                    </div>
                    <div class="metric">
                        <span class="metric-val">
                            {metrics.get("error_rate", 0):.1f}%
                        </span>
                        <span class="metric-lbl">Error Rate</span>
                    </div>
                    <div class="metric">
                        <span class="metric-val">
                            {metrics.get("response_ms", 0):.0f}ms
                        </span>
                        <span class="metric-lbl">Avg Response</span>
                    </div>
                </div>

                <div class="section-label">Root Cause</div>
                <div class="root-cause">
                    {analysis.get("root_cause", "N/A")}
                </div>

                <div class="section-label">Impact</div>
                <div class="impact-text">
                    {analysis.get("impact", "N/A")}
                </div>

                <div class="two-col">
                    <div>
                        <div class="section-label">Remediation Steps</div>
                        <ol class="remediation-list">{remediation_html}</ol>
                    </div>
                    <div>
                        <div class="section-label">Healing Actions Taken</div>
                        <div class="actions-taken">{actions_html}</div>
                    </div>
                </div>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Incident Report — {report_id}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #0f1117;
    color: #e0e0e0;
    padding: 40px 20px;
  }}
  .container {{ max-width: 960px; margin: 0 auto; }}

  .report-header {{
    background: #1a1d2e;
    border: 1px solid #2a2d4a;
    border-radius: 12px;
    padding: 32px;
    margin-bottom: 32px;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }}
  .report-title {{
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 8px;
  }}
  .report-subtitle {{
    color: #888;
    font-size: 14px;
    font-family: monospace;
  }}
  .summary-pills {{
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }}
  .pill {{
    padding: 10px 20px;
    border-radius: 8px;
    text-align: center;
    min-width: 90px;
  }}
  .pill-num {{
    font-size: 24px;
    font-weight: 700;
    display: block;
  }}
  .pill-lbl {{
    font-size: 11px;
    opacity: 0.8;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .pill-red   {{ background: rgba(231,76,60,0.15);
                 border: 1px solid #e74c3c; color: #e74c3c; }}
  .pill-green {{ background: rgba(39,174,96,0.15);
                 border: 1px solid #27ae60; color: #27ae60; }}
  .pill-blue  {{ background: rgba(52,152,219,0.15);
                 border: 1px solid #3498db; color: #3498db; }}

  .section-title {{
    font-size: 13px;
    font-weight: 600;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 16px;
  }}

  .service-card {{
    background: #1a1d2e;
    border: 1px solid #2a2d4a;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
  }}
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-left: 12px;
    margin-bottom: 20px;
  }}
  .service-name {{
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-right: 10px;
  }}
  .severity-badge {{
    font-size: 11px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 4px;
    color: #fff;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .recovery-time {{
    font-size: 13px;
    color: #888;
    font-family: monospace;
  }}

  .metrics-row {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }}
  .metric {{
    background: #0f1117;
    border-radius: 8px;
    padding: 12px;
    text-align: center;
  }}
  .metric-val {{
    display: block;
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    font-family: monospace;
  }}
  .metric-lbl {{
    display: block;
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
  }}

  .section-label {{
    font-size: 11px;
    font-weight: 600;
    color: #3498db;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin: 16px 0 8px;
  }}
  .root-cause {{
    background: #0f1117;
    border-left: 3px solid #e67e22;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    line-height: 1.6;
    color: #ccc;
  }}
  .impact-text {{
    background: #0f1117;
    border-left: 3px solid #e74c3c;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    line-height: 1.6;
    color: #ccc;
  }}

  .two-col {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 8px;
  }}
  .remediation-list {{
    padding-left: 18px;
    font-size: 13px;
    line-height: 2;
    color: #ccc;
  }}
  .actions-taken {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .action-item {{
    background: rgba(39,174,96,0.1);
    border: 1px solid rgba(39,174,96,0.3);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: monospace;
    color: #27ae60;
  }}

  .footer {{
    text-align: center;
    color: #444;
    font-size: 12px;
    margin-top: 40px;
    font-family: monospace;
  }}
</style>
</head>
<body>
<div class="container">

  <div class="report-header">
    <div>
      <div class="report-title">🤖 AIOps Autopilot</div>
      <div class="report-title" style="font-size:20px;margin-top:4px">
          Incident Report
      </div>
      <div class="report-subtitle" style="margin-top:12px">
          ID: {report_id}<br>
          Generated: {timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")}
      </div>
    </div>
    <div class="summary-pills">
      <div class="pill pill-red">
        <span class="pill-num">{anomaly_count}</span>
        <span class="pill-lbl">Anomalies</span>
      </div>
      <div class="pill pill-blue">
        <span class="pill-num">{action_count}</span>
        <span class="pill-lbl">Actions</span>
      </div>
      <div class="pill pill-green">
        <span class="pill-num">{success_count}</span>
        <span class="pill-lbl">Healed</span>
      </div>
    </div>
  </div>

  <div class="section-title">Affected Services</div>
  {service_cards}

  <div class="footer">
    Generated by AIOps Autopilot &nbsp;·&nbsp;
    github.com/shahmikh/aiops-autopilot
  </div>

</div>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  ✅ HTML report saved: reports/{filename}")
        return filepath

    def create_incident_report(self, analyses: list,
                               actions: list,
                               detections: list) -> str:
        """Main entry point — generates HTML report and sends Slack alert."""
        print("\n📋 Generating incident report...")
        filepath = self.generate_html_report(analyses, actions, detections)
        print("📣 Sending Slack alert...")
        self.send_slack_alert(analyses, actions)
        return filepath


if __name__ == "__main__":
    import sys
    import time
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.ingestor import collect_snapshot
    from agent.detector import AnomalyDetector, print_detections
    from agent.brain    import analyze_all_anomalies
    from agent.healer   import AutoHealer

    print("📋 Reporter test — full pipeline with report generation...\n")

    # Collect + train
    detector  = AnomalyDetector(contamination=0.1)
    snapshots = []
    while len(snapshots) < 20:
        batch = collect_snapshot()
        for s in batch:
            detector.add_snapshot(s)
            snapshots.append(s)
        print(f"  Collected {len(snapshots)} snapshots...")
        if len(snapshots) < 20:
            time.sleep(5)

    detector.train()

    # Detect
    latest     = collect_snapshot()
    results    = [detector.predict(s) for s in latest]
    print_detections(results)

    # Analyze
    analyses   = analyze_all_anomalies(results)

    # Heal
    healer     = AutoHealer()
    actions    = healer.heal_all(results, analyses)
    healer.print_heal_summary(actions)

    # Report
    reporter   = IncidentReporter()
    filepath   = reporter.create_incident_report(analyses, actions, results)

    print(f"\n✅ Done! Open your report:")
    print(f"   {filepath}")
