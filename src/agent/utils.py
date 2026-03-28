import os
import sys
import shutil
import requests
import subprocess
from typing import TypeVar, Type, overload


BASH_PATH = ""
SYSTEM_PROMPT = """
You are an expert coding assistant operating inside a coding agent harness. You help users by reading files, executing commands, editing code, and writing new files.

Available tools:
- read: Read file contents
- bash: Execute bash commands (ls, grep, find, etc.)
- edit: Make surgical edits to files (find exact text and replace)
- write: Create or overwrite files

In addition to the tools above, you may have access to other custom tools depending on the project.

Guidelines:
- Use bash for file operations like ls, rg, find
- Use read to examine files instead of cat or sed.
- Use edit for precise changes (old text must match exactly).
- Use write only for new files or complete rewrites.
- Be concise in your responses
- Show file paths clearly when working with files
""".strip()


def _bash_path() -> str:
    global BASH_PATH

    if not BASH_PATH:
        if sys.platform == "win32":
            git_path = shutil.which("git")
            if not git_path:
                raise RuntimeError("Git is not installed or not in PATH")
            BASH_PATH = os.path.abspath(
                os.path.join(os.path.dirname(git_path), "../../bin/bash.exe")
            )
        else:
            BASH_PATH = "/bin/bash"

        if not os.path.exists(BASH_PATH):
            raise RuntimeError(f"Bash not found at {BASH_PATH}")

    return BASH_PATH


def bash_command(
    command: str, cwd: str, timeout: int | None = None
) -> tuple[bytes, int]:
    """Run a bash command and return its output and return code."""
    result = subprocess.run(
        [_bash_path(), "-c", command],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        timeout=timeout,
    )
    return result.stdout, result.returncode


T = TypeVar("T")


@overload
def post_json(url: str, bearer: str, body: dict) -> dict: ...
@overload
def post_json(url: str, bearer: str, body: dict, response_type: Type[T]) -> T: ...


def post_json(url: str, bearer: str, body: dict, response_type=None):
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    if response.status_code != 200:
        raise Exception(f"HTTP POST {url} failed: {response.text}")
    return response.json()
