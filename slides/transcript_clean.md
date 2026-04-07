# Build Your Own Coding Agent - Workshop Transcript (Cleaned)

> Workshop by Duncan Ogilvie, 2026-04-07
>
> Sections in [brackets] are side conversations or setup that occurred during the workshop.

---

## Pre-talk Setup [00:00 - 06:30]

[Setting up the room, audio checks, finding seats for latecomers. Duncan asks someone to verify the audio is working on the remote meeting.]

---

## Introduction [06:34 - 08:45]

Thanks for attending the workshop. The idea is that we will do actual work, and preferably without any agents - because you want to learn something, and in this case it's usually not good to use an agent.

I'll do a quick presentation where I'll try to explain the basics of coding agents - what does a coding agent look like and how does it work on the back end? And then the idea is that within one hour you should be able to make your own coding agent that can call bash commands, read files, write files - basically like a Claude Code alternative, but super shitty obviously because it's only a few hundred lines of code.

But that's what I want to convey today: I want to show you that it's super easy to make an agent because the model is actually doing all the work. That's kind of the trick in the end - spoiler.

**Goals:**
- Form a technical intuition - when someone says "coding agent", what does it actually mean?
- Build your own agent
- Once the minimal version is built, you will use the agent itself to improve itself - that's the idea, to show that these agents can work on themselves

**Non-goals:**
- The previous session was about showing how people use agents. I don't want to go into how to *use* agents
- How to make your own LLMs
- Discuss the ethics of LLMs or company strategy
- The goal is really just to make your own agent on a technical level

---

## Large Language Models [09:40 - 13:10]

The way that I see a large language model is that it's just a stateless magic black box. Here I put the Python definition: you take some input which is a string, and then out of it comes a string - that's all they can do. For me this is enough of an abstraction. I know that it's very complicated under the hood with machine learning, but we can forget about all of that because it's completely irrelevant to what we're doing here, which is building an agent.

### Tokens

One thing that's important to highlight is that the internal representation of the text you put into the model - it becomes tokens. I'm using a tool called TikTokenizer where you can put some text in. For example, "How is the weather?" - the conversation with system prompt, user message, assistant reply - gets translated to a bunch of numbers.

If you highlight a token, you can see that, for example, the word "you" in GPT-4o has the value 3575. It's not important for us to understand the translation, but it's important to know that:
- Text is not stored as text inside the model
- You pay per token
- One word is not necessarily one token - sometimes longer words are multiple tokens

I also recommend Andrej Karpathy's deep dive video (about four hours) - it goes into depth on how LLMs actually work, not at the machine learning level but kind of in between the black box and the ML details. Really worth watching.

### Context Window

The context window is just the maximum length of the string that goes in, measured in tokens. It can be one million tokens right now, but two years ago that would have been unthinkably high.

When you use Claude Code and you get "compaction", that means the context window was so full that nothing else fit. So there's some heuristic process to summarize what happened, keep the most important files that were modified, and create a compressed form of the conversation. That's what compaction is - it happens when the context window is full.

---

## LLM Providers [13:10 - 15:54]

- **OpenAI and Anthropic** - the leaders. It's kind of a race, sometimes the new Opus 4.7 is much better, then whatever. But OpenAI and Anthropic are the clear winners of the AI arms race so far.
- **Google** - makes the worst models you can possibly imagine. They're completely useless in my view. They literally cannot do anything, not even basic tasks. But that was maybe six months ago, so maybe they fixed some things.
- **Mistral** - one European provider, but their models are not very good. Typical European fashion.
- **Chinese providers** (Z.ai, Moonshot, MiniMax) - not as good as the Anthropic models, but can be really good especially considering the cost.

We will not be using Claude Opus for this workshop because we have $200 for everyone.

> **Q: What about Copilot?**
>
> A: Copilot is not a model in itself. Copilot is a harness - like what we're going to build. They usually use Claude or some form of ChatGPT. Microsoft has an agreement with OpenAI, so it's like GPT-4o for semi-pro, and on pro you have a bit higher tier. Those are brand names; these [on the slide] are the actual providers of the actual models.

