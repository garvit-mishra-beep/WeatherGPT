"""CLI Showcase Scenario Driver for VAYUBODHAK Video Demonstration.

Allows one-touch execution of showcase steps:
[1] START (Step 0: Nominal Baseline -> Revision 1)
[2] NEXT  (Step 1: Precipitation Escalation -> Selective Recalculation -> Revision 2)
[3] NEXT  (Step 2: Official Warning Escalation -> Revision 3 -> Priority Notification)
[4] NEXT  (Step 3: Ready for Offline / Reconnect Mobile Flow)
[0] RESET (Restore Clean Baseline)
"""

import sys
import os
import json

# Ensure project root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.showcase.runner import showcase_runner


def print_status(res: dict):
    print("\n" + "=" * 60)
    print(f"STATUS: {res.get('status')} | STEP: {res.get('step_index')} ({res.get('step_name', 'N/A')})")
    print("-" * 60)
    if "verdict" in res:
        print(f"-> Verdict: {res.get('verdict')} | Severity: {res.get('severity')}")
    if "revision_id" in res:
        print(f"-> DecisionRevision: {res.get('revision_id')} (rev={res.get('revision_number')})")
    if "event_id" in res:
        print(f"-> OperationalEvent: {res.get('event_id')} (seq={res.get('sequence_number')})")
    if "notification" in res and res.get("notification"):
        n = res["notification"]
        print(f"-> Emitted Notification [{n.get('priority')}]: {n.get('title')}")
    if "reused_stages" in res:
        print(f"-> Reused Stages: {res.get('reused_stages')}")
        print(f"-> Recomputed Stages: {res.get('recomputed_stages')}")
    print("=" * 60 + "\n")


def main():
    print("\n=== VAYUBODHAK SHOWCASE SCENARIO CONTROLLER ===")
    print("Controlled Input -> Real Pipeline -> Real Decision -> Real Sync\n")

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "start":
            res = showcase_runner.start_sync()
            print_status(res)
        elif cmd == "next":
            res = showcase_runner.next_sync()
            print_status(res)
        elif cmd == "reset":
            res = showcase_runner.reset_sync()
            print_status(res)
        elif cmd == "status":
            res = showcase_runner.get_status()
            print(json.dumps(res, indent=2))
        else:
            print(f"Unknown command: {cmd}. Use: start, next, reset, status")
        return

    # Interactive mode
    while True:
        status = showcase_runner.get_status()
        step = status.get("current_step_index")
        print(f"Current State: Step {step} | Latest Rev: {status.get('latest_revision_number')} | Events: {status.get('latest_sequence')}")
        print("1. START (Step 0 - Baseline Nominal)")
        print("2. NEXT  (Advance to next chronological step)")
        print("3. RESET (Clean repository state)")
        print("4. STATUS")
        print("5. QUIT")
        choice = input("\nSelect option [1-5]: ").strip()

        if choice == "1":
            res = showcase_runner.start_sync()
            print_status(res)
        elif choice == "2":
            res = showcase_runner.next_sync()
            print_status(res)
        elif choice == "3":
            res = showcase_runner.reset_sync()
            print_status(res)
        elif choice == "4":
            print(json.dumps(showcase_runner.get_status(), indent=2))
        elif choice in ("5", "q", "quit", "exit"):
            break
        else:
            print("Invalid selection.")


if __name__ == "__main__":
    main()
