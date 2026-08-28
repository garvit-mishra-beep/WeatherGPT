# Contributing to WeatherGPT

Thank you for your interest in contributing to WeatherGPT.

## Core Architectural Invariants
All contributions must respect the following core architectural rules:
1. **The LLM is NOT the source of meteorological truth:** Weather observations, forecasts, alerts, and calculations must originate exclusively from deterministic tools via the `ToolGateway`.
2. **Alert Immutability:** Official IMD warning levels (Red, Orange, Yellow, Green) cannot be modified or downgraded.
3. **Language Numerical Invariance:** Scientific quantities ($33.2^\circ\text{C}$, $24.5\text{ mm}$) must remain invariant across all 5 supported Indian languages (English, Hindi, Bengali, Marathi, Gujarati).
4. **Strict Typing:** All data models must use Pydantic v2 schemas and Python 3.11+ type hints.
5. **No Secrets:** Never commit `.env` files, API keys, credentials, or private tokens.

## Development Setup
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd WeatherGPT
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure local environment variables in `.env` as required for your development setup.

## Pull Request Guidelines
- Ensure all code conforms to PEP 8 and includes strict type annotations.
- Provide descriptive pull request titles and descriptions linking to relevant documentation in `docs/`.
- Do not commit secrets, test suites, or temporary local configuration files.
