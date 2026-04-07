# Chapter Continuity Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main writing flow produce chapter-to-chapter continuations that are readable as true sequels: not simple rewrites of the previous chapter, clearly connected to the previous ending state, and advancing at least one carried-forward hook, emotion, or consequence.

**Architecture:** Reuse the project’s existing continuity primitives (`prev_chapters`, `build_next_chapter_baton`, duplication checking, chapter-plan constraints), but harden them into a dual-layer quality gate. Before generation, build stronger baton/anti-backtrack constraints into chapter planning and writing prompts. After generation, verify repetition and end-state carryover; if continuity is weak, repair the opening/continuation instead of regenerating the entire chapter when possible.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, `WritingService`, pytest, async tests, current story memory / chapter persistence helpers.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Primary continuity logic should live here: baton strengthening, duplication heuristics, carryover verification, and minimal repair.
- **Modify:** `backend/tests/test_second_chapter_continuation.py`
  - Existing continuation-related tests should become the main regression surface for readable continuity.
- **Modify if needed:** `backend/tests/test_blueprint_continuation.py`
  - Only if blueprint context tests need stricter assertions about baton/context propagation.
- **Create if needed:** `backend/tests/test_chapter_continuity_quality.py`
  - Use only if continuity tests become too large to keep readable in existing files.

Do **not** spread continuity fixes into unrelated API routes unless a route contract directly blocks testing. Keep the quality gate centered in the workflow executor.

---

### Task 1: Strengthen baton and anti-backtrack guidance before generation

**Files:**
- Modify: `backend/tests/test_second_chapter_continuation.py`
- Modify: `backend/app/workflow_executor.py:215-222`
- Modify: `backend/app/workflow_executor.py:196-212`

- [ ] **Step 1: Write a failing test that checks the next-chapter baton explicitly forbids replaying the just-finished chapter**

Add a unit test that verifies `build_next_chapter_baton(...)` and/or `build_chapter_plan(...)` encode:
- must continue from the last chapter’s end state
- must carry forward emotion/hook
- must not repeat the previous completed core event

```python
def test_next_chapter_baton_requires_continuation_not_replay():
    ...
    assert "禁止重复" in ...
    assert "延续" in ...
```

- [ ] **Step 2: Run the focused test to verify the red state if baton wording is too weak**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_next_chapter_baton_requires_continuation_not_replay -v`

- [ ] **Step 3: Tighten baton/chapter-plan wording with the minimum code change**

Update the planning helpers so they explicitly require:
- the next chapter must begin from the prior end-state, not from an earlier chapter setup
- recap is allowed only briefly and only in service of new progression
- replaying a completed core event is forbidden

- [ ] **Step 4: Re-run the focused baton/planning test**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_next_chapter_baton_requires_continuation_not_replay -v`

Expected: PASS.

---

### Task 2: Add post-generation continuity checks for repetition and carryover

**Files:**
- Modify: `backend/tests/test_second_chapter_continuation.py`
- Modify: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing workflow-level test where chapter 2 replays chapter 1 too heavily**

Add an async test around `WritingWorkflowExecutor.execute_chapter_workflow(...)` with stubs such that:
- previous chapter exists
- generated chapter 2 is highly similar to chapter 1
- the workflow is expected to reject or repair the replay instead of silently passing it through

```python
@pytest.mark.asyncio
async def test_executor_rejects_or_repairs_second_chapter_replay(...):
    ...
    assert result["status"] == "error" or ...
```

- [ ] **Step 2: Run the focused replay test to verify the red state**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_executor_rejects_or_repairs_second_chapter_replay -v -s`

- [ ] **Step 3: Add the minimum continuity post-check in the workflow**

The post-check should verify both:
- **repetition**: second chapter is not too similar to prior chapter content
- **carryover**: second chapter opening shows meaningful linkage to the previous ending state (emotion / hook / direct consequence)

If repetition is high or carryover is weak:
- prefer targeted opening/continuation repair first
- only hard-fail if repair cannot produce a valid continuation

- [ ] **Step 4: Re-run the focused replay test**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_executor_rejects_or_repairs_second_chapter_replay -v -s`

Expected: PASS.

---

### Task 3: Prove chapter 2 carries forward the previous ending state

**Files:**
- Modify: `backend/tests/test_second_chapter_continuation.py`
- Modify if needed: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing test where chapter 1 ends with a clear emotional/hook state and chapter 2 ignores it**

Example shape:
- chapter 1 ends with “主角发现码头有人等他”
- chapter 2 wrongly starts from generic morning narration

The test should expect the workflow to require explicit carryover of at least one of:
- end-state scene continuation
- emotional continuation
- unresolved hook continuation

- [ ] **Step 2: Run the focused carryover test to verify the red state**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_executor_requires_second_chapter_to_carry_forward_previous_ending_state -v -s`

- [ ] **Step 3: Add the minimum carryover heuristic and repair path**

Possible implementation shape:
- compare the previous chapter’s ending excerpt / baton against the opening window of the new chapter
- if no hook/emotion/event carryover is detected, trigger a targeted continuation-opening repair helper

Keep this minimal. Do not add a broad semantic-scoring subsystem yet.

- [ ] **Step 4: Re-run the focused carryover test**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py::test_executor_requires_second_chapter_to_carry_forward_previous_ending_state -v -s`

Expected: PASS.

---

### Task 4: Tighten existing integration tests to assert “连续可读” rather than just “not empty”

**Files:**
- Modify: `backend/tests/test_second_chapter_continuation.py`
- Modify if needed: `backend/tests/test_blueprint_continuation.py`

- [ ] **Step 1: Upgrade existing continuation tests with stronger assertions**

At minimum assert:
- chapter 2 is not identical to chapter 1
- chapter 2 does not open by replaying the same completed core event
- chapter 2 opening window contains at least one carryover signal from chapter 1 ending / baton / hook
- chapter 2 also advances to something new

- [ ] **Step 2: Run the upgraded integration-style tests in isolation**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py -v -s`

Expected: PASS.

---

### Task 5: Run continuity regressions and protected baseline suite

**Files:**
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_blueprint_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`
- Test: `backend/tests/test_config_service.py`
- Test: `backend/tests/test_config_api.py`

- [ ] **Step 1: Run continuity-focused regressions**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py backend/tests/test_blueprint_continuation.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_second_chapter_continuation.py backend/tests/test_blueprint_continuation.py backend/tests/test_ending_completeness.py backend/tests/test_config_service.py backend/tests/test_config_api.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- every modified continuity-related test file

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of the continuity gain and stop before AI-tone work

**Files:**
- Optional notes only if needed; avoid introducing new doc churn unless useful

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- an example of second-chapter replay now rejected or repaired
- an example of prior ending state now carried into chapter 2 opening
- evidence that the chapter still advances new material rather than becoming a recap paragraph

- [ ] **Step 2: Stop after “连续可读” is verified**

Do not continue into:
- AI-tone removal
- style stability
- platform moderation constraints

- [ ] **Step 3: If asked to continue, write the next plan for ‘去AI腔’ or ‘风格与人设稳定’ on top of the hardened continuity baseline**

The next plan should assume ending completeness + continuity are already in place.
