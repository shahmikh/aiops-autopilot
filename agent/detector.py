import os
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Features we feed into the model — order matters, keep consistent
FEATURES = [
    "avg_cpu",
    "avg_memory",
    "avg_response_ms",
    "error_rate_pct",
    "avg_error_count",
]

# Thresholds for rule-based confirmation (backup to ML)
HARD_THRESHOLDS = {
    "avg_cpu":          70.0,
    "avg_memory":       80.0,
    "avg_response_ms":  1000.0,
    "error_rate_pct":   10.0,
    "avg_error_count":  10.0,
}


class AnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        """
        contamination = expected fraction of anomalies in training data.
        0.1 means we expect ~10% of snapshots to be anomalous.
        """
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=100,
            random_state=42
        )
        self.scaler  = StandardScaler()
        self.trained = False
        self.history = []   # stores all snapshots seen so far

    def _extract_features(self, snapshot: dict) -> list:
        """Pulls feature values from a snapshot dict in consistent order."""
        return [snapshot.get(f, 0.0) for f in FEATURES]

    def add_snapshot(self, snapshot: dict):
        """Add a single service snapshot to history."""
        self.history.append(self._extract_features(snapshot))

    def train(self):
        """
        Train the Isolation Forest on all snapshots collected so far.
        Needs at least 20 data points for meaningful results.
        """
        if len(self.history) < 20:
            print(f"  ⚠️  Not enough data to train "
                  f"({len(self.history)}/20 snapshots). "
                  f"Keep collecting...")
            return False

        X = np.array(self.history)
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.trained = True
        print(f"  ✅ Model trained on {len(self.history)} snapshots.")
        return True

    def predict(self, snapshot: dict) -> dict:
        """
        Scores a single snapshot.
        Returns a result dict with is_anomaly, confidence, reasons.
        """
        features   = self._extract_features(snapshot)
        service    = snapshot.get("service", "unknown")
        reasons    = []
        is_anomaly = False
        ml_score   = 0.0

        # ── ML detection ─────────────────────────────────────────
        if self.trained:
            X = np.array([features])
            X_scaled = self.scaler.transform(X)

            prediction = self.model.predict(X_scaled)[0]   # 1=normal, -1=anomaly
            ml_score   = self.model.score_samples(X_scaled)[0]
            # score_samples: more negative = more anomalous

            if prediction == -1:
                is_anomaly = True
                reasons.append(
                    f"ML model flagged as anomaly "
                    f"(isolation score: {ml_score:.3f})"
                )

        # ── Rule-based confirmation ───────────────────────────────
        for feature, threshold in HARD_THRESHOLDS.items():
            value = snapshot.get(feature, 0.0)
            if value > threshold:
                is_anomaly = True
                reasons.append(
                    f"{feature} is {value:.1f} "
                    f"(threshold: {threshold})"
                )

        return {
            "service":    service,
            "timestamp":  snapshot.get("timestamp", datetime.now().isoformat()),
            "is_anomaly": is_anomaly,
            "ml_score":   round(ml_score, 4),
            "reasons":    reasons,
            "metrics": {
                "cpu":         snapshot.get("avg_cpu", 0),
                "memory":      snapshot.get("avg_memory", 0),
                "response_ms": snapshot.get("avg_response_ms", 0),
                "error_rate":  snapshot.get("error_rate_pct", 0),
            }
        }

    def analyze_snapshots(self, snapshots: list) -> list:
        """
        Takes a full list of service snapshots,
        trains if enough data exists, returns predictions for all.
        """
        # Add all to history for training
        for s in snapshots:
            self.add_snapshot(s)

        # Try to train
        if not self.trained:
            self.train()

        # Score every snapshot
        results = []
        for s in snapshots:
            result = self.predict(s)
            results.append(result)

        return results


def print_detections(results: list):
    """Pretty-prints detection results to terminal."""
    anomalies = [r for r in results if r["is_anomaly"]]
    normal    = [r for r in results if not r["is_anomaly"]]

    print(f"\n{'═'*65}")
    print(f"  DETECTION RESULTS  |  "
          f"🔴 {len(anomalies)} anomalies  "
          f"🟢 {len(normal)} normal")
    print(f"{'═'*65}")

    for r in results:
        if r["is_anomaly"]:
            print(f"\n  🔴 ANOMALY — {r['service']}")
            print(f"     CPU: {r['metrics']['cpu']:.1f}%  "
                  f"MEM: {r['metrics']['memory']:.1f}%  "
                  f"ERR: {r['metrics']['error_rate']:.1f}%  "
                  f"MS: {r['metrics']['response_ms']:.0f}")
            for reason in r["reasons"]:
                print(f"     ↳ {reason}")
        else:
            print(f"  🟢 normal  — {r['service']:<25} CPU:{r['metrics']['cpu']:>5.1f}%  ERR:{r['metrics']['error_rate']:>5.1f}%")

if __name__ == "__main__":
    import sys
    import os
    import time
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent.ingestor import collect_snapshot

    detector = AnomalyDetector(contamination=0.1)

    print("🧠 Detector test — collecting 5 rounds of snapshots to build training data...\n")

    for round_num in range(1, 6):
        print(f"  Round {round_num}/5 — collecting snapshots...")
        snapshots = collect_snapshot()

        if not snapshots:
            print("  ⚠️  No data — run log_generator.py in another terminal")
            time.sleep(10)
            continue

        results = detector.analyze_snapshots(snapshots)
        print_detections(results)
        time.sleep(8)

    print("✅ Detector test complete.")
