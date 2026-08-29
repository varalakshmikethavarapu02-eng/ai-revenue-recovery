import json
import random
from datetime import datetime

def simulate_retry_charge(event):
    # Base success 70%, lower if retry_count >= 2
    success_rate = 0.7
    if event.get("retry_count", 0) >= 2:
        success_rate = 0.4
    
    if random.random() < success_rate:
        return "success", {"message": "Charge successful"}
    else:
        return "failed", {"message": "Charge failed"}

def simulate_send_reminder(event):
    # Always succeeds
    channel = event.get("channel", "email")
    return "success", {"message": f"Reminder sent via {channel}"}

def simulate_offer_discount(event):
    # Mock discount offer
    return "success", {"message": "10% discount offer generated and sent"}

def simulate_escalate(event):
    return "queued_for_human", {"message": "Event queued for human review"}

def process_events():
    input_path = "data/guarded_events.json"
    output_path = "data/executed_events.json"
    
    with open(input_path, 'r') as f:
        events = json.load(f)
    
    executed_events = []
    summary = {
        "success": 0,
        "failed": 0,
        "skipped_opt_out": 0,
        "queued_for_human": 0,
        "execution_error": 0,
        "blocked_by_guardrails": 0,
        "held_by_guardrails": 0
    }
    
    for event in events:
        try:
            guardrail_status = event.get("guardrail_status")
            final_action = event.get("final_action")
            
            # Skip if blocked or held by guardrails
            if guardrail_status == "blocked":
                status = "blocked_by_guardrails"
                notes = "Blocked by guardrails."
                details = {}
            elif guardrail_status == "held":
                status = "held_by_guardrails"
                notes = "Held by guardrails."
                details = {}
            else:
                # Execute action
                if final_action in ["retry_now", "retry_later"]:
                    status, details = simulate_retry_charge(event)
                    notes = "Charge retry attempted."
                elif final_action == "send_reminder":
                    status, details = simulate_send_reminder(event)
                    notes = "Reminder sent."
                elif final_action == "offer_discount":
                    status, details = simulate_offer_discount(event)
                    notes = "Discount offer generated."
                elif final_action == "escalate_to_human":
                    status, details = simulate_escalate(event)
                    notes = "Escalated to human."
                else:
                    status = "failed"
                    details = {"error": f"Unknown action: {final_action}"}
                    notes = "Unknown action."
            
            executed_event = {
                **event,
                "execution_status": status,
                "execution_timestamp": datetime.now().isoformat(),
                "execution_notes": notes,
                "execution_details": details
            }
            executed_events.append(executed_event)
            summary[status] += 1
            
        except Exception as e:
            # Error handling
            executed_event = {
                **event,
                "execution_status": "execution_error",
                "execution_timestamp": datetime.now().isoformat(),
                "execution_notes": str(e),
                "execution_details": {}
            }
            executed_events.append(executed_event)
            summary["execution_error"] += 1
            
    with open(output_path, 'w') as f:
        json.dump(executed_events, f, indent=2)
        
    print(f"Processed {len(events)} events.")
    print("Summary:")
    for status, count in summary.items():
        print(f"  {status}: {count}")

if __name__ == "__main__":
    process_events()
