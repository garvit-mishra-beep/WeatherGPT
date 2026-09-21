@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Vayubodhak Demo Connection Launcher

:: ============================================================================
:: 1. OS & Environment Check
:: ============================================================================
if not "%OS%"=="Windows_NT" (
    echo [ERROR] This script requires a Windows NT environment.
    exit /b 1
)

:: Resolve script directory and project root robustly [supports paths with spaces]
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

:: Ensure logs directory exists
if not exist "%PROJECT_ROOT%\logs" mkdir "%PROJECT_ROOT%\logs"
set "LOG_FILE=%PROJECT_ROOT%\logs\vayubodhak_demo_startup.log"
set "BACKEND_LOG=%PROJECT_ROOT%\logs\vayubodhak_backend.log"
set "BRIDGE_LOG=%PROJECT_ROOT%\logs\vayubodhak_bridge.log"
set "BACKEND_PID_FILE=%PROJECT_ROOT%\logs\vayubodhak_backend.pid"
set "BRIDGE_PID_FILE=%PROJECT_ROOT%\logs\vayubodhak_bridge.pid"

:: Parse optional command line arguments
set "CHECK_ONLY=0"
set "STOP_ONLY=0"

if /i "%~1"=="--check-only" set "CHECK_ONLY=1"
if /i "%~1"=="-check-only" set "CHECK_ONLY=1"
if /i "%~1"=="--check" set "CHECK_ONLY=1"
if /i "%~1"=="--stop" set "STOP_ONLY=1"
if /i "%~1"=="-stop" set "STOP_ONLY=1"

:: ============================================================================
:: 2. STOP ROUTINE [--stop]
:: ============================================================================
if "!STOP_ONLY!"=="1" (
    echo.
    echo =====================================================================
    echo      VAYUBODHAK DEMO CONNECTION LAUNCHER - STOPPING SERVICES
    echo =====================================================================
    echo [%date% %time%] Stopping Vayubodhak demo services... >> "%LOG_FILE%"

    :: 2.1 Stop Backend on port 8000
    set "STOPPED_BACKEND=0"
    if exist "%BACKEND_PID_FILE%" (
        set /p BPID=<"%BACKEND_PID_FILE%"
        if defined BPID (
            tasklist /fi "PID eq !BPID!" 2>nul | findstr /i "python" >nul
            if !errorlevel! equ 0 (
                echo [*] Terminating recorded Backend PID !BPID!...
                taskkill /F /PID !BPID! >nul 2>nul
                set "STOPPED_BACKEND=1"
            )
        )
        del /f /q "%BACKEND_PID_FILE%" 2>nul
    )

    :: Fallback port check if recorded PID was not active
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
        set "PID=%%P"
        if not "!PID!"=="0" (
            tasklist /fi "PID eq !PID!" 2>nul | findstr /i "python" >nul
            if !errorlevel! equ 0 (
                echo [*] Stopping Python Backend PID !PID! on port 8000...
                taskkill /F /PID !PID! >nul 2>nul
                set "STOPPED_BACKEND=1"
            )
        )
    )
    if "!STOPPED_BACKEND!"=="1" (
        echo [OK] FastAPI Backend on port 8000 stopped.
        echo [%date% %time%] FastAPI Backend on port 8000 stopped. >> "%LOG_FILE%"
    ) else (
        echo [INFO] No active Python backend found on port 8000.
    )

    :: 2.2 Stop Ollama Bridge on port 11434
    set "STOPPED_BRIDGE=0"
    if exist "%BRIDGE_PID_FILE%" (
        set /p OPID=<"%BRIDGE_PID_FILE%"
        if defined OPID (
            tasklist /fi "PID eq !OPID!" 2>nul | findstr /i "python" >nul
            if !errorlevel! equ 0 (
                echo [*] Terminating recorded Ollama Bridge PID !OPID!...
                taskkill /F /PID !OPID! >nul 2>nul
                set "STOPPED_BRIDGE=1"
            )
        )
        del /f /q "%BRIDGE_PID_FILE%" 2>nul
    )

    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":11434 .*LISTENING"') do (
        set "PID=%%P"
        if not "!PID!"=="0" (
            tasklist /fi "PID eq !PID!" 2>nul | findstr /i "python" >nul
            if !errorlevel! equ 0 (
                echo [*] Stopping Python Ollama Bridge PID !PID! on port 11434...
                taskkill /F /PID !PID! >nul 2>nul
                set "STOPPED_BRIDGE=1"
            )
        )
    )
    if "!STOPPED_BRIDGE!"=="1" (
        echo [OK] Ollama TCP Bridge on port 11434 stopped.
        echo [%date% %time%] Ollama TCP Bridge on port 11434 stopped. >> "%LOG_FILE%"
    ) else (
        echo [INFO] No active Python Ollama bridge found on port 11434.
    )

    echo.
    echo [SUCCESS] Demo services shutdown complete.
    exit /b 0
)

