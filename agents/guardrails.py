import json
from datetime import datetime, timezone, timedelta

GUARDRAILS_ENABLED = True

def process_guardrails():
    input_path = "data/decided_events.json"
    output_path = "data/guarded_events.json"
    
    with open(input_path, 'r') as f:
        events = json.load(f)
    
    guarded_events = []
    summary = {
        "approved": 0,
        "blocked": 0,
        "downgraded": 0,
        "held": 0,
        "guardrail_error": 0
    }
    
    # Track specific counts for summary
    stats = {
        "opt_out_blocked": 0,
        "retry_downgraded": 0
    }
    
    IST = timezone(timedelta(hours=5, minutes=30))
    
    for event in events:
        try:
            extra_fields = {}
            if not GUARDRAILS_ENABLED:
                status = "approved"
                final_action = event.get("action")
                reason = "guardrails disabled"
            else:
                # Initialize variables
                action = event.get("action")
                contact_opt_out = event.get("contact_opt_out", False)
                retry_count = event.get("retry_count", 0)
                timestamp_str = event.get("timestamp")
                amount = event.get("amount", 0)
                
                status = None
                
                # Rule a: OPT-OUT CHECK
                contact_actions = ["retry_now", "retry_later", "send_reminder", "offer_discount"]
                if contact_opt_out and action in contact_actions:
                    status = "blocked"
                    final_action = action
                    reason = "contact_opt_out is True"
                    stats["opt_out_blocked"] += 1
                
                # Rule b: RETRY CAP CHECK
                elif retry_count >= 3 and action in ["retry_now", "retry_later"]:
                    status = "downgraded"
                    final_action = "escalate_to_human"
                    reason = "retry_count >= 3, forcing human escalation"
                    stats["retry_downgraded"] += 1
                
                # Rule c: BUSINESS HOURS CHECK
                elif action in contact_actions and timestamp_str:
                    dt = datetime.fromisoformat(timestamp_str).astimezone(IST)
                    if not (8 <= dt.hour < 21):
                        status = "held"
                        final_action = action
                        reason = "outside business hours (8AM-9PM IST), holding for next window"
                
                # Rule d: MAX DISCOUNT CAP
                if status is None and action == "offer_discount":
                    discount_value = amount * 0.10
                    if discount_value > 5000:
                        status = "approved"
                        final_action = "offer_discount"
                        reason = "discount capped at ₹5000 max"
                        extra_fields = {"capped_discount_amount": 5000}
                    else:
                        status = "approved"
                        final_action = action
                        reason = "no rule triggered"
                
                # Default
                if status is None:
                    status = "approved"
                    final_action = action
                    reason = "no rule triggered"
            
            # Construct output
            guarded_event = {
                **event,
                "guardrail_status": status,
                "final_action": final_action,
                "guardrail_reason": reason,
                "guardrail_timestamp": datetime.now().isoformat(),
                **extra_fields
            }
            guarded_events.append(guarded_event)
            summary[status] += 1
            
        except Exception as e:
            # Error handling
            guarded_event = {
                **event,
                "guardrail_status": "guardrail_error",
                "final_action": "escalate_to_human",
                "guardrail_reason": str(e),
                "guardrail_timestamp": datetime.now().isoformat()
            }
            guarded_events.append(guarded_event)
            summary["guardrail_error"] += 1
            
    with open(output_path, 'w') as f:
        json.dump(guarded_events, f, indent=2)
        
    print(f"Processed {len(events)} events.")
    print("Summary:")
    for status, count in summary.items():
        print(f"  {status}: {count}")
    print(f"Blocked due to opt-out: {stats['opt_out_blocked']}")
    print(f"Downgraded due to retry cap: {stats['retry_downgraded']}")

if __name__ == "__main__":
    process_guardrails()
