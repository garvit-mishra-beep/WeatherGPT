# VAYUBODHAK — LOCAL DEVELOPMENT & ENVIRONMENT SETUP

**Document**: Developer Onboarding & Local Environment Setup Guide  
**Applies to**: Backend (Python 3.12+), Android Client (Kotlin / Compose), and Showcase Runner  

---

## 1. Prerequisites

### Backend Prerequisites
* **Python**: Version 3.11 or 3.12+
* **Virtual Environment**: `venv` or `virtualenv`
* **Optional Services**:
  * PostgreSQL 15+ with PostGIS (for persistent GIS boundary storage, SQLite/In-memory fallback available)
  * Local Ollama with `gemma2:2b` (for conversational chat, fallback to template synthesis available)

### Android Prerequisites
* **Android Studio**: Ladybug / Hedgehog or newer
* **JDK**: OpenJDK 17 or 21
* **Android SDK**: API Level 34 (Android 14) or API Level 35 (Android 15)
* **Gradle**: 8.9+ (Managed via `gradlew`)

---

## 2. Python Backend Setup

### Step 1: Clone Repository & Create Virtual Environment
```bash
git clone https://github.com/your-org/vayubodhak.git
cd vayubodhak

# Create and activate virtual environment
python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
# Copy example configuration template
cp .env.example .env
```
Edit `.env` to configure your parameters (defaults work out-of-the-box for in-memory / local staging mode).

### Step 4: Run Backend Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API documentation available at: `http://localhost:8000/docs`

---

## 3. Android Application Setup

### Step 1: Open Project in Android Studio
Open the `android/` directory in Android Studio.

### Step 2: Build Debug APK
```bash
# On Linux / macOS:
./android/gradlew -p android assembleDebug

# On Windows:
.\android\gradlew.bat -p android assembleDebug
```
Output APK generated at: `android/app/build/outputs/apk/debug/app-debug.apk`

### Step 3: Run Unit Tests
```bash
.\android\gradlew.bat -p android testDebugUnitTest
```

---

## 4. Running the Showcase Demonstration Scenario

VAYUBODHAK includes a built-in deterministic showcase scenario for video recording and evaluations:

```bash
# 1. Reset state to baseline
python scripts/showcase/run_showcase.py reset

# 2. Step 0: Ingest baseline nominal weather (3.0mm rain -> Revision 1)
python scripts/showcase/run_showcase.py start

# 3. Step 1: Convective rain escalation (88.5mm rain -> Revision 2)
python scripts/showcase/run_showcase.py next

# 4. Step 2: Statutory alert escalation (Red Alert -> Revision 3)
python scripts/showcase/run_showcase.py next

# 5. Step 3: Disconnect mobile device (Offline resilience demonstration)
python scripts/showcase/run_showcase.py next

# 6. Step 4: Reconnect mobile device (Incremental recovery & sync)
python scripts/showcase/run_showcase.py next
```

---

## 5. Running Test Suites

### Complete Backend Pytest Suite
```bash
pytest tests/ -q
```

### Dedicated Showcase Test Suite
```bash
pytest tests/test_showcase_scenario.py -v
```

### Android Showcase End-to-End Suite
```bash
.\android\gradlew.bat -p android testDebugUnitTest --tests "com.weathergpt.data.sync.ShowcaseAndroidE2ETest"
```
