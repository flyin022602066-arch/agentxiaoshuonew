# Fanqie Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the main writing flow so generated chapters feel closer to Fanqie-ready submissions: faster openings, sustained progression density, clearer conflict turns, stronger chapter-end hooks, and more direct commercial web-fiction readability.

**Architecture:** Reuse the existing platform style templates in `StyleLearner`, but harden them into a workflow-level platform adaptation gate. Before generation, inject Fanqie pacing and hook constraints into planning and writing prompts. After generation, run deterministic checks for opening speed, progression density, conflict presence, and hook strength; if the chapter underperforms, trigger localized Fanqie-style polishing before deciding whether to pass or fail.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, `StyleLearner`, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Main place to add Fanqie-specific prompt injection, pacing checks, hook checks, and repair flow.
- **Modify:** `backend/app/services/style_learner.py`
  - Only if existing Fanqie template needs stronger execution-level constraints.
- **Create:** `backend/tests/test_fanqie_adaptation.py`
  - Dedicated regression surface for Fanqie pacing, conflict density, and hook quality.
- **Reference only:** `backend/tests/test_publishability_guardrails.py`
  - Keep platform safety separate from platform “feel”.

Do **not** dilute this phase into generic style work or Qimao tuning. This plan is Fanqie-specific and writing-flow-specific.

---

### Task 1: Define deterministic Fanqie-feel checks with failing tests first

**Files:**
- Create: `backend/tests/test_fanqie_adaptation.py`
- Modify if needed: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write failing tests for key Fanqie feel signals**

At minimum cover these checks:
- **opening speed**: first ~200-300 chars should enter an event/problem quickly
- **progression density**: chapter should not spend too much space in static explanation
- **hook strength**: ending should contain a clear pull-forward question / danger / reveal pressure

- [ ] **Step 2: Include a benign non-Fanqie prose example that should score lower but not be mislabeled as broken prose**

This phase is about adaptation quality, not “bad writing” in the abstract.

- [ ] **Step 3: Run the focused tests to verify the red state**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py -k "opening or progression or hook" -v`

- [ ] **Step 4: Implement the minimum deterministic Fanqie checks**

Use a simple, transparent helper layer rather than opaque scoring magic. Keep the checks explainable.

- [ ] **Step 5: Re-run the focused Fanqie-feel tests**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py -k "opening or progression or hook" -v`

Expected: PASS.

---

### Task 2: Strengthen pre-generation Fanqie constraints in planning and writing prompts

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify if needed: `backend/app/services/style_learner.py`
- Modify: `backend/tests/test_fanqie_adaptation.py`

- [ ] **Step 1: Write a failing prompt-level test that requires Fanqie-specific constraints beyond the existing generic template**

The test should assert prompt language explicitly requires:
- fast event entry
- at least one conflict/turn in the chapter
- reduced explanatory slowdown
- stronger end hook

- [ ] **Step 2: Run the focused prompt test to verify the red state if current constraints are too generic**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_fanqie_prompt_requires_fast_entry_and_strong_hook -v`

- [ ] **Step 3: Add the minimum stronger Fanqie constraints**

Inject these rules into the relevant plan/write prompts without turning all prose into caricature.

- [ ] **Step 4: Re-run the focused prompt test**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_fanqie_prompt_requires_fast_entry_and_strong_hook -v`

Expected: PASS.

---

### Task 3: Add a post-generation Fanqie adaptation polish pass for underperforming chapters

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_fanqie_adaptation.py`

- [ ] **Step 1: Write a failing workflow-level test where a chapter is structurally fine but too slow / too soft for Fanqie**

The expected behavior should be:
- workflow detects weak Fanqie feel
- triggers a localized Fanqie adaptation polish pass
- polished result improves opening/hook while preserving plot facts

- [ ] **Step 2: Run the focused adaptation workflow test to verify the red state**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_executor_repairs_underpowered_fanqie_chapter -v -s`

- [ ] **Step 3: Add the minimum Fanqie polish helper and trigger logic**

Acceptable implementation shape:
- `_fanqie_adaptation_polish(content, diagnostics)` helper
- trigger only when Fanqie-feel checks fail
- preserve plot, compress exposition, strengthen chapter-end pull

- [ ] **Step 4: Re-run the focused adaptation workflow test**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_executor_repairs_underpowered_fanqie_chapter -v -s`

Expected: PASS.

---

### Task 4: Add a hard block for chapters that still fail Fanqie baseline after repair

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_fanqie_adaptation.py`

- [ ] **Step 1: Write a failing workflow-level test for a chapter that remains too slow or hookless even after repair attempt**

Expected behavior:
- final workflow result = error
- message indicates Fanqie adaptation failure / platform readiness failure

- [ ] **Step 2: Run the focused hard-block test to verify the red state**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_executor_blocks_chapter_that_still_lacks_fanqie_feel -v -s`

- [ ] **Step 3: Add the minimum denial path after failed Fanqie repair re-check**

Do not silently pass chapters that still miss the platform baseline.

- [ ] **Step 4: Re-run the focused hard-block test**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py::test_executor_blocks_chapter_that_still_lacks_fanqie_feel -v -s`

Expected: PASS.

---

### Task 5: Run Fanqie regressions and the protected suite

**Files:**
- Test: `backend/tests/test_fanqie_adaptation.py`
- Test: `backend/tests/test_publishability_guardrails.py`
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run Fanqie-specific regressions**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_fanqie_adaptation.py backend/tests/test_publishability_guardrails.py backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- `backend/app/services/style_learner.py` if modified
- `backend/tests/test_fanqie_adaptation.py`

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of “番茄可发稿感” and stop before Qimao tuning

**Files:**
- Optional notes only if useful; avoid unnecessary doc churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one example of slow opening now flagged
- one example of weak hook chapter now strengthened
- one example of still-unqualified Fanqie chapter now blocked

- [ ] **Step 2: Stop after Fanqie baseline is verified**

Do not continue into:
- Qimao-specific tuning
- dual-platform conflict resolution

- [ ] **Step 3: If asked to continue, write the next plan for Qimao adaptation or dual-platform branching**

That next phase should build on the Fanqie-ready baseline rather than redoing shared quality infrastructure.
