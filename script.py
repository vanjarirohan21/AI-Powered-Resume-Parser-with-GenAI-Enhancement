import requests
import json

# Replace with your actual batch file name
batch_filename = "batch_1760652401.json"

url = f"http://127.0.0.1:8000/analyze/{batch_filename}"

job_description = {
    "job_description": "We are hiring a Python developer with Django, AWS, and Docker experience."
}

response = requests.post(url, json=job_description)

# Print full analysis
json.dumps(response.json(), indent=4)
