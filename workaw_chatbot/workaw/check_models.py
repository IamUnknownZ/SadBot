import google.generativeai as genai
import os

# Replace with your actual key if not set in env
api_key = os.getenv("GEMINI_API_KEY_INSURVERSE") or os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

print("Available models:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Name: {m.name}")
