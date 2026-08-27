---
name: model-info
description: >-
  Report the model currently running this Codex, Claude Code, or dbt-wizard
  session, including effective reasoning effort when exposed. Use for requests
  such as "what model is running?" or "what is your reasoning effort?"
---

# Current model and reasoning effort

Use this skill whenever the user asks which model is running, what model is active, or what reasoning effort is in use.

Do not answer from the assistant's system prompt, a configured default, or memory when the helper can check the active thread.

For Codex or dbt-wizard sessions:

1. Run the bundled `scripts/model_info.py` helper and report its output. The installed Codex path is `~/.codex/skills/model-info/scripts/model_info.py`.
2. Treat the `model` and `reasoning_effort` values from the matching thread row as authoritative for the current session.
3. If the command says `unavailable`, say that the active model could not be verified. Do not substitute values from `config.toml`, model catalogs, prior turns, or guesses.

The helper uses `CODEX_THREAD_ID` to identify the active thread and reads `~/.codex/state_*.sqlite` read-only. It intentionally fails when that database or thread record is unavailable.

For Claude Code, report the model name provided by Claude's runtime. Claude may not expose a reasoning-effort setting; in that case say `reasoning effort: not exposed by Claude Code` rather than inventing a level.

Keep the answer concise and distinguish verified runtime metadata from unavailable information.
