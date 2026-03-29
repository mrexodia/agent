# Build your own coding agent

Minimal workshop scaffold in Python and C++. This is a workshop scaffold; tool calling and the agent loop are intentionally incomplete.

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

Run:

```bash
uv run agent
```

Select a different model:

```bash
uv run agent --model openai/gpt-oss-120b
```

### C++

Build and run:

```bash
cmake -B build
cmake --build build -j
build/agent
```

Select a different model:

```bash
build/agent --model openai/gpt-oss-120b
```
