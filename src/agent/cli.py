import os
import sys
import argparse
from datetime import datetime

from agent.utils import post_json
from agent.constants import SYSTEM_PROMPT
from agent import tools


def run() -> int:
    default_model = "openai/gpt-oss-20b"
    parser = argparse.ArgumentParser(description="Agent CLI")
    parser.add_argument(
        "--model",
        type=str,
        default=default_model,
        help=f"Model to use for the agent (default: {default_model})",
    )
    parser.add_argument(
        "--cwd",
        type=str,
        default=os.getcwd(),
        help="Working directory (default: current directory)",
    )
    args = parser.parse_args()
    tools.WORKING_DIRECTORY = os.path.abspath(os.path.expanduser(args.cwd))

    # NOTE: pyauto-dotenv handles loading .env files
    openai_base_url = os.getenv("OPENAI_BASE_URL", "")
    if not openai_base_url:
        print("OPENAI_BASE_URL environment variable is not set")
        return 1

    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_api_key:
        print("OPENAI_API_KEY environment variable is not set")
        return 1

    tool_definitions = tools.generate_tool_definitions()
    system_prompt = (
        SYSTEM_PROMPT
        + f"""
Date: {datetime.now().strftime("%Y-%m-%d")}
Working directory: {tools.WORKING_DIRECTORY}
"""
    )
    messages = [{"role": "system", "content": system_prompt}]
    while True:
        query = input("😎 ")
        messages.append({"role": "user", "content": query})
        while True:
            response = post_json(
                f"{openai_base_url}/chat/completions",
                openai_api_key,
                {
                    "model": args.model,
                    "messages": messages,
                    "tools": tool_definitions,
                    "cache_prompt": True,
                },
            )
            message = response["choices"][0]["message"]
            messages.append(message)

            reasoning = message.get("reasoning", "").strip()
            if not reasoning:
                reasoning = message.get("reasoning_content", "").strip()
            if reasoning:
                print("💭", f"[{reasoning}]")

            content = message.get("content", "").strip()
            if content:
                print("🤖", content)

            tool_calls = message.get("tool_calls", [])
            for tool_call in tool_calls:
                assert tool_call["type"] == "function"
                function = tool_call["function"]
                result = tools.call_tool(function["name"], function["arguments"])
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": tool_call["id"]}
                )

            usage = response.get("usage", {})
            total_tokens = usage.get("total_tokens")
            if total_tokens:
                print("📊", f"{total_tokens / 1000:.1f}k tokens")

            if not tool_calls:
                print()
                break


def main() -> int:
    try:
        return run()
    except (KeyboardInterrupt, EOFError):
        print()
        return 130


if __name__ == "__main__":
    sys.exit(main())
