# Fraud Detection System

A state-of-the-art multi-agent AI system for comprehensive fraud detection across financial transactions, insurance claims, identity verification, and e-commerce orders.
This app is a multi-agent AI fraud detection system designed to analyze financial transactions, insurance claims, identity verification, and e-commerce orders. It uses specialized agents to gather context, query external APIs, reason through evidence, make explainable decisions, take containment actions, and escalate to humans when needed. The system covers transaction, insurance, identity, and e-commerce fraud, and includes observability, evaluation, and safety guardrails like rate limiting and PII masking. The backend is built with Python (FastAPI), and the frontend is a modern web app.

## Overview

This system implements an **agentic fraud detection architecture** that goes beyond traditional rule-based systems. Instead of just flagging anomalies, it acts as an automated, 24/7 forensic investigator that:

- Gathers context from multiple sources
- Queries external APIs for risk assessment
- Reasons through evidence with Chain-of-Thought
- Makes decisions with full explainability
- Takes immediate containment actions
- Escalates to humans when needed
- Learns from feedback to improve

## Architecture

```
                  [Incoming High-Risk Alert]
                             │
                             ▼
                ┌─────────────────────────┐
                │     Triage Agent        │ (Assesses severity & routes)
                └────────────┬────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│ Context Gatherer Agent│         │  Pattern Matcher Agent│
│  (Queries APIs/DBs)   │         │ (Checks historical DB)│
└───────────┬───────────┘         └───────────┬───────────┘
            │                                 │
            └────────────────┬────────────────┘
                             ▼
                ┌─────────────────────────┐
                │   The Decider Agent     │ (Weighs evidence & reasons)
                └────────────┬────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────┐         ┌───────────────────────┐
│     Action Agent      │         │   Human-in-the-Loop   │
│(Freezes card/notifies)│         │(Escalates high-value) │
└───────────────────────┘         └───────────────────────┘
```

## Features

### Multi-Agent System

- **Triage Agent**: Assesses alert severity and routes appropriately
- **Context Gatherer Agent**: Queries IP, device, email, and velocity data
- **Decider Agent**: Makes decisions with Chain-of-Thought reasoning
- **Action Agent**: Executes soft/hard mitigation actions
- **Investigation Agent**: LLM-powered forensic analysis

### Fraud Detection Domains

- **Transaction Fraud**: Velocity attacks, amount anomalies, geographic risks
- **Insurance Fraud**: Staged incidents, exaggerated claims, serial claimants
- **Identity Fraud**: Synthetic identity, account takeover, new account fraud
- **E-commerce Fraud**: Reseller fraud, stolen cards, friendly fraud

### Red Team & Detection Testing

- **Attack Simulation**: LLM-powered synthetic fraud attack generation
- **Detection Score Dashboard**: Measure detection effectiveness with detailed metrics
- **Supported Attack Types**: Velocity attack, card testing, address mismatch, high amount, device spoofing, synthetic identity

### Observability & Evaluation

- **Distributed Tracing**: Full request lifecycle tracking
- **Metrics Collection**: Counters, gauges, histograms for all operations
- **Evaluation Framework**: Confusion matrix, precision/recall, F1 score
- **Feedback Loop**: Learn from human overrides and chargebacks

### Safety Guardrails

- **Rate Limiting**: Prevents runaway automation
- **PII Masking**: Protects sensitive data
- **Human-in-the-Loop**: Mandatory escalation for high-value/ambiguous cases

## Project Structure

