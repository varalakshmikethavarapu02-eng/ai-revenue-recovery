import json
import os
import time
import logging
import argparse
from typing import Dict, Any, Optional, List
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# File paths
FLAGGED_EVENTS_FILE = "data/flagged_events.json"
CUSTOMERS_FILE = "data/customers.json"
DIAGNOSED_EVENTS_FILE = "data/diagnosed_events.json"

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-lite-latest")

def load_json(file_path: str) -> Any:
    if not os.path.exists(file_path):
        return {} if file_path == DIAGNOSED_EVENTS_FILE else []
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(file_path: str, data: Any):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def construct_batch_prompt(batch: List[Dict[str, Any]], customer_map: Dict[str, Any]) -> str:
    """Constructs a prompt to diagnose a batch of revenue events."""
    events_data = []
    for event in batch:
        customer = customer_map.get(event.get('customer_id'))
        events_data.append({
            "event": event,
            "customer": customer
        })
        
    prompt = f"""
    Diagnose the following {len(batch)} revenue events:
    {json.dumps(events_data, indent=2)}
    
    For each event, classify the root cause into exactly one of these 5 categories: 
    "card_expired", "insufficient_funds", "gateway_timeout", "customer_dispute", "no_engagement".
    
    Return ONLY a JSON ARRAY of objects. No markdown, no preamble. 
    Each object MUST be in this shape:
    {{"event_id": "...", "root_cause": "...", "confidence": 0-100, "reasoning": "one sentence"}}
    """
    return prompt

def diagnose_batch(batch: List[Dict[str, Any]], customer_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    prompt = construct_batch_prompt(batch, customer_map)
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        
        return json.loads(text)
    except Exception as e:
        logging.warning(f"Batch diagnosis failed for {len(batch)} events: {e}")
        return [
            {
                "event_id": event.get('event_id'),
                "root_cause": "diagnosis_failed",
                "confidence": 0,
                "reasoning": f"Diagnosis failed: {e}"
            } for event in batch
        ]

def run_diagnosis(limit: Optional[int] = None):
    flagged_events = load_json(FLAGGED_EVENTS_FILE)
    customer_map = {c['customer_id']: c for c in load_json(CUSTOMERS_FILE)}
    diagnosed_cache = load_json(DIAGNOSED_EVENTS_FILE)
    
    # Filter for un-diagnosed events
    pending_events = [e for e in flagged_events if e.get('event_id') not in diagnosed_cache]
    if limit:
        pending_events = pending_events[:limit]
        
    summary = {
        "diagnosed": 0,
        "from_cache": len(diagnosed_cache),
        "fresh_api": 0,
        "diagnosis_failed": 0,
        "breakdown": {}
    }
    
    # Batch processing
    batch_size = 15
    for i in range(0, len(pending_events), batch_size):
        batch = pending_events[i:i+batch_size]
        logging.info(f"Processing batch {i//batch_size + 1}...")
        
        diagnoses = diagnose_batch(batch, customer_map)
        summary["fresh_api"] += len(batch)
        
        # Cache results
        for diag in diagnoses:
            event_id = diag.get("event_id")
            # Find the original event to get opt-out
            original_event = next((e for e in batch if e.get('event_id') == event_id), {})
            customer = customer_map.get(original_event.get('customer_id'))
            
            diag["contact_opt_out"] = customer.get('contact_opt_out', False) if customer else False
            diagnosed_cache[event_id] = {**original_event, **diag}
            
            # Breakdown
            root_cause = diag.get("root_cause")
            summary["breakdown"][root_cause] = summary["breakdown"].get(root_cause, 0) + 1
            if root_cause == "diagnosis_failed":
                summary["diagnosis_failed"] += 1
        
        summary["diagnosed"] += len(batch)
        time.sleep(5) # Rate limiting
            
    save_json(DIAGNOSED_EVENTS_FILE, diagnosed_cache)
    
    print("\n--- DIAGNOSIS AGENT SUMMARY ---")
    print(f"Total events diagnosed (total processed in run): {summary['diagnosed']}")
    print(f"  Served from cache: {summary['from_cache']}")
    print(f"  Fresh API calls (batch events): {summary['fresh_api']}")
    print(f"  Diagnosis failed: {summary['diagnosis_failed']}")
    print("Breakdown by root_cause:")
    for cause, count in summary["breakdown"].items():
        print(f"  {cause}: {count}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of events to process")
    args = parser.parse_args()
    
    if not os.environ.get("GEMINI_API_KEY"):
        logging.error("GEMINI_API_KEY not set in environment.")
    else:
        run_diagnosis(args.limit)
