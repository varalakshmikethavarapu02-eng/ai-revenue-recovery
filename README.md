# AI Revenue Recovery Agent

## Pitch
An AI agent that detects revenue at risk from failed payments, abandoned checkouts, and overdue invoices, diagnoses root cause, and executes a bounded recovery workflow.

## Problem Statement
Businesses lose significant revenue due to easily recoverable failed payments. Current manual retry processes are inefficient, non-personalized, and often lead to poor customer experiences.

## Architecture Overview
Detection Agent -> Diagnosis Agent -> Decision Engine -> Execution Layer -> Guardrails -> Audit Trail
```mermaid
flowchart TD
    A[📊 data/dataset.py<br/>175 synthetic events] --> B[🔍 Detection Agent<br/>rule-based flagging]
    B -->|data/flagged_events.json| C[🧠 Diagnosis Agent<br/>Gemini LLM: root cause]
    C -->|data/diagnosed_events.json| D[⚖️ Decision Engine<br/>root_cause → action mapping<br/>+ retry-cap override]
    D -->|data/decided_events.json| E[🛡️ Guardrails<br/>opt-out block · business hours ·<br/>discount cap · kill switch]
    E -->|data/guarded_events.json| F[⚡ Execution Layer<br/>simulated Razorpay actions]
    F -->|data/executed_events.json| G[📋 Audit Trail +<br/>Streamlit Dashboard]
    F -.->|high-value overdue invoice| H[🎙️ Voice Recovery<br/>Hinglish call simulation]
    H -->|data/voice_calls.json| G

    style A fill:#e8f0fe,stroke:#4285f4
    style B fill:#fef7e0,stroke:#f9ab00
    style C fill:#fce8e6,stroke:#ea4335
    style D fill:#e6f4ea,stroke:#34a853
    style E fill:#fce8e6,stroke:#ea4335
    style F fill:#e6f4ea,stroke:#34a853
    style G fill:#f3e8fd,stroke:#a142f4
    style H fill:#e0f7fa,stroke:#00acc1
```

## Tech Stack
- Python
- Streamlit
- Gemini API
- Razorpay API

## Setup Instructions
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in the required API keys:
   ```bash
   cp .env.example .env
   # Edit .env and add your keys
   ```
4. Run the application: `streamlit run app.py`

## Status
Under active development for Razorpay Buildathon 2026.
