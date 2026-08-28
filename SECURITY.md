# Security Policy

## Supported Versions
Security updates are actively maintained on the main branch.

## Reporting a Vulnerability
If you discover a potential security vulnerability in WeatherGPT, please report it responsibly by contacting the project maintainers privately rather than opening a public issue.

## Key Security Practices
- **Credential Protection:** Never commit `.env` files, API keys, database passwords, or private access tokens to source control.
- **Role Isolation:** User prompts and conversation history are isolated in user-role messages to prevent prompt injection and system override attacks.
- **Input Validation:** All input payloads and tool arguments are strictly validated against Pydantic v2 schemas and JSON parameter schemas.
- **Output Grounding:** All LLM outputs are checked against deterministic evidence packages to prevent fabrication of severe weather warnings.
