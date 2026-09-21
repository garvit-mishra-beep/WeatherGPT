#!/usr/bin/env python3
"""Showcase Scenario CLI Forwarder.

Delegates directly to canonical entrypoint: scripts/showcase/run_showcase.py
"""

import sys
import os

canonical_script = os.path.join(os.path.dirname(__file__), "showcase", "run_showcase.py")

if __name__ == "__main__":
    if os.path.exists(canonical_script):
        # Delegate execution with same python interpreter and arguments
        import runpy
        sys.argv[0] = canonical_script
        runpy.run_path(canonical_script, run_name="__main__")
    else:
        print(f"Error: Canonical showcase script not found at {canonical_script}", file=sys.stderr)
        sys.exit(1)
