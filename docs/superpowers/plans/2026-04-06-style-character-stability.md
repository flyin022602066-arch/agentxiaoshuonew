# Style and Character Stability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main writing flow produce chapters that remain stable in both character behavior/voice and chapter-level stylistic focus, so the output reads like the same author writing the same cast rather than drifting mid-chapter.

**Architecture:** Reuse the project’s existing `character_state_packet`, `style_feedback`, and `review_packet` structures, but turn them into an enforceable quality gate. Before generation, strengthen character-state and style-focus constraints in prompts. After generation, explicitly detect character drift and tone drift; if the drift is local, repair locally, and only fail when the chapter cannot satisfy the stability threshold.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, current style evaluator, current consistency review packet, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Main place for style/character pre-constraints, drift checks, and local repair flow.
- **Modify:** `backend/tests/test_style_feedback.py`
  - Extend from “style feedback exists” to “style drift is detected and enforced”.
- **Modify:** `backend/tests/test_style_propagation.py`
  - Strengthen prompt-level tests for style focus and character state usage.
- **Create if needed:** `backend/tests/test_character_consistency.py`
  - Use only if character-drift tests would overload existing files.

Keep stability enforcement in the workflow executor. Do **not** scatter partial checks across unrelated services.

---

### Task 1: Strengthen pre-generation character-state and voice constraints

**Files:**
- Modify: `backend/tests/test_style_propagation.py`
- Modify: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing prompt-level test that requires the writing pipeline to mention behavior constraints and dialogue tone explicitly**

The test should assert that the prompt used for writing or final polishing includes concrete character-state guidance such as:
- current goal
- current emotion
- behavior constraints
- dialogue tone / identity markers

- [ ] **Step 2: Run the focused test to verify the red state if prompt constraints are too weak**

Run:
`python -m pytest backend/tests/test_style_propagation.py::test_writing_prompt_includes_character_state_and_voice_constraints -v`

- [ ] **Step 3: Add the minimum prompt constraint strengthening**

Ensure the relevant generation/polish prompt explicitly carries:
- protagonist current goal
- protagonist current emotion
- behavior constraints
- supporting character dialogue tone where available
- chapter style focus (top matched style features)

- [ ] **Step 4: Re-run the focused prompt-level stability test**

Run:
`python -m pytest backend/tests/test_style_propagation.py::test_writing_prompt_includes_character_state_and_voice_constraints -v`

Expected: PASS.

---

### Task 2: Add a style-drift quality gate for chapters that lose their selected authorial focus

**Files:**
- Modify: `backend/tests/test_style_feedback.py`
- Modify: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing workflow-level test where a chapter starts in one style and drifts into a mismatched tone**

Example:
- selected style is `wuxia_gulong`
- generated chapter becomes verbose, explanatory, and soft-toned halfway through

The test should expect the workflow to either repair the drift locally or fail the chapter rather than silently passing it.

- [ ] **Step 2: Run the focused style-drift test to verify the red state**

Run:
`python -m pytest backend/tests/test_style_feedback.py::test_executor_rejects_or_repairs_style_drift -v -s`

- [ ] **Step 3: Add the minimum style-drift gate in the workflow**

Acceptable implementation shape:
- use `style_feedback` score and matched/missing features
- if style score falls below the minimum stable threshold, trigger a localized style repair pass
- only fail if repair cannot recover a stable style signal

Keep this deterministic and small.

- [ ] **Step 4: Re-run the focused style-drift test**

Run:
`python -m pytest backend/tests/test_style_feedback.py::test_executor_rejects_or_repairs_style_drift -v -s`

Expected: PASS.

---

### Task 3: Add a character-consistency gate for obvious OOC behavior or voice drift

**Files:**
- Modify: `backend/tests/test_style_feedback.py` or create `backend/tests/test_character_consistency.py`
- Modify: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing workflow-level test where character behavior clearly violates the provided state packet**

Example:
- state packet says protagonist is cautious / wounded / suppressing emotion
- generated output makes them suddenly flamboyant, reckless, or tonally out of character without setup

- [ ] **Step 2: Run the focused character-drift test to verify the red state**

Run:
`python -m pytest <target-file>::test_executor_rejects_or_repairs_character_drift -v -s`

- [ ] **Step 3: Add the minimum character-drift check and local repair trigger**

Possible implementation shape:
- inspect `review_packet` / quality issues for OOC-like signals
- add deterministic rule checks against `behavior_constraints`
- if drift is local, repair only affected passages
- if clearly unrecoverable, fail the chapter rather than silently returning it

- [ ] **Step 4: Re-run the focused character-drift test**

Run:
`python -m pytest <target-file>::test_executor_rejects_or_repairs_character_drift -v -s`

Expected: PASS.

---

### Task 4: Tighten existing integration tests so “stable readable” means more than just metadata exposure

**Files:**
- Modify: `backend/tests/test_style_feedback.py`
- Modify: `backend/tests/test_style_propagation.py`

- [ ] **Step 1: Strengthen current tests to assert stability behavior, not just field presence**

At minimum add assertions that:
- style feedback remains above the expected floor after workflow completion
- character state packet is not ignored by downstream prompts
- repairs preserve plot progression while correcting stability drift

- [ ] **Step 2: Run the strengthened integration-style tests in isolation**

Run:
`python -m pytest backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py -v -s`

Expected: PASS.

---

### Task 5: Run stability regressions and the protected suite

**Files:**
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run style/character stability regressions**

Run:
`python -m pytest backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- any changed stability-related test files

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of the stability gain and stop before platform moderation work

**Files:**
- Optional notes only if needed; avoid extra churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one example of style drift now rejected or repaired
- one example of OOC/voice drift now rejected or repaired
- evidence that plot progression survives the repair

- [ ] **Step 2: Stop after “稳定可读” is verified**

Do not continue into:
- platform moderation / content compliance
- marketplace-specific taboo filtering

- [ ] **Step 3: If asked to continue, write the next plan for platform-facing moderation / publishing constraints**

That next phase should assume ending completeness + continuity + de-AI + stability are already in place.
