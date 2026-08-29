import json
from datetime import datetime

# Load data
with open("data/sample_data.json", "r") as f:
    events = json.load(f)
with open("data/flagged_events.json", "r") as f:
    flagged = json.load(f)

NOW = datetime(2026, 8, 25, 10, 0, 0)

# 1. Warnings extraction
print("--- WARNING MESSAGES ---")
for f_event in flagged:
    if f_event.get("warnings"):
        for warning in f_event["warnings"]:
            print(f"Event {f_event['event_id']}: {warning}")

# 2. Statistics
# subscription_failed: retry_count > 3
sub_failed_events = [e for e in events if e['event_type'] == 'subscription_failed']
retry_over_3 = [e for e in sub_failed_events if e.get('retry_count', 0) > 3]
flagged_sub_failed = [e for e in flagged if e['event_type'] == 'subscription_failed']

# checkout_abandoned: > 24h window
checkout_abandoned_events = [e for e in events if e['event_type'] == 'checkout_abandoned']
outside_window = []
for e in checkout_abandoned_events:
    ts = datetime.fromisoformat(e['timestamp']) if e.get('timestamp') else None
    if ts and (NOW - ts).total_seconds() / 3600 >= 24:
        outside_window.append(e)

flagged_checkout = [e for e in flagged if e['event_type'] == 'checkout_abandoned']

print("\n--- STATISTICS ---")
print(f"subscription_failed (retry_count > 3): {len(retry_over_3)}")
print(f"subscription_failed (total flagged): {len(flagged_sub_failed)}")
print(f"checkout_abandoned (outside 24h window): {len(outside_window)}")
print(f"checkout_abandoned (total flagged): {len(flagged_checkout)}")
