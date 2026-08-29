# Razorpay Buildathon 2026 — AI Revenue Recovery Agent

## Deadline: 05/09/2026 | Today's real progress marker updated below

## Track
Track 03: AI Revenue Recovery — detect revenue at risk, diagnose root cause, 
execute bounded recovery workflow across payment failures, checkout abandonment, 
subscription failures, overdue receivables.

## Stack
Python + Streamlit (UI) + Gemini CLI (code generation) + Gemini API (LLM calls 
for diagnosis/decision/voice) + gTTS (Hinglish voice synthesis) + Razorpay 
test-mode API (simulated execution)

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
(rules, bounded intervention) → Guardrails (retry caps, opt-out, business hours, 
discount caps — pre-execution gate) → Execution Layer (simulated Razorpay actions) → 
Audit Trail + Streamlit Dashboard (₹ at risk, ₹ recovered, recovery %) + 
Voice Recovery (Hinglish call simulation for high-value overdue invoices)

## Progress Log

- Repo init, folder structure, README, architecture doc — DONE

- Dataset generator (data/dataset.py) — DONE (multiple iterations, v1-v6, see below)
  - Final dataset: 175 events, 40 customers, data/customers.json + data/sample_data.json
  - Key fixes: frozen-NOW-timestamp bug (v5), missing retry_count on subscription 
    events (v6)
  - NOTE: dataset must be regenerated close to demo day (timestamps are now-relative) 
    — re-run `python data/dataset.py` right before final demo/recording

- Detection Agent (agents/detection_agent.py) — DONE
  - 2 bugs fixed: field-dropping dict rebuild, subscription_failed events wrongly 
    pre-filtered before reaching Decision Engine
  - Verified: 175 scanned, 174 flagged, edge cases handled
  - Output: data/flagged_events.json

- Diagnosis Agent (agents/diagnosis_agent.py) — DONE
  - Gemini-based root cause classification, batched (15/call), model 
    gemini-flash-lite-latest, deprecated google.generativeai SDK (intentional, 
    not migrating pre-deadline)
  - 1 bug fixed: cache overwrite was discarding original event fields
  - Verified: 174/174 diagnosed, 0 failures
  - Output: data/diagnosed_events.json

- Decision Engine (agents/decision_engine.py) — DONE
  - root_cause → action mapping table (locked), global retry-cap override 
    (retry_count >= 3 → escalate_to_human regardless of root_cause)
  - Deliberately does not enforce contact_opt_out (left to Guardrails) or read 
    ground_truth_recoverable (reserved for scoring)
  - Verified end-to-end: 175 → 174 flagged → 174 diagnosed → 173 decided (1-event 
    dip = expected duplicate-ID collapse, not a bug)
  - Output: data/decided_events.json

- Guardrails (agents/guardrails.py) — DONE, refactored as PRE-EXECUTION gate 
  (runs between Decision Engine and Execution Layer, not after)
  - Rules (first match wins): (a) opt-out block for customer-facing actions, 
    (b) retry-cap downgrade to escalate_to_human, (c) business-hours hold 
    (8AM-9PM IST) for customer-facing actions only, (d) max discount cap (₹5000)
  - GUARDRAILS_ENABLED kill-switch for emergency disable
  - 2 real bugs found & fixed today (28/08):
    - Business-hours rule (c) was incorrectly applying to escalate_to_human 
      events (should be fully exempt from timing rules) — caused 2 opted-out 
      escalate_to_human events to have final_action wrongly overwritten to 
      retry_now/retry_later. FIXED: rule c now only applies to the 4 
      customer-facing actions.
    - extra_fields dict was only initialized inside the GUARDRAILS_ENABLED=True 
      branch but used unconditionally in output construction — caused NameError/
      guardrail_error crash whenever kill-switch set to False. FIXED: initialize 
      extra_fields = {} before the if/else.
  - Verified: 173 processed → 123 approved, 3 blocked (opt-out), 47 held 
    (business hours), 0 downgraded (retry-cap already handled upstream by 
    Decision Engine). Kill-switch tested both ON and OFF, confirmed correct.
  - Output: data/guarded_events.json

- Execution Layer (agents/execution_layer.py) — DONE, reads guarded_events.json 
  (not decided_events.json directly — refactored after Guardrails became a 
  pre-execution gate)
  - Simulates retry charges (weighted random success, more failure at higher 
    retry_count), reminders, discount offers, human escalation queueing
  - Reads final_action (post-guardrails) not action; skips simulation entirely 
    for "blocked"/"held" guardrail_status, marking blocked_by_guardrails / 
    held_by_guardrails
  - Verified: 173/173 processed, count matches guarded_events.json, opt-out 
    events correctly skipped, edge cases (orphan customer, null timestamp) 
    handled without crashing
  - Output: data/executed_events.json

- Streamlit App (app.py) — DONE — this is the "Working AI App" deliverable
  - "Run Batch Pipeline" button: runs all 5 pipeline scripts in sequence via 
    subprocess, live status per step
  - Results panel: ₹ At Risk, ₹ Recovered (only successful retry_now/retry_later 
    counted as real recovered revenue, not reminders/discounts), Recovery %, 
    Events Processed
  - Bar charts: execution status breakdown, final action breakdown
  - Filterable audit trail table (event_type, final_action, execution_status, 
    guardrail_status, customer_id search)
  - 2 bugs found & fixed today (28/08):
    - Stale cache bug: @st.cache_data wasn't invalidated after pipeline re-run, 
      showing old data in the table after fresh runs. FIXED: st.cache_data.clear() 
      called after pipeline completes.
    - Pipeline run logs (per-step status) disappeared after st.rerun() since they 
      were only rendered inside the button's if-block. FIXED: logs now persisted 
      to st.session_state and rendered in a collapsible expander outside the 
      button block, survives reruns.

