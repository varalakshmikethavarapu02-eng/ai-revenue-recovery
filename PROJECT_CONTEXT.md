# Razorpay Buildathon 2026 — AI Revenue Recovery Agent

## Deadline: 05/09/2026 | Today's real progress marker updated below

## Track
Track 03: AI Revenue Recovery — detect revenue at risk, diagnose root cause, 
execute bounded recovery workflow across payment failures, checkout abandonment, 
subscription failures, overdue receivables.

## Stack
Python + Streamlit (UI) + Gemini CLI (code generation) + Gemini API (LLM calls 
for diagnosis/decision) + Razorpay test-mode API (simulated execution)

## Workflow
- Claude = planning, exact prompts for Gemini CLI, debugging, architecture decisions
- Gemini CLI = actual code generation/execution (free tier, avoids Claude limits)
- Every task: Claude gives exact prompt → paste into Gemini CLI → paste output/errors back to Claude → verify → commit

## Scope (locked)
- Primary: Payment degradation → root cause → recovery action
- Secondary: Hinglish voice recovery — using existing voice agent experience
- (Originally considered receivables+promise-to-pay as secondary, switched to voice 
  since it's a stronger differentiator)

## Architecture
Detection Agent (rules) → Diagnosis Agent (Gemini LLM, root cause) → Decision Engine 
(rules+LLM, bounded intervention) → Execution Layer (simulated Razorpay actions) → 
Guardrails (retry caps, opt-out, stopping rules) → Audit Trail + Streamlit Dashboard 
(₹ at risk, ₹ recovered, recovery %)

## Progress Log
- Repo init, folder structure, README, architecture doc — DONE
- Dataset generator — DONE (multiple iterations, see below)
  - v1: basic random dataset — had no correlation, no ground truth
  - v2: added ground_truth_recoverable, Indian failure codes, B2B gstin/industry fields
  - v3: fixed urgency_decay_hours bug (per event_type: failed_payment=48, 
    checkout_abandoned=24, subscription_failed=72, overdue_receivable=336) + 
    fixed consecutive-failure bug
  - v4 (final): switched to relative timestamps (based on datetime.now() instead 
    of fixed calendar dates, so dataset stays "fresh" regardless of demo date) + 
    added random.seed(42) for full reproducibility + patched missing retry_count 
    field for subscription_failed events (0-4 distribution, some ≥3 to exercise 
    the cap filter)
  - Final dataset: 175 events, 40 customers, data/customers.json + data/sample_data.json
  - Consecutive-failure customers (locked, current): CUST-0034, CUST-0036, 
    CUST-0021, CUST-0029, CUST-0033, CUST-0028
  - VERIFIED reproducible (byte-for-byte identical across two runs), committed
- Detection Agent — DONE
  - agents/detection_agent.py: rule-based flagging per event_type, assigns priority_score
  - Fixed NOW to use datetime.now() (was hardcoded to a fixed date, which broke 
    the 24h checkout_abandoned window check)
  - Verified filter logic correct via unit test (retry=5, 48h-old event both 
    correctly excluded)
  - Final verified run: 175 events, 165 flagged, 1 skipped (₹0 edge case), 
    3 warnings (duplicate ID, orphan customer, null timestamp), all 5 edge 
    cases confirmed handled
  - Output: data/flagged_events.json

## Current blocker (if any)
gemini-2.5-flash deprecated for new API keys — must use gemini-3.6-flash only 
(confirmed). Diagnosis agent now batches 15 events/call, so full 165-event 
dataset needs only ~11 calls — fits well within 20/day quota IF run fresh, 
in one sitting, without prior test calls burning quota. Cache was accidentally 
cleared during model-testing — starting fresh tomorrow.

## Next task
Do NOT run diagnosis_agent.py with --limit or any test calls first. Run the 
FULL batch (python3 agents/diagnosis_agent.py, no flags) as the very first 
API call of the day, so all ~11 batch calls succeed within the 20/day quota.

## Key files
- data/customers.json — 40 customer profiles (risk_profile, contact_opt_out, 
  channel preferences, B2B fields)
- data/sample_data.json — 175 events across 4 types, with ground_truth_recoverable 
  (hidden from agent, used for accuracy scoring later)
- data/flagged_events.json — output of detection_agent.py
- data/diagnosed_events.json — output of diagnosis_agent.py (upcoming)
- docs/ARCHITECTURE.md — full pipeline description

## Known nuances to remember
- ground_truth_recoverable is for LATER accuracy measurement, agent should NOT see 
  this field when making decisions
- 13 customers have contact_opt_out=True with pending events — guardrails must 
  respect this; diagnosis/decision agents can still process these events but must 
  not trigger actual contact
- Edge cases in sample_data.json: EDGE-0001 (₹0 amount), duplicate event_id "EVT-0001" 
  (appears twice), EDGE-0003 (orphan customer CUST-9999), EDGE-0004 (null timestamp), 
  EDGE-0005 — pipeline must handle these without crashing
- Dataset uses relative timestamps (datetime.now()-based) + fixed random.seed(42) — 
  regenerating dataset.py without preserving the seed will silently change customer 
  IDs, event counts, and which customers have consecutive-failure sequences