```
fraud_detection_system/
├── backend/                          # Python FastAPI backend
│   ├── src/
│   │   ├── agents/                   # Fraud detection agents
│   │   │   ├── base_agent.py
│   │   │   ├── transaction_agent.py
│   │   │   ├── insurance_agent.py
│   │   │   ├── identity_agent.py
│   │   │   ├── ecommerce_agent.py
│   │   │   ├── risk_scoring_agent.py
│   │   │   ├── investigation_agent.py
│   │   │   ├── simulation_agent.py       # LLM-powered attack simulation
│   │   │   └── fraud_simulation_agent.py # Attack simulation orchestration
│   │   ├── workflow/                 # Multi-agent workflow
│   │   │   ├── state.py              # Workflow state models
│   │   │   ├── triage_agent.py
│   │   │   ├── context_agent.py
│   │   │   ├── decider_agent.py
│   │   │   ├── action_agent.py
│   │   │   └── graph.py              # Workflow orchestrator
│   │   ├── tools/                    # External tools & actions
│   │   │   ├── external.py           # IP, device, email tools
│   │   │   └── actions.py            # Mitigation actions
│   │   ├── observability/            # Tracing, metrics, evaluation
│   │   │   ├── tracing.py
│   │   │   ├── metrics.py
│   │   │   ├── evaluation.py
│   │   │   └── logging.py
│   │   ├── api/                      # FastAPI REST API
│   │   │   ├── routes.py
│   │   │   ├── observability_routes.py
│   │   │   └── models.py
│   │   ├── utils/                    # Utilities
│   │   ├── data/                     # Data generators
│   │   ├── orchestrator.py           # Main orchestrator
│   │   └── demo.py                   # Demo script
│   ├── tests/                        # Unit tests
│   ├── pyproject.toml
│   └── .env.example
├── frontend/                         # React dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── DetectionScoreDashboard.jsx  # Detection metrics dashboard
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── SimulateAttackPage.jsx       # Attack simulation UI
│   │   │   ├── DetectionScorePage.jsx       # Detection score analysis UI
│   │   │   └── ...
│   │   ├── services/
│   │   └── hooks/
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Backend Setup

```bash
# Navigate to backend
cd backend

# Install dependencies with uv
uv sync

# Copy environment file and configure
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY (optional, for LLM features)

# Run the API server
uv run fraud-api
```

The API will be available at `http://localhost:8000`

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

The dashboard will be available at `http://localhost:5173`

### Running the Backend FastAPI

```bash

# Backend
cd backend
uv sync
uv run python -m uvicorn api:app --reload --app-dir src

# Or use the script (after uv sync)
cd src && python -m uvicorn api:app --reload
```

### Running Tests

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=fraud_detection --cov-report=html

# Run specific test file
uv run pytest tests/test_agents.py -v
```

### Running the Demo

```bash
cd backend
uv run fraud-demo
```

This demonstrates:

- Transaction, insurance, identity, and e-commerce fraud detection
- Batch processing capabilities
- Risk distribution analysis
- Comprehensive multi-source analysis

## API Endpoints

### Analysis Endpoints

| Method | Endpoint                          | Description                               |
| ------ | --------------------------------- | ----------------------------------------- |
| POST   | `/api/v1/analyze/transaction`     | Analyze a financial transaction           |
| POST   | `/api/v1/analyze/insurance-claim` | Analyze an insurance claim                |
| POST   | `/api/v1/analyze/user-profile`    | Analyze a user profile for identity fraud |
| POST   | `/api/v1/analyze/ecommerce-order` | Analyze an e-commerce order               |
| POST   | `/api/v1/analyze/comprehensive`   | Multi-source comprehensive analysis       |
| POST   | `/api/v1/analyze/batch`           | Batch analyze multiple items              |
| GET    | `/api/v1/health`                  | Health check                              |

### Simulation & Red Team Endpoints

| Method | Endpoint                          | Description                               |
| ------ | --------------------------------- | ----------------------------------------- |
| GET    | `/api/v1/simulate-attack`         | Simulate a fraud attack (single)          |
| POST   | `/api/v1/detection-score`         | Run detection score analysis (configurable) |
| GET    | `/api/v1/detection-score`         | Run detection score analysis (defaults)   |

### Observability Endpoints

| Method | Endpoint                                                 | Description                    |
| ------ | -------------------------------------------------------- | ------------------------------ |
| GET    | `/api/v1/observability/metrics`                          | Get all metrics                |
| GET    | `/api/v1/observability/evaluation/summary`               | Get evaluation summary         |
| GET    | `/api/v1/observability/evaluation/confusion-matrix`      | Get accuracy metrics           |
| POST   | `/api/v1/observability/feedback/human-override`          | Record human override          |
| POST   | `/api/v1/observability/feedback/chargeback`              | Record chargeback              |
| GET    | `/api/v1/observability/feedback/improvement-suggestions` | Get AI improvement suggestions |

## Usage Examples

### Analyze a Transaction

```bash
curl -X POST "http://localhost:8000/api/v1/analyze/transaction" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-12345",
    "amount": 5000.00,
    "currency": "USD",
    "merchant_category": "electronics",
    "merchant_name": "Tech Store",
    "location": "New York, US",
    "device_id": "dev-abc123",
    "ip_address": "192.168.1.1"
  }'
