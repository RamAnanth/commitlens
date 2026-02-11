# CommitLens

AI-powered terminal tool that critiques commit message quality and helps you write clear, high-signal commits from your shell.

CommitLens analyzes Git history, scores message quality, and suggests well-structured Conventional Commit messages from staged changes.

---

## ✨ Why this exists

Commit messages are often:

- vague (`fixed bug`)
- noisy (`wip`)
- missing context
- inconsistent across teams

CommitLens turns commit history into actionable feedback and helps teams write clearer commits consistently.

---

## 🧠 Features

### Analysis mode

- Analyze the last `N` commits from local repositories
- Optionally analyze public remote repositories via `--url`
- AI critique + score (0-10)
- Suggestions for weak commits
- Stats dashboard (average score, vague %, one-word %)

### Interactive mode

- Reads `git diff --staged`
- Summarizes staged changes
- Suggests a Conventional Commit message
- You always review/edit manually (tool never runs `git commit`)

### Engineering quality

- Structured LLM output validation with Pydantic
- Rich terminal UX with progress and panels
- Diff filtering for lockfiles/binary assets
- Large diff truncation for prompt safety
- Lightweight eval harness for scoring behavior
- Minimal test suite for parsing/scoring/git-validation logic

---

## 🛠 Tech stack

- Python 3.11+
- OpenAI API
- Pydantic
- Rich
- Typer
- python-dotenv
- uv

---

## ⚡ Quick start

```bash
git clone <your-repo-url>
cd commitlens
cp .env.example .env
# add OPENAI_API_KEY to .env
uv sync
uv run python commit_critic.py --analyze --limit 10
```

---

## 🚀 Installation

### With uv (recommended)

```bash
uv sync
```

### Without uv

```bash
python -m venv .venv && source .venv/bin/activate && pip install .
```

Create `.env`:

```env
OPENAI_API_KEY=your_key_here
```

---

## 📦 Usage

```bash
# Analyze last 50 commits (local repo)
uv run python commit_critic.py --analyze

# Analyze last 50 commits from a remote public repo
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

### Help

```bash
uv run python commit_critic.py --help
```

---

## 📊 Example output

### Analyze mode (real sample)

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💩 COMMITS THAT NEED WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

No weak commits found.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💎 WELL-WRITTEN COMMITS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Commit: "chore: add MIT license and update README with license link                                                  │
│                                                                                                                      │
│   - Added a new LICENSE file containing the full MIT License text                                                    │
│   - Updated README.md to replace placeholder license text with a link to the LICENSE file"                           │
│ Score: 8/10                                                                                                          │
│ Why it's good: The message clearly states what was done and uses the correct type. The detailed bullet points help   │
│ understand the changes but could be shortened for brevity.                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 YOUR STATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────┬──────────┐
│ Average score    │ 7.5/10   │
│ Vague commits    │ 0 (0.0%) │
│ One-word commits │ 0 (0.0%) │
└──────────────────┴──────────┘
```

### Interactive mode

```text
Analyzing staged changes... (2 files changed, +22 -1 lines)
╭─────────────────────────────────────────────────────────────────────────────────────────╮
│ SUMMARY:                                                                                │
│ - Add MIT License file with full text                                                   │
│ - Update README to link to the new LICENSE file                                         │
│                                                                                         │
│ SUBJECT:                                                                                │
│ chore: add MIT license and update README with license link                              │
│                                                                                         │
│ BODY:                                                                                   │
│ - Added a new LICENSE file containing the full MIT License text                         │
│ - Updated README.md to replace placeholder license text with a link to the LICENSE file │
╰─────────────────────────────────────────────────────────────────────────────────────────╯

Changes detected:
- Add MIT License file with full text
- Update README to link to the new LICENSE file

Suggested commit message:
╭─────────────────────────────────────────────────────────────────────────────────────────╮
│ chore: add MIT license and update README with license link                              │
│                                                                                         │
│ - Added a new LICENSE file containing the full MIT License text                         │
│ - Updated README.md to replace placeholder license text with a link to the LICENSE file │
╰─────────────────────────────────────────────────────────────────────────────────────────╯
Press Enter to accept, or type your own message ():
```

---

## 🧪 Evaluation

Run eval suite:

```bash
uv run python evals/run_eval.py
```

Eval report includes:

- bucket accuracy (`needs_work`/`mid`/`well_written`)
- score tolerance metric (±1) for LLM variance

---

## ✅ Tests

Run tests:

```bash
python -m unittest discover -s tests -v
```

---

## 🧱 Architecture

```text
git commits/diff
    -> prompt construction
    -> OpenAI LLM call
    -> Pydantic validation
    -> scoring + stats
    -> Rich terminal rendering
```

Key modules:

- `commit_critic/app.py`: CLI entry and mode orchestration
- `commit_critic/git_ops.py`: git cloning/log/diff utilities
- `commit_critic/llm_client.py`: LLM prompts, API calls, parsing, validation
- `commit_critic/scoring.py`: thresholds and statistics
- `commit_critic/ui.py`: rich output rendering
- `evals/run_eval.py`: lightweight scoring evaluation harness

---

## ⚙️ Options

- `--limit`: number of commits to analyze (default: 50)
- `--model`: OpenAI model to use (default: `gpt-4.1-mini`)
- `--url`: analyze a remote repository
- `--analyze`: analyze commit history mode
- `--write`: interactive commit writer mode

---

## 🎯 Current scope

- OpenAI models are supported
- Remote `--url` analysis supports public Git repositories

---

## 🔮 Future work

- Multi-provider support (Anthropic/Gemini)
- Local model support
- Optional caching for repeated analyses

---

## 📂 Project structure

```text
.
├── commit_critic/          # Core package logic
│   ├── app.py              # Typer CLI mode orchestration (--analyze / --write)
│   ├── config.py           # .env loading and API key validation
│   ├── git_ops.py          # Git operations (clone/log/diff/repo checks)
│   ├── llm_client.py       # LLM prompts, API calls, response parsing
│   ├── models.py           # Pydantic schemas for critiques/suggestions
│   ├── scoring.py          # Commit bucket logic and aggregate stats
│   ├── ui.py               # Rich terminal rendering
│   └── diff_cleaner.py     # Diff filtering/truncation for prompt safety
├── tests/                  # Unit tests (logic and mocked integrations)
├── evals/                  # LLM scoring evaluation harness
├── commit_critic.py        # CLI entry point
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Reproducible dependency lockfile
├── .env.example            # Environment variable template
├── README.md               # Documentation
└── LICENSE                 # MIT license
```

---

## License

[MIT License](LICENSE)
