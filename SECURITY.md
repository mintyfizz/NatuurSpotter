# Security Policy

## Supported Versions

The latest version on the default branch is the supported version.

## Reporting a Vulnerability

If you discover a security issue, report it privately to `thomasgatse@outlook.be`.
Please include:

- A clear description of the issue
- Steps to reproduce
- Potential impact

Do not open a public issue for sensitive vulnerabilities.

## Secret Management

- Never commit API keys or credentials to the repository.
- Use environment variables (`.env`) for local development.
- If a key is exposed, rotate it immediately at the provider.
