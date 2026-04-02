# Build your own coding agent

Minimal workshop scaffold in Python and C++. This is a workshop scaffold; tool calling and the agent loop are intentionally incomplete. Look at [`EXERCISES.md`](./EXERCISES.md) for the tasks you can do.

**Note**: This project uses the system prompt from [Pi](https://shittycodingagent.ai) and takes great inspiration from Mario's post [What I learned building an opinionated and minimal coding agent](https://mariozechner.at/posts/2025-11-30-pi-coding-agent/).

## Setup

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Fill in:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

## CLI

The CLI:
- Loads the `.env` file
- Prints the system prompt
- Runs `pwd` via bash
- Prints the command output and exit code
- Sends one `/chat/completions` request
- Prints the JSON response

### Python

You need to [install uv](https://github.com/astral-sh/uv#installation) and then run the `agent`:

```bash
uv run agent
```

Alternatively use `pip` from a venv:

```bash
pip install -e .
```

Select a different model:

```bash
uv run agent --model openai/gpt-oss-120b
```

### C++

You need [CMake](https://cmake.org/download) and a C++ compiler and then you can build and run:

```bash
cmake -B build
cmake --build build -j
build/agent
```

Select a different model:

```bash
build/agent --model openai/gpt-oss-120b
```
