"""WeatherGPT Native Production Startup & Smoke Benchmark Tool.

Measures:
1. Application factory instantiation and cold start time.
2. Health (/api/v1/health) and Readiness (/api/v1/ready) latencies.
3. Representative API endpoint latencies (Weather, GIS, Map, Analytics).
4. Controlled smoke load test (100 requests) with average and p95 latency.
"""

import asyncio
import os
import sys
import time
from typing import List
import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import Settings
from app.core.factory import create_app


def run_benchmark():
    print("=====================================================================")
    print("WeatherGPT Native Production Startup & Latency Benchmark")
    print("=====================================================================")

    # 1. Measure Cold Start
    start_time = time.perf_counter()
    cfg = Settings(app_env="test")
    app = create_app(settings=cfg, configure_logging_enabled=False)
    client = TestClient(app)
    with client:
        startup_ms = (time.perf_counter() - start_time) * 1000.0
        print(f"[Cold Start] Application Construction & Startup: {startup_ms:.2f} ms")

        # 2. Measure Health Probe
        health_latencies: List[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            health_latencies.append((time.perf_counter() - t0) * 1000.0)
        print(f"[Liveness Probe]   /api/v1/health:  avg={np.mean(health_latencies):.2f} ms, p95={np.percentile(health_latencies, 95):.2f} ms")

        # 3. Measure Readiness Probe
        ready_latencies: List[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            resp = client.get("/api/v1/ready")
            assert resp.status_code in (200, 503)
            ready_latencies.append((time.perf_counter() - t0) * 1000.0)
        print(f"[Readiness Probe]  /api/v1/ready:   avg={np.mean(ready_latencies):.2f} ms, p95={np.percentile(ready_latencies, 95):.2f} ms")

        # 4. Controlled Smoke Load Test on Domain Endpoints
        endpoints = [
            ("GET", "/api/v1/weather/current?lat=21.17&lon=72.83", None),
            ("GET", "/api/v1/weather/forecast?lat=21.17&lon=72.83", None),
            ("GET", "/api/v1/weather/alerts?district_name=Surat", None),
            ("POST", "/api/v1/farmer/spray-window", {"wind_speed_kmh": 8.0, "rain_probability_pct": 10.0}),
            ("POST", "/api/v1/farmer/irrigation-advisory", {"latitude": 21.17, "longitude": 72.83, "crop_name": "Wheat"}),
        ]

        total_requests = 100
        latencies: List[float] = []
        success_count = 0
        failure_count = 0

        print(f"\n[Smoke Load Test] Executing {total_requests} sequential requests across domain endpoints...")
        for i in range(total_requests):
            method, path, body = endpoints[i % len(endpoints)]
            t0 = time.perf_counter()
            if method == "POST":
                resp = client.post(path, json=body)
            else:
                resp = client.get(path)
            lat = (time.perf_counter() - t0) * 1000.0
            latencies.append(lat)
            if resp.status_code == 200:
                success_count += 1
            else:
                failure_count += 1

        print("---------------------------------------------------------------------")
        print(f"Total Requests:     {total_requests}")
        print(f"Success Count:      {success_count} ({success_count/total_requests*100:.1f}%)")
        print(f"Failure Count:      {failure_count}")
        print(f"Average Latency:    {np.mean(latencies):.2f} ms")
        print(f"Median Latency:     {np.median(latencies):.2f} ms")
        print(f"P95 Latency:        {np.percentile(latencies, 95):.2f} ms")
        print(f"Min / Max Latency:  {np.min(latencies):.2f} ms / {np.max(latencies):.2f} ms")
        print("=====================================================================")


if __name__ == "__main__":
    run_benchmark()
