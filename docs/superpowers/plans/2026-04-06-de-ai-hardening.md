# De-AI Tone Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main writing flow produce prose that reads more naturally human-written by reducing obvious AI-template phrases, mechanical action/emotion patterns, and expository filler without changing plot structure.

**Architecture:** Reuse the existing AI-pattern detector and `_de_ai_polish()` pass, but harden the system into a dual-layer gate. Before writing, strengthen prompt constraints against stock AI phrasing. After draft generation, explicitly measure AI-pattern density and trigger targeted de-AI polish only when the content crosses a meaningful threshold. Keep the repair localized and do not replace plot logic.

**Tech Stack:** Python, existing `WritingWorkflowExecutor`, `QualityChecker`, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/workflow_executor.py`
  - Main place to strengthen anti-template prompt constraints and de-AI decision logic.
- **Modify:** `backend/tests/test_de_ai_polish.py`
  - Core regression surface for AI-pattern detection and de-AI workflow behavior.
- **Modify if needed:** `backend/app/services/quality_checker.py`
  - Only if the AI-pattern detector is too weak for the new failing tests.
- **Create if needed:** `backend/tests/test_de_ai_main_flow.py`
  - Use only if flow-level de-AI tests become too heavy to keep inside `test_de_ai_polish.py`.

Keep de-AI behavior centered in the writing workflow, not spread into unrelated services.

---

### Task 1: Strengthen AI-pattern detection coverage with failing tests first

**Files:**
- Modify: `backend/tests/test_de_ai_polish.py`
- Modify if needed: `backend/app/services/quality_checker.py`

- [ ] **Step 1: Write a failing test for clustered low-grade AI phrasing that should count as de-AI-worthy**

Add a test where the text contains several individually mild clichés that together should trigger de-AI handling.

```python
def test_ai_pattern_detection_catches_clustered_template_prose():
    ...
    assert len(patterns) >= 3
```

Examples to cover:
- “不由得一怔”
- “心头微微一沉”
- “空气仿佛凝固”
- “某种预感涌上心头”

- [ ] **Step 2: Run the focused test to verify the red state**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_ai_pattern_detection_catches_clustered_template_prose -v`

- [ ] **Step 3: Extend `QualityChecker._check_ai_patterns` minimally to catch the new clustered clichés**

Do not make the detector so broad that ordinary natural prose becomes a false positive. Add only the minimum additional patterns required by the failing test.

- [ ] **Step 4: Re-run the focused detection test plus the natural-writing safety test**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_ai_pattern_detection_catches_clustered_template_prose backend/tests/test_de_ai_polish.py::test_ai_pattern_detection_accepts_natural_writing -v`

Expected: both PASS.

---

### Task 2: Make de-AI triggering depend on meaningful pattern density, not only a binary hit

**Files:**
- Modify: `backend/tests/test_de_ai_polish.py`
- Modify: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing workflow-level test where content contains enough AI clichés that de-AI polish must trigger**

The test should stub the writing workflow so that:
- initial drafted content contains multiple AI-template patterns
- `_de_ai_polish` is expected to be called
- the final returned content is the polished version

```python
@pytest.mark.asyncio
async def test_executor_triggers_de_ai_polish_for_high_pattern_density(...):
    ...
    assert result["content"] == polished_version
```

- [ ] **Step 2: Run the focused workflow test to verify the red state if triggering is too weak or inconsistent**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_executor_triggers_de_ai_polish_for_high_pattern_density -v -s`

- [ ] **Step 3: Implement the minimum trigger hardening in the workflow**

Within `execute_chapter_workflow(...)`, make de-AI triggering depend on a stronger threshold than “any pattern exists”.

Example acceptable approaches:
- pattern count threshold
- weighted severity threshold
- clustered-pattern threshold within a short span

Keep it simple and deterministic.

- [ ] **Step 4: Re-run the focused workflow de-AI trigger test**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_executor_triggers_de_ai_polish_for_high_pattern_density -v -s`

Expected: PASS.

---

### Task 3: Ensure clean prose is not over-polished unnecessarily

**Files:**
- Modify: `backend/tests/test_de_ai_polish.py`
- Modify if needed: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing test where already-natural prose should bypass de-AI polish**

```python
@pytest.mark.asyncio
async def test_executor_skips_de_ai_polish_for_natural_prose(...):
    ...
    assert de_ai_called is False
```

- [ ] **Step 2: Run the focused natural-prose bypass test to verify the red state if over-triggering occurs**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_executor_skips_de_ai_polish_for_natural_prose -v -s`

- [ ] **Step 3: Implement the minimum safeguard against unnecessary de-AI passes**

If the current workflow de-AIs too aggressively, tighten the threshold so naturally readable prose is left alone.

- [ ] **Step 4: Re-run the focused bypass test**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_executor_skips_de_ai_polish_for_natural_prose -v -s`

Expected: PASS.

---

### Task 4: Improve anti-template prompt guidance before draft generation

**Files:**
- Modify: `backend/app/workflow_executor.py`
- Modify: `backend/tests/test_de_ai_polish.py`

- [ ] **Step 1: Write a failing test that checks writing prompts explicitly forbid the highest-frequency AI clichés**

You can assert against prompt content generated for `_de_ai_polish` or draft-generation helpers, depending on where the prompt constraints are best enforced.

- [ ] **Step 2: Run the focused prompt-constraint test to verify the red state**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_de_ai_prompt_explicitly_forbids_stock_ai_templates -v`

- [ ] **Step 3: Add the minimum anti-template instructions to the relevant writing/de-AI prompts**

The prompt should explicitly warn against recurring stock phrasing such as:
- “眼中闪过一丝”
- “嘴角勾起一抹”
- “深吸一口气”
- “心头一震/一沉”
- “空气仿佛凝固”

- [ ] **Step 4: Re-run the focused prompt test**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py::test_de_ai_prompt_explicitly_forbids_stock_ai_templates -v`

Expected: PASS.

---

### Task 5: Run de-AI regressions and protected suite

**Files:**
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`
- Test: `backend/tests/test_config_service.py`
- Test: `backend/tests/test_config_api.py`

- [ ] **Step 1: Run the de-AI-focused regression suite**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py backend/tests/test_config_service.py backend/tests/test_config_api.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/workflow_executor.py`
- `backend/tests/test_de_ai_polish.py`
- `backend/app/services/quality_checker.py` if modified

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of the naturalness gain and stop before style/persona work

**Files:**
- Optional notes only if useful; avoid doc churn if not needed

- [ ] **Step 1: Capture exact evidence of the gain**

At minimum capture:
- an example of cliché-heavy prose now triggering de-AI polish
- an example of natural prose now bypassing de-AI polish
- evidence that plot structure is preserved while phrasing becomes less templated

- [ ] **Step 2: Stop after “自然可读” is verified**

Do not continue into:
- style stability
- character voice consistency
- platform moderation constraints

- [ ] **Step 3: If asked to continue, write the next plan for ‘风格与人设稳定’ on top of the hardened de-AI baseline**

That next phase should assume ending completeness + continuity + de-AI hardening are already in place.
