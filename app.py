import streamlit as st
import pandas as pd
import subprocess
import os
import json
from datetime import datetime

# Page Config
st.set_page_config(page_title="AI Revenue Recovery Agent", layout="wide")
st.title("AI Revenue Recovery Agent")
st.write("Orchestrate the AI-driven revenue recovery pipeline and monitor performance metrics.")

# Initialize session state
if "pipeline_logs" not in st.session_state:
    st.session_state.pipeline_logs = []
if "last_run_time" not in st.session_state:
    st.session_state.last_run_time = None

# Pipeline Definition
PIPELINE_SCRIPTS = [
    ("Detection Agent", "agents/detection_agent.py"),
    ("Diagnosis Agent", "agents/diagnosis_agent.py"),
    ("Decision Engine", "agents/decision_engine.py"),
    ("Guardrails", "agents/guardrails.py"),
    ("Execution Layer", "agents/execution_layer.py"),
]

def run_pipeline():
    logs = []
    success = True
    for name, script in PIPELINE_SCRIPTS:
        with st.status(f"Running {name}...", expanded=True) as status:
            try:
                result = subprocess.run(["python", script], capture_output=True, text=True)
                if result.returncode != 0:
                    st.error(f"Error running {name}:")
                    st.code(result.stderr)
                    status.update(label=f"❌ {name} failed", state="error")
                    logs.append({"step": name, "success": False, "output": result.stderr})
                    success = False
                    break
                st.text(result.stdout)
                status.update(label=f"✅ {name} complete", state="complete")
                logs.append({"step": name, "success": True, "output": result.stdout})
            except Exception as e:
                st.error(f"System error running {name}: {str(e)}")
                status.update(label=f"❌ {name} error", state="error")
                logs.append({"step": name, "success": False, "output": str(e)})
                success = False
                break
    
    if success:
        st.success("Pipeline complete!")
        st.cache_data.clear()
        
    st.session_state.pipeline_logs = logs
    st.session_state.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return success

# --- UI Logic ---

# Button to run pipeline
if st.button("▶ Run Batch Pipeline"):
    if run_pipeline():
        st.rerun()

# Persistent Log Section
if st.session_state.pipeline_logs:
    st.caption(f"Last run: {st.session_state.last_run_time}")
    with st.expander("Pipeline Run Log", expanded=False):
        for log in st.session_state.pipeline_logs:
            icon = "✅" if log["success"] else "❌"
            st.write(f"{icon} **{log['step']}**")
            st.code(log["output"])

# Load Data
data_path = "data/executed_events.json"
if not os.path.exists(data_path):
    st.info("Run the batch pipeline first to generate data.")
    st.stop()

@st.cache_data
def load_data(path, mtime):
    return pd.read_json(path)

try:
    # Use mtime as a cache-busting argument
    mtime = os.path.getmtime(data_path)
    df = load_data(data_path, mtime)
    
    # Ensure final_action exists for easier calculation
    if 'final_action' not in df.columns:
        df['final_action'] = df['action']
    df['effective_action'] = df['final_action'].fillna(df['action'])
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Metrics Panel
col1, col2, col3, col4 = st.columns(4)

at_risk = df['amount'].sum()
recovered = df[(df['effective_action'].isin(['retry_now', 'retry_later'])) & 
               (df['execution_status'] == 'success')]['amount'].sum()
recovery_pct = (recovered / at_risk * 100) if at_risk > 0 else 0

col1.metric("₹ At Risk", f"₹{at_risk:,.2f}")
col2.metric("₹ Recovered", f"₹{recovered:,.2f}")
col3.metric("Recovery %", f"{recovery_pct:.1f}%")
col4.metric("Events Processed", len(df))

st.divider()

# Secondary Breakdown
col1, col2 = st.columns(2)
with col1:
    st.subheader("Execution Status")
    status_counts = df['execution_status'].value_counts()
    st.bar_chart(status_counts)

with col2:
    st.subheader("Final Actions")
    action_counts = df['effective_action'].value_counts()
    st.bar_chart(action_counts)

st.divider()

# Audit Trail Table
st.subheader("Audit Trail")

# Filter widgets
c1, c2, c3, c4 = st.columns(4)
type_filter = c1.multiselect("Event Type", sorted(df['event_type'].unique()))
action_filter = c2.multiselect("Effective Action", sorted(df['effective_action'].unique()))
status_filter = c3.multiselect("Execution Status", sorted(df['execution_status'].unique()))
guardrail_filter = []
if 'guardrail_status' in df.columns:
    guardrail_filter = c4.multiselect("Guardrail Status", sorted(df['guardrail_status'].unique()))

customer_search = st.text_input("Search Customer ID")

# Apply filters
filtered_df = df.copy()
if type_filter: filtered_df = filtered_df[filtered_df['event_type'].isin(type_filter)]
if action_filter: filtered_df = filtered_df[filtered_df['effective_action'].isin(action_filter)]
if status_filter: filtered_df = filtered_df[filtered_df['execution_status'].isin(status_filter)]
if guardrail_filter: filtered_df = filtered_df[filtered_df['guardrail_status'].isin(guardrail_filter)]
if customer_search: filtered_df = filtered_df[filtered_df['customer_id'].str.contains(customer_search, case=False, na=False)]

# Table Display
cols_to_show = [c for c in ['event_id', 'customer_id', 'event_type', 'amount', 'root_cause', 
                           'action', 'guardrail_status', 'final_action', 'execution_status', 
                           'execution_notes', 'guardrail_reason'] if c in filtered_df.columns]
st.dataframe(filtered_df[cols_to_show], use_container_width=True)
st.caption(f"Showing {len(filtered_df)} of {len(df)} events")

st.divider()

# Voice Recovery Call (Hinglish)
st.subheader("🎙️ Voice Recovery Call (Hinglish)")
if st.button("Simulate Voice Call for Top Overdue Invoice"):
    with st.status("Running voice simulation...", expanded=True) as status:
        # Use '../voice_recovery.py' to access the file at the project root
        result = subprocess.run(["python", "voice_recovery.py"], capture_output=True, text=True)
        if result.returncode == 0:
            st.text(result.stdout)
            status.update(label="✅ Simulation complete", state="complete")
        else:
            st.error(result.stderr)
            status.update(label="❌ Simulation failed", state="error")
    st.rerun()

voice_calls_path = "data/voice_calls.json"
if os.path.exists(voice_calls_path):
    with open(voice_calls_path, 'r') as f:
        voice_calls = json.load(f)
    
    if voice_calls:
        # Get most recent
        most_recent_id = max(voice_calls.keys(), key=lambda k: voice_calls[k]["call_timestamp"])
        call = voice_calls[most_recent_id]
        
        st.write(f"**Customer:** {call['customer_id']} | **Invoice Amount:** ₹{call['amount']} | **Days Overdue:** {call['days_overdue']}")
        st.write("**Agent Script:**")
        st.write(call['agent_script_text'])
        
        if os.path.exists(call['agent_audio_path']):
            st.audio(call['agent_audio_path'])
            
        st.write("**Customer Response:**")
        st.write(call['customer_response_text'])
        
        # Promise info box
        promise_type = call.get('promise_type')
        if promise_type == 'promise_to_pay':
            st.success(f"Promise to pay: {call.get('committed_date') or 'No date specified'}")
        elif promise_type in ['request_extension', 'unclear']:
            st.warning(f"Response: {promise_type} (Date: {call.get('committed_date') or 'N/A'})")
        else:
            st.error(f"Response: {promise_type}")
    else:
        st.info("No voice calls simulated yet.")
else:
    st.info("No voice calls simulated yet.")
