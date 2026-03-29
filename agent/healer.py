import os
import subprocess
import yaml
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "rules.yaml"
)


class AutoHealer:
    def __init__(self):
        self.rules      = self._load_rules()
        self.heal_log   = []   # full history of all healing actions
        self.cooldowns  = {}   # tracks last heal time per service+action

    def _load_rules(self) -> list:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        rules = sorted(
            config["rules"],
            key=lambda r: r["priority"],
            reverse=True   # highest priority first
        )
        print(f"  ✅ Loaded {len(rules)} healing rules from config")
        return rules

    def _evaluate_condition(self, condition: str, metrics: dict) -> bool:
        """Safely evaluates a condition string against metrics."""
        try:
            return eval(condition, {"__builtins__": {}}, metrics)
        except Exception:
            return False

    def _is_on_cooldown(self, service: str, action: str,
                        cooldown_minutes: int) -> bool:
        key       = f"{service}:{action}"
        last_heal = self.cooldowns.get(key)
        if not last_heal:
            return False
        elapsed = datetime.now(timezone.utc) - last_heal
        return elapsed < timedelta(minutes=cooldown_minutes)

    def _set_cooldown(self, service: str, action: str):
        key = f"{service}:{action}"
        self.cooldowns[key] = datetime.now(timezone.utc)

    def _execute_script(self, script_path: str,
                        service: str) -> dict:
        """Runs a shell script and captures output."""
        full_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            script_path
        )

        print(f"    ⚙️  Executing: {script_path} {service}")

        try:
            result = subprocess.run(
                ["bash", full_path, service],
                capture_output=True,
                text=True,
                timeout=30
            )
            output  = result.stdout.strip()
            success = result.returncode == 0

            for line in output.splitlines():
                print(f"      {line}")

            return {
                "success": success,
                "output":  output,
                "error":   result.stderr.strip()
            }

        except subprocess.TimeoutExpired:
            return {"success": False,
                    "output": "", "error": "Script timed out"}
        except Exception as e:
            return {"success": False,
                    "output": "", "error": str(e)}

    def heal(self, detection: dict, analysis: dict = None) -> list:
        """
        Takes a detection result, finds matching rules,
        executes healing scripts. Returns list of actions taken.
        """
        service  = detection["service"]
        metrics  = detection["metrics"]
        actions  = []

        # Flatten metrics for condition evaluation
        flat_metrics = {
            "error_rate_pct":  metrics.get("error_rate", 0),
            "avg_cpu":         metrics.get("cpu", 0),
            "avg_memory":      metrics.get("memory", 0),
            "avg_response_ms": metrics.get("response_ms", 0),
        }

        print(f"\n  🔧 Evaluating healing rules for: {service}")

        for rule in self.rules:
            condition      = rule["condition"]
            action         = rule["action"]
            script         = rule["script"]
            cooldown_mins  = rule["cooldown_minutes"]
            description    = rule["description"]

            if not self._evaluate_condition(condition, flat_metrics):
                continue

            if self._is_on_cooldown(service, action, cooldown_mins):
                print(f"    ⏳ [{action}] on cooldown for {service}, skipping")
                continue

            print(f"    ✅ Rule matched: {description}")
            exec_result = self._execute_script(script, service)
            self._set_cooldown(service, action)

            action_record = {
                "timestamp":   datetime.now(timezone.utc).isoformat(),
                "service":     service,
                "rule":        rule["name"],
                "action":      action,
                "description": description,
                "success":     exec_result["success"],
                "output":      exec_result["output"],
            }

            self.heal_log.append(action_record)
            actions.append(action_record)

        if not actions:
            print(f"    ℹ️  No healing rules matched for {service}")

        return actions

    def heal_all(self, detections: list,
                 analyses: list = None) -> list:
        """Heals all anomalous services in a detection batch."""
        anomalies    = [d for d in detections if d["is_anomaly"]]
        all_actions  = []

        if not anomalies:
            print("  ✅ No anomalies to heal.")
            return []

        analyses_map = {}
        if analyses:
            analyses_map = {a["service"]: a for a in analyses}

        print(f"\n🔧 AutoHealer — processing {len(anomalies)} anomalies...\n")

        for detection in anomalies:
            analysis = analyses_map.get(detection["service"])
            actions  = self.heal(detection, analysis)
            all_actions.extend(actions)

        return all_actions

    def print_heal_summary(self, actions: list):
        """Prints a summary of all healing actions taken."""
        if not actions:
            print("\n  ℹ️  No healing actions were executed.")
            return

        success = [a for a in actions if a["success"]]
        failed  = [a for a in actions if not a["success"]]

        print(f"\n{'━'*65}")
        print(f"  HEALING SUMMARY  |  "
              f"✅ {len(success)} succeeded  "
              f"❌ {len(failed)} failed")
        print(f"{'━'*65}")

        for a in actions:
            status = "✅" if a["success"] else "❌"
            print(f"  {status} {a['service']:<25} → {a['action']}")

        print(f"{'━'*65}\n")


if __name__ == "__main__":
    import sys
    import time
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.ingestor  import collect_snapshot
    from agent.detector  import AnomalyDetector, print_detections
    from agent.brain     import analyze_all_anomalies

    print("🤖 AutoHealer test — full pipeline run...\n")

    # ── Step 1: collect + train ───────────────────────────────────
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

    # ── Step 2: detect ────────────────────────────────────────────
    latest    = collect_snapshot()
    results   = [detector.predict(s) for s in latest]
    print_detections(results)

    # ── Step 3: analyze with Groq ─────────────────────────────────
    analyses  = analyze_all_anomalies(results)

    # ── Step 4: heal ──────────────────────────────────────────────
    healer    = AutoHealer()
    actions   = healer.heal_all(results, analyses)
    healer.print_heal_summary(actions)

    print("✅ Full pipeline test complete.")
