import re

def detect_lead(text):
    triggers = ["price", "cost", "project", "build", "hire"]
    return any(t in text.lower() for t in triggers)

def extract_email(text):
    match = re.search(r'\S+@\S+', text)
    return match.group(0) if match else None