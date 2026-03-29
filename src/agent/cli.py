import argparse
import json
import os
import sys

from agent.utils import bash_command, post_json
from agent.constants import SYSTEM_PROMPT, TOOL_DEFINITIONS


def run() -> int:
    parser = argparse.ArgumentParser(description="Agent CLI")
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-oss-20b",
        help="Model to use for the agent (default: openai/gpt-oss-20b)",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=os.getcwd(),
        help="Working directory (default: current directory)",
    )
    args = parser.parse_args()

    # NOTE: pyauto-dotenv handles loading .env files
    openai_base_url = os.getenv("OPENAI_BASE_URL", "")
    if not openai_base_url:
        print("OPENAI_BASE_URL environment variable is not set")
        return 1

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        print("OPENAI_API_KEY environment variable is not set")
        return 1

    print(f"[System prompt]\n{SYSTEM_PROMPT}")

    print("\n[Bash command: pwd]")
    output, exit_code = bash_command("pwd", cwd=args.cwd)
    print(output.decode("utf-8").strip())
    print(f"Exit code: {exit_code}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Hello, world!"},
    ]

    response = post_json(
        f"{openai_base_url}/chat/completions",
        openai_api_key,
        {
            "model": args.model,
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
        },
    )
    print("\n[OpenAI Response]")
    print(json.dumps(response, indent=2))
    return 0


def main() -> int:
    try:
        return run()
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
