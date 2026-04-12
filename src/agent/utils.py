import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Type, TypeVar, overload

import requests

BASH_PATH = ""
HTTP_CONNECT_TIMEOUT_SECONDS = 5
LOG_DIR = Path(os.getenv("AGENT_LOG_DIR", ".agent-logs")) / datetime.now().strftime(
    "%Y-%m-%d_%H-%M-%S"
)
_REQUEST_COUNTER = 0
_REQUEST_COUNTER_LOCK = Lock()


def _windows_bash_path(git_path: str) -> str:
    """Resolve the console bash executable relative to ``git`` on Windows.

    ``git-bash.exe`` is a GUI launcher, so for subprocess execution we prefer
    the real shell binary shipped with Git for Windows at ``usr/bin/bash.exe``.
    If that layout is not present (for example in Cygwin), fall back to
    ``bin/bash.exe`` while walking up from the discovered ``git`` location.
    """
    git_dir = Path(os.path.abspath(git_path)).parent
    ancestors = (git_dir, *git_dir.parents)

    for relative in (Path("usr") / "bin" / "bash.exe", Path("bin") / "bash.exe"):
        for base in ancestors:
            candidate = (base / relative).resolve()
            if candidate.exists():
                return os.fspath(candidate)

    raise RuntimeError(f"Bash not found relative to Git at {git_path}")


def _bash_path() -> str:
    """Return the absolute path to the bash executable.

    On Windows this resolves the console bash executable that ships with Git.

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
            BASH_PATH = _windows_bash_path(git_path)
        else:
            BASH_PATH = "/bin/bash"

        if not os.path.exists(BASH_PATH):
            raise RuntimeError(f"Bash not found at {BASH_PATH}")

    return BASH_PATH


def _next_request_id() -> int:
    global _REQUEST_COUNTER

    with _REQUEST_COUNTER_LOCK:
        _REQUEST_COUNTER += 1
        return _REQUEST_COUNTER


def _log_json(data: Any, filename: str) -> None:
    try:
        if not LOG_DIR.exists():
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            (LOG_DIR.parent / ".gitignore").write_text("*\n", encoding="utf-8")
    except OSError as e:
        print(
            f"Warning: Failed to create log directory {LOG_DIR}: {e}",
            file=sys.stderr,
        )
        return

    try:
        (LOG_DIR / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError as e:
        print(
            f"Warning: Failed to write log file {LOG_DIR / filename}: {e}",
            file=sys.stderr,
        )


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

    Request and response payloads are logged under ``AGENT_LOG_DIR`` or the
    default ``.agent-logs/<timestamp>`` directory, matching the C++ utility
    behavior.

    Args:
        url: Absolute endpoint URL.
        bearer: Bearer token without the ``Bearer `` prefix.
        body: JSON request body.
        response_type: Optional static typing hint for callers that want a
            narrower return type, for example a ``TypedDict``. This argument is
            ignored at runtime and no validation or deserialization is
            performed.

    Raises:
        requests.RequestException: If the HTTP request itself fails. HTTP
            connections time out after ``HTTP_CONNECT_TIMEOUT_SECONDS`` seconds,
            but response reads have no timeout so slow local inference can
            complete.
        RuntimeError: If the server responds with a non-200 status code or the
            response body cannot be parsed as JSON.
    """
    request_id = _next_request_id()
    _log_json(body, f"{request_id}_request.json")

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {bearer}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=(HTTP_CONNECT_TIMEOUT_SECONDS, None),
    )
    if response.status_code != 200:
        try:
            error = response.json()
            _log_json(error, f"{request_id}_response.json")
            error_message = (
                f"HTTP POST {url} failed with status {response.status_code}:\n"
                f"{json.dumps(error, indent=2)}"
            )
        except Exception:
            error_message = (
                f"HTTP POST {url} failed with status {response.status_code}: "
                f"{response.text}"
            )
        raise RuntimeError(error_message)

    try:
        result = response.json()
        _log_json(result, f"{request_id}_response.json")
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to parse JSON response from {url}: {e}") from e
