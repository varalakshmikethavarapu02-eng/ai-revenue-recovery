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
(rules, bounded intervention) → Execution Layer (simulated Razorpay actions) → 
Guardrails (retry caps, opt-out, stopping rules) → Audit Trail + Streamlit Dashboard 
(₹ at risk, ₹ recovered, recovery %)

## Progress Log

- Repo init, folder structure, README, architecture doc — DONE

- Dataset generator (data/dataset.py) — DONE (multiple iterations)
  - v1: basic random dataset — had no correlation, no ground truth
  - v2: added ground_truth_recoverable, Indian failure codes, B2B gstin/industry fields
  - v3: fixed urgency_decay_hours bug (per event_type: failed_payment=48, 
    checkout_abandoned=24, subscription_failed=72, overdue_receivable=336) + 
    fixed consecutive-failure bug
  - v4: switched to relative timestamps (intended: based on datetime.now()) + 
    random.seed(42) for reproducibility
  - v5 (27/08, real fix): v4's "relative timestamps" claim was FALSE — NOW was 
    actually hardcoded to `datetime(2026, 8, 25, 10, 0, 0)`, a frozen fixed date. 
    This silently made all "relative" timestamps stale over time (discovered when 
    checkout_abandoned events were 56-72h old instead of <24h). Fixed: 
    `NOW = datetime.now()`. Verified fresh run produces current-relative timestamps.
  - v6 (27/08, real fix): subscription_failed events (both the 37 random ones and 
    the 6 reserved-customer sequences) were missing the retry_count field entirely 
    — only had consecutive_failure_number, never copied to retry_count. Fixed: 
    added retry_count = same value as consecutive_failure_number in both 
    generation blocks. Verified: reserved customers now correctly reach retry_count=3.
  - Final dataset: 175 events, 40 customers, data/customers.json + data/sample_data.json
  - Consecutive-failure customers (reserved, current run): CUST-0034, CUST-0021, 
    CUST-0029 reach retry_count=3; CUST-0036, CUST-0033, CUST-0028 reach retry_count=2
  - NOTE: dataset must be regenerated close to demo day (timestamps are now-relative, 
    not frozen) — re-run `python data/dataset.py` right before final demo/recording.
  - Located at data/dataset.py (not agents/ — note for consistency)

- Detection Agent (agents/detection_agent.py) — DONE, with 2 real bugs found & fixed today
  - Rule-based flagging per event_type, assigns priority_score
  - BUG FOUND (27/08): flagged_event dict was built from scratch with only 8 
    explicit fields, silently dropping retry_count, timestamp, payment_method, 
    failure_reason, status, ground_truth_recoverable, urgency_decay_hours from 
    every event. FIXED: now uses `{**event, "amount": amount, ...computed fields}` 
    to preserve all original fields and layer computed ones on top.
  - BUG FOUND (27/08): subscription_failed events with retry_count>=3 were being 
    filtered OUT entirely (`if retry_count < 3: is_at_risk = True`), meaning they 
    never reached Decision Engine at all — silently defeating the retry-cap 
    override before it could ever run. FIXED (per decision: Detection Agent should 
    flag ALL subscription_failed events regardless of retry_count; Decision Engine 
    alone owns the "what to do about high retries" logic). Detection Agent now 
    just flags all subscription_failed as at-risk; Decision Engine's global 
    override handles escalation.
  - Verified final run: 175 scanned, 174 flagged, 1 skipped (₹0 edge case), 
    3 warnings (duplicate ID, orphan customer, null timestamp) — all edge cases 
    confirmed handled, checkout_abandoned now correctly represented (was 0 before 
    the NOW bug fix, now 40)
  - Output: data/flagged_events.json

- Diagnosis Agent (agents/diagnosis_agent.py) — DONE, with 1 real bug found & fixed today
  - LLM-powered root cause classification via Gemini API
  - Batches 15 events per API call (reduces ~174 calls → ~12) to fit free-tier 
    daily quota limits
  - Model: gemini-flash-lite-latest (gemini-3.6-flash hit 20/day quota cap; 
    gemini-2.5-flash returned 404 deprecated-for-new-users)
  - Uses google.generativeai package — DEPRECATED (FutureWarning on every run, 
    Google has ended support). Still functional, decided to NOT migrate to 
    google.genai before deadline due to risk of breaking a working pipeline 
    mid-crunch. Revisit only if there's spare time after core build is done, or 
    if the old package actually stops working.
  - BUG FOUND (27/08): diagnosed_cache[event_id] = diag was REPLACING the cached 
    event with only Gemini's 4 output fields (event_id, root_cause, confidence, 
    reasoning) + contact_opt_out, discarding retry_count, amount, event_type, 
    customer_id, etc. from the original event. FIXED: 
    `diagnosed_cache[event_id] = {**original_event, **diag}` to merge instead 
    of replace.
  - Caching to data/diagnosed_events.json (dict keyed by event_id) — skips 
    already-diagnosed events on re-run. NOTE: because it's a dict keyed by 
    event_id, the intentional duplicate edge case (EVT-0001 appears twice in 
    raw dataset) collapses to 1 entry here — this is expected/correct behavior 
    for the edge-case test, not a bug.
  - Error handling: failed batches marked diagnosis_failed, batch continues 
    without crashing
  - contact_opt_out preserved in output for downstream guardrails
  - Final verified run (post-fixes): 174/174 diagnosed successfully, 0 failures
  - Output: data/diagnosed_events.json

