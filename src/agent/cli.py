import os
import sys
import requests

OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
if not OPENAI_ENDPOINT:
    print("OPENAI_ENDPOINT environment variable is not set")
    sys.exit(1)

OPENAI_BEARER_TOKEN = os.getenv("OPENAI_BEARER_TOKEN")
if not OPENAI_BEARER_TOKEN:
    print("OPENAI_BEARER_TOKEN environment variable is not set")
    sys.exit(1)


def main():
    response = requests.post(
        f"{OPENAI_ENDPOINT}/v1/agent",
        headers={
            "Authorization": f"Bearer {OPENAI_BEARER_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": "Hello, world!"}],
        },
    )
    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} {response.text}")
    print(response.json())
