# Backend Dual-Platform Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a backend export API that can generate Fanqie and Qimao chapter variants on demand from the same chapter source and return clearly labeled versions without breaking the main writing workflow.

**Architecture:** Reuse existing chapter retrieval, platform routing, and platform adaptation logic. Add a dedicated export endpoint that reads the source chapter, routes it through the requested platform adaptation branch(es) on demand, and returns a response containing one or two labeled platform versions plus basic metadata. Keep export generation isolated from the main chapter persistence path.

**Tech Stack:** Python, FastAPI routes, existing `ChapterService`, `WritingService`, `WritingWorkflowExecutor`, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/api/novel_routes.py`
  - Best place to add a chapter export endpoint since it already owns chapter retrieval routes.
- **Modify:** `backend/app/services/writing_service.py`
  - Add export-oriented helper(s) that can produce platform variants without mutating the main saved chapter.
- **Modify if needed:** `backend/app/workflow_executor.py`
  - Only if export reuse requires a small helper to run platform adaptation on existing content.
- **Create:** `backend/tests/test_dual_platform_export.py`
  - Dedicated regression surface for single-platform and dual-platform export responses.

Do **not** build a full artifact packaging system in this phase. This is an on-demand backend export API for chapter content only.

---

### Task 1: Add single-platform export tests first

**Files:**
- Create: `backend/tests/test_dual_platform_export.py`
- Modify: `backend/app/api/novel_routes.py`
- Modify: `backend/app/services/writing_service.py`

- [ ] **Step 1: Write a failing test for exporting a chapter as Fanqie**

The test should assert:
- input identifies `novel_id`, `chapter_num`, and `target="fanqiao"`
- response status is success
- response contains exactly one exported variant labeled `fanqiao`

- [ ] **Step 2: Write a second failing test for exporting a chapter as Qimao**

- [ ] **Step 3: Run the focused single-platform export tests to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py -k "single" -v`

- [ ] **Step 4: Implement the minimum export endpoint and service helper**

Suggested shape:
- route under chapter management, e.g. `POST /api/novels/{novel_id}/chapters/{chapter_num}/export`
- request body accepts `target`
- service helper loads source chapter and generates the requested platform variant

- [ ] **Step 5: Re-run the focused single-platform export tests**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py -k "single" -v`

Expected: PASS.

---

### Task 2: Add dual-platform export tests and implementation

**Files:**
- Modify: `backend/tests/test_dual_platform_export.py`
- Modify: `backend/app/services/writing_service.py`

- [ ] **Step 1: Write a failing test for `target="both"`**

The test should assert:
- response contains both `fanqiao` and `qimao`
- the variants are clearly labeled
- both variants carry the same chapter identity metadata

- [ ] **Step 2: Run the focused dual-export test to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_both_platform_variants -v`

- [ ] **Step 3: Implement the minimum dual-export logic**

Rules:
- generate both variants on demand
- do not overwrite the persisted chapter content
- keep export generation isolated from the normal save path

- [ ] **Step 4: Re-run the focused dual-export test**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_both_platform_variants -v`

Expected: PASS.

---

### Task 3: Expose clear export metadata in the API response

**Files:**
- Modify: `backend/tests/test_dual_platform_export.py`
- Modify: `backend/app/api/novel_routes.py`
- Modify: `backend/app/services/writing_service.py`

- [ ] **Step 1: Write a failing test that requires export metadata in the response**

At minimum include:
- `novel_id`
- `chapter_num`
- `target`
- `variants`
- per-variant `platform`

- [ ] **Step 2: Run the focused metadata test to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_response_includes_platform_metadata -v`

- [ ] **Step 3: Implement the minimum response metadata shape**

Keep the schema compact and explicit. Do not add dashboard/report payloads yet.

- [ ] **Step 4: Re-run the focused metadata test**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_response_includes_platform_metadata -v`

Expected: PASS.

---

### Task 4: Ensure export generation reuses the correct platform adaptation branch without mutating source content

**Files:**
- Modify: `backend/tests/test_dual_platform_export.py`
- Modify if needed: `backend/app/services/writing_service.py`

- [ ] **Step 1: Write a failing test that proves export generation does not overwrite the saved chapter**

The test should:
- load a stored chapter
- request one or two platform exports
- verify the stored chapter content is unchanged afterward

- [ ] **Step 2: Run the focused non-mutation test to verify the red state if export path mutates source content**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_does_not_mutate_saved_chapter -v`

- [ ] **Step 3: Implement the minimum non-mutation safeguard**

Keep export as a pure transformation of source content to derived variants.

- [ ] **Step 4: Re-run the focused non-mutation test**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py::test_export_does_not_mutate_saved_chapter -v`

Expected: PASS.

---

### Task 5: Run export regressions and the protected suite

**Files:**
- Test: `backend/tests/test_dual_platform_export.py`
- Test: `backend/tests/test_dual_platform_routing.py`
- Test: `backend/tests/test_qimao_adaptation.py`
- Test: `backend/tests/test_fanqie_adaptation.py`
- Test: `backend/tests/test_publishability_guardrails.py`
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run export-specific regressions**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_dual_platform_export.py backend/tests/test_dual_platform_routing.py backend/tests/test_qimao_adaptation.py backend/tests/test_fanqie_adaptation.py backend/tests/test_publishability_guardrails.py backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/api/novel_routes.py`
- `backend/app/services/writing_service.py`
- `backend/tests/test_dual_platform_export.py`
- `backend/app/workflow_executor.py` if modified

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of dual-platform export and stop before UI work

**Files:**
- Optional notes only if useful; avoid unnecessary doc churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one single-platform Fanqie export example
- one single-platform Qimao export example
- one dual-platform export example
- proof that source chapter content remains unchanged

- [ ] **Step 2: Stop after backend export is verified**

Do not continue yet into:
- frontend export button / UI
- quality console dashboard

- [ ] **Step 3: If asked to continue, write the next plan for UI integration or quality console productization**

That next phase should build on this backend export API instead of redoing export semantics.
