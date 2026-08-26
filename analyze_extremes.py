import json
from datetime import datetime

# Load data
with open("data/sample_data.json", "r") as f:
    events = json.load(f)

NOW = datetime(2026, 8, 25, 10, 0, 0)

# 1. Max retry_count for subscription_failed
sub_events = [e for e in events if e['event_type'] == 'subscription_failed']
retry_counts = [e.get('retry_count', 0) for e in sub_events if e.get('retry_count') is not None]
max_retry = max(retry_counts) if retry_counts else 0

# 2. Oldest timestamp for checkout_abandoned
checkout_events = [e for e in events if e['event_type'] == 'checkout_abandoned']
timestamps = [datetime.fromisoformat(e['timestamp']) for e in checkout_events if e.get('timestamp')]
oldest_ts = min(timestamps) if timestamps else NOW

# Calculate hours ago
hours_ago = (NOW - oldest_ts).total_seconds() / 3600

print(f"Max retry_count (subscription_failed): {max_retry}")
print(f"Oldest timestamp (checkout_abandoned): {oldest_ts}")
print(f"Hours elapsed from oldest timestamp to NOW: {hours_ago:.2f} hours")
