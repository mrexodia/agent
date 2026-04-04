import inspect
import json
import os
import tempfile
import types
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Union,
    get_origin,
    get_args,
    get_type_hints,
    is_typeddict,
)
import re
import subprocess
from dataclasses import dataclass


WORKING_DIRECTORY = ""
DEFAULT_MAX_LINES = 2000
DEFAULT_MAX_BYTES = 50 * 1024
TOOLS = {}


class ToolError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


def tool(func: Callable) -> Callable:
    TOOLS[getattr(func, "__name__")] = func
    return func


@dataclass
class TruncationResult:
    content: str
    truncated: bool
    truncated_by: Literal["lines", "bytes"] | None
    total_lines: int
    total_bytes: int
    output_lines: int
    output_bytes: int
    last_line_partial: bool
    first_line_exceeds_limit: bool


@dataclass
class FuzzyMatchResult:
    found: bool
    index: int
    match_length: int
    content_for_replacement: str


def normalize_at_prefix(path: str) -> str:
    return path[1:] if path.startswith("@") else path


def resolve_path(path: str) -> str:
    """Resolve a path to an absolute path."""
    expanded = os.path.expanduser(normalize_at_prefix(path))
    if os.path.isabs(expanded):
        return expanded
    return os.path.abspath(os.path.join(WORKING_DIRECTORY, expanded))


def utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def format_size(bytes_count: int) -> str:
    if bytes_count < 1024:
        return f"{bytes_count}B"
    if bytes_count < 1024 * 1024:
        return f"{bytes_count / 1024:.1f}KB"
    return f"{bytes_count / (1024 * 1024):.1f}MB"


def truncate_head(content: str) -> TruncationResult:
    total_bytes = utf8_len(content)
    lines = content.split("\n")
    total_lines = len(lines)

    if total_lines <= DEFAULT_MAX_LINES and total_bytes <= DEFAULT_MAX_BYTES:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            last_line_partial=False,
            first_line_exceeds_limit=False,
        )

    first_line_bytes = utf8_len(lines[0])
    if first_line_bytes > DEFAULT_MAX_BYTES:
        return TruncationResult(
            content="",
            truncated=True,
            truncated_by="bytes",
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=0,
            output_bytes=0,
            last_line_partial=False,
            first_line_exceeds_limit=True,
        )

    output_lines: list[str] = []
    output_bytes = 0
    truncated_by: Literal["lines", "bytes"] = "lines"

    for index, line in enumerate(lines[:DEFAULT_MAX_LINES]):
        line_bytes = utf8_len(line) + (1 if index > 0 else 0)
        if output_bytes + line_bytes > DEFAULT_MAX_BYTES:
            truncated_by = "bytes"
            break
        output_lines.append(line)
        output_bytes += line_bytes

    if len(output_lines) >= DEFAULT_MAX_LINES and output_bytes <= DEFAULT_MAX_BYTES:
        truncated_by = "lines"

    output_content = "\n".join(output_lines)
    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines),
        output_bytes=utf8_len(output_content),
        last_line_partial=False,
        first_line_exceeds_limit=False,
    )


def truncate_string_to_bytes_from_end(text: str, max_bytes: int) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text

    start = len(encoded) - max_bytes
    while start < len(encoded) and (encoded[start] & 0xC0) == 0x80:
        start += 1
    return encoded[start:].decode("utf-8", errors="ignore")


