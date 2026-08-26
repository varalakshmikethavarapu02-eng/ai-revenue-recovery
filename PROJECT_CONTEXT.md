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
- Every day: Claude gives exact prompt → paste into Gemini CLI → paste output/errors back to Claude → verify → commit

## Scope (locked)
- Primary: Payment degradation → root cause → recovery action
- Secondary: Hinglish voice recovery (Day 9) — using existing voice agent experience
- (Originally considered receivables+promise-to-pay as secondary, switched to voice 
  since it's a stronger differentiator)

## Architecture
Detection Agent (rules) → Diagnosis Agent (Gemini LLM, root cause) → Decision Engine 
(rules+LLM, bounded intervention) → Execution Layer (simulated Razorpay actions) → 
Guardrails (retry caps, opt-out, stopping rules) → Audit Trail + Streamlit Dashboard 
(₹ at risk, ₹ recovered, recovery %)

## Progress Log
- Day 1 (24/08): Repo init, folder structure, README, architecture doc — DONE
- Day 2 (25/08): Dataset generator — DONE (multiple iterations, see below)
  - v1: basic random dataset — had no correlation, no ground truth
  - v2: added ground_truth_recoverable, Indian failure codes, B2B gstin/industry fields
  - v3 (final): fixed urgency_decay_hours bug (was random, now fixed per event_type: 
    failed_payment=48, checkout_abandoned=24, subscription_failed=72, 
    overdue_receivable=336) + fixed consecutive-failure bug (6 customers now have 
    clean 24h-apart sequences: CUST-0036, 0024, 0023, 0012, 0009, 0031)
  - Final dataset: 174 events (169 numbered + 5 edge cases), 40 customers, 
    data/customers.json + data/sample_data.json
  - VERIFIED correct, committed
- Day 3 (26/08): Detection Agent — [update when done]

## Current blocker (if any)
None currently.

## Next task
Day 3: Build agents/detection_agent.py — rule-based engine that scans dataset, 
flags revenue-at-risk events, assigns priority_score, handles edge cases gracefully, 
respects contact_opt_out compliance flag.

## Key files
- data/customers.json — 40 customer profiles (risk_profile, contact_opt_out, 
  channel preferences, B2B fields)
- data/sample_data.json — 174 events across 4 types, with ground_truth_recoverable 
  (hidden from agent, used for accuracy scoring later)
- docs/ARCHITECTURE.md — full pipeline description

## Known nuances to remember
- ground_truth_recoverable is for LATER accuracy measurement, agent should NOT see 
  this field when making decisions
- 13 customers have contact_opt_out=True with pending events — guardrails must 
  respect this
- Edge cases in sample_data.json: EDGE-0001 (₹0 amount), duplicate event_id "EVT-0001" 
  (appears twice), EDGE-0003 (orphan customer CUST-9999), EDGE-0004 (null timestamp), 
  EDGE-0005 — pipeline must handle these without crashing