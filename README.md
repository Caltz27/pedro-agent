# Pedro Agent

Week 2 agent harness for AI in Research.

## Status

OpenRouter plain-chat and tool-call checks passed with `cohere/north-mini-code:free`. The student completed the learning checkpoint and approved the local web interface. Live project-file listing, denial handling, and failed-command recovery passed, with cached tokens reported. Local approval/history, failed-command, and output-truncation tests passed. The broader home-directory scan awaits explicit consent to send that metadata to the API. Publication and the class submission pull request await approval; the install skill is prepared in the separate Week 2 submission checkout.

Keep the API key in `.env`; Git ignores this file.

## Run

Requires Python 3.10 or newer, with no third-party dependencies.

Copy `.env.example` to `.env` and enter your API key locally. Configure `BASE_URL`, `API_KEY`, and a tool-capable `MODEL`. Environment variables override `.env` values.

Run `uv run server.py` or `python server.py`, then open http://127.0.0.1:8765. On Pedro's Windows computer, first run `conda activate Calimero` in the same terminal. Stop the server with Ctrl+C.

The web server listens on `127.0.0.1` only. Each command requires approval; unanswered approvals expire after five minutes. Commands run in this repository's folder, through PowerShell on Windows or bash on macOS/Linux, with a 60-second timeout and the last 10,000 output characters. Each turn allows 20 tool rounds. Restarting the server clears the in-memory chat.

## Check

Run `python check_api.py` to verify text and tool calling without executing a tool. Run `python -m unittest test_agent` for local checks. In the web chat, ask “What files are in this folder?”, approve the command, and check its output and the final answer. Then deny a command and try a command that fails. Each API call displays input, cached input (when reported), and output token counts.

## Understand the code

`agent.py` holds the conversation loop and shell tool. `check_api.py` handles configuration and plain HTTP requests. `server.py` connects the loop to browser events and approvals. `system_prompt.md` is the editable system prompt.