def truncate_tail(content: str) -> TruncationResult:
    total_bytes = utf8_len(content)
    lines = content.split("\n")
    total_lines = len(lines)

    if total_lines <= DEFAULT_MAX_LINES and total_bytes <= DEFAULT_MAX_BYTES:
        return TruncationResult(
            content=content,
            truncated=False,
            truncated_by=None,
            total_lines=total_lines,
            total_bytes=total_bytes,
            output_lines=total_lines,
            output_bytes=total_bytes,
            last_line_partial=False,
            first_line_exceeds_limit=False,
        )

    output_lines: list[str] = []
    output_bytes = 0
    truncated_by: Literal["lines", "bytes"] = "lines"
    last_line_partial = False

    for line in reversed(lines):
        if len(output_lines) >= DEFAULT_MAX_LINES:
            break

        line_bytes = utf8_len(line) + (1 if output_lines else 0)
        if output_bytes + line_bytes > DEFAULT_MAX_BYTES:
            truncated_by = "bytes"
            if not output_lines:
                truncated_line = truncate_string_to_bytes_from_end(
                    line, DEFAULT_MAX_BYTES
                )
                output_lines.insert(0, truncated_line)
                output_bytes = utf8_len(truncated_line)
                last_line_partial = True
            break

        output_lines.insert(0, line)
        output_bytes += line_bytes

    if len(output_lines) >= DEFAULT_MAX_LINES and output_bytes <= DEFAULT_MAX_BYTES:
        truncated_by = "lines"

    output_content = "\n".join(output_lines)
    return TruncationResult(
        content=output_content,
        truncated=True,
        truncated_by=truncated_by,
        total_lines=total_lines,
        total_bytes=total_bytes,
        output_lines=len(output_lines),
        output_bytes=utf8_len(output_content),
        last_line_partial=last_line_partial,
        first_line_exceeds_limit=False,
    )


def normalize_to_lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def detect_line_ending(content: str) -> str:
    crlf_index = content.find("\r\n")
    lf_index = content.find("\n")
    if lf_index == -1 or (crlf_index != -1 and crlf_index < lf_index):
        return "\r\n"
    return "\n"


def restore_line_endings(text: str, ending: str) -> str:
    return text.replace("\n", ending) if ending == "\r\n" else text


def strip_bom(content: str) -> tuple[str, str]:
    if content.startswith("\ufeff"):
        return "\ufeff", content[1:]
    return "", content


def normalize_for_fuzzy_match(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.split("\n"))
    normalized = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", normalized)
    normalized = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', normalized)
    normalized = re.sub(
        r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", normalized
    )
    normalized = re.sub(r"[\u00A0\u2002-\u200A\u202F\u205F\u3000]", " ", normalized)
    return normalized


def fuzzy_find_text(content: str, old_text: str) -> FuzzyMatchResult:
    exact_index = content.find(old_text)
    if exact_index != -1:
        return FuzzyMatchResult(
            found=True,
            index=exact_index,
            match_length=len(old_text),
            content_for_replacement=content,
        )

    fuzzy_content = normalize_for_fuzzy_match(content)
    fuzzy_old_text = normalize_for_fuzzy_match(old_text)
    fuzzy_index = fuzzy_content.find(fuzzy_old_text)
    if fuzzy_index == -1:
        return FuzzyMatchResult(
            found=False,
            index=-1,
            match_length=0,
            content_for_replacement=content,
        )

    return FuzzyMatchResult(
        found=True,
        index=fuzzy_index,
        match_length=len(fuzzy_old_text),
        content_for_replacement=fuzzy_content,
    )