:: ============================================================================
:: 3. Startup Banner & Information
:: ============================================================================
echo.
echo =====================================================================
echo           VAYUBODHAK [WEATHERGPT] - DEMO CONNECTION LAUNCHER         
echo                 SIH PHYSICAL DEMO NETWORK PREPARATION                
echo =====================================================================
echo [*] Project Root     : %PROJECT_ROOT%
echo [*] Launch Log       : %LOG_FILE%
echo [*] Target Gateway   : 192.168.137.1 [GarvitHotspot]
echo [*] Target LLM Host  : 169.254.88.2:11434 [UJJWAL]
if "!CHECK_ONLY!"=="1" echo [*] Mode             : CHECK-ONLY [Diagnostics without launching]
echo =====================================================================
echo.
echo [%date% %time%] Demo connection launcher started [CHECK_ONLY=!CHECK_ONLY!]. >> "%LOG_FILE%"

:: ============================================================================
:: 4. Network Adapter & IP Address Detection
:: ============================================================================
echo [*] Step 1/6: Detecting network adapters and IP configurations...

set "HOTSPOT_ACTIVE=0"
set "HOTSPOT_IP="
set "ETHERNET_IP="
set "ETHERNET_ADAPTER="

:: 4.1 Detect Hotspot Gateway 192.168.137.1 via PowerShell Get-NetIPAddress
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -eq '192.168.137.1' }).IPAddress" 2^>nul`) do (
    set "HOTSPOT_IP=%%A"
)

if "!HOTSPOT_IP!"=="192.168.137.1" (
    set "HOTSPOT_ACTIVE=1"
    echo [✓] Mobile Hotspot Gateway detected: 192.168.137.1
    echo [%date% %time%] Hotspot Gateway detected: 192.168.137.1 >> "%LOG_FILE%"
) else (
    echo [WARN] GarvitHotspot gateway 192.168.137.1 not detected!
    echo        Explanation : The Android phone connects to Laptop 1 via Windows Mobile Hotspot.
    echo        Required Fix: Open Windows Settings -^> Network ^& Internet -^> Mobile Hotspot -^> Turn ON.
    echo                      Set SSID to 'GarvitHotspot' and ensure the gateway is 192.168.137.1.
    echo [%date% %time%] WARNING: Hotspot gateway 192.168.137.1 not detected. >> "%LOG_FILE%"
)

:: 4.2 Detect Ethernet Adapter IP [direct link to Laptop 2 / UJJWAL]
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -like '*Ethernet*' -and $_.IPAddress -ne '127.0.0.1' }).IPAddress | Select-Object -First 1" 2^>nul`) do (
    set "ETHERNET_IP=%%A"
)