- Decision Engine (agents/decision_engine.py) — DONE, verified end-to-end today
  - Maps root_cause -> action using locked mapping table:
    - card_expired        -> send_reminder
    - insufficient_funds  -> retry_later
    - gateway_timeout     -> retry_now
    - customer_dispute    -> escalate_to_human (always)
    - no_engagement       -> send_reminder (amount >= 5000 -> offer_discount instead)
    - diagnosis_failed    -> escalate_to_human (safe fallback)
    - unrecognized        -> escalate_to_human (safe fallback)
  - GLOBAL OVERRIDE: if retry_count >= 3 (any root_cause) -> force escalate_to_human
  - Does NOT read ground_truth_recoverable (reserved for later accuracy scoring only)
  - Does NOT enforce contact_opt_out — deliberately left to Guardrails (Day 7), 
    to keep separation of concerns clean. Decision Engine picks the "ideal" action; 
    Guardrails will veto/downgrade based on opt-out status.
  - Adds action + action_reason (human-readable) fields, preserves all original fields
  - Handles missing fields gracefully (missing retry_count -> 0, missing amount -> 0, 
    missing root_cause -> diagnosis_failed), never crashes
  - Had initial path bugs (hardcoded 'ai-revenue-recovery/' prefix in file paths 
    from Gemini CLI's confusion about working directory) — fixed to relative paths
  - VERIFIED end-to-end on real fixed data: 175 scanned -> 174 flagged -> 174 
    diagnosed -> 173 decided (1-event dip is the expected duplicate-ID collapse 
    from Diagnosis Agent's dict cache, not a bug)
  - VERIFIED retry-cap override specifically: 13 subscription_failed events with 
    retry_count=3 in this run, ALL 13 correctly assigned action=escalate_to_human
  - Output: data/decided_events.json

## Current blocker (if any)
none

## Next task
Execution Layer — build agents/execution_layer.py: simulate Razorpay actions per 
the `action` field from Decision Engine (retry charge, send mock reminder 
notification, etc.), log every action + result for the audit trail.

## Key files
- data/dataset.py — dataset generator (note: lives in data/, not agents/)
- data/customers.json — 40 customer profiles (risk_profile, contact_opt_out, 
  channel preferences, B2B fields)
- data/sample_data.json — 175 events across 4 types, with ground_truth_recoverable 
  (hidden from agent, used for accuracy scoring later)
- data/flagged_events.json — output of detection_agent.py
- data/diagnosed_events.json — output of diagnosis_agent.py
- data/decided_events.json — output of decision_engine.py
- agents/detection_agent.py, agents/diagnosis_agent.py, agents/decision_engine.py
- docs/ARCHITECTURE.md — full pipeline description

## Known nuances to remember
- ground_truth_recoverable is for LATER accuracy measurement, agent should NOT see 
  this field when making decisions (verified: decision_engine.py never reads it)
- 13 customers have contact_opt_out=True with pending events — Guardrails (Day 7) 
  must respect this; diagnosis/decision agents can still process these events but 
  must not trigger actual contact
- Edge cases in sample_data.json: EDGE-0001 (₹0 amount), duplicate event_id "EVT-0001" 
  (appears twice), EDGE-0003 (orphan customer CUST-9999), EDGE-0004 (null timestamp), 
  EDGE-0005 — pipeline handles all of these without crashing (verified today)
- Dataset uses relative timestamps (datetime.now()-based, fixed as of 27/08) + 
  fixed random.seed(42). MUST regenerate dataset (python data/dataset.py) close to 
  demo day so timestamps stay within urgency windows — they are NOT self-updating.
- Diagnosis Agent uses gemini-flash-lite-latest (NOT gemini-3.6-flash or 
  gemini-2.5-flash — both hit quota/deprecation issues). Batches 15 events per 
  API call. Uses deprecated google.generativeai SDK on purpose (see above) — 
  do not "fix" this without deliberate decision to migrate.
- IMPORTANT LESSON FROM TODAY: multiple agents were silently dropping fields by 
  building fresh dicts with only their own explicit fields instead of spreading 
  the original event ({**event, ...}). When adding any NEW agent (Execution 
  Layer next), always spread the original event object first, then layer new 
  fields on top — do not reconstruct dicts field-by-field from scratch.
- Repo path note: working directory is ~/ai-revenue-recovery/ai-revenue-recovery/ 
  (nested folder) — always cd there before running scripts, and use plain 
  relative paths like 'data/foo.json' in code (not prefixed with the repo name).