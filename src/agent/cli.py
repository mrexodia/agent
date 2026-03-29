import argparse
import json
import os
import sys
from agent.utils import SYSTEM_PROMPT, bash_command, post_json

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "")
if not OPENAI_BASE_URL:
    print("OPENAI_BASE_URL environment variable is not set")
    sys.exit(1)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    print("OPENAI_API_KEY environment variable is not set")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Agent CLI")
    parser.add_argument("--model", type=str, default="openai/gpt-oss-20b", help="Model to use for the agent (default: openai/gpt-oss-20b)")
    args = parser.parse_args()

    print(f"[System prompt]\n{SYSTEM_PROMPT}")

    print("\n[Bash command: pwd]")
    output, exit_code = bash_command("pwd", cwd=os.getcwd())
    print(output.decode("utf-8").strip())
    print(f"Exit code: {exit_code}")

    response = post_json(
        f"{OPENAI_BASE_URL}/chat/completions",
        OPENAI_API_KEY,
        {
            "model": args.model,
            "messages": [{"role": "user", "content": "Hello, world!"}],
        },
    )
    print("\n[OpenAI Response]")
    print(json.dumps(response, indent=2))
