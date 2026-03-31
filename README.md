#  AIOps Autopilot

> Autonomous IT Incident Detection & Self-Healing Agent powered by Machine Learning and LLM

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-8.x-green?style=flat-square&logo=elasticsearch)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-orange?style=flat-square)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=flat-square&logo=docker)
![ML](https://img.shields.io/badge/ML-Isolation_Forest-purple?style=flat-square)

---

##  What It Does

AIOps Autopilot is a production-grade autonomous agent that monitors infrastructure, detects anomalies using ML, diagnoses root causes using an LLM, and executes self-healing scripts — **without any human intervention**.
```
Infrastructure Logs → Elasticsearch → ML Anomaly Detection
       → Groq LLM Diagnosis → Auto-Healing Scripts
               → HTML Incident Report + Slack Alert
```

---

##  Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    AIOps Autopilot                      │
│                                                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────┐  │
│  │ingestor  │───▶│ detector │───▶│      brain       │  │
│  │          │    │          │    │                  │  │
│  │Polls ES  │    │Isolation │    │ Groq LLaMA 3.3   │  │
│  │every 30s │    │Forest ML │    │ Root cause +     │  │
│  │          │    │+ Rules   │    │ Remediation plan │  │
│  └──────────┘    └──────────┘    └────────┬─────────┘  │
│                                           │             │
│  ┌──────────┐    ┌──────────┐             │             │
│  │ reporter │◀───│  healer  │◀────────────┘             │
│  │          │    │          │                           │
│  │HTML report    │Executes  │                           │
│  │Slack alert    │scripts   │                           │
│  └──────────┘    └──────────┘                           │
└─────────────────────────────────────────────────────────┘
```

---

##  Key Features

- **ML Anomaly Detection** — Isolation Forest trained on live metrics (CPU, memory, error rate, response time)
- **LLM Root Cause Analysis** — Groq LLaMA 3.3 70B diagnoses every anomaly with root cause, impact assessment, and remediation steps
- **Autonomous Self-Healing** — Rule-based engine maps anomalies to remediation scripts and executes them automatically with cooldown protection
- **Incident Reporting** — Generates beautiful HTML incident reports for every detected incident
- **Slack Alerts** — Real-time Slack notifications with per-service summaries
- **Zero Human Intervention** — Detects, diagnoses, heals, and reports fully autonomously

---

##  Tech Stack

| Component | Technology |
|---|---|
| Log Storage | Elasticsearch 8.x |
| Visualization | Kibana |
| ML Model | Isolation Forest (scikit-learn) |
| LLM | Groq — LLaMA 3.3 70B Versatile |
| Containerization | Docker Compose |
| Language | Python 3.10+ |
| Alerting | Slack Webhooks |

---

##  Quick Start

### Prerequisites
- Docker + Docker Compose
- Python 3.10+
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone and setup
```bash
git clone https://github.com/shahmikh/aiops-autopilot.git
cd aiops-autopilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 3. Start Elasticsearch + Kibana
```bash
docker compose up -d
```

### 4. Ship sample logs
```bash
python agent/log_generator.py
```

### 5. Run the autonomous agent
```bash
# Normal mode (30s interval)
python agent/main.py

# Fast demo mode (10s interval)
python agent/main.py --fast
```

---

##  Project Structure
```
aiops-autopilot/
├── agent/
│   ├── main.py              #  Entry point — autonomous loop
│   ├── ingestor.py          #  Polls Elasticsearch for metrics
│   ├── detector.py          #  Isolation Forest anomaly detection
│   ├── brain.py             #  Groq LLM root cause analysis
│   ├── healer.py            #  Executes remediation scripts
│   ├── reporter.py          #  HTML reports + Slack alerts
│   └── log_generator.py     #  Simulates infrastructure logs
├── scripts/
│   ├── restart_service.sh   # Restarts a failing service
│   ├── clear_cache.sh       # Clears service cache
│   ├── kill_high_cpu.sh     # Throttles high CPU processes
│   ├── scale_up.sh          # Scales service instances
│   └── free_memory.sh       # Frees memory
├── config/
│   └── rules.yaml           # Healing rules configuration
├── reports/                 # Generated HTML incident reports
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

##  Healing Rules

The agent uses configurable rules in `config/rules.yaml` to map anomaly conditions to healing actions:

| Condition | Action | Cooldown |
|---|---|---|
| Error rate > 20% | Restart service | 5 min |
| Response time > 1000ms | Clear cache | 3 min |
| CPU > 70% | Throttle processes | 5 min |
| Memory > 80% | Free memory | 5 min |
| Error rate > 10% | Scale up | 10 min |

---

##  Sample Incident Report

Every detected incident generates an HTML report containing:
- Anomaly summary with severity classification
- Per-service metrics (CPU, memory, error rate, response time)
- LLM-generated root cause analysis
- Business impact assessment
- Remediation steps taken
- Healing actions executed with success/failure status

---

##  Roadmap

- [ ] Prometheus + Grafana integration
- [ ] Kubernetes pod auto-restart via kubectl
- [ ] Multi-environment support (staging, production)
- [ ] Anomaly trend dashboard (Streamlit)
- [ ] PagerDuty / OpsGenie integration

---

##  Author

**Syed Shahmikh Ali**
- GitHub: [@shahmikh](https://github.com/shahmikh)
- LinkedIn: [syed-shahmikh-ali](https://linkedin.com/in/syed-shahmikh-ali-6b962b201)
- Email: syedshahmikh@gmail.com

---

##  License

MIT License — feel free to use, modify, and distribute.
