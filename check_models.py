import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

genai.configure(api_key=GOOGLE_API_KEY)

print("Available models:")
for m in genai.list_models():
  # Check if the model supports the method we need ('generateContent')
  if 'generateContent' in m.supported_generation_methods:
    print(m.name)