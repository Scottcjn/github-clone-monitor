# Contributing to GitHub Clone Monitor

Thanks for helping improve GitHub Clone Monitor. This repository is intentionally small: one Python script, a README, and project metadata. Keep changes focused and easy to review.

## Local Setup

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/<your-user>/github-clone-monitor.git
   cd github-clone-monitor
   ```

2. Create an optional virtual environment:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```

3. Install the runtime dependency:

   ```bash
   python3 -m pip install requests
   ```

4. Configure local environment variables. Never commit tokens or personal repository lists.

   ```bash
   export GITHUB_TOKEN=ghp_your_token
   export GITHUB_USERNAME=your-github-user
   ```

## Development Guidelines

- Keep compatibility with the standard Python 3 runtime available on common Linux systems.
- Prefer the standard library unless a dependency clearly improves reliability or security.
- Do not hard-code GitHub tokens, private repository names, or user-specific state paths.
- Keep the default repository list and alert text easy to customize.
- Use clear function names and small changes. This project should stay readable from top to bottom.

## Validation

Before opening a pull request, run:

```bash
python3 -m py_compile github_clone_monitor.py
python3 github_clone_monitor.py
```

If you test live GitHub traffic data, use your own token and repositories. Include a short note in the PR explaining whether validation was static only or used live API calls.

## Pull Request Checklist

- Describe what changed and why.
- Note any new environment variables, files, or dependencies.
- Confirm that no secrets, tokens, or private data are included.
- Include the validation commands you ran.
- Keep unrelated formatting or wording changes out of the same PR.

## Security Reports

If you find a vulnerability involving token handling, local state files, shell execution, or GitHub API usage, do not include secrets or exploit data in a public issue. Open a minimal public report or contact the maintainer with enough detail to reproduce safely.
