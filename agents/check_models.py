import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# Configure API
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# List models and print details
print("--- AVAILABLE MODELS ---")
for m in genai.list_models():
    print(f"Name: {m.name}")
    print(f"  Description: {m.description}")
    # Print the full object representation instead
    print(f"  Full details: {m}")
    print("-" * 20)
