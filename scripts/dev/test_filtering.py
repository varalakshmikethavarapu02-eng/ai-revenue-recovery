from datetime import datetime, timedelta
import json

NOW = datetime(2026, 8, 25, 10, 0, 0)

def check_event(event):
    event_type = event.get('event_type')
    is_at_risk = False
    
    if event_type == 'checkout_abandoned':
        timestamp = datetime.fromisoformat(event.get('timestamp')) if event.get('timestamp') else None
        if timestamp and (NOW - timestamp).total_seconds() / 3600 < 24:
            is_at_risk = True
    elif event_type == 'subscription_failed':
        if event.get('retry_count', 0) < 3:
            is_at_risk = True
    return is_at_risk

# 1. Fake subscription_failed (retry=5) -> Should be False
sub_event = {'event_type': 'subscription_failed', 'retry_count': 5}
sub_result = check_event(sub_event)
print(f"Subscription (retry=5) is_at_risk: {sub_result} (Expected: False)")

# 2. Fake checkout_abandoned (48h past) -> Should be False
past_time = (NOW - timedelta(hours=48)).isoformat()
checkout_event = {'event_type': 'checkout_abandoned', 'timestamp': past_time}
checkout_result = check_event(checkout_event)
print(f"Checkout (48h past) is_at_risk: {checkout_result} (Expected: False)")
