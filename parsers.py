from pathlib import Path
import spacy
import os

from dotenv import load_dotenv 
load_dotenv() 

# Uploads directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


# Load spaCy model once (expensive operation, so keep it global)
nlp = spacy.load("en_core_web_sm")

# Get OpenAI API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")