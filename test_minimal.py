#!/usr/bin/env python3
"""Minimal test to show exact error"""

import requests
import json

# Make a simple API request
api_url = "http://localhost:8000/api/code"
repo_url = "https://github.com/mrlancelot/tb-test"
prompt = "Add a simple README.md with 'Hello World'"

payload = {
    "repo_url": repo_url,
    "prompt": prompt
}

print("Sending request...")
response = requests.post(api_url, json=payload, stream=True)

if response.status_code != 200:
    print(f"Error: {response.status_code}")
    print(response.text)
else:
    print("Streaming response...")
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    print(f"Event: {data.get('type')} - {data.get('data', {})}")
                except:
                    print(f"Raw: {line}")