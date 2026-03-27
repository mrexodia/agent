import json
import requests
import subprocess
from typing import TypedDict, NotRequired, Optional


class FunctionCall(TypedDict):
    name: str
    arguments: str


class ToolCall(TypedDict):
    type: str
    id: str
    function: FunctionCall


class Message(TypedDict):
    role: str
    content: str
    reasoning_content: NotRequired[str]
    tool_calls: NotRequired[list[ToolCall]]
    tool_call_id: NotRequired[str]


class Property(TypedDict):
    type: str
    description: str
    enum: NotRequired[list[str]]


class Parameters(TypedDict):
    type: str
    properties: dict[str, Property]
    required: list[str]
    additionalProperties: bool


class Function(TypedDict):
    name: str
    description: str
    parameters: Parameters


class Tool(TypedDict):
    type: str
    function: Function


class Request(TypedDict):
    model: str
    messages: list[Message]
    tools: list[Tool]


class Choice(TypedDict):
    index: int
    message: Message
    finish_reason: str


class Response(TypedDict):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]


def json_post(url: str, request: dict) -> dict:
    return requests.post(url, json=request).json()


def lmstudio(request: Request) -> Response:
    return json_post("http://127.0.0.1:1234/v1/chat/completions", request)  # type: ignore


SYSTEM_PROMPT = """
You are an expert coding assistant. You help users with coding tasks by reading files, executing commands, editing code, and writing new files.

Available tools:
- read: Read file contents
- bash: Execute bash commands
- edit: Make surgical edits to files
- write: Create or overwrite files

Guidelines:
- Use bash for file operations like ls, grep, find
- Use read to examine files before editing
- Use edit for precise changes (old text must match exactly)
- Use write only for new files or complete rewrites
- When summarizing your actions, output plain text directly - do NOT use cat or bash to display what you did
- Be concise in your responses
- Show file paths clearly when working with files
""".strip()

TOOLS: list[Tool] = [
    {
        "type": "function",
        "function": {
            "name": "tell_joke",
            "description": "Tell a banger joke to the user",
            "parameters": {
                "type": "object",
                "properties": {
                    "censorship_level": {
                        "type": "string",
                        "description": "Level of censorship applied to the final joke",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": ["censorship_level"],
                "additionalProperties": False,
            },
        },
    }
]

TOOLS: list[Tool] = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read the contents of a file. Supports text files and images (jpg, png, gif, webp). Images are sent as attachments. For text files, defaults to first 2000 lines. Use offset/limit for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read (relative or absolute)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (1-based)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of lines to read",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Execute a bash command in the current working directory. Returns stdout and stderr. Optionally provide a timeout in seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (optional, no default timeout)",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": "Edit a file by replacing exact text. The oldText must match exactly (including whitespace). Use this for precise, surgical edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to edit (relative or absolute)",
                    },
                    "oldText": {
                        "type": "string",
                        "description": "Exact text to find and replace (must match exactly)",
                    },
                    "newText": {
                        "type": "string",
                        "description": "New text to replace the old text with",
                    },
                },
                "required": ["path", "oldText", "newText"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write",
            "description": "Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Automatically creates parent directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write (relative or absolute)",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
]


def main():
    prompt = "Can you tell me a dark joke? API: https://sv443.net/jokeapi/v2/. You can use the bash tool to do this."
    messages: list[Message] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    model = "nouscoder-14b"
    model = "nvidia/nemotron-3-nano"
    while True:
        request: Request = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
        }
        response = lmstudio(request)
        print(json.dumps(response, indent=2))
        choice = response["choices"][0]
        match choice["finish_reason"]:
            case "tool_calls":
                message = choice["message"]
                messages.append(message)
                reasoning = message.get("reasoning_content")
                if reasoning:
                    print(f"[reasoning] {reasoning}")
                content = message["content"].strip()
                if content:
                    print(f"[message] {content}")
                tool_calls = message.get("tool_calls")
                if tool_calls:
                    for tool_call in tool_calls:
                        function = tool_call["function"]
                        name = function["name"]
                        arguments_str = function["arguments"]
                        arguments: dict = json.loads(arguments_str)
                        pretty_args = ",".join(
                            [f"{arg}={repr(value)}" for arg, value in arguments.items()]
                        )
                        print(f"[tool] {name}({pretty_args})")

                        if name == "bash":
                            command = arguments["command"]
                            result = subprocess.run(
                                [
                                    "C:\\Program Files\\Git\\bin\\bash.exe",
                                    "-c",
                                    command,
                                ],
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                            )
                            stdout = result.stdout.strip()
                            if len(stdout) > 10000:
                                stdout = stdout[:10000] + f"...[truncated ({len(stdout) - 10000} chars)]"
                            stderr = result.stderr.strip()
                            if len(stderr) > 10000:
                                stderr = stderr[:10000] + f"...[truncated ({len(stderr) - 10000} chars)]"
                            tool_result = {
                                "stdout": stdout,
                                "stderr": stderr,
                                "exit_code": result.returncode,
                            }
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": json.dumps(tool_result),
                                }
                            )

                            print(f"[bash] {result.stdout}")
            case reason:
                print(f"[finish_reason] {reason}")
                break


if __name__ == "__main__":
    main()
