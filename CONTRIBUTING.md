# Contributing

Thanks for helping improve GitHub Clone Monitor. Contributions should keep the
project simple, auditable, and useful for repository owners who want visibility
into clone activity.

## Local Setup

Clone the repository:

```bash
git clone https://github.com/Scottcjn/github-clone-monitor.git
cd github-clone-monitor
```

Review the README before changing behavior so terminology stays consistent.

## Contribution Guidelines

- Keep monitoring behavior transparent and documented.
- Avoid collecting or exposing secrets, tokens, or private repository data.
- Prefer small changes that are easy to test manually.
- Update documentation when changing configuration or expected output.
- Keep examples generic and avoid including real credentials.

## Validation

For documentation-only changes:

```bash
git diff --check
```

For script or code changes, include the exact command you used to run the tool
and a short sample of the output in the pull request.

## Pull Request Checklist

- Summarize the change.
- Note any privacy or security impact.
- Include validation commands.
- Link the related issue or bounty, if applicable.
