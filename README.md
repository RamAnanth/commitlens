# CommitLens

AI-powered terminal tool that analyzes commit message quality and helps you write better commits.

## Features

- Analyze the last N commits in any Git repo (local or remote).
- Interactive mode that suggests a conventional commit message from staged changes.
- LLM output validation with Pydantic.
- Clean terminal UI with Rich.
- Safe by design: never runs `git commit` on your behalf.


## Prerequisites

- Python 3.11+
- Git
- `OPENAI_API_KEY` set in `./.env` or environment

## Dependencies

- `openai`: LLM access (OpenAI only)
- `pydantic`: schema validation for AI output
- `rich`: terminal UI
- `typer`: CLI parsing
- `python-dotenv`: `.env` loading

## Install

```bash
uv sync
```

### Install without uv

If you prefer not to use uv:

```bash
python -m venv .venv && source .venv/bin/activate && pip install .
```

Create `./.env`:

```env
OPENAI_API_KEY=your_key_here
```

## Usage

```bash
# Analyze last 50 commits
uv run python commit_critic.py --analyze

# Analyze last 50 commits of remote repo
uv run python commit_critic.py --analyze --url="https://github.com/steel-dev/steel-browser"

# Interactive commit writer
uv run python commit_critic.py --write
```

### Run without uv

```bash
source .venv/bin/activate
python commit_critic.py --analyze
python commit_critic.py --analyze --url="https://github.com/steel-dev/steel-browser"
python commit_critic.py --write
```

## Eval

Run the lightweight eval suite against sample commits:

```bash
uv run python evals/run_eval.py
```

## Tests

Run the minimal test suite:

```bash
python -m unittest discover -s tests -v
```

### Options

- `--limit`: number of commits to analyze (default: 50)
- `--model`: OpenAI model (default: `gpt-4.1-mini`)
- `--url`: analyze a remote repository

### Help

```bash
uv run python commit_critic.py --help
```

## Output

### Analysis mode

- **Commits that need work**: score `< 5`, includes Issue + Better message (top 5 shown)
- **Well-written commits**: score `>= 8`, shows only “Why it’s good” (top 5 shown)
- **Stats**: average score + vague and one-word counts with percentages


### Interactive mode

- Summarizes staged changes and proposes a commit message.
- Prompts you to accept or override.
- The suggested message is generated live in the terminal.

## How scoring works

The LLM is guided to score commits on a 1–10 scale based on Conventional Commits clarity and specificity.

Bucket thresholds (used in analysis and evals):

- `needs_work`: 0–4
- `mid`: 5–7
- `well_written`: 8–10

## Diff filtering

Lockfiles and binary assets are excluded from the diff context. Large diffs are truncated with a clear marker.

## Troubleshooting

- **“Please set OPENAI_API_KEY…”**: add the key to `./.env` or your shell environment.
- **“Please run inside a git repository…”**: run the command in a repo or use `--url`.
- **Remote repo access issues**: private repos require credentials; use a token or SSH key.

## Design choices

- **Pydantic**: guarantees structured LLM output before stats and UI rendering.
- **Rich**: readable sections and commit panels in the terminal.
- **uv**: fast, reproducible installs.

## Current scope
- OpenAI models are supported.
- Remote `--url` analysis supports public Git repositories.

## Future work

- Add multi-provider support via a small adapter layer (OpenAI/Anthropic/Gemini).

## Project layout

Flat layout for simplicity:

```
commit_critic.py
commit_critic/
```

## License

License to be added.
