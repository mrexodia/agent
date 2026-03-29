import os
import shutil
import subprocess
import sys
from typing import Type, TypeVar, overload

import requests

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
    """Return the absolute path to the bash executable.

    On Windows this resolves Git Bash from the installed Git location.

    Raises:
        RuntimeError: If Git is missing on Windows or the resolved bash path
            does not exist.
    """
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
    """Run a bash command and return combined output and exit code.

    Stdout and stderr are merged to match the workshop C++ implementation.

    Raises:
        RuntimeError: If bash cannot be located.
        subprocess.TimeoutExpired: If the command exceeds ``timeout`` seconds.
        OSError: If process creation fails.
    """
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
    """POST JSON to an authenticated endpoint and parse the JSON response.

    Args:
        url: Absolute endpoint URL.
        bearer: Bearer token without the ``Bearer `` prefix.
        body: JSON request body.
        response_type: Optional static typing hint for callers that want a
            narrower return type, for example a ``TypedDict``. This argument is
            ignored at runtime and no validation or deserialization is
            performed.

    Raises:
        requests.RequestException: If the HTTP request itself fails.
        RuntimeError: If the server responds with a non-200 status code.
        ValueError: If the response body is not valid JSON.
    """
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        json=body,
    )
    if response.status_code != 200:
        raise RuntimeError(f"HTTP POST {url} failed: {response.text}")
    return response.json()
