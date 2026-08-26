import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker

fake = Faker('en_IN')
NOW = datetime(2026, 8, 25, 10, 0, 0)

def generate_data():
    customers = []
    # 40 customers
    for i in range(40):
        is_business = random.random() < 0.4
        name = fake.company() if is_business else fake.name()
        segment = "business" if is_business else "individual"
        
        customer = {
            "customer_id": f"CUST-{i+1:04d}",
            "name": name,
            "segment": segment,
            "risk_profile": random.choice(["low", "medium", "high"]),
            "contact_opt_out": random.random() < 0.1,
            "payment_method_reliability": round(random.random(), 2),
            "language_preference": random.choice(["hindi", "english", "hinglish"]) if not is_business else "english"
        }
        
        # Bias channel preference
        channels = ["sms", "email", "whatsapp", "voice_call"]
        if customer["risk_profile"] == "high" and customer["payment_method_reliability"] < 0.4:
            customer["preferred_channel"] = random.choice(["whatsapp", "voice_call"])
        else:
            customer["preferred_channel"] = random.choice(channels)
            
        # Success rates
        rates = {ch: round(random.uniform(0.1, 0.6), 2) for ch in channels}
        rates[customer["preferred_channel"]] = round(random.uniform(0.7, 0.95), 2)
        customer["channel_success_rate"] = rates
        
        if is_business:
            customer["gstin_present"] = random.random() < 0.7
            customer["industry_type"] = random.choice(["retail_kirana", "wholesale_trading", "manufacturing", "services_it", "restaurant_fnb", "ecommerce_seller"])
            customer["business_size"] = "micro" if not customer["gstin_present"] else random.choice(["small", "medium", "large"])
            
        customers.append(customer)

    # Reserve 6 customers
    reserved_customers = random.sample(customers, 6)
    non_reserved_customers = [c for c in customers if c not in reserved_customers]

    # 155 events
    events = []
    
    # 1. Failed Payments (40)
    for i in range(40):
        cust = random.choice(customers)
        method = random.choice(["upi", "card", "netbanking"])
        reasons = {
            "upi": ["UPI_PIN_INVALID", "NPCI_DOWN", "VPA_NOT_FOUND"],
            "card": ["CARD_EXPIRED", "OTP_TIMEOUT"],
            "netbanking": ["BANK_SERVER_ERROR", "INSUFFICIENT_FUNDS"]
        }
        events.append({
            "event_id": f"EVT-{len(events)+1:04d}",
            "event_type": "failed_payment",
            "customer_id": cust["customer_id"],
            "status": "pending_action",
            "timestamp": (NOW - timedelta(hours=random.randint(1, 47))).isoformat(),
            "ground_truth_recoverable": random.choice([True, False]),
            "urgency_decay_hours": 48,
            "amount": random.randint(199, 49999),
            "payment_method": method,
            "failure_reason": random.choice(reasons[method]),
            "retry_count": random.randint(0, 2)
        })

    # 2. Checkout Abandoned (40)
    for i in range(40):
        cust = random.choice(customers)
        dev = random.choice(["mobile", "desktop"])
        stage = random.choice(["address", "payment_method_selection", "otp_verification", "payment_processing"])
        conn_issue = (dev == "mobile" and stage in ["payment_processing", "otp_verification"]) and random.random() < 0.5
        events.append({
            "event_id": f"EVT-{len(events)+1:04d}",
            "event_type": "checkout_abandoned",
            "customer_id": cust["customer_id"],
            "status": "pending_action",
            "timestamp": (NOW - timedelta(hours=random.randint(1, 23))).isoformat(),
            "ground_truth_recoverable": random.choice([True, False]),
            "urgency_decay_hours": 24,
            "cart_value": random.randint(500, 10000),
            "device_type": dev,
            "is_first_time_buyer": random.choice([True, False]),
            "drop_off_stage": stage,
            "connectivity_issue_suspected": conn_issue
        })

    # 3. Subscription Failed
    # 3a. Random (37) for non-reserved only
    for i in range(37):
        cust = random.choice(non_reserved_customers)
        events.append({
            "event_id": f"EVT-{len(events)+1:04d}",
            "event_type": "subscription_failed",
            "customer_id": cust["customer_id"],
            "status": "pending_action",
            "timestamp": (NOW - timedelta(hours=random.randint(1, 71))).isoformat(),
            "ground_truth_recoverable": random.choice([True, False]),
            "urgency_decay_hours": 72,
            "plan_name": "Premium",
            "mrr_amount": random.randint(99, 999),
            "failure_reason": random.choice(["AUTO_DEBIT_MANDATE_FAILED", "INSUFFICIENT_FUNDS", "CARD_EXPIRED"]),
            "consecutive_failure_number": random.choice([1, 2, 3])
        })
        
    # 3b. Sequences for 6 reserved customers
    for cust in reserved_customers:
        seq_len = random.choice([2, 3])
        # Start time at least 5 days ago to allow for 24h intervals
        start_time = NOW - timedelta(days=random.randint(5, 7))
        for i in range(seq_len):
            events.append({
                "event_id": f"EVT-{len(events)+1:04d}",
                "event_type": "subscription_failed",
                "customer_id": cust["customer_id"],
                "status": "pending_action",
                "timestamp": (start_time + timedelta(hours=24 * i)).isoformat(),
                "ground_truth_recoverable": False,
                "urgency_decay_hours": 72,
                "plan_name": "Premium",
                "mrr_amount": 500,
                "failure_reason": "AUTO_DEBIT_MANDATE_FAILED",
                "consecutive_failure_number": i + 1
            })

    # 4. Overdue Receivable (38)
    biz_customers = [c for c in customers if c["segment"] == "business"]
    for i in range(38):
        cust = random.choice(biz_customers)
        size = cust.get("business_size", "micro")
        amt = random.randint(5000, 50000) if size in ["micro", "small"] else random.randint(50000, 500000)
        events.append({
            "event_id": f"EVT-{len(events)+1:04d}",
            "event_type": "overdue_receivable",
            "customer_id": cust["customer_id"],
            "status": "pending_action",
            "timestamp": (NOW - timedelta(days=random.randint(1, 89))).isoformat(),
            "ground_truth_recoverable": random.choice([True, False]),
            "urgency_decay_hours": 336,
            "invoice_id": f"INV-{i}",
            "invoice_amount": amt,
            "days_overdue": random.randint(1, 90),
            "previous_reminders_sent": random.randint(0, 3),
            "recommended_tone": "formal" if (size in ["medium", "large"] or cust["gstin_present"]) else "friendly"
        })

    # Edge cases (5)
    edge_cases = [
        {"event_id": "EDGE-0001", "event_type": "failed_payment", "customer_id": customers[0]["customer_id"], "amount": 0, "status": "pending_action", "timestamp": NOW.isoformat()},
        {"event_id": "EVT-0001", "event_type": "failed_payment", "customer_id": customers[1]["customer_id"], "amount": 100, "status": "pending_action", "timestamp": NOW.isoformat()},
        {"event_id": "EDGE-0003", "event_type": "failed_payment", "customer_id": "CUST-9999", "amount": 100, "status": "pending_action", "timestamp": NOW.isoformat()},
        {"event_id": "EDGE-0004", "event_type": "failed_payment", "customer_id": customers[2]["customer_id"], "amount": 100, "status": "pending_action", "timestamp": None},
        {"event_id": "EDGE-0005", "event_type": "failed_payment", "customer_id": [c for c in customers if c["contact_opt_out"]][0]["customer_id"], "amount": 100, "status": "pending_action", "timestamp": NOW.isoformat()},
    ]
    events.extend(edge_cases)

    # 5. Validation Check
    for cust in reserved_customers:
        cust_events = [e for e in events if e["customer_id"] == cust["customer_id"] and e["event_type"] == "subscription_failed"]
        cust_events.sort(key=lambda x: x["consecutive_failure_number"])
        
        assert len(cust_events) in [2, 3], f"Customer {cust['customer_id']} should have 2 or 3 events, has {len(cust_events)}"
        
        for i in range(len(cust_events)):
            assert cust_events[i]["consecutive_failure_number"] == i + 1, f"Customer {cust['customer_id']} event {i} has wrong consecutive number"
            if i > 0:
                prev_time = datetime.fromisoformat(cust_events[i-1]["timestamp"])
                curr_time = datetime.fromisoformat(cust_events[i]["timestamp"])
                assert curr_time - prev_time == timedelta(hours=24), f"Customer {cust['customer_id']} events not 24h apart"
    
    # Save
    with open("data/customers.json", "w") as f:
        json.dump(customers, f, indent=2)
    with open("data/sample_data.json", "w") as f:
        json.dump(events, f, indent=2)
        
    # Metrics
    print("--- DATASET SUMMARY ---")
    
    types = [e["event_type"] for e in events]
    print(f"Total events: {len(events)}")
    for t in set(types):
        print(f"  {t}: {types.count(t)}")
        
    # Output Reserved Sequences
    print("\n--- RESERVED CUSTOMER SEQUENCES ---")
    for cust in reserved_customers:
        print(f"Customer: {cust['customer_id']}")
        cust_events = [e for e in events if e["customer_id"] == cust['customer_id'] and e["event_type"] == "subscription_failed"]
        cust_events.sort(key=lambda x: x["consecutive_failure_number"])
        for e in cust_events:
            print(f"  {e['event_id']} | {e['timestamp']} | {e['consecutive_failure_number']}")
        
if __name__ == "__main__":
    generate_data()
