# Global Development Agent Context

## Environment
* OS: Linux (Mint-Cinnamon)
* Shell: bash
* Terminal: herdr
* Python: uv-managed virtual environments; conda/miniforge not used
* Rust: rustup toolchain; cargo for package management

## Python Package Management
Bare pip, pip3, and python3 invocations are blocked by a PreToolUse hook. Always use:

* `uv run <--with package_I_likely_wont_use_again> python3 -c "..."` — inline Python
* `uv run script.py` — run a script
* `uv add <package>` — add a dependency to a project. You're allowed to add dependencies if you think it truly is the best way to solve a problem.
* `uvx <tool>` — run a one-off tool (e.g. `uvx ruff check`)

## General Ethos

### 1. Boil the Lake
AI-assisted coding makes the marginal cost of completeness near-zero. When the complete implementation costs minutes more than the shortcut — do the complete thing. Every time.

Lake vs. ocean: A "lake" is boilable — 100% test coverage for a module, full feature implementation, all edge cases, complete error paths. An "ocean" is not — rewriting an entire system from scratch, multi-quarter platform migrations. Boil lakes. Flag oceans as out of scope.

Completeness is cheap. When evaluating "approach A (full, ~150 LOC) vs approach B (90%, ~80 LOC)" — always prefer A. The 70-line delta costs seconds with AI coding. "Ship the shortcut" is legacy thinking from when human engineering time was the bottleneck.

Anti-patterns:

"Choose B — it covers 90% with less code." (If A is 70 lines more, choose A.)
"Let's defer tests to a follow-up PR." (Tests are the cheapest lake to boil.)
"This would take 2 weeks." (Say: "2 weeks human / ~1 hour AI-assisted.")
Read more: https://garryslist.org/posts/boil-the-ocean