### OpenRouter

Today we'll be using a platform called OpenRouter. It's a unified interface that exposes the OpenAI API - the most common API. You can use most models through it: Google experimental models, Xiaomi, ChatGPT, Mistral, everything.

For example, Opus 4.1 costs $15 per million input tokens and $75 per million output tokens. That's not what we'll use for testing, but once you have something working, you can change the model string and use any model with the same API key. That's nice because we don't have to learn the Gemini API vs. Anthropic API vs. Chinese versions - it's a centralized platform.

---

## OpenAI API: Endpoints [15:54 - 17:34]

The OpenAI API was the first and became the de facto standard for all open-source stuff and other providers, because everyone wants to be compatible with it.

**Two endpoints:**

1. **`/v1/chat/completions`** (older, most widely supported, stateless) - this is what we'll use. It's nice for teaching because it's just input string, output string.

2. **`/v1/responses`** (newer, more features) - allows you to not resend the whole state again; you can say "I want to resume the previous state." But it's trickier for teaching, so we won't use this.

Similarly, there's the **Anthropic API** (`/v1/messages`) - also very popular, used by Claude Code. Many Chinese model vendors expose both the Anthropic API and the OpenAI API so you can use Codex and Claude Code clients directly with Chinese models, cheaper. But fundamentally they're all the same, just different formats.

---

## OpenAI API: Messages Request [17:41 - 21:04]

I'm using a tool called LM Studio that runs locally on the Mac. It's the same as the remote API because it implements the same endpoint.

LM Studio lets you load local models. I was using GPT-OSS-20B - 20 billion parameters, very small, fits in about 12 GB of VRAM. If you have a Mac, you can run it locally on pretty much every Mac unless you have an 8 GB Air. On Windows you'd need a better GPU like a 3090. If you don't want to send any data to the cloud, you can run local models, but they're pretty bad - I just use them for testing and developing.

### Example Request

```
POST 127.0.0.1:1234/v1/chat/completions
Content-Type: application/json
Authorization: Bearer <API_KEY>
```

The body has:
- **`model`**: which model to use (e.g., `openai/gpt-oss-20b`)
- **`messages`**: array with different roles
  - `system` role: the system prompt (e.g., "You answer in one word")
  - `user` role: what I type into the chat (e.g., "Which country invented brie?")

### Example Response