for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "(Get-NetAdapter | Where-Object { $_.InterfaceAlias -like '*Ethernet*' }).Name | Select-Object -First 1" 2^>nul`) do (
    set "ETHERNET_ADAPTER=%%A"
)

if defined ETHERNET_IP (
    echo [✓] Ethernet link detected on '!ETHERNET_ADAPTER!' : !ETHERNET_IP!
    echo [%date% %time%] Ethernet link detected on !ETHERNET_ADAPTER!: !ETHERNET_IP! >> "%LOG_FILE%"
) else (
    echo [WARN] No active IPv4 address found on Ethernet adapter.
    echo        Explanation : Direct LAN communication to Laptop 2 [UJJWAL] requires Ethernet.
    echo        Required Fix: Plug Ethernet cable between Laptop 1 and Laptop 2.
    echo [%date% %time%] WARNING: No active IPv4 address found on Ethernet adapter. >> "%LOG_FILE%"
)
echo.

:: ============================================================================
:: 5. Windows Firewall Verification & Configuration
:: ============================================================================
echo [*] Step 2/6: Verifying Windows Firewall rules for private demo network...

:: 5.1 Check TCP 8000 rule
set "RULE_8000_EXISTS=0"
for /f "usebackq tokens=*" %%R in (`powershell -NoProfile -Command "(Get-NetFirewallRule -DisplayName 'Vayubodhak_Backend_8000' -ErrorAction SilentlyContinue).DisplayName" 2^>nul`) do (
    if "%%R"=="Vayubodhak_Backend_8000" set "RULE_8000_EXISTS=1"
)

if "!RULE_8000_EXISTS!"=="1" (
    echo [✓] Inbound Firewall Rule 'Vayubodhak_Backend_8000' [TCP 8000] already exists.
    echo [%date% %time%] Firewall Rule Vayubodhak_Backend_8000 already exists. >> "%LOG_FILE%"
) else (
    echo [*] Creating scoped inbound Firewall rule for TCP port 8000 [Private profile]...
    netsh advfirewall firewall add rule name="Vayubodhak_Backend_8000" dir=in action=allow protocol=TCP localport=8000 profile=private,domain >nul 2>nul
    if !errorlevel! equ 0 (
        echo [✓] Created Firewall rule 'Vayubodhak_Backend_8000' [TCP 8000].
        echo [%date% %time%] Created Firewall rule Vayubodhak_Backend_8000 [TCP 8000]. >> "%LOG_FILE%"
    ) else (
        echo [INFO] Could not add firewall rule [requires Administrator privileges].
        echo        If external hotspot requests fail, run this script as Administrator once.
    )
)

:: 5.2 Check TCP 11434 rule
set "RULE_11434_EXISTS=0"
for /f "usebackq tokens=*" %%R in (`powershell -NoProfile -Command "(Get-NetFirewallRule -DisplayName 'Vayubodhak_Ollama_11434' -ErrorAction SilentlyContinue).DisplayName" 2^>nul`) do (
    if "%%R"=="Vayubodhak_Ollama_11434" set "RULE_11434_EXISTS=1"
)

if "!RULE_11434_EXISTS!"=="1" (
    echo [✓] Inbound Firewall Rule 'Vayubodhak_Ollama_11434' [TCP 11434] already exists.
    echo [%date% %time%] Firewall Rule Vayubodhak_Ollama_11434 already exists. >> "%LOG_FILE%"
) else (
    echo [*] Creating scoped inbound Firewall rule for TCP port 11434 [Private profile]...
    netsh advfirewall firewall add rule name="Vayubodhak_Ollama_11434" dir=in action=allow protocol=TCP localport=11434 profile=private,domain >nul 2>nul
    if !errorlevel! equ 0 (
        echo [✓] Created Firewall rule 'Vayubodhak_Ollama_11434' [TCP 11434].
        echo [%date% %time%] Created Firewall rule Vayubodhak_Ollama_11434 [TCP 11434]. >> "%LOG_FILE%"
    ) else (
        echo [INFO] Could not add firewall rule [requires Administrator privileges].
    )
)
echo.

:: ============================================================================
:: 6. Python Environment Resolution
:: ============================================================================
echo [*] Step 3/6: Resolving Python virtual environment...

set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
    echo [✓] Using project virtualenv: %PROJECT_ROOT%\.venv
) else if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%PROJECT_ROOT%\venv\Scripts\python.exe"
    echo [✓] Using project virtualenv: %PROJECT_ROOT%\venv
) else (
    where python.exe >nul 2>nul
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python.exe"
        echo [✓] Using system Python from PATH.
    ) else (
        echo [ERROR] No Python runtime found in .venv, venv, or system PATH!
        exit /b 1
    )
)
echo.

:: ============================================================================
:: 7. Backend & Bridge Service Management
:: ============================================================================
echo [*] Step 4/6: Checking service status [Backend :8000 and Ollama Bridge :11434]...

:: 7.1 Check if Backend port 8000 is listening
set "BACKEND_LISTENING=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
    set "BACKEND_LISTENING=1"
    set "BACKEND_PID=%%P"
)

if "!BACKEND_LISTENING!"=="1" (
    echo [✓] Backend is already listening on port 8000 [PID !BACKEND_PID!].
    echo [%date% %time%] Backend already running on port 8000 [PID !BACKEND_PID!]. >> "%LOG_FILE%"
) else (
    if "!CHECK_ONLY!"=="1" (
        echo [FAIL] Backend port 8000 is NOT listening.
    ) else (
        echo [*] Starting FastAPI Backend on 0.0.0.0:8000...
        echo [%date% %time%] Launching FastAPI backend... >> "%LOG_FILE%"
        pushd "%PROJECT_ROOT%"
        start "Vayubodhak_Backend" /b "%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "%BACKEND_LOG%" 2>&1
        popd

        :: Wait up to 25 seconds for port 8000 to listen
        set "WAIT_COUNT=0"
        :WAIT_BACKEND_LOOP
        ping 127.0.0.1 -n 2 >nul
        set /a WAIT_COUNT+=1
        for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8000 .*LISTENING"') do (
            set "BACKEND_LISTENING=1"
            set "BACKEND_PID=%%P"
            echo !BACKEND_PID! > "%BACKEND_PID_FILE%"
        )
        if "!BACKEND_LISTENING!"=="0" (
            if !WAIT_COUNT! lss 25 goto :WAIT_BACKEND_LOOP
        )

        if "!BACKEND_LISTENING!"=="1" (
            echo [✓] FastAPI Backend successfully started on 0.0.0.0:8000 [PID !BACKEND_PID!].
            echo [%date% %time%] FastAPI Backend successfully started on port 8000 [PID !BACKEND_PID!]. >> "%LOG_FILE%"
        ) else (
            echo [ERROR] Failed to start FastAPI Backend within 25 seconds. Check logs\vayubodhak_backend.log.
        )
    )
)

:: 7.2 Check if Ollama Bridge port 11434 is listening on Laptop 1
set "BRIDGE_LISTENING=0"
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":11434 .*LISTENING"') do (
    set "BRIDGE_LISTENING=1"
    set "BRIDGE_PID=%%P"
)

if "!BRIDGE_LISTENING!"=="1" (
    echo [✓] Ollama TCP Bridge is already listening on port 11434 [PID !BRIDGE_PID!].
    echo [%date% %time%] Ollama TCP Bridge already running on port 11434 [PID !BRIDGE_PID!]. >> "%LOG_FILE%"
) else (
    if "!CHECK_ONLY!"=="1" (
        echo [FAIL] Ollama TCP Bridge port 11434 is NOT listening.
    ) else (
        echo [*] Starting Ollama TCP Bridge [0.0.0.0:11434 -^> 169.254.88.2:11434]...
        echo [%date% %time%] Launching Ollama TCP bridge... >> "%LOG_FILE%"
        pushd "%PROJECT_ROOT%"
        start "Vayubodhak_Bridge" /b "%PYTHON_EXE%" "%PROJECT_ROOT%\scripts\ethernet_ollama_bridge.py" > "%BRIDGE_LOG%" 2>&1
        popd

        set "WAIT_BRIDGE_COUNT=0"
        :WAIT_BRIDGE_LOOP
        ping 127.0.0.1 -n 2 >nul
        set /a WAIT_BRIDGE_COUNT+=1
        for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":11434 .*LISTENING"') do (
            set "BRIDGE_LISTENING=1"
            set "BRIDGE_PID=%%P"
            echo !BRIDGE_PID! > "%BRIDGE_PID_FILE%"
        )
        if "!BRIDGE_LISTENING!"=="0" (
            if !WAIT_BRIDGE_COUNT! lss 8 goto :WAIT_BRIDGE_LOOP
        )

        if "!BRIDGE_LISTENING!"=="1" (
            echo [✓] Ollama TCP Bridge successfully started on port 11434 [PID !BRIDGE_PID!].
            echo [%date% %time%] Ollama TCP Bridge started on port 11434 [PID !BRIDGE_PID!]. >> "%LOG_FILE%"
        ) else (
            echo [ERROR] Failed to start Ollama TCP Bridge on port 11434.
        )
    )
)
echo.

:: ============================================================================
:: 8. Connectivity & Service Health Probes
:: ============================================================================
echo [*] Step 5/6: Probing network endpoints and model availability...

:: 8.1 Probe Laptop 1 -> Laptop 2 [UJJWAL:11434 via direct Ethernet]
set "UJJWAL_REACHABLE=0"
"%PYTHON_EXE%" -c "import sys, socket; s=socket.socket(); s.settimeout(2.5); s.connect(('169.254.88.2', 11434)); sys.exit(0)" >nul 2>nul && (
    set "UJJWAL_REACHABLE=1"
    echo [✓] Direct Ethernet connection to Laptop 2 [169.254.88.2:11434] is ACTIVE.
    echo [%date% %time%] UJJWAL 169.254.88.2:11434 reachable. >> "%LOG_FILE%"
) || (
    set "UJJWAL_REACHABLE=0"
    echo [WARN] Cannot reach Laptop 2 [UJJWAL] at 169.254.88.2:11434.
    echo [%date% %time%] WARNING: UJJWAL 169.254.88.2:11434 unreachable. >> "%LOG_FILE%"
)

:: 8.2 Probe Local Ollama Bridge [127.0.0.1:11434]
set "LOCAL_BRIDGE_REACHABLE=0"
"%PYTHON_EXE%" -c "import sys, socket; s=socket.socket(); s.settimeout(2.0); s.connect(('127.0.0.1', 11434)); sys.exit(0)" >nul 2>nul && (
    set "LOCAL_BRIDGE_REACHABLE=1"
) || (
    set "LOCAL_BRIDGE_REACHABLE=0"
)

:: 8.3 Probe Local Backend [127.0.0.1:8000/api/v1/health]
set "BACKEND_HEALTH_OK=0"
for /f "usebackq delims=" %%C in (`curl.exe -s -m 3 -o NUL -w "%%{http_code}" http://127.0.0.1:8000/api/v1/health 2^>nul`) do (
    if "%%C"=="200" set "BACKEND_HEALTH_OK=1"
)

