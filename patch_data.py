import json
import random

# Load data
with open("data/sample_data.json", "r") as f:
    events = json.load(f)

# Define distribution
# ~40% (0), ~30% (1), ~20% (2), ~10% (3 or 4)
weights = [40, 30, 20, 5, 5] # 0, 1, 2, 3, 4
values = [0, 1, 2, 3, 4]

# Update events
for e in events:
    if e['event_type'] == 'subscription_failed':
        e['retry_count'] = random.choices(values, weights=weights, k=1)[0]

# Save back to file
with open("data/sample_data.json", "w") as f:
    json.dump(events, f, indent=2)

print("Successfully patched retry_count fields in data/sample_data.json")
