# Security

NEVER:

- Hardcode secrets, API keys, passwords, or tokens in source code
- Use eval(), exec(), or similar dynamic code execution
- Commit .env files, credentials.json, or private keys
- Disable security checks or secret scanning

ALWAYS:

- Use environment variables for secrets (see .env.example for patterns)
- Validate user input at API boundaries
- Use parameterized queries (SQLAlchemy handles this)