:: 8.4 Probe Hotspot Backend Endpoint [192.168.137.1:8000]
set "HOTSPOT_BACKEND_OK=0"
for /f "usebackq delims=" %%C in (`curl.exe -s -m 3 -o NUL -w "%%{http_code}" http://192.168.137.1:8000/api/v1/health 2^>nul`) do (
    if "%%C"=="200" set "HOTSPOT_BACKEND_OK=1"
)

:: 8.5 Probe Hotspot Ollama Bridge Endpoint [192.168.137.1:11434/api/tags]
set "HOTSPOT_OLLAMA_OK=0"
set "HAS_GEMMA_MODEL=0"
if "!UJJWAL_REACHABLE!"=="1" (
    for /f "usebackq delims=" %%C in (`curl.exe -s -m 3 -o NUL -w "%%{http_code}" http://192.168.137.1:11434/api/tags 2^>nul`) do (
        if "%%C"=="200" set "HOTSPOT_OLLAMA_OK=1"
    )
    "%PYTHON_EXE%" -c "import sys, urllib.request, json; data=json.loads(urllib.request.urlopen('http://192.168.137.1:11434/api/tags', timeout=3).read()); sys.exit(0 if any('gemma4:e2b' in m.get('name','') for m in data.get('models',[])) else 1)" >nul 2>nul && (
        set "HAS_GEMMA_MODEL=1"
    ) || (
        set "HAS_GEMMA_MODEL=0"
    )
)

