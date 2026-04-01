# Build your own coding agent

Below are the exercises to help you build your own coding agent incrementally. I strongly advise against using an LLM for this at first. Once your own coding agent works you can use it to improve itself.

## Exercise 1: Hello, world!

Get the template to run in the language of your choice. Expected output:

```
[System prompt]
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

[Bash command: pwd]
/Users/duncan/Projects/agent
Exit code: 0

[OpenAI Response]
{
  "choices": [
    {
      "finish_reason": "stop",
      "index": 0,
      "logprobs": null,
      "message": {
        "content": "Hello! 😊",
        "reasoning": "We need to respond appropriately. It's a chat; user says \"Hello, world!\". The developer instruction is empty. So just respond.",
        "reasoning_details": [
          {
            "format": "unknown",
            "index": 0,
            "text": "We need to respond appropriately. It's a chat; user says \"Hello, world!\". The developer instruction is empty. So just respond.",
            "type": "reasoning.text"
          }
        ],
        "refusal": null,
        "role": "assistant"
      },
      "native_finish_reason": "stop"
    }
  ],
  "created": 1775013057,
  "id": "gen-1775013057-t9PzCg7ULQWl45FmO8hd",
  "model": "openai/gpt-oss-20b",
  "object": "chat.completion",
  "provider": "Fireworks",
  "system_fingerprint": null,
  "usage": {
    "completion_tokens": 40,
    "completion_tokens_details": {
      "audio_tokens": 0,
      "image_tokens": 0,
      "reasoning_tokens": 32
    },
    "cost": 2.7995e-05,
    "cost_details": {
      "upstream_inference_completions_cost": 1.2e-05,
      "upstream_inference_cost": 2.7995e-05,
      "upstream_inference_prompt_cost": 1.5995e-05
    },
    "is_byok": false,
    "prompt_tokens": 231,
    "prompt_tokens_details": {
      "audio_tokens": 0,
      "cache_write_tokens": 0,
      "cached_tokens": 5,
      "video_tokens": 0
    },
    "total_tokens": 271
  }
}
```

## Exercise 2: ChatGPT

Make a basic chat app with multi-turn support (ChatGPT clone). Print `reasoning` if available.

Have a conversation about your favorite programming language. Verify that the model remembers what you said in previous turns.

## Exercise 3: Bash

Implement `bash` tool calling support (**use `bash_command` from utils**). If you want, add tool approval (and a `--yolo` flag to bypass it).

Test prompt:

> What programming languages is this project written in, and how many lines of code are in each?

Once that works, try something like this:

> Can you add a comment to the top of `cli.py`?

How will the agent write to files?

## Exercise 4: Agent

Add `read/write/edit` tools:

```python
def read(path: str, offset: int | None = None, limit: int | None = None) -> str: pass
def write(path: str, content: str) -> str: pass
def edit(path: str, oldText: str, newText: str) -> str: pass
```

Test prompt:

> Add a docstring to `utils.py` explaining its purpose.

More ambitious prompt:

> Create a log viewer web UI for the `.agent-logs` produced by this coding agent.

_Note_: you will likely reach the limits of `gpt-oss-20b` here. Feel free to go to the next exercise and try a different model!

_Hint_: if you get stuck, look at `demos/agentic-trace` for the tool definitions.

## Exercise 5: Picking a model

Go ahead and try some other models. You can polish the log viewer or play around with another project.

| Model                  | Input  | Output | Purpose     |
| ---------------------- | ------ | ------ | ----------- |
| `openai/gpt-oss-20b`   | $0.03  | $0.11  | Testing     |
| `openai/gpt-oss-120b`  | $0.039 | $0.19  | Testing     |
| `minimax/minimax-m2.7` | $0.30  | $1.20  | Actual work |
| `z-ai/glm-4.7`         | $0.39  | $1.75  | Actual work |
| `moonshotai/kimi-k2.5` | $0.42  | $2.20  | Actual work |
| `xiaomi/mimo-v2-pro`   | $1.00  | $3.00  | Actual work |
| `z-ai/glm-5`           | $0.72  | $2.30  | Actual work |

Free models: https://openrouter.ai/models?max_price=0&order=most-popular (check privacy policy).

Benchmarks:
- https://openrouter.ai/rankings
- https://onyx.app/best-llm-for-coding
- https://arena.ai/leaderboard/code
- https://artificialanalysis.ai/leaderboards/models
- https://whatllm.org/blog/best-coding-models-january-2026
- https://aider.chat/docs/leaderboards/

## Exercise 6: Self improvement

Some ideas for homework/follow-up:

- Token usage/cost tracking
- Implement session/resume support
- Support https://agents.md protocol
- Support [skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) protocol
- Add a web UI for your agent

The idea is that you dogfood your own agent and let it improve itself.
