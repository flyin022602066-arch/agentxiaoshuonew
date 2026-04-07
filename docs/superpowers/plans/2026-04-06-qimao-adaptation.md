# Qimao Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapt the main writing flow so generated chapters feel closer to Qimao-ready submissions: smoother emotional continuity, richer scene and sensory texture, more layered character interaction, and softer but still effective chapter-end pull.

**Architecture:** Reuse the existing platform style template for Qimao, but add a workflow-level Qimao adaptation gate similar to the Fanqie path. Before generation, inject Qimao-specific constraints into planning and writing prompts. After generation, run deterministic checks for emotional continuity, scene texture, interaction layering, and moderated hook strength; if the chapter underperforms, trigger localized Qimao-style polishing before deciding whether to pass or fail.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, `StyleLearner`, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Main place to add Qimao feel evaluation, Qimao adaptation polish, and fail/repair logic.
- **Modify:** `backend/app/services/style_learner.py`
  - Only if the existing Qimao prompt needs stronger operational constraints.
- **Create:** `backend/tests/test_qimao_adaptation.py`
  - Dedicated regression surface for Qimao emotional flow, detail texture, interaction depth, and hook softness.
- **Reference only:** `backend/tests/test_fanqie_adaptation.py`
  - Reuse the same execution pattern, but tune the criteria for Qimao instead of Fanqie.

Do **not** collapse Qimao into generic “good writing”. This phase is specifically about Qimao-ready reading feel.

---

### Task 1: Define deterministic Qimao-feel checks with failing tests first

**Files:**
- Create: `backend/tests/test_qimao_adaptation.py`
- Modify if needed: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write failing tests for key Qimao feel signals**

At minimum cover these checks:
- **emotional continuity**: emotional movement should feel smooth, not abrupt or purely functional
- **scene texture**: prose should include some sensory/environmental texture, not only plot events
- **interaction layering**: character interaction should include subtext / reaction / emotional shading, not just raw dialogue exchange
- **hook moderation**: ending can pull forward, but should not feel explosively “hard-hooked” like Fanqie

- [ ] **Step 2: Include a too-harsh / too-blunt chapter sample that should fail Qimao adaptation even if it works for Fanqie**

- [ ] **Step 3: Run the focused tests to verify the red state**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py -k "emotion or texture or interaction or hook" -v`

- [ ] **Step 4: Implement the minimum deterministic Qimao checks**

Keep the checks simple, explainable, and distinct from Fanqie.

- [ ] **Step 5: Re-run the focused Qimao-feel tests**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py -k "emotion or texture or interaction or hook" -v`

Expected: PASS.

---

### Task 2: Strengthen pre-generation Qimao constraints in planning and writing prompts

**Files:**
- Modify: `backend/app/services/style_learner.py`
- Modify if needed: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_qimao_adaptation.py`

- [ ] **Step 1: Write a failing prompt-level test that requires Qimao-specific constraints beyond the current generic template**

The prompt should explicitly push for:
- smoother emotional progression
- richer sensory and spatial detail
- layered interaction, not just blunt exchange
- chapter-end pull that is effective but not over-hard

- [ ] **Step 2: Run the focused prompt test to verify the red state if the current Qimao template is too generic**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_qimao_prompt_requires_emotion_texture_and_layered_interaction -v`

- [ ] **Step 3: Add the minimum stronger Qimao constraints**

Adjust the Qimao prompt only enough to make the differences operational and testable.

- [ ] **Step 4: Re-run the focused prompt test**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_qimao_prompt_requires_emotion_texture_and_layered_interaction -v`

Expected: PASS.

---

### Task 3: Add a post-generation Qimao adaptation polish pass for chapters that feel too dry or too blunt

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_qimao_adaptation.py`

- [ ] **Step 1: Write a failing workflow-level test where a chapter is structurally fine but emotionally thin / texturally dry for Qimao**

Expected behavior:
- workflow detects weak Qimao feel
- triggers localized Qimao adaptation polish
- polished result adds emotional continuity / texture / layered interaction without changing plot facts

- [ ] **Step 2: Run the focused adaptation workflow test to verify the red state**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_executor_repairs_underpowered_qimao_chapter -v -s`

- [ ] **Step 3: Add the minimum Qimao polish helper and trigger logic**

Acceptable implementation shape:
- `_qimao_adaptation_polish(content, diagnostics)` helper
- trigger only when Qimao-feel checks fail
- preserve plot, deepen texture and interaction, soften overly blunt hooks

- [ ] **Step 4: Re-run the focused adaptation workflow test**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_executor_repairs_underpowered_qimao_chapter -v -s`

Expected: PASS.

---

### Task 4: Add a hard block for chapters that still fail Qimao baseline after repair

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_qimao_adaptation.py`

- [ ] **Step 1: Write a failing workflow-level test for a chapter that remains too blunt / too dry / too hard-hooked even after repair**

Expected behavior:
- final workflow result = error
- message indicates Qimao adaptation failure / platform readiness failure

- [ ] **Step 2: Run the focused hard-block test to verify the red state**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_executor_blocks_chapter_that_still_lacks_qimao_feel -v -s`

- [ ] **Step 3: Add the minimum denial path after failed Qimao repair re-check**

Do not silently pass chapters that still miss the Qimao baseline.

- [ ] **Step 4: Re-run the focused hard-block test**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py::test_executor_blocks_chapter_that_still_lacks_qimao_feel -v -s`

Expected: PASS.

---

### Task 5: Run Qimao regressions and the protected suite

**Files:**
- Test: `backend/tests/test_qimao_adaptation.py`
- Test: `backend/tests/test_fanqie_adaptation.py`
- Test: `backend/tests/test_publishability_guardrails.py`
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run Qimao-specific regressions**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_qimao_adaptation.py backend/tests/test_fanqie_adaptation.py backend/tests/test_publishability_guardrails.py backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- `backend/app/services/style_learner.py` if modified
- `backend/tests/test_qimao_adaptation.py`

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of “七猫可发稿感” and stop before dual-platform conflict tuning

**Files:**
- Optional notes only if useful; avoid unnecessary doc churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one example of emotion-thin / dry chapter now flagged
- one example of Qimao adaptation polish improving texture or interaction
- one example of still-unqualified Qimao chapter now blocked

- [ ] **Step 2: Stop after Qimao baseline is verified**

Do not continue yet into:
- Fanqie vs Qimao dynamic branching
- one-click multi-platform output negotiation

- [ ] **Step 3: If asked to continue, write the next plan for dual-platform branching / export strategy**

That phase should build on both Fanqie-ready and Qimao-ready baselines.
