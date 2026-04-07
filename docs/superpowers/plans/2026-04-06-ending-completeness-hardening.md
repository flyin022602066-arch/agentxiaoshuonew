# Ending Completeness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main writing flow end chapters as readable complete chapters, not half-written drafts, by enforcing local chapter closure during generation and repairing only the ending when post-checks detect an incomplete close.

**Architecture:** Reuse the existing ending-detection and ending-repair helpers in `workflow_executor.py`, but connect them into the real chapter generation pipeline as an explicit dual-layer quality gate. First, strengthen the chapter-plan / generation requirements so endings aim for local closure. Second, after draft generation and quality checks, run ending-completeness evaluation and trigger ending-only continuation/repair when the chapter still reads unfinished.

**Tech Stack:** Python, FastAPI backend, existing `WritingWorkflowExecutor`, pytest, async tests, existing quality-checking helpers.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - The core place where ending-completeness logic, completion evaluation, and post-generation repair should be orchestrated.
- **Modify:** `backend/tests/test_ending_completeness.py`
  - Extend existing ending tests from primitive detection into main-flow-like behavior checks.
- **Create if needed:** `backend/tests/test_main_flow_quality_endings.py`
  - Only if `test_ending_completeness.py` becomes too overloaded; use this file for integration-style flow tests specific to chapter closure.

Do **not** spread ending logic across unrelated services or routes. Keep the quality gate in the workflow executor where draft generation and revision already live.

---

### Task 1: Lock down the “readable complete chapter” ending heuristics

**Files:**
- Modify: `backend/tests/test_ending_completeness.py`
- Reference: `backend/app/workflow_executor.py:57-111`

- [ ] **Step 1: Write a failing test for endings that are grammatically finished but still read unfinished**

Add one or two examples that end in a complete sentence but still feel like they stop at a transitional setup instead of a chapter beat.

```python
def test_ending_completeness_rejects_transition_only_endings():
    from app.workflow_executor import check_ending_completeness

    text = "他推开仓库门，朝里面走去。下一秒，他看见前方亮起一盏灯。"
    result = check_ending_completeness(text)
    assert result["is_complete"] is False
```

- [ ] **Step 2: Run the single test to verify the red state**

Run:
`python -m pytest backend/tests/test_ending_completeness.py::test_ending_completeness_rejects_transition_only_endings -v`

Expected: FAIL because the current heuristic likely treats punctuation alone as sufficient.

- [ ] **Step 3: Implement the minimum heuristic expansion in `check_ending_completeness`**

Teach the checker to reject endings that are structurally complete but still clearly transitional, such as:
- “下一秒/下一刻/紧接着/就在这时” leading into a scene that has not resolved
- a fresh setup beat with no local emotional or plot closure
- endings that only open a door / see a person / hear a voice without completing the beat

Keep this heuristic conservative. It should reject obvious unfinished endings, not valid suspense endings.

- [ ] **Step 4: Run the focused ending tests and confirm old valid suspense endings still pass**

Run:
`python -m pytest backend/tests/test_ending_completeness.py -v`

Expected: existing complete/suspense cases still PASS; new transition-only case now PASS.

---

### Task 2: Add a post-generation ending repair gate to the main writing workflow

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Reference: `backend/app/workflow_executor.py:203-232`
- Reference: `backend/app/workflow_executor.py:489-517`
- Reference: `backend/app/workflow_executor.py:556-579`

- [ ] **Step 1: Write a failing async test that simulates a chapter ending in an unfinished way and expects repair**

Extend `backend/tests/test_ending_completeness.py` with a flow-level test around the executor, not just the helper.

```python
@pytest.mark.asyncio
async def test_executor_repairs_transition_only_chapter_endings(monkeypatch):
    ...
    assert result["content"].endswith("。")
    assert "下一秒" not in result["content"][-40:]
```

This test should stub LLM calls so that:
- initial draft ends in a transition-only close
- repair call returns a better chapter-ending paragraph

- [ ] **Step 2: Run the focused async test to verify the red state**

Run:
`python -m pytest backend/tests/test_ending_completeness.py::test_executor_repairs_transition_only_chapter_endings -v -s`

Expected: FAIL because the main workflow does not yet guarantee ending repair for this case.

- [ ] **Step 3: Insert the ending gate into the real workflow sequence**

