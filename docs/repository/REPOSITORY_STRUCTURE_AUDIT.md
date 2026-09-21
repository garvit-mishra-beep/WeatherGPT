# VAYUBODHAK — REPOSITORY STRUCTURE AUDIT

**Milestone**: Git-Ready Repository Organization  
**Date**: September 21, 2026  
**Auditor**: Antigravity System Architect  

---

## 1. Executive Summary

This audit catalogs every top-level directory, code module, documentation file, test suite, data fixture, script, and configuration element in the VAYUBODHAK repository. The goal is to rationalize the structure, eliminate machine-specific artifacts, consolidate scattered phase reports, ensure zero broken imports/references, and prepare the repository for production Git publication.

---

## 2. Directory-by-Directory Audit & Action Matrix

| Current Path | Purpose / Description | Identified Issue / Risk | Proposed Final Path | Action | Risk Level |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `PHASE_9C_CLOSURE_CORRECTION_REPORT.md` | Phase 9C verification closure audit | Scattered at root; clutters repo entry | `docs/phases/phase-09c/PHASE_9C_CLOSURE_CORRECTION_REPORT.md` | MOVE | LOW |
| `VIDEO_READY_PRODUCT_COMPLETION.md` | Video-ready showcase completion report | Scattered at root | `docs/showcase/VIDEO_READY_PRODUCT_COMPLETION.md` | MOVE | LOW |
| `all_md_files.txt` | Temporary developer file list | Temporary scratch file | N/A | REMOVE | LOW |
| `artifacts_screen_*.png` (4 files) | UI screenshots captured during validation | Located at root | `docs/images/showcase/` | MOVE | LOW |
| `scratch/` | Agent/scratch execution directory | Uncommitted scratch scripts | Ignored by `.gitignore` | KEEP/IGNORE | LOW |
| `logs/` | Runtime logs | Runtime output | Ignored by `.gitignore` | KEEP/IGNORE | LOW |
| `app/` | Core Python backend application | Canonical backend modules | `app/` | KEEP | LOW (DO NOT BREAK) |
| `app/api/v1/showcase.py` | Internal showcase REST API controller | Must remain protected/internal | `app/api/v1/showcase.py` | KEEP | LOW |
| `app/showcase/` | Showcase scenario runner engine | Deterministic demonstration engine | `app/showcase/` | KEEP | LOW |
| `data/showcase/` (6 JSON files) | Controlled scenario fixtures for Gwalior | High-value deterministic inputs | `data/showcase/` | KEEP | LOW |
| `data/reference/` | Static reference spatial and lookup data | Recommended by target structure | `data/reference/` | NEW | LOW |
| `data/schemas/` | Static JSON event and evidence schemas | Recommended for schema validation | `data/schemas/` | NEW | LOW |
| `docs/*.md` (159 files) | Flat collection of historical specs & phases | Cluttered flat directory structure | Grouped in `docs/{phases,specs,architecture,operations,showcase,repository}/` | MOVE | LOW |
| `scripts/run_showcase.py` | CLI scenario controller | Should be under `scripts/showcase/` | `scripts/showcase/run_showcase.py` + root forwarder | MOVE/SHIM | LOW |
| `scripts/*.sh`, `*.bat`, `*.py` | Ops, deployment, and testing utilities | Flat `scripts/` directory | Categorized under `scripts/{showcase,validation,operations,development}/` | ORGANIZE | LOW |
| `tests/` (82 test files) | Backend pytest regression suite | Fully working, canonical suite | `tests/` (Preserve structure to guarantee zero broken imports) | KEEP | ZERO |
| `android/` | Android native Jetpack Compose app | Android Gradle project | `android/` | KEEP | ZERO |
| `.gitignore` | Git exclusion rules | Missing at repository root | `.gitignore` | NEW | HIGH IMPORTANCE |
| `README.md` | Primary project presentation & entrypoint | Missing at repository root | `README.md` | NEW | HIGH IMPORTANCE |
| `CONTRIBUTING.md` | Developer contribution & coding guidelines | Missing at repository root | `CONTRIBUTING.md` | NEW | HIGH IMPORTANCE |
| `SECURITY.md` | Security disclosure & data integrity policy | Missing at repository root | `SECURITY.md` | NEW | HIGH IMPORTANCE |
| `LICENSE` | Open-source/Proprietary licensing file | Requires review status statement | `LICENSE` | NEW | HIGH IMPORTANCE |
| `.env.example` | Environment configuration template | Placeholder-only variable list | `.env.example` | KEEP/UPDATE | LOW |

---

## 3. Structural Decision Rules

1. **Analytical Engine Immunity**:
   * No refactoring or renaming of files within `app/hazard/`, `app/exposure/`, `app/vulnerability/`, `app/risk/`, `app/impact/`, `app/decision/`, `app/evidence/`, `app/events/`, or `app/pipeline/`.
2. **Backward Compatibility Shims**:
   * Any moved script (e.g. `scripts/run_showcase.py` -> `scripts/showcase/run_showcase.py`) will retain a delegating shim at the legacy path to ensure automation scripts do not fail.
3. **Documentation Categorization**:
   * Numbered historical design specifications (`01_PRD.md` to `74_*.md`) move into `docs/specs/`.
   * Phase completion records move into `docs/phases/phase-XX/`.
   * Cross-cutting operational documents move into `docs/operations/`.
   * Architectural specifications move into `docs/architecture/`.
   * Showcase scenario manuals move into `docs/showcase/`.
4. **Machine-Specific Path Eradication**:
   * All machine-specific path strings (`file:///d:/`, `D:\WeatherGPT`, etc.) must be replaced with clean repository-relative links.