echo [*] Target Android endpoints:
echo       Backend : http://192.168.137.1:8000
echo       Ollama  : http://192.168.137.1:11434
echo.

:: ============================================================================
:: 9. Connection Matrix Evaluation
:: ============================================================================
echo =====================================================================
echo                      CONNECTION MATRIX EVALUATION                    
echo =====================================================================

if "!HOTSPOT_ACTIVE!"=="1" (
    echo [PASS] GarvitHotspot
    echo [PASS] Laptop 1 gateway 192.168.137.1
) else (
    echo [FAIL] GarvitHotspot
    echo [FAIL] Laptop 1 gateway 192.168.137.1
)

if "!BACKEND_HEALTH_OK!"=="1" (
    echo [PASS] Laptop 1 backend :8000
) else (
    echo [FAIL] Laptop 1 backend :8000
)

if "!LOCAL_BRIDGE_REACHABLE!"=="1" (
    echo [PASS] Laptop 1 Ollama bridge :11434
) else (
    echo [FAIL] Laptop 1 Ollama bridge :11434
)

if "!UJJWAL_REACHABLE!"=="1" (
    echo [PASS] Ethernet → UJJWAL
    echo [PASS] UJJWAL Ollama :11434
) else (
    echo [FAIL] Ethernet → UJJWAL
    echo [FAIL] UJJWAL Ollama :11434
)

if "!HAS_GEMMA_MODEL!"=="1" (
    echo [PASS] gemma4:e2b
) else (
    echo [FAIL] gemma4:e2b
)

if "!HOTSPOT_BACKEND_OK!"=="1" (
    echo [PASS] Android backend endpoint
) else (
    echo [FAIL] Android backend endpoint
)

