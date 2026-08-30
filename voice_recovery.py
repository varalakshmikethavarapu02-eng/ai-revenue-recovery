import os
import json
import base64
import random
import google.generativeai as genai
from gtts import gTTS
from sarvamai import SarvamAI
from datetime import datetime
from utils.config import SARVAM_API_KEY
from dotenv import load_dotenv
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-lite-latest")

def generate_audio_gtts(script_text, audio_path):
    tts = gTTS(text=script_text, lang='hi', tld='co.in')
    tts.save(audio_path)

def generate_audio_sarvam(script_text, audio_path):
    if len(script_text) > 2000:
        print("Warning: Script text exceeds 2000 characters, truncating.")
        script_text = script_text[:2000]
    
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
    audio = client.text_to_speech.convert(
        text=script_text,
        language_code="hi-IN",
        model="bulbul:v3",
        speaker="priya"
    )
    # The SDK returns audio content directly as bytes in this example context,
    # assume audio.audios[0] is the binary data.
    with open(audio_path, "wb") as f:
        f.write(base64.b64decode(audio.audios[0]))
    return True

def format_indian_currency(amount):
    s = str(int(amount))
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return ','.join(parts) + ',' + last3

def generate_script(event):
    tone = event.get("recommended_tone", "friendly")
    amount = event.get("amount")
    days = event.get("days_overdue")
    
    formatted_amount = format_indian_currency(amount)
    
    prompt = f"""
    Write a short (3-4 sentences), natural-sounding Hinglish (Hindi + English mixed) voice reminder script for a collections call.
    Target Tone: {tone}
    Details: Invoice amount ₹{formatted_amount}, {days} days overdue.
    Requirements:
    - Include a greeting, mention the amount and days overdue, and politely request payment.
    - Use the amount exactly as given below, do not reformat or re-insert commas yourself: ₹{formatted_amount}
    - Use Devanagari script for Hindi parts mixed with English words as commonly spoken.
    - Do NOT include any markdown or quotes in the output.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def simulate_customer_response(script_text, days):
    prompt = f"""
    The agent said: "{script_text}"
    Simulate a realistic Hinglish customer reply (1-2 sentences) to this reminder.
    The customer should express one of: a promise to pay, a request for more time, or a claim of already having paid.
    Vary naturally based on {days} days overdue.
    Do not use casual filler address terms like 'bhai', 'yaar', 'boss' — keep the tone natural but neutral, as if speaking to a formal collections representative, without assuming the listener's gender or familiarity level.
    Output only the natural language reply.
    """
    response = model.generate_content(prompt)
    reply = response.text.strip()

    extraction_prompt = f"""
    Extract the following information from this customer reply: "{reply}"
    Output strictly in JSON format: {{"promise_type": "promise_to_pay" | "request_extension" | "claims_paid" | "unclear", "committed_date": "YYYY-MM-DD" or null, "confidence": <0-100>}}
    """
    extraction_response = model.generate_content(extraction_prompt)
    
    try:
        # Simple parsing to handle potential markdown in JSON output
        json_str = extraction_response.text.strip().replace("```json", "").replace("```", "")
        extraction_data = json.loads(json_str)
    except:
        extraction_data = {"promise_type": "unclear", "committed_date": None, "confidence": 0}
        
    return reply, extraction_data

def run_voice_recovery():
    input_path = "data/executed_events.json"
    voice_calls_path = "data/voice_calls.json"
    audio_dir = "data/voice_calls"
    
    if not os.path.exists(input_path):
        print("No executed events found.")
        return

    with open(input_path, 'r') as f:
        events = json.load(f)

    # Filter
    candidates = [e for e in events if e.get("event_type") == "overdue_receivable" and 
                  e.get("final_action") in ["send_reminder", "offer_discount"] and 
                  e.get("execution_status") == "success"]
    
    if not candidates:
        print("No high-value overdue invoice candidates found.")
        return

    # Select highest value
    top_event = max(candidates, key=lambda e: e.get("amount", 0))
    event_id = top_event["event_id"]

    # Cache check
    voice_calls = {}
    if os.path.exists(voice_calls_path):
        with open(voice_calls_path, 'r') as f:
            voice_calls = json.load(f)
            
    if event_id in voice_calls:
        print("Already generated, skipping")
        return

    # Create audio dir
    os.makedirs(audio_dir, exist_ok=True)

    try:
        # Generate
        script = generate_script(top_event)
        
        # Audio
        audio_path = os.path.join(audio_dir, f"{event_id}_agent.mp3")
        
        if SARVAM_API_KEY:
            try:
                generate_audio_sarvam(script, audio_path)
                print("Audio generated via Sarvam AI")
                provider_used = "Sarvam AI"
            except Exception as e:
                print(f"Sarvam AI TTS failed ({e}), falling back to gTTS")
                generate_audio_gtts(script, audio_path)
                provider_used = "gTTS (fallback)"
        else:
            print("SARVAM_API_KEY not set, using gTTS")
            generate_audio_gtts(script, audio_path)
            provider_used = "gTTS (direct)"
        
        # Customer response
        reply, extraction = simulate_customer_response(script, top_event.get("days_overdue"))
        
        # Build record
        record = {
            "event_id": event_id,
            "customer_id": top_event["customer_id"],
            "invoice_id": top_event.get("invoice_id"),
            "amount": top_event["amount"],
            "days_overdue": top_event.get("days_overdue"),
            "recommended_tone": top_event.get("recommended_tone"),
            "agent_script_text": script,
            "agent_audio_path": audio_path,
            "tts_provider": provider_used,
            "customer_response_text": reply,
            "promise_type": extraction.get("promise_type"),
            "committed_date": extraction.get("committed_date"),
            "extraction_confidence": extraction.get("confidence"),
            "call_timestamp": datetime.now().isoformat()
        }
        
        # Save
        voice_calls[event_id] = record
        with open(voice_calls_path, 'w') as f:
            json.dump(voice_calls, f, indent=2)
            
        print(f"Successfully simulated call for event {event_id}")
        print(f"Script: {script}")
        print(f"Customer Response: {reply}")
        print(f"Extraction: {extraction}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_voice_recovery()