Within `WritingWorkflowExecutor.execute_chapter_workflow(...)`, ensure the flow does this in order:
1. generate draft
2. run completion / quality evaluation
3. if ending incomplete → repair only the ending (`_complete_ending` or targeted continuation)
4. re-check ending completeness
5. only then move to later polish/save stages

Do not re-run the whole chapter from scratch unless the existing flow already does so. Prefer ending-only repair.

- [ ] **Step 4: Re-run the focused async test**

Run:
`python -m pytest backend/tests/test_ending_completeness.py::test_executor_repairs_transition_only_chapter_endings -v -s`

Expected: PASS.

---

### Task 3: Strengthen chapter-plan guidance so the model aims for local closure before repair

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Reference: `backend/app/workflow_executor.py:174-200`

- [ ] **Step 1: Write a failing unit test for chapter plan ending guidance**

Add a test asserting that `build_chapter_plan(...)` makes “local closure + hook” explicit, not just “留下接续点”.

```python
def test_build_chapter_plan_requires_local_closure_before_hook():
    from app.workflow_executor import build_chapter_plan
    plan = build_chapter_plan(...)
    assert "收束" in str(plan["ending_state"])
```

- [ ] **Step 2: Run the test to verify the red state if wording is too weak**

Run:
`python -m pytest backend/tests/test_ending_completeness.py::test_build_chapter_plan_requires_local_closure_before_hook -v`

- [ ] **Step 3: Tighten `build_chapter_plan` ending instructions**

Update the ending guidance so it explicitly says:
- this chapter must land a local beat
- suspense is allowed only after a local closure point
- the chapter cannot stop at pure setup or interruption

- [ ] **Step 4: Re-run the focused plan test**

Run:
`python -m pytest backend/tests/test_ending_completeness.py::test_build_chapter_plan_requires_local_closure_before_hook -v`

Expected: PASS.

---

### Task 4: Prove the repaired ending survives the wider writing-quality flow

**Files:**
- Modify: `backend/tests/test_ending_completeness.py`
- Modify if needed: `backend/tests/test_main_flow_validation.py`

- [ ] **Step 1: Add a focused integration-style regression for “可读成章” ending output**

The test should verify all of the following after repair:
- ending is a full sentence
- final 1-3 sentences contain a local closure beat
- text does not end in a dangling setup phrase
- chapter can still end with suspense, but not unfinished scaffolding

- [ ] **Step 2: Run the new regression in isolation**

Run:
`python -m pytest backend/tests/test_ending_completeness.py -k "readable_complete or repair" -v -s`

Expected: PASS.

- [ ] **Step 3: If the current main-flow validation test uses fake writing output, extend it minimally to assert chapter endings are complete**

Only do this if it improves confidence without making the main-flow test brittle.

---

### Task 5: Run the protected regression suite and diagnostics

**Files:**
- Test: `backend/tests/test_ending_completeness.py`
- Test: `backend/tests/test_main_flow_validation.py` (if modified)
- Test: `backend/tests/test_config_service.py`
- Test: `backend/tests/test_config_api.py`

- [ ] **Step 1: Run ending-focused regression tests**

Run:
`python -m pytest backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_ending_completeness.py backend/tests/test_main_flow_validation.py backend/tests/test_config_service.py backend/tests/test_config_api.py -v`

If `test_main_flow_validation.py` is only present in the active worktree branch for previous work, use the exact file set available in that workspace and note it explicitly.

- [ ] **Step 3: Run diagnostics on all changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- every modified ending-related test file

Expected: no new blocking diagnostics introduced by this work.

---

### Task 6: Capture the exact quality gain and stop before broader quality work

**Files:**
- Optional modify/create only if the repo prefers durable notes: `docs/superpowers/plans/` or adjacent docs

- [ ] **Step 1: Record evidence of the gain**

At minimum capture:
- an example of previously accepted bad ending now rejected
- an example of repaired ending now passing
- evidence that valid suspense endings are still accepted

- [ ] **Step 2: Stop after “结尾完整 / 可读成章” is verified**

Do not continue into:
- AI-tone removal
- full continuity quality hardening
- style stability
- platform-specific moderation rules

Those are separate follow-up phases.

- [ ] **Step 3: If asked to continue, write the next plan for ‘上下章连续性’ or ‘去AI腔’ based on the newly hardened ending gate**

That plan should build on this ending-complete baseline rather than re-solving ending logic again.
