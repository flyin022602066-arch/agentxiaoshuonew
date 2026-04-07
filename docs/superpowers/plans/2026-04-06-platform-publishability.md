# Platform Publishability Guardrail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a platform-facing publishability gate to the main writing flow so chapters become more submission-ready for channels like 番茄 / 七猫 by reducing obvious high-risk phrasing, locally repairing fixable issues, and blocking only when risk remains clearly too high.

**Architecture:** Reuse the project’s existing style-learning, editor-review, and prompt infrastructure, but add a dedicated publishability layer in the main writing workflow. Before generation, inject platform-friendly constraints into prompts. After generation, run deterministic publish-risk checks, trigger targeted local rewrites for fixable categories, then re-check before allowing the chapter to pass.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, current prompt/config modules, pytest, async tests, deterministic rule checks.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Main place to add platform-friendly prompt constraints, publish-risk checks, and repair/deny logic.
- **Modify or Create:** `backend/app/services/quality_checker.py`
  - Use this if deterministic publish-risk scanning fits naturally there; otherwise keep helper logic in the workflow executor.
- **Create:** `backend/tests/test_publishability_guardrails.py`
  - Dedicated regression surface for platform-facing publishability checks and repairs.
- **Reference only:** `backend/app/services/style_learner.py`
  - For platform style context and config reuse.

Do **not** try to build a full legal/compliance engine. This phase only targets a pragmatic “平台可投” pre-check for obvious risk categories in the main writing flow.

---

### Task 1: Define the deterministic “平台可投” risk categories with failing tests first

**Files:**
- Create: `backend/tests/test_publishability_guardrails.py`
- Modify if needed: `backend/app/services/quality_checker.py` or `backend/app/workflow_executor.py`

- [ ] **Step 1: Write failing tests for clearly high-risk phrasing that should be flagged**

Cover a small, concrete ruleset only. Good initial categories:
- explicit sexual/obscene phrasing beyond platform-safe description
- highly graphic violence / gore wording
- drug / coercive abuse wording that is too direct or exploitative
- direct incitement-style wording or other obviously non-platform-friendly shock phrasing

```python
def test_publishability_scan_flags_graphic_and_explicit_risk():
    ...
    assert flagged_categories == {...}
```

- [ ] **Step 2: Write a failing test for benign prose that should NOT be flagged**

Run both tests to ensure the initial rules don’t immediately over-block ordinary conflict or suspense prose.

- [ ] **Step 3: Run the focused tests to verify the red state**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py -k "flags or benign" -v`

- [ ] **Step 4: Implement the minimum deterministic rule scanner**

Use a small, explicit ruleset with category labels and excerpts. Keep it transparent and explainable.

- [ ] **Step 5: Re-run the focused risk-scanner tests**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py -k "flags or benign" -v`

Expected: PASS.

---

### Task 2: Add platform-friendly prompt constraints before draft generation

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_publishability_guardrails.py`

- [ ] **Step 1: Write a failing test that the writing prompt includes platform-friendly guardrails**

The prompt should explicitly steer the writer away from:
- explicit pornographic detail
- gratuitously graphic gore
- obvious platform-hostile shock phrasing

But it should still allow conflict, danger, and suspense.

- [ ] **Step 2: Run the focused prompt-constraint test to verify the red state**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_writing_prompt_includes_platform_friendly_constraints -v`

- [ ] **Step 3: Add the minimum prompt constraints to the main writing flow**

Do not make the prompt timid or generic. Keep the instruction practical:
- write platform-friendly conflict
- avoid explicit over-detailing in risky categories
- preserve story intensity without direct违规表达

- [ ] **Step 4: Re-run the focused prompt test**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_writing_prompt_includes_platform_friendly_constraints -v`

Expected: PASS.

---

### Task 3: Add targeted publish-risk repair for fixable categories

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_publishability_guardrails.py`

- [ ] **Step 1: Write a failing workflow-level test where a chapter contains a locally repairable risky phrase**

The test should simulate:
- generated content contains a few high-risk spans
- the system should trigger a targeted publish-safe rewrite pass
- repaired content preserves plot while downgrading risky expression

- [ ] **Step 2: Run the focused workflow repair test to verify the red state**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_executor_repairs_fixable_publish_risks -v -s`

- [ ] **Step 3: Add the minimum targeted repair path**

The repair should:
- rewrite only flagged spans / local passages where possible
- preserve plot facts and scene direction
- avoid whole-chapter replacement

Acceptable implementation: a dedicated `_publishability_polish(...)` helper that only runs when flagged categories are repairable.

- [ ] **Step 4: Re-run the focused workflow repair test**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_executor_repairs_fixable_publish_risks -v -s`

Expected: PASS.

---

### Task 4: Add a hard block for unrepairable high-risk output

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_publishability_guardrails.py`

- [ ] **Step 1: Write a failing workflow-level test where the content remains too risky after attempted repair**

The expected behavior should be:
- final workflow result = error
- message indicates publishability / platform-risk failure

- [ ] **Step 2: Run the focused hard-block test to verify the red state**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_executor_blocks_unrepairable_publish_risk -v -s`

- [ ] **Step 3: Add the minimum denial path after repair re-check fails**

Do not silently pass the risky text. The workflow should fail clearly when content remains outside the acceptable envelope.

- [ ] **Step 4: Re-run the focused hard-block test**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py::test_executor_blocks_unrepairable_publish_risk -v -s`

Expected: PASS.

---

### Task 5: Run publishability regressions and the protected suite

**Files:**
- Test: `backend/tests/test_publishability_guardrails.py`
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run publishability-specific regressions**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_publishability_guardrails.py backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- any changed risk-scanning helper file
- `backend/tests/test_publishability_guardrails.py`

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of “平台可投” gain and stop before platform-specific micro-tuning

**Files:**
- Optional notes only if useful; avoid unnecessary churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one example of risky phrasing now flagged
- one example of locally repairable risk now rewritten safely
- one example of unrecoverable risk now blocked

- [ ] **Step 2: Stop after the general platform-facing gate is verified**

Do not continue yet into:
- fanqiao-specific micro-optimization
- qimao-specific micro-optimization
- platform-by-platform split rulebooks

- [ ] **Step 3: If asked to continue, write a separate plan for platform-specific tuning (番茄 vs 七猫)**

That next phase should build on this shared publishability baseline rather than redoing common risk scanning.