if "!HOTSPOT_OLLAMA_OK!"=="1" (
    echo [PASS] Android Ollama endpoint
) else (
    echo [FAIL] Android Ollama endpoint
)
echo =====================================================================
echo.

:: ============================================================================
:: 10. Failure Diagnosis & Exact Fixes [if any component failed]
:: ============================================================================
set "HAS_FAILURES=0"

if "!HOTSPOT_ACTIVE!"=="0" (
    set "HAS_FAILURES=1"
    echo [DIAGNOSIS: HOTSPOT GATEWAY]
    echo   WHAT FAILED : Windows Mobile Hotspot is not broadcasting on 192.168.137.1.
    echo   WHY IT MATTERS: The phone cannot reach the backend or Ollama bridge over Wi-Fi.
    echo   EXACT FIX   : 1. Open Windows Settings -^> Network ^& Internet -^> Mobile Hotspot.
    echo                 2. Turn Mobile Hotspot ON.
    echo                 3. Confirm Network name is 'GarvitHotspot'.
    echo.
)

if "!BACKEND_HEALTH_OK!"=="0" (
    set "HAS_FAILURES=1"
    echo [DIAGNOSIS: BACKEND SERVICE]
    echo   WHAT FAILED : FastAPI Backend on port 8000 failed health probe [/api/v1/health].
    echo   WHY IT MATTERS: Android app cannot reach backend APIs or sync intelligence.
    echo   EXACT FIX   : 1. Check logs\vayubodhak_backend.log for Python exceptions.
    echo                 2. Verify PostgreSQL / PostGIS database is running.
    echo                 3. Run: %PYTHON_EXE% -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    echo.
)

if "!UJJWAL_REACHABLE!"=="0" (
    set "HAS_FAILURES=1"
    echo [DIAGNOSIS: UJJWAL / OLLAMA CONNECTIVITY]
    echo   WHAT FAILED : Direct Ethernet connection to Laptop 2 [169.254.88.2:11434] refused or timed out.
    echo   WHY IT MATTERS: Android phone cannot perform Gemma LLM explanations across LAN.
    echo   EXACT FIX   : 1. Confirm Ethernet cable is plugged securely into both laptops.
    echo                 2. On Laptop 2 [UJJWAL], ensure Ollama is listening on all interfaces:
    echo                      set OLLAMA_HOST=0.0.0.0:11434
    echo                      ollama serve
    echo                 3. Allow port 11434 inbound through Windows Firewall on Laptop 2:
    echo                      netsh advfirewall firewall add rule name="Ollama 11434" dir=in action=allow protocol=TCP localport=11434
    echo.
)

if "!HAS_GEMMA_MODEL!"=="0" (
    set "HAS_FAILURES=1"
    echo [DIAGNOSIS: GEMMA MODEL]
    echo   WHAT FAILED : Model 'gemma4:e2b' was not found in Ollama /api/tags response.
    echo   WHY IT MATTERS: Chat queries will fall back to deterministic local synthesis.
    echo   EXACT FIX   : On Laptop 2 [UJJWAL], pull the required model:
    echo                   ollama pull gemma4:e2b
    echo.
)

:: ============================================================================
:: 11. Final Demo Network Ready Banner
:: ============================================================================
if "!HAS_FAILURES!"=="0" (
    echo ================================================
    echo VAYUBODHAK DEMO NETWORK READY
    echo ================================================
    echo.
    echo Phone:
    echo    Connect Wi-Fi → GarvitHotspot
    echo.
    echo Backend:
    echo    http://192.168.137.1:8000
    echo.
    echo Ollama:
    echo    http://192.168.137.1:11434
    echo.
    echo Model:
    echo    gemma4:e2b
    echo.
    echo USB:
    echo    NOT REQUIRED FOR RUNTIME
    echo.
    echo After this point the phone can be unplugged from USB.
    echo Keep Laptop 1 hotspot ON.
    echo Keep Laptop 1 and UJJWAL connected by Ethernet.
    echo Keep this terminal window running.
    echo ================================================
    echo.
    echo [%date% %time%] VAYUBODHAK DEMO NETWORK READY: ALL CHECKS PASSED. >> "%LOG_FILE%"
    exit /b 0
) else (
    echo =====================================================================
    echo [WARN] VAYUBODHAK DEMO NETWORK HAS WARNINGS OR FAILURES [See above].
    echo =====================================================================
    echo [%date% %time%] Demo connection launcher finished with failures. >> "%LOG_FILE%"
    exit /b 1
)
