"""
Decision Engine for revenue recovery pipeline.

This module processes diagnosed events to determine appropriate recovery actions
based on root cause and event metadata.

Mapping Table:
- card_expired        -> send_reminder
- insufficient_funds  -> retry_later
- gateway_timeout     -> retry_now
- customer_dispute    -> escalate_to_human
- no_engagement       -> send_reminder (amount >= 5000 -> offer_discount)
- diagnosis_failed    -> escalate_to_human
- unrecognized        -> escalate_to_human

Override Rule:
- if retry_count >= 3, action = escalate_to_human (regardless of root_cause).
"""

import json
from collections import Counter

def determine_action(event):
    # Handle missing/malformed fields gracefully
    retry_count = event.get('retry_count', 0)
    # Ensure retry_count is numeric
    try:
        retry_count = int(retry_count)
    except (TypeError, ValueError):
        retry_count = 0
        
    amount = event.get('amount', 0)
    # Ensure amount is numeric
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0.0
        
    root_cause = event.get('root_cause', 'diagnosis_failed')

    # Rule 1: Root Cause Mapping
    if root_cause == 'card_expired':
        action = 'send_reminder'
        reason = 'root_cause=card_expired -> send_reminder'
    elif root_cause == 'insufficient_funds':
        action = 'retry_later'
        reason = 'root_cause=insufficient_funds -> retry_later'
    elif root_cause == 'gateway_timeout':
        action = 'retry_now'
        reason = 'root_cause=gateway_timeout -> retry_now'
    elif root_cause == 'customer_dispute':
        action = 'escalate_to_human'
        reason = 'root_cause=customer_dispute -> escalate_to_human'
    elif root_cause == 'no_engagement':
        if amount >= 5000:
            action = 'offer_discount'
            reason = 'root_cause=no_engagement, amount >= 5000 -> offer_discount'
        else:
            action = 'send_reminder'
            reason = 'root_cause=no_engagement, amount < 5000 -> send_reminder'
    else:
        # Default for diagnosis_failed or unrecognized
        action = 'escalate_to_human'
        reason = f'root_cause={root_cause} -> escalate_to_human'

    # Rule 2: Global Override
    if retry_count >= 3:
        action = 'escalate_to_human'
        reason = f'retry_count={retry_count} >= 3 -> escalated regardless of root_cause'

    event['action'] = action
    event['action_reason'] = reason
    return event

def main():
    input_path = 'data/diagnosed_events.json'
    output_path = 'data/decided_events.json'

    try:
        with open(input_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading {input_path}: {e}")
        return

    processed_events = []
    action_counts = Counter()

    # The input seems to be a dictionary of events
    if isinstance(data, dict):
        events = list(data.values())
    elif isinstance(data, list):
        events = data
    else:
        print("Invalid data format")
        return

    for event in events:
        processed_event = determine_action(event)
        processed_events.append(processed_event)
        action_counts[processed_event['action']] += 1

    with open(output_path, 'w') as f:
        json.dump(processed_events, f, indent=2)

    # Print summary
    print(f"Processed {len(processed_events)} events.")
    print("Breakdown by action:")
    for action, count in action_counts.items():
        print(f"  {action}: {count}")

if __name__ == "__main__":
    main()