```

### Python SDK Usage

```python
from fraud_detection.orchestrator import FraudDetectionOrchestrator

# Initialize orchestrator
orchestrator = FraudDetectionOrchestrator(
    enable_llm=True,
    openai_api_key="your-api-key",
    auto_investigate_threshold=60.0
)

# Analyze a transaction
result = orchestrator.analyze_transaction({
    "transaction_id": "TXN-12345",
    "amount": 5000.00,
    "location": "Moscow, Russia",
    "velocity_24h": 25,
})

print(f"Risk Score: {result.risk_score}")
print(f"Risk Level: {result.risk_level}")
print(f"Recommendation: {result.recommendation}")
```

### Running Detection Score Analysis

```python
from fraud_detection.orchestrator import FraudDetectionOrchestrator

# Initialize orchestrator
orchestrator = FraudDetectionOrchestrator(
    enable_llm=True,
    openai_api_key="your-api-key",
    auto_investigate_threshold=60.0
)

# Run detection score analysis
results = orchestrator.run_detection_score_analysis(
    attack_types=["velocity_attack", "high_amount", "card_testing"],
    simulations_per_type=2,
    detection_threshold=60.0
)

# Access overall metrics
print(f"Overall Detection Rate: {results['overall_metrics']['overall_detection_rate']:.1f}%")
print(f"False Negative Rate: {results['overall_metrics']['overall_false_negative_rate']:.1f}%")

# Access per-attack-type metrics
for attack_type, metrics in results['metrics_by_attack_type'].items():
    print(f"\n{attack_type}:")
    print(f"  Detection Rate: {metrics['detection_rate']:.1f}%")
    print(f"  Avg Confidence: {metrics['average_confidence_score']:.1f}")
```

### Using the Multi-Agent Workflow

```python
from fraud_detection.workflow.graph import create_workflow, FraudAlert

# Create workflow
workflow = create_workflow(
    ip_api_key="your-ip-api-key",
    device_api_key="your-device-api-key",
)

# Create alert
alert = FraudAlert(
    alert_id="ALERT-001",
    entity_type="transaction",
    entity_id="TXN-12345",
    entity_data={"amount": 5000, "location": "Nigeria"},
    initial_risk_score=75.0,
    triggered_rules=["high_risk_location", "large_amount"],
    timestamp="2024-01-15T10:30:00Z",
)

# Process through workflow
import asyncio
state = asyncio.run(workflow.process_alert(alert))

# Get explainability summary
print(state.get_explainability_summary())
```

## Risk Levels

| Score  | Level    | Typical Action         |
| ------ | -------- | ---------------------- |
| 80-100 | CRITICAL | Block/Deny immediately |
| 60-79  | HIGH     | Require verification   |
| 40-59  | MEDIUM   | Enhanced monitoring    |
| 0-39   | LOW      | Standard processing    |

## Red Team: Attack Simulation & Detection Testing

The system includes comprehensive red team capabilities to test and measure the effectiveness of fraud detection.

### Simulate Attack

Generate synthetic fraud attacks using LLM-powered simulation:

```bash
# Simulate a random attack type
curl "http://localhost:8000/api/v1/simulate-attack"

# Simulate a specific attack type
curl "http://localhost:8000/api/v1/simulate-attack?attack_type=velocity_attack"
```

**Supported Attack Types:**
| Attack Type | Description |
|-------------|-------------|
| `velocity_attack` | Rapid burst of transactions from same account/device |
| `card_testing` | Multiple small transactions to test stolen cards |
| `address_mismatch` | Shipping/billing address discrepancies |
| `high_amount` | Unusually large transaction amounts |
| `device_spoofing` | Same user, different devices |
| `synthetic_identity` | Fabricated identity information |

### Detection Score Dashboard

Measure your fraud detection system's effectiveness:

```bash
# Run detection score analysis with defaults (all attack types, 1 simulation each)
curl "http://localhost:8000/api/v1/detection-score"