def decode_output(output: bytes | str | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def format_bash_output(output: str) -> str:
    truncation = truncate_tail(output)
    output_text = truncation.content or "(no output)"

    if not truncation.truncated:
        return output_text

    with tempfile.NamedTemporaryFile(
        delete=False, mode="w", encoding="utf-8", suffix=".log"
    ) as temp_file:
        temp_file.write(output)
        temp_path = temp_file.name

    start_line = truncation.total_lines - truncation.output_lines + 1
    end_line = truncation.total_lines

    if truncation.last_line_partial:
        last_line = output.split("\n")[-1]
        last_line_size = format_size(utf8_len(last_line))
        output_text += (
            f"\n\n[Showing last {format_size(truncation.output_bytes)} of line "
            f"{end_line} (line is {last_line_size}). Full output: {temp_path}]"
        )
    elif truncation.truncated_by == "lines":
        output_text += (
            f"\n\n[Showing lines {start_line}-{end_line} of "
            f"{truncation.total_lines}. Full output: {temp_path}]"
        )
    else:
        output_text += (
            f"\n\n[Showing lines {start_line}-{end_line} of "
            f"{truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). "
            f"Full output: {temp_path}]"
        )

    return output_text


@tool
def read(
    path: Annotated[str, "Path to the file to read (relative or absolute)"],
    offset: Annotated[
        Optional[int], "Line number to start reading from (1-indexed)"
    ] = None,
    limit: Annotated[Optional[int], "Maximum number of lines to read"] = None,
) -> str:
    """Read the contents of a file. Supports text files. For text files, output is truncated to 2000 lines or 50KB (whichever is hit first). Use offset/limit for large files. When you need the full file, continue with offset until complete."""
    try:
        with open(resolve_path(path), "r", encoding="utf-8") as file_handle:
            text_content = file_handle.read()

        all_lines = text_content.split("\n")
        start_line = max(0, offset - 1) if offset else 0
        start_line_display = start_line + 1

        if start_line >= len(all_lines):
            raise ToolError(
                f"Offset {offset} is beyond end of file ({len(all_lines)} lines total)"
            )

        if limit is not None:
            end_line = min(start_line + limit, len(all_lines))
            selected_content = "\n".join(all_lines[start_line:end_line])
            user_limited_lines = end_line - start_line
        else:
            selected_content = "\n".join(all_lines[start_line:])
            user_limited_lines = None

        truncation = truncate_head(selected_content)

        if truncation.first_line_exceeds_limit:
            first_line_size = format_size(utf8_len(all_lines[start_line]))
            return (
                f"[Line {start_line_display} is {first_line_size}, exceeds "
                f"{format_size(DEFAULT_MAX_BYTES)} limit. Use bash: sed -n "
                f"'{start_line_display}p' {path} | head -c {DEFAULT_MAX_BYTES}]"
            )

        if truncation.truncated:
            end_line_display = start_line_display + truncation.output_lines - 1
            next_offset = end_line_display + 1
            output_text = truncation.content
            if truncation.truncated_by == "lines":
                output_text += (
                    f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                    f"of {len(all_lines)}. Use offset={next_offset} to continue.]"
                )
            else:
                output_text += (
                    f"\n\n[Showing lines {start_line_display}-{end_line_display} "
                    f"of {len(all_lines)} ({format_size(DEFAULT_MAX_BYTES)} limit). "
                    f"Use offset={next_offset} to continue.]"
                )
            return output_text

        if user_limited_lines is not None and start_line + user_limited_lines < len(
            all_lines
        ):
            remaining = len(all_lines) - (start_line + user_limited_lines)
            next_offset = start_line + user_limited_lines + 1
            output_text = truncation.content
            output_text += (
                f"\n\n[{remaining} more lines in file. Use offset={next_offset} "
                f"to continue.]"
            )
            return output_text

        return truncation.content
    except ToolError:
        raise
    except Exception as error:
        raise ToolError(f"Failed to read file {path}: {error}")


@tool
def bash(
    command: Annotated[str, "Bash command to execute"],
    timeout: Annotated[
        Optional[int], "Timeout in seconds (optional, no default timeout)"
    ] = None,
) -> str:
    """Execute a bash command in the current working directory. Returns stdout and stderr. Output is truncated to last 2000 lines or 50KB (whichever is hit first). If truncated, full output is saved to a temp file. Optionally provide a timeout in seconds."""
    if not os.path.exists(WORKING_DIRECTORY):
        raise ToolError(
            f"Working directory does not exist: {WORKING_DIRECTORY}\n"
            "Cannot execute bash commands."
        )

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKING_DIRECTORY,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = decode_output(result.stdout)
        output_text = format_bash_output(output)
        if result.returncode != 0:
            raise ToolError(
                f"{output_text}\n\nCommand exited with code {result.returncode}"
            )
        return output_text
    except ToolError:
        raise
    except subprocess.TimeoutExpired as error:
        output = decode_output(error.stdout)
        if output:
            output += "\n\n"
        raise ToolError(f"{output}Command timed out after {timeout} seconds")
    except Exception as error:
        raise ToolError(f"Failed to execute bash command '{command}': {error}")


@tool
def edit(
    path: Annotated[str, "Path to the file to edit (relative or absolute)"],
    oldText: Annotated[str, "Exact text to find and replace (must match exactly)"],
    newText: Annotated[str, "New text to replace the old text with"],
) -> str:
    """Edit a file by replacing exact text. The oldText must match exactly (including whitespace). Use this for precise, surgical edits."""
    try:
        abs_path = resolve_path(path)
        if not os.path.exists(abs_path):
            raise ToolError(f"File not found: {path}")

        with open(abs_path, "r", encoding="utf-8") as file_handle:
            raw_content = file_handle.read()

        bom, content = strip_bom(raw_content)
        original_ending = detect_line_ending(content)
        normalized_content = normalize_to_lf(content)
        normalized_old_text = normalize_to_lf(oldText)
        normalized_new_text = normalize_to_lf(newText)

        match_result = fuzzy_find_text(normalized_content, normalized_old_text)
        if not match_result.found:
            raise ToolError(
                f"Could not find the exact text in {path}. The old text must "
                "match exactly including all whitespace and newlines."
            )

        fuzzy_content = normalize_for_fuzzy_match(normalized_content)
        fuzzy_old_text = normalize_for_fuzzy_match(normalized_old_text)
        occurrences = fuzzy_content.count(fuzzy_old_text)
        if occurrences > 1:
            raise ToolError(
                f"Found {occurrences} occurrences of the text in {path}. The "
                "text must be unique. Please provide more context to make it unique."
            )

        base_content = match_result.content_for_replacement
        new_content = (
            base_content[: match_result.index]
            + normalized_new_text
            + base_content[match_result.index + match_result.match_length :]
        )

        if base_content == new_content:
            raise ToolError(
                f"No changes made to {path}. The replacement produced identical "
                "content. This might indicate an issue with special characters or "
                "the text not existing as expected."
            )

        final_content = bom + restore_line_endings(new_content, original_ending)
        with open(abs_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(final_content)

        return f"Successfully replaced text in {path}."
    except ToolError:
        raise
    except Exception as error:
        raise ToolError(f"Failed to edit file {path}: {error}")


@tool
def write(
    path: Annotated[str, "Path to the file to write (relative or absolute)"],
    content: Annotated[str, "Content to write to the file"],
) -> str:
    """Write content to a file. Creates the file if it doesn't exist, overwrites if it does. Automatically creates parent directories."""
    try:
        abs_path = resolve_path(path)
        directory = os.path.dirname(abs_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(content)
        return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as error:
        raise ToolError(f"Failed to write file {path}: {error}")


def _unwrap_annotated(annotation: Any) -> tuple[Any, str | None]:
    description = None
    while get_origin(annotation) is Annotated:
        args = get_args(annotation)
        annotation = args[0]
        for metadata in args[1:]:
            if isinstance(metadata, str):
                description = metadata
                break
    return annotation, description


def _openai_schema_for_type(annotation: Any) -> dict[str, Any]:
    annotation, _ = _unwrap_annotated(annotation)

    if annotation is Any or annotation is inspect.Parameter.empty:
        return {}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and len(non_none_args) != len(args):
            return _openai_schema_for_type(non_none_args[0])
        return {"anyOf": [_openai_schema_for_type(arg) for arg in args]}

    if origin is Literal:
        literal_values = list(args)
        schema: dict[str, Any] = {"enum": literal_values}
        if literal_values and all(isinstance(value, str) for value in literal_values):
            schema["type"] = "string"
        elif literal_values and all(
            isinstance(value, bool) for value in literal_values
        ):
            schema["type"] = "boolean"
        elif literal_values and all(
            isinstance(value, (int, float)) for value in literal_values
        ):
            schema["type"] = "number"
        return schema

    if annotation is str:
        return {"type": "string"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation in (int, float):
        return {"type": "number"}
    if annotation is type(None):
        return {"type": "null"}

    if is_typeddict(annotation):
        properties: dict[str, Any] = {}
        required: list[str] = []
        hints = get_type_hints(annotation, include_extras=True)
        required_keys = getattr(annotation, "__required_keys__", set())

        for field_name, field_type in hints.items():
            field_schema = _openai_schema_for_type(field_type)
            _, description = _unwrap_annotated(field_type)
            if description:
                field_schema["description"] = description
            properties[field_name] = field_schema
            if field_name in required_keys:
                required.append(field_name)

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }
        return schema

    if origin in (list, set, frozenset):
        item_schema = _openai_schema_for_type(args[0]) if args else {}
        return {"type": "array", "items": item_schema}

    if origin is tuple:
        item_schema = _openai_schema_for_type(args[0]) if args else {}
        return {"type": "array", "items": item_schema}

    if origin is dict:
        schema: dict[str, Any] = {"type": "object"}
        if len(args) == 2:
            schema["additionalProperties"] = _openai_schema_for_type(args[1])
        return schema

    if annotation is dict:
        return {"type": "object"}

    if annotation in (list, tuple, set, frozenset):
        return {"type": "array", "items": {}}

    return {}


def generate_tool_definitions() -> list[dict]:
    result = []
    for tool_name, tool_func in TOOLS.items():
        sig = inspect.signature(tool_func)
        hints = get_type_hints(tool_func, include_extras=True)

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            annotation = hints.get(param_name, param.annotation)
            base_annotation, description = _unwrap_annotated(annotation)
            param_schema = _openai_schema_for_type(base_annotation)

            if description:
                param_schema["description"] = description

            properties[param_name] = param_schema

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        result.append(
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": (tool_func.__doc__ or "").strip(),
                    "parameters": {
                        "type": "object",
                        "required": required,
                        "properties": properties,
                    },
                    "strict": False,
                },
            }
        )

    return result


def _format_tool_argument(value: Any, max_length: int = 120) -> str:
    if isinstance(value, str):
        formatted = json.dumps(value, ensure_ascii=False)
    else:
        try:
            formatted = json.dumps(value, ensure_ascii=False)
        except TypeError:
            formatted = repr(value)

    if len(formatted) > max_length:
        formatted = formatted[: max_length - 3] + "..."

    return formatted


def _pretty_print_tool_call(name: str, params: dict[str, Any]) -> None:
    if name == "bash" and isinstance(params.get("command"), str):
        pretty_tool = f"$ {params['command']}"
        timeout = params.get("timeout")
        if timeout is not None:
            pretty_tool += f" ({timeout}s timeout)"
        print("🦾", pretty_tool)
        return

    tool_func = TOOLS.get(name)
    ordered_names = []
    if tool_func is not None:
        ordered_names.extend(inspect.signature(tool_func).parameters)
    ordered_names.extend(param for param in params if param not in ordered_names)

    pretty_args = ", ".join(
        f"{param_name}={_format_tool_argument(params[param_name])}"
        for param_name in ordered_names
        if param_name in params
    )
    print("🦾", f"{name}({pretty_args})")


def call_tool(name: str, arguments: str) -> str:

    try:
        params = json.loads(arguments)
    except json.JSONDecodeError as error:
        return f"[failed to decode arguments JSON for {name}: {error}]"

    if not isinstance(params, dict):
        return (
            f"[invalid arguments for {name}: expected a JSON object, "
            f"got {type(params).__name__}]"
        )

    tool_func = TOOLS.get(name)
    if tool_func is None:
        return f"[unknown tool: {name}]"

    try:
        bound = inspect.signature(tool_func).bind(**params)
    except TypeError as error:
        return f"[invalid arguments for {name}: {error}]"

    _pretty_print_tool_call(name, params)

    try:
        result = tool_func(*bound.args, **bound.kwargs)
        if result is None:
            return ""
        if not isinstance(result, str):
            return str(result)
        return result
    except ToolError as error:
        return f"[{error}]"
    except Exception as error:
        return f"[failed to execute tool {name}: {error}]"
