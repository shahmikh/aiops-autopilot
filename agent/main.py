import os
import sys
import time
import signal
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.ingestor import collect_snapshot
from agent.detector import AnomalyDetector, print_detections
from agent.brain    import analyze_all_anomalies
from agent.healer   import AutoHealer
from agent.reporter import IncidentReporter

# ── CONFIG ────────────────────────────────────────────────────────
POLL_INTERVAL     = 30    # seconds between each scan cycle
MIN_TRAIN_SAMPLES = 20    # snapshots needed before ML kicks in
BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           🤖  AIOps Autopilot  —  by Shahmikh Ali           ║
║      Autonomous IT Incident Detection & Self-Healing         ║
║   Elastic Stack · Isolation Forest · Groq LLM · AutoHeal    ║
╚══════════════════════════════════════════════════════════════╝
"""


class AIOpsAgent:
    def __init__(self, poll_interval: int = POLL_INTERVAL):
        self.poll_interval  = poll_interval
        self.detector       = AnomalyDetector(contamination=0.1)
        self.healer         = AutoHealer()
        self.reporter       = IncidentReporter()
        self.cycle_count    = 0
        self.total_anomalies = 0
        self.total_heals    = 0
        self.running        = True

        # Graceful shutdown on Ctrl+C
        signal.signal(signal.SIGINT,  self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def _shutdown(self, signum, frame):
        print("\n\n⚠️  Shutdown signal received — stopping agent gracefully...")
        self.running = False

    def _print_cycle_header(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'═'*65}")
        print(f"  CYCLE #{self.cycle_count:04d}  |  {now}  |  "
              f"⚡ {self.total_anomalies} anomalies caught  "
              f"🔧 {self.total_heals} heals executed")
        print(f"{'═'*65}")

    def _print_status(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts}] {msg}")

    def _collect_phase(self) -> list:
        """Phase 1 — collect metrics from Elasticsearch."""
        self._print_status("📡 Collecting metrics from Elasticsearch...")
        snapshots = collect_snapshot()
        if snapshots:
            self._print_status(
                f"✅ {len(snapshots)} services reporting"
            )
            for s in snapshots:
                self.detector.add_snapshot(s)
        else:
            self._print_status("⚠️  No data — is log_generator.py running?")
        return snapshots

    def _detect_phase(self, snapshots: list) -> list:
        """Phase 2 — run anomaly detection."""
        total = len(self.detector.history)

        if total < MIN_TRAIN_SAMPLES:
            self._print_status(
                f"⏳ Building training data "
                f"({total}/{MIN_TRAIN_SAMPLES} snapshots)..."
            )
            # Still run rule-based detection even before ML is ready
            results = [self.detector.predict(s) for s in snapshots]
        else:
            if not self.detector.trained:
                self._print_status("🧠 Training Isolation Forest model...")
                self.detector.train()
            results = [self.detector.predict(s) for s in snapshots]

        anomalies = [r for r in results if r["is_anomaly"]]
        self._print_status(
            f"🔍 Detection complete — "
            f"🔴 {len(anomalies)} anomalies  "
            f"🟢 {len(results) - len(anomalies)} normal"
        )
        return results

    def _analyze_phase(self, results: list) -> list:
        """Phase 3 — Groq LLM root cause analysis."""
        anomalies = [r for r in results if r["is_anomaly"]]
        if not anomalies:
            return []
        self._print_status(
            f"🤖 Sending {len(anomalies)} anomalies to Groq LLM..."
        )
        analyses = analyze_all_anomalies(results)
        self._print_status(f"✅ LLM analysis complete")
        return analyses

    def _heal_phase(self, results: list, analyses: list) -> list:
        """Phase 4 — auto-heal anomalous services."""
        anomalies = [r for r in results if r["is_anomaly"]]
        if not anomalies:
            return []
        self._print_status(f"🔧 Running AutoHealer...")
        actions = self.healer.heal_all(results, analyses)
        success = len([a for a in actions if a["success"]])
        self._print_status(
            f"✅ Healing complete — {success}/{len(actions)} actions succeeded"
        )
        return actions

    def _report_phase(self, analyses: list,
                      actions: list, results: list):
        """Phase 5 — generate report and send Slack alert."""
        if not analyses:
            return
        self._print_status("📋 Generating incident report...")
        filepath = self.reporter.create_incident_report(
            analyses, actions, results
        )
        self._print_status(f"✅ Report saved: {os.path.basename(filepath)}")

    def _print_summary(self, results: list, actions: list):
        """Prints end-of-cycle summary."""
        anomalies = [r for r in results if r["is_anomaly"]]
        self.total_anomalies += len(anomalies)
        self.total_heals     += len(actions)

        if not anomalies:
            self._print_status("✅ All services healthy — no action needed")
        else:
            print_detections(results)
            self.healer.print_heal_summary(actions)

    def run(self):
        """Main agent loop."""
        print(BANNER)
        print(f"  Poll interval : {self.poll_interval}s")
        print(f"  Min train pts : {MIN_TRAIN_SAMPLES}")
        print(f"  Reports dir   : reports/")
        print(f"\n  Press Ctrl+C to stop the agent gracefully.\n")
        print(f"{'─'*65}")

        while self.running:
            self.cycle_count += 1
            self._print_cycle_header()

            try:
                # Phase 1 — collect
                snapshots = self._collect_phase()
                if not snapshots:
                    self._print_status(
                        f"⏳ Waiting {self.poll_interval}s..."
                    )
                    time.sleep(self.poll_interval)
                    continue

                # Phase 2 — detect
                results = self._detect_phase(snapshots)

                # Phase 3 — analyze (only if anomalies found)
                analyses = self._analyze_phase(results)

                # Phase 4 — heal
                actions = self._heal_phase(results, analyses)

                # Phase 5 — report
                self._report_phase(analyses, actions, results)

                # Summary
                self._print_summary(results, actions)

            except Exception as e:
                self._print_status(f"❌ Cycle error: {e}")
                import traceback
                traceback.print_exc()

            # Wait for next cycle
            if self.running:
                self._print_status(
                    f"💤 Sleeping {self.poll_interval}s until next cycle..."
                )
                time.sleep(self.poll_interval)

        # Shutdown summary
        print(f"\n{'═'*65}")
        print(f"  AGENT STOPPED")
        print(f"  Total cycles   : {self.cycle_count}")
        print(f"  Total anomalies: {self.total_anomalies}")
        print(f"  Total heals    : {self.total_heals}")
        print(f"{'═'*65}\n")


def parse_args():
    parser = argparse.ArgumentParser(
        description="AIOps Autopilot — Autonomous IT Incident Detection"
    )
    parser.add_argument(
        "--interval", type=int, default=POLL_INTERVAL,
        help=f"Poll interval in seconds (default: {POLL_INTERVAL})"
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Fast mode — poll every 10s (for demos)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args     = parse_args()
    interval = 10 if args.fast else args.interval
    agent    = AIOpsAgent(poll_interval=interval)
    agent.run()
