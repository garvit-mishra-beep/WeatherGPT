# Contributing to WeatherGPT

Thank you for your interest in contributing to **WeatherGPT**! We welcome contributions from developers, researchers, meteorologists, and data scientists to help build a domain-grounded weather decision-intelligence platform for India.

---

## 1. Core Architectural Invariants

Before writing code, please review our core architectural rules. All contributions must uphold these standards:

1. **The LLM is NOT the Source of Meteorological Truth:** All weather observations, forecasts, alerts, and calculations must originate exclusively from deterministic tools via the `ToolGateway`. The LLM is strictly an NLP, reasoning orchestration, and synthesis layer.
2. **Alert Immutability:** Official IMD warning levels (`Red`, `Orange`, `Yellow`, `Green`) are legally authoritative and cannot be modified, invented, or downgraded.
3. **Language Numerical Invariance:** Scientific measurements ($33.2^\circ\text{C}$, $24.5\text{ mm}$) and warning levels must remain identical across all supported Indian languages (English, Hindi, Bengali, Marathi, Gujarati).
4. **Strict Type Annotations:** All data models must use Pydantic v2 schemas and Python 3.11+ type hints. Untyped dictionaries must not cross component boundaries.
5. **Zero Credentials in Git:** Never commit `.env` files, API keys, passwords, private tokens, or cloud credentials.

---

## 2. Development Setup

### Prerequisites
- Python 3.11+
- Git

### Initial Setup
1. **Clone the Repository:**
   ```bash
   git clone <repository_url>
   cd WeatherGPT
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv .venv
   
   # Linux / macOS:
   source .venv/bin/activate
   
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Local Environment:**
   Create a local `.env` file in the project root:
   ```ini
   LLM_PROVIDER_TYPE=openai_compatible
   LLM_BASE_URL=http://127.0.0.1:8001/v1
   LLM_MODEL_NAME=Qwen/Qwen2.5-14B-Instruct
   LLM_API_KEY=not_required_for_local_vllm
   LLM_TEMPERATURE=0.1
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weathergpt
   REDIS_URL=redis://localhost:6379/0
   ```

---

## 3. Contribution Workflow

```text
Fork / Clone ──> Feature Branch ──> Implement ──> Local Test ──> Commit ──> Pull Request
```

### Step 1: Create a Feature Branch
Use descriptive branch names with a relevant prefix:
```bash
# Features:
git checkout -b feat/farmer-spray-window

# Bug fixes:
git checkout -b fix/indic-numeral-edgecase

# Documentation:
git checkout -b docs/update-api-contract
```

### Step 2: Implement Changes
- Follow existing directory conventions under `app/`.
- Ensure new features adhere to specifications in `docs/`.
- If modifying domain tools, update the permissions matrix in [`docs/05_TOOL_REGISTRY.md`](docs/05_TOOL_REGISTRY.md).

### Step 3: Run Local Tests
Verify that all changes pass existing automated test suites:
```bash
python -m pytest -v tests/
```

### Step 4: Commit Changes
Write clear, conventional commit messages:
```bash
git add app/
git commit -m "feat(farmer): implement spray suitability window evaluation"
```

*Common Commit Prefixes:*
- `feat:` A new feature or capability
- `fix:` A bug fix
- `docs:` Documentation only changes
- `refactor:` Code refactoring without behavior change
- `perf:` Performance improvements
- `chore:` Tooling, configuration, or repository maintenance

### Step 5: Submit a Pull Request
1. Push your feature branch to your fork.
2. Open a Pull Request against the `master` branch.
3. Describe the change, the problem it solves, and link to relevant documentation in `docs/`.

---

## 4. Coding Standards

- **PEP 8 & Formatting:** Follow standard Python style guidelines.
- **Async First:** All I/O operations (LLM calls, tool executions, HTTP requests, database queries) must be asynchronous using `async`/`await`.
- **Error Handling:** Return structured RFC 7807 problem details (`ProblemDetailRFC7807`) for API-level errors; never leak raw stack traces or internal configuration.
- **Grounding Integration:** Any new reasoning flow must validate candidate outputs through `GroundingService` before returning responses to the user.

---

## 5. Pull Request Checklist

Before submitting your PR, verify:
- [ ] Code follows project architecture invariants.
- [ ] All functions, classes, and models include type hints.
- [ ] No `.env`, credentials, or private keys are staged.
- [ ] Documentation updated if schemas, endpoints, or contracts changed.
- [ ] PR title is descriptive and follows conventional commit formats.
