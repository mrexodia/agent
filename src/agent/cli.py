import argparse
import json
import os
import sys

from agent.utils import SYSTEM_PROMPT, bash_command, post_json


def run() -> int:
    """Run the demo CLI.

    Returns:
        Process exit code.

    Raises:
        Exception: Propagates unexpected infrastructure failures from utility
            functions such as shell execution and HTTP requests.
    """
    openai_base_url = os.getenv("OPENAI_BASE_URL", "")
    if not openai_base_url:
        print("OPENAI_BASE_URL environment variable is not set")
        return 1

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        print("OPENAI_API_KEY environment variable is not set")
        return 1

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
        help="Current working directory for bash commands (default: current directory)",
    )
    args = parser.parse_args()

    print(f"[System prompt]\n{SYSTEM_PROMPT}")

    print("\n[Bash command: pwd]")
    output, exit_code = bash_command("pwd", cwd=args.cwd)
    print(output.decode("utf-8").strip())
    print(f"Exit code: {exit_code}")

    response = post_json(
        f"{openai_base_url}/chat/completions",
        openai_api_key,
        {
            "model": args.model,
            "messages": [{"role": "user", "content": "Hello, world!"}],
        },
    )
    print("\n[OpenAI Response]")
    print(json.dumps(response, indent=2))
    return 0


def main() -> int:
    """Run the CLI with workshop-friendly top-level error handling."""
    try:
        return run()
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