- Voice Recovery (voice_recovery.py, project root) — DONE — Hinglish voice call 
  simulation for high-value overdue invoices (secondary differentiator)
  - Selects highest-value overdue_receivable event with successful 
    send_reminder/offer_discount action
  - Two Gemini calls: (1) generates natural Hinglish reminder script matching 
    recommended_tone field, (2) simulates realistic customer response + 
    structured promise-to-pay extraction (promise_type, committed_date, confidence)
  - gTTS generates actual Hinglish audio (mp3) for the agent script
  - Caching by event_id (same pattern as diagnosis_agent.py)
  - Integrated into app.py: "🎙️ Voice Recovery Call (Hinglish)" section with 
    button, audio player, transcript, and color-coded promise-type info box
  - Bugs found & fixed today (29/08):
    - Gemini CLI created the file in the WRONG working directory twice (outer 
      ~/ai-revenue-recovery/ instead of nested ~/ai-revenue-recovery/ai-revenue-recovery/) 
      and reported false "successfully implemented" both times — classic silent-fail 
      pattern, always physically verify file existence with ls, don't trust 
      CLI success claims.
    - Import bug: script tried `from utils.config import API_KEY` (a name that 
      doesn't exist — actual utils/config.py exports GEMINI_API_KEY). FIXED to 
      match diagnosis_agent.py's actual pattern: 
      `genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))`.
    - Hardcoded wrong path prefix (`ai-revenue-recovery/data/...`) from the same 
      nested-folder confusion as decision_engine.py had earlier. FIXED to plain 
      `data/...` paths.
    - Amount formatting bug: raw integer amount passed to Gemini prompt caused 
      Gemini to generate incorrect Indian-style comma placement (e.g. "₹19,8502" 
      instead of "₹1,98,502"). FIXED by pre-formatting the amount in Python with 
      a proper Indian-numbering function before interpolating into the prompt, 
      plus an explicit instruction to Gemini not to reformat it.
  - Verified: script generates correct Hinglish text with correct ₹1,98,502 
    formatting, gTTS produces a valid ~168KB mp3, customer response and 
    promise-to-pay extraction are realistic and structurally correct.
  - Output: data/voice_calls.json, data/voice_calls/{event_id}_agent.mp3

## Current blocker (if any)
none

## Next task
Day 10 — Full end-to-end test through the Streamlit app itself (not backend 
scripts): click through the UI like a judge would — Run Batch Pipeline, verify 
metrics/charts/audit trail, trigger the Voice Recovery Call button, listen to 
the audio, check the promise-to-pay display. Fix any UI-level bugs found. 
Also verify the Voice Recovery button integration in app.py specifically (built 
but not yet click-tested through the actual dashboard).

## Key files
- data/dataset.py — dataset generator
- data/customers.json, data/sample_data.json — source data (175 events, 40 customers)
- data/flagged_events.json — output of detection_agent.py
- data/diagnosed_events.json — output of diagnosis_agent.py
- data/decided_events.json — output of decision_engine.py
- data/guarded_events.json — output of guardrails.py (pre-execution gate)
- data/executed_events.json — output of execution_layer.py (final audit trail source)
- data/voice_calls.json, data/voice_calls/*.mp3 — voice recovery outputs
- agents/detection_agent.py, agents/diagnosis_agent.py, agents/decision_engine.py, 
  agents/guardrails.py, agents/execution_layer.py
- voice_recovery.py — project root, NOT in agents/ (per plan structure)
- app.py — project root, the Streamlit dashboard ("Working AI App" deliverable)
- docs/ARCHITECTURE.md — full pipeline description (needs update to reflect 
  Guardrails now sitting BEFORE Execution Layer, not after)

## Known nuances to remember
- ground_truth_recoverable is for LATER accuracy measurement, never read by any 
  decision-making agent
- Pipeline order is: Decision Engine → Guardrails → Execution Layer (Guardrails 
  moved to be a pre-execution gate, not a post-execution auditor — original 
  architecture doc text listed it after Execution Layer, this was corrected 
  during implementation)
- escalate_to_human is exempt from ALL guardrail timing/contact rules — it never 
  triggers automated customer contact, so opt-out and business-hours checks don't 
  apply to it. This caused two real bugs when accidentally violated.
- Dataset uses relative timestamps (datetime.now()-based) + fixed random.seed(42). 
  MUST regenerate dataset (python data/dataset.py) close to demo day.
- Diagnosis Agent + Voice Recovery both use gemini-flash-lite-latest, deprecated 
  google.generativeai SDK (intentional, not migrating pre-deadline), both cache 
  by event_id to control free-tier quota usage.
- RECURRING LESSON (applies to every new agent/script going forward): always 
  spread the original event object first ({**event, ...}) before adding new 
  fields — multiple agents had silent field-dropping bugs from rebuilding dicts 
  field-by-field.
- RECURRING LESSON: Gemini CLI has repeatedly (a) confused the nested working 
  directory (~/ai-revenue-recovery/ai-revenue-recovery/) and hardcoded wrong 
  path prefixes, and (b) reported false "successfully implemented/verified" 
  summaries when the file was never created, created in the wrong location, or 
  the code had import errors it never actually ran. ALWAYS physically verify 
  with `ls -la` and by actually running the script and reading real output — 
  never trust a CLI's success claim without independent verification.
- Repo path note: working directory is ~/ai-revenue-recovery/ai-revenue-recovery/ 
  (nested folder) — always cd there before running scripts, use plain relative 
  paths like 'data/foo.json' in code.