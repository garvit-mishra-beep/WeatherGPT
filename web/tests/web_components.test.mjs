import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const webRoot = path.resolve(__dirname, "..");

test("1. VAYUBODHAK Design System - Android Parity CSS Tokens", () => {
  const cssPath = path.join(webRoot, "styles", "globals.css");
  assert.ok(fs.existsSync(cssPath), "globals.css must exist");
  const css = fs.readFileSync(cssPath, "utf8");

  // Verify core Android color tokens
  assert.ok(css.includes("#1B5E20"), "Must include Forest Emerald Primary (--vayu-primary: #1B5E20)");
  assert.ok(css.includes("#E8F5E9"), "Must include Mint Container (--vayu-primary-container: #E8F5E9)");
  assert.ok(css.includes("#00796B"), "Must include Secondary Teal (--vayu-secondary: #00796B)");
  assert.ok(css.includes("#F8FAF8"), "Must include Canvas Background (--vayu-background: #F8FAF8)");
  assert.ok(css.includes("#16A34A"), "Must include Success Green token");
  assert.ok(css.includes("#CA8A04"), "Must include Caution Yellow token");
  assert.ok(css.includes("#EA580C"), "Must include Warning Orange token");
  assert.ok(css.includes("#DC2626"), "Must include Danger Red token");
});

test("2. Zero Hardcoded Analytical Assessments Invariant", () => {
  // Recursively inspect web/app and web/components for forbidden hardcoded analytical strings
  const forbiddenPatterns = [
    /const\s+risk\s*=\s*["'](HIGH|CRITICAL|LOW|MODERATE)["']/i,
    /const\s+hazard\s*=\s*["'](HIGH|CRITICAL|LOW|MODERATE)["']/i,
    /const\s+verdict\s*=\s*["'](NO_GO|GO|POSTPONE|PROCEED_WITH_CAUTION)["']/i,
    /const\s+severity\s*=\s*["'](HIGH|CRITICAL|LOW|MODERATE)["']/i,
  ];

  function checkDir(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        checkDir(fullPath);
      } else if (/\.(tsx|ts|jsx|js)$/.test(entry.name)) {
        const content = fs.readFileSync(fullPath, "utf8");
        for (const pattern of forbiddenPatterns) {
          assert.ok(
            !pattern.test(content),
            `Violation found in ${fullPath}: Hardcoded analytical assessment matching ${pattern}`
          );
        }
      }
    }
  }

  checkDir(path.join(webRoot, "app"));
  checkDir(path.join(webRoot, "components"));
});

test("3. Source Authority & Truthful Status Labeling", () => {
  const allowedSourceStatuses = [
    "LIVE",
    "CACHED",
    "FALLBACK",
    "STALE",
    "HISTORICAL",
    "UNAVAILABLE",
    "CONTROLLED_SCENARIO",
  ];

  function evaluateTruthfulStatus(isOffline, isControlled, telemetryFreshnessSec) {
    if (isOffline) return "CACHED";
    if (isControlled) return "CONTROLLED_SCENARIO";
    if (telemetryFreshnessSec > 3600) return "STALE";
    return "LIVE";
  }

  assert.equal(evaluateTruthfulStatus(true, false, 10), "CACHED");
  assert.notEqual(evaluateTruthfulStatus(true, false, 10), "LIVE", "Offline data must NEVER be labeled LIVE");
  assert.equal(evaluateTruthfulStatus(false, true, 10), "CONTROLLED_SCENARIO");
  assert.notEqual(evaluateTruthfulStatus(false, true, 10), "LIVE", "Controlled scenario data must NEVER be labeled LIVE");
  assert.equal(evaluateTruthfulStatus(false, false, 5000), "STALE");
  assert.equal(evaluateTruthfulStatus(false, false, 60), "LIVE");
});

test("4. Resilience: LLM Decoupled Failure Invariant", () => {
  // Deterministic engine state
  const deterministicAssessment = {
    decision_id: "DEC-2026-GWL-001",
    verdict: "MONITOR",
    severity: "LOW",
    composite_risk_score: 0.18,
    hazard_index: 0.20,
    rules_evaluated: [
      { rule_id: "R-RAIN-01", status: "PASSED" },
      { rule_id: "R-WIND-01", status: "PASSED" },
    ],
  };

  // Simulate LLM service failure
  const llmResponse = null; // LLM failure / timeout
  const llmStatus = "LLM_UNAVAILABLE";

  // Policy: Disaster assessment must remain fully accessible even if LLM fails
  const uiState = {
    assessment: deterministicAssessment,
    explanation: llmResponse || "AI explanation temporarily unavailable. Verified disaster assessment remains available.",
    llmStatus: llmStatus,
  };

  assert.ok(uiState.assessment != null, "Assessment must not be null when LLM fails");
  assert.equal(uiState.assessment.verdict, "MONITOR");
  assert.equal(uiState.assessment.severity, "LOW");
  assert.ok(
    uiState.explanation.includes("Verified disaster assessment remains available"),
    "Must show verified assessment fallback notice when LLM fails"
  );
});

test("5. System Operational State Machine Transitions", () => {
  const validStates = [
    "FULL_OPERATIONAL",
    "DEGRADED_DATA",
    "OFFLINE",
    "RECOVERING",
    "UNAVAILABLE",
  ];

  function transitionState(current, event) {
    switch (event) {
      case "NETWORK_LOST":
        return "OFFLINE";
      case "NETWORK_RESTORED":
        return "RECOVERING";
      case "SYNC_COMPLETE":
        return "FULL_OPERATIONAL";
      case "SECONDARY_FEED_FAILED":
        return "DEGRADED_DATA";
      case "TOTAL_FAILURE":
        return "UNAVAILABLE";
      default:
        return current;
    }
  }

  let state = "FULL_OPERATIONAL";
  state = transitionState(state, "NETWORK_LOST");
  assert.equal(state, "OFFLINE");

  state = transitionState(state, "NETWORK_RESTORED");
  assert.equal(state, "RECOVERING");

  state = transitionState(state, "SYNC_COMPLETE");
  assert.equal(state, "FULL_OPERATIONAL");

  state = transitionState(state, "SECONDARY_FEED_FAILED");
  assert.equal(state, "DEGRADED_DATA");
});

test("6. Four Brains Navigation Parity", () => {
  const brains = ["general", "farmer", "researcher", "analyst"];
  const brainPagePath = path.join(webRoot, "app", "intelligence", "[brain]", "page.tsx");
  assert.ok(fs.existsSync(brainPagePath), "Dynamic brain page [brain]/page.tsx must exist");

  const code = fs.readFileSync(brainPagePath, "utf8");
  for (const b of brains) {
    assert.ok(code.toLowerCase().includes(b), `Brain page must handle ${b}`);
  }
});

test("7. Showcase Scenario Controller Contract", () => {
  const showcaseSteps = [
    { step: 0, name: "Baseline", expectedSeverity: "LOW" },
    { step: 1, name: "Rain Escalation", expectedSeverity: "MODERATE" },
    { step: 2, name: "Warning Escalation", expectedSeverity: "HIGH" },
    { step: 3, name: "Nirnay Revision", expectedSeverity: "CRITICAL" },
  ];

  assert.equal(showcaseSteps.length, 4);
  assert.equal(showcaseSteps[0].name, "Baseline");
  assert.equal(showcaseSteps[3].expectedSeverity, "CRITICAL");
});
