# Contributing

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Before Opening a PR

- Run a quick syntax check:

```bash
python3 -m compileall src/natuurspotter
```

- If you changed behavior, update `README.md` examples or notes.
- Do not commit real API keys or generated files from `output/`.

## Coding Notes

- Keep function names and public API stable where possible.
- Prefer small, focused changes.
- Document new environment variables in `.env.example` and `README.md`.