# Run with custom parameters
curl -X POST "http://localhost:8000/api/v1/detection-score" \
  -H "Content-Type: application/json" \
  -d '{
    "attack_types": ["velocity_attack", "high_amount"],
    "simulations_per_type": 3,
    "detection_threshold": 60.0
  }'
```

**Response includes:**
- **Detection Rate**: Percentage of attacks caught per attack type
- **False Negative Rate**: Percentage of attacks that slipped through
- **Average Confidence Score**: Mean risk score assigned to attacks
- **Detailed Results**: Per-transaction breakdown with caught/missed status

### Detection Metrics Explained

| Metric | Formula | Description |
|--------|---------|-------------|
| Detection Rate | `(caught / total) * 100` | % of fraudulent transactions flagged |
| False Negative Rate | `(missed / total) * 100` | % of fraudulent transactions missed |
| Avg Confidence Score | `sum(risk_scores) / total` | Mean risk score for attack transactions |

A transaction is "caught" if its `risk_score >= detection_threshold` (default: 60).

### Simulated Transaction Fields

The simulation agent generates realistic transactions with context fields required for accurate detection:

```json
{
  "transaction_id": "txn_001",
  "amount": 5500.00,
  "currency": "USD",
  "merchant_category": "electronics",
  "merchant_name": "TechStore Pro",
  "location": "Lagos, Nigeria",
  "device_id": "device_abc123",
  "ip_address": "82.165.123.45",
  "timestamp": "2024-01-15T03:32:00Z",
  "user_id": "user_12345",
  "velocity_24h": 25,
  "avg_amount_30d": 150.00,
  "is_international": true,
  "card_present": false
}
```

**Context Fields:**
| Field | Description | Suspicious Values |
|-------|-------------|-------------------|
| `velocity_24h` | Transactions in last 24h | > 10 (high), > 20 (attack) |
| `avg_amount_30d` | User's 30-day average | Low when amount is high |
| `is_international` | Cross-border transaction | `true` |
| `card_present` | Physical card used | `false` (CNP fraud) |

## Configuration

### Environment Variables

```env
# API Settings
APP_NAME="Fraud Detection API"
DEBUG=false
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]

# OpenAI (for LLM features)
OPENAI_API_KEY=your-api-key
ENABLE_LLM=true

# Thresholds
AUTO_INVESTIGATE_THRESHOLD=60.0
HIGH_RISK_THRESHOLD=60.0

# Logging
LOG_LEVEL=INFO
```

## Extending the System

### Adding a New Agent

```python
from fraud_detection.agents import BaseAgent, AgentResult, FraudSignal

class CustomFraudAgent(BaseAgent):
    def __init__(self):
        super().__init__("CustomFraudAgent")

    def analyze(self, data: dict) -> AgentResult:
        signals = []

        # Your detection logic
        if data.get("suspicious_field"):
            signals.append(FraudSignal(
                name="custom_signal",
                description="Suspicious activity detected",
                weight=0.7,
                category="custom"
            ))

        risk_score = len(signals) * 20
        return self._create_result(
            entity_id=data.get("id"),
            risk_score=risk_score,
            signals=signals,
            recommendation="Review required"
        )
```

### Adding External Tool Integration

```python
from fraud_detection.tools.external import IPInfoTool

class MyIPInfoTool(IPInfoTool):
    async def lookup(self, ip_address: str):
        # Call your actual IP intelligence API
        response = await self.client.get(f"https://api.ipinfo.io/{ip_address}")
        return self._parse_response(response)
```

## Tech Stack

| Component       | Technology                     |
| --------------- | ------------------------------ |
| Backend         | Python 3.12, FastAPI, Pydantic |
| Frontend        | React 19, Vite, React Router   |
| Package Manager | uv (Python), npm (Node.js)     |
| Agent Framework | Custom (LangGraph-compatible)  |
| LLM             | OpenAI GPT-4 (optional)        |
| Testing         | pytest, pytest-asyncio         |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

## License

MIT License

## Author

Emmanuel Ochade

Built as a demonstration of state-of-the-art multi-agent AI systems for fraud detection.