The response is JSON with a `choices` array (you can ask for top-5 replies, but we always use only one because it's expensive). The first choice contains:
- `role`: "assistant"
- `content`: "France"
- `reasoning`: "Need one word answer. Brie invented in France. So answer: France."
- `tool_calls`: [] (empty - no tools yet)

The reasoning key is the "thinking" of the model. It's important to know that this thinking is not actually thinking - it's kind of regurgitating relevant stuff to produce a better result. Sometimes it gives insight into why it came up with something, sometimes it's complete nonsense in the thinking but the answer is still correct.

---

## OpenAI API: Messages Demo [21:04 - 27:50]

[Live demo using a VS Code extension to send HTTP requests to OpenRouter. See [`demos/chat-turn1.http`](../demos/chat-turn1.http) and [`demos/chat-turn2.http`](../demos/chat-turn2.http).]

The response also shows usage: 81 tokens in the prompt, 43 in the reply, 124 total, costing $0.0000121. Very cheap for this case, but with a million tokens it multiplies quickly.

### Multi-turn Chat (Second Turn)

To ask a follow-up question like "What is the capital?" (ambiguous without context), we have to build the request with:
1. System message: "You answer in one word"
2. User message: "Which country invented brie?"
3. Assistant message: "France" (the previous reply)
4. User message: "What is the capital?"

We have to append to the messages array - our memory - to get the correct answer. The model replies "Paris" and in the reasoning says: "The question 'what is the capital' is ambiguous. Probably France's capital: Paris."

Every user-assistant combination is called a **turn**. You go back and forth, keeping appending those messages.

> **Q: Does it send back the whole conversation?**
>
> A: No, it only sends the reply back. You have to construct the request again with all previous messages appended. The whole request with everything is sent again each time. You append the reply to your request, and the next one, and the next one.

> **Q: Isn't that wasteful bandwidth?**
>
> A: Yes! That's why the newer Responses API exists - you get a response ID and can resume from it. But we're using the completions API for teaching.

---

## Tool Calling: History (Few-Shot Prompting) [28:55 - 36:44]

In 2023-ish, before actual tool calling was added to the API, we used a technique called **few-shot prompting** to emulate tool calling.

The system prompt would say: "You are a coding assistant and you have access to the following tools," followed by XML definitions of tools like `read_file`, `write_file`, `run_bash_command` with their parameters and descriptions.

Then we'd tell the model: "If you want to use a tool, use this format" - with `<tool_use>` XML tags containing the tool name and parameters. We'd also say "only print this XML, no other stuff." Then we'd give examples - this is the "few-shot" part, and it's a pretty effective way to get the model to work the way you want.

### Live Demo (few-shot)

[This demo was done live in LM Studio. The full conversation export is at [`demos/historical-tool-calling.md`](../demos/historical-tool-calling.md).]

Using GPT-OSS-20B (very small model) with this system prompt. When asked "What is this project?", the model replied with a `tool_use` to read `readme.md` - pretty clever. I simulated the tool result by pasting the README content back. Then the model summarized the project. I asked "How does it work? What APIs is this project using?" and it asked to read `poc.py`.

The idea: we inject the text of tool results back into the chat so the model knows the results, because the model can only input text and output text.

### Downsides of XML approach:
- Models aren't great at producing correct XML - parsing failures were common
- People kept tweaking their prompts and adding more examples to get it working
- It was "very disgusting hacking"

### Modern Tool Calling

Under the hood, the modern API still works similarly, except with special tokens instead of text. The provider can abstract and optimize it on their side. But the text/XML method still works - even Cline (VS Code plugin) only switched to the actual API in December 2025.

> **Q: Can it call multiple tools in one reply?**
>
> A: Yes, it can call twenty tools in a row in one reply. And with streaming APIs, you can start executing tools in parallel while the model is still generating more tool calls. But we won't get into streaming today.

---

## Tool Calling: OpenAI API [36:44 - 38:09]

In the completions API, we pass our messages plus an array of `tools`. Each tool has a JSON Schema definition:

```json
{
  "type": "function",
  "function": {
    "name": "get_weather",
    "description": "Get the current weather for a location",
    "parameters": {
      "type": "object",
      "required": ["location"],
      "properties": {
        "location": { "type": "string", "description": "..." }
      }
    }
  }
}
```

---

## Tool Calling: Demo [38:09 - 40:56]

[Live demo: "How is the weather in Paris?" with `get_weather` tool defined. See [`demos/tools-turn1.http`](../demos/tools-turn1.http) and [`demos/tools-turn2.http`](../demos/tools-turn2.http).]

The response contains `tool_calls` array: the model asks us to call `get_weather` with arguments `{"location": "Paris"}`.

Our job: extract the arguments, deserialize the JSON, call the actual weather API, then inject the result back.

**Second turn** - we append:
1. The original system + user messages
2. The assistant message (with tool_calls) - this must be in context or the model gets confused
3. A message with `role: "tool"`, `content: "The weather in Paris is sunny, 25 degrees"`, and `tool_call_id` matching the original call

The model then produces the final answer: "The weather in Paris is currently sunny with a temperature of 25 degrees." The `tool_calls` array is now empty - meaning we're done, and we give control back to the user.

---

## Coding Agents: Definition [41:12 - 42:42]

Simon Willison, who writes really good blog posts about AI, came up with a great definition:

> **"An LLM agent runs tools in a loop to achieve a goal."**

This is important because we can actually implement this - we can write a loop. Any other definitions are basically marketing bullshit. Microsoft Copilot mixes the term "agent" with system prompts and memory and it's very unclear.

The key insight: **we do not stop calling tools until the model says we are done.** That's the loop part. It's not one question, one answer - it's one question, then the model is reading files, writing stuff, running commands, and only when the model says it's finished do you stop. That's fundamentally different from just chatting.

---

## Coding Agents: Pseudocode [42:42 - 45:23]

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]
while True:  # Outer loop: user interaction
    user_input = input()
    messages.append({"role": "user", "content": user_input})

    while True:  # Inner loop: agent/tool loop
        message = llm_request({
            "model": "openai/gpt-oss-20b",
            "messages": messages,
            "tools": TOOL_DEFINITIONS,
        })["choices"][0]["message"]
        messages.append(message)  # role: "assistant"

        if not message.get("tool_calls"):
            print(message["content"])
            break  # Done - back to user input

        for tool_call in message["tool_calls"]:
            result = call_tool(tool_call)
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            })
```

**Explanation:**
- Start with system prompt in messages array
- **Outer loop**: ask for user input, append as `role: "user"`
- **Inner loop** (the agentic loop): send messages + tool definitions to the LLM, get the response, append it as `role: "assistant"`
  - If no tool calls → print the content, break back to user input
  - If tool calls → execute each tool, append results as `role: "tool"` with the matching `tool_call_id`, then loop again
- **This is it. This is the coding agent. There is nothing else. The rest is just UI on top.**

---

## Coding Agents: Caching [45:38 - 46:55]

[See diagram: [`slides/cache-invalidation.svg`](./cache-invalidation.svg)]

We keep re-sending the same context, but on the server side they cache the processing so they don't have to re-process 100K tokens every time. They process just the additional user message or tool result.

For bigger models, cached tokens cost much less - like one-tenth or less. So it's very important to keep appending messages correctly and not modify anything at the beginning, because that invalidates the cache and costs go up. The cost accumulates roughly quadratically.

Interesting note: the agent called OpenCode is still modifying messages internally and invalidating the cache every time, and nobody knows why.

---

## Templates & Getting Started [46:55 - 49:16]

Templates are in the repo - Python or C++, both tested and working.

What's provided:
- JSON POST request with logging (logs request/response bodies to a local directory)
- `bash_command` tool implementation (for Windows: finds git bash path so models can use bash instead of CMD/PowerShell - models are very good at bash and very bad at CMD)
- Pi's system prompt (see [Pi coding agent blog post](https://marioslab.io/posts/pi-coding-agent/building-pi/)) - a short system prompt that works really well, just copy-paste it

**Practical notes:**
- Please use cheap models first (GPT-OSS-20B) before switching to expensive ones
- The exercise file ([`EXERCISES.md`](../EXERCISES.md)) lists models that are good but still cheap
- OpenRouter API key shared with $200 budget
- Free models are available too (they use your data for training, but decent for playing around at home)
- Python template uses `uv` (a Python package manager) - run from the repo root
- For C++ you need CMake and a compiler

---

## Working Session [49:16 onwards]

[Participants start coding. Duncan walks around helping people. A full agentic request/response trace from the Pi coding agent is available in [`demos/agentic-trace/`](../demos/agentic-trace/) (requests `1-request.http` through `4-request.http` with corresponding responses), showing the complete multi-turn tool loop in action. Below are notable interactions.]

> **Q: How do you handle when you have too many tokens?**
>
> A: There's the concept of compaction. One strategy: put the tokens into the model with a system prompt saying "please summarize what happened." But usually it's a mix of summary and deterministic extraction - like which files were read and written - to give the model context about what it was working on. You shouldn't have to worry about this for the basic exercises; it's in the advanced exercises at the end if you're very fast.

> **Q: Is there a library for compacting/caching tokens?**
>
> A: You can do both - there are different approaches you can mix.

> **Q: The repo link points to C++?**
>
> A: No, there's also Python. The Python template is in a subdirectory. Run it with `uv run` from the repo root.

> **Q: If the agent asks for multiple tool calls, how do we handle that?**
>
> A: If there are multiple, you just go one by one. Call the first one, append `role: "tool"` with the result and `tool_call_id`, then the next, and so on. Append all results, then send the whole thing back to the model.

> **Q: What are the message roles?**
>
> A: System, user, assistant, and tool. There are some unofficial ones, but those are the main four.

> **Q: What about the `choices` array?**
>
> A: For the completions API, you could ask for multiple choices (e.g., five replies for code competition). But we always use `choices[0]` because multiple choices are expensive.

> **Q: What tools should we implement?**
>
> A: I'd recommend first getting tool calling to work, then focus on implementing `bash_command` (it's already provided in the template with timeouts and everything), then add `read_file`, `write_file`, and `edit_file` (string replace). Check [`EXERCISES.md`](../EXERCISES.md) for the order.

> **Q: What do you use for diagrams?**
>
> A: Excalidraw. It's great - you can draw something quickly, copy as SVG for slides. I use it from Obsidian. It has that hand-drawn aesthetic that's not so professional, but you can quickly make things.

> **Q: What do you use for slides?**
>
> A: Marp - you write Markdown and use three dashes to create the next slide. It's ugly as hell but I can't be bothered with Google Slides or PowerPoint. You can do themes and make it nice, but I just use dark mode.

> **Q: Is there a `.env` file needed?**
>
> A: Yes, you need to create a `.env` file and put the API key from the meeting chat in there. The template auto-loads secrets from it.

> **Q: What formatter/linter for Python?**
>
> A: Ruff. You can set up VS Code to format on save. For type checking, I use MyPy (it's slow compared to others, but works). There's also Basedpyright.

---

## Notable Observations

- The bash tool was already implemented in the template to reduce boilerplate - participants only needed to implement the tool loop, tool definitions, and additional tools (read/write/edit file)
- The logging folder (`.agent-logs/`) captures all request/response JSONs for debugging
- Several participants got their agents working during the session, with the model successfully calling bash commands and reading files
- Duncan emphasized repeatedly: "This is it. This is everything. The coding agent is literally just this loop. Claude Code, Codex - they're literally this plus UI on top."

---

# Q&A Summary

| # | Question | Answer | Potential Confusion |
|---|----------|--------|-------------------|
| 1 | Is the context window measured in tokens or characters? | In tokens. The context window is measured in tokens, and can be up to one million tokens currently. | Some might confuse tokens with words or characters - they're none of these; they're subword units. |
| 2 | What is Copilot? Is it a model? | No, Copilot is a harness (like what we're building), not a model. It uses GPT-4o or Claude under the hood. Microsoft has an agreement with OpenAI. | People confuse product brand names (Copilot, ChatGPT) with the underlying models (GPT-4o, Claude Opus). |
| 3 | Does the API send back the whole conversation? | No, only the new reply. You must reconstruct the full message array yourself and resend everything each time. | This is counterintuitive for people used to stateful chat UIs - the API is stateless. |
| 4 | Isn't resending everything wasteful? | Yes. That's why the newer Responses API exists with `previous_message_id`. But the completions API we're using is stateless. | - |
| 5 | Can the model call multiple tools in one response? | Yes, potentially many. You process them one by one, appending each result, then send all back. | People might think it's limited to one tool call per response. |
| 6 | How do you handle too many tokens / context overflow? | Compaction: a mix of LLM-generated summary and deterministic extraction of which files were read/written. Not needed for basic exercises. | Compaction is not just "summarize" - it's a mix of strategies. |
| 7 | What are the valid message roles? | `system`, `user`, `assistant`, `tool` (and some unofficial ones). | The `tool` role is distinct from `user` - tool results must use `role: "tool"` with a `tool_call_id`. |
| 8 | What model should I use? | Start with cheap models like GPT-OSS-20B for testing. Once working, try GLM-4-7B or other models listed in the exercises file. Don't burn the budget on expensive models during development. | - |
| 9 | Where is the Python template? | In a subdirectory of the repo. Run with `uv run` from the repo root. | Some participants initially only saw the C++ template. |
| 10 | How does the `.env` file work? | Create a `.env` file in the repo root with the OpenRouter API key. The template auto-loads it. | Need to copy from `.env.example` first. |
