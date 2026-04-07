# Main Flow Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate and harden the API-first main user path for novel creation and chapter writing so the system can create a sample novel, generate chapter 1, persist it, generate chapter 2, and prove chapter 2 meaningfully continues chapter 1.

**Architecture:** Use backend API integration tests as the primary validation surface because the current repository already exposes the novel-library and writing-flow endpoints. Seed a temporary sample novel through the real novel API, drive chapter generation through the real writing task API, poll task completion, then verify persistence and continuation through chapter read endpoints. Keep fixes minimal and scoped to gaps found by these tests.

**Tech Stack:** FastAPI, pytest, pytest-asyncio, httpx AsyncClient/TestClient, SQLite-backed services, existing writing workflow/task manager.

---

## File Structure / Responsibility Map

- **Modify:** `backend/tests/test_main_flow_validation.py`
  - New API-first integration regression tests for the “novel library + writing” path.
- **Modify if needed:** `backend/app/api/novel_routes.py`
  - Only if the tests reveal create/list/chapter retrieval response mismatches.
- **Modify if needed:** `backend/app/api/writing_routes.py`
  - Only if the tests reveal task submission or polling shape issues.
- **Modify if needed:** `backend/app/services/writing_service.py`
  - Only if real workflow orchestration fails to persist chapter output or pass continuation context.
- **Modify if needed:** `backend/app/services/novel_service.py`
  - Only if sample novel creation cannot persist the minimum settings/context needed by writing flow.

Keep all changes tightly bounded. Do **not** refactor unrelated route/service code while implementing this plan.

---

### Task 1: Add the sample-novel API flow test skeleton

**Files:**
- Create: `backend/tests/test_main_flow_validation.py`
- Reference: `backend/tests/test_config_api.py`
- Reference: `backend/tests/test_auto_creation_flow.py`

- [ ] **Step 1: Write the failing test for sample novel creation and chapter 1 generation request**

```python
import pytest


@pytest.mark.asyncio
async def test_main_flow_can_create_sample_novel_and_submit_chapter_one(client, tmp_path, monkeypatch):
    payload = {
        "title": "联调样例小说",
        "genre": "urban",
        "description": "用于验证主流程联调",
        "author": "Test Runner",
        "settings": {
            "blueprint": {},
        },
    }

    create_response = await client.post("/api/novels", json=payload)
    create_body = create_response.json()

    assert create_response.status_code == 200
    novel_id = create_body["data"]["novel_id"]

    chapter_response = await client.post(
        "/api/writing/chapter",
        json={
            "novel_id": novel_id,
            "chapter_num": 1,
            "outline": "主角在雨夜收到一封改变命运的信。",
            "word_count_target": 1200,
            "style": "default",
        },
    )
    chapter_body = chapter_response.json()

    assert chapter_response.status_code == 200
    assert chapter_body["data"]["task_id"]
```

- [ ] **Step 2: Run the new test to verify the red state**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py::test_main_flow_can_create_sample_novel_and_submit_chapter_one -v`

Expected: FAIL because the new file/test does not exist yet.

- [ ] **Step 3: Create the test file with the minimal imports/fixtures needed**

Use the existing async API test style from `test_config_api.py`. Reuse the project’s `client` fixture if already provided elsewhere; if missing, define only the minimum fixture required for this file.

- [ ] **Step 4: Re-run the single test and confirm it reaches a meaningful failure**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py::test_main_flow_can_create_sample_novel_and_submit_chapter_one -v`

Expected: FAIL on a real behavior mismatch, not on import/fixture errors.

---

### Task 2: Add polling + chapter 1 persistence verification

**Files:**
- Modify: `backend/tests/test_main_flow_validation.py`
- Reference: `backend/app/api/writing_routes.py`
- Reference: `backend/app/api/novel_routes.py`

- [ ] **Step 1: Extend the test with task polling expectations**

Add polling logic that repeatedly calls `/api/writing/task/{task_id}` until it reaches `completed` or `failed`, with a tight max-iteration/time cap so the test cannot hang forever.

```python
for _ in range(20):
    task_response = await client.get(f"/api/writing/task/{task_id}")
    task_body = task_response.json()["data"]
    if task_body["status"] in {"completed", "failed"}:
        break
    await asyncio.sleep(0.05)

assert task_body["status"] == "completed"
assert task_body["result"]["content"]
```

- [ ] **Step 2: Run the single test to verify it fails for the right reason**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py::test_main_flow_can_create_sample_novel_and_submit_chapter_one -v -s`

Expected: FAIL because either the task never completes in time, returns failed, or content/persistence expectations are not met.

- [ ] **Step 3: Add persistence assertions through the real chapter read API**

After task completion, call:
`GET /api/novels/{novel_id}/chapters/1`

Assert:
- status code is 200
- chapter content exists
- title or chapter number matches chapter 1
- persisted content is substantially non-empty (e.g. `len(content.strip()) > 100`)

- [ ] **Step 4: Re-run the single test until chapter 1 creation + persistence pass**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py::test_main_flow_can_create_sample_novel_and_submit_chapter_one -v -s`

Expected: PASS.

---

### Task 3: Add chapter 2 continuation regression test

**Files:**
- Modify: `backend/tests/test_main_flow_validation.py`
- Reference: `backend/app/services/writing_service.py`
- Reference: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write the failing test for chapter 2 continuation behavior**

```python
@pytest.mark.asyncio
async def test_main_flow_chapter_two_continues_after_saved_chapter_one(client):
    ...
    assert chapter_two_content.strip()
    assert chapter_two_content != chapter_one_content
```

The test should:
- create a sample novel
- generate and persist chapter 1
- submit chapter 2 generation against the same novel
- poll task completion
- fetch persisted chapter 2 from the chapter API

- [ ] **Step 2: Add a concrete “non-trivial continuation” assertion**

Assert all of the following:
- chapter 2 is non-empty
- chapter 2 is not byte-identical to chapter 1
- chapter 2 length is above a minimum threshold
- chapter 2 does not begin with a large repeated prefix from chapter 1

Use a conservative heuristic, for example:

```python
assert chapter_one_content[:150] not in chapter_two_content[:300]
```

- [ ] **Step 3: Run only the chapter 2 test and confirm the red state**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py::test_main_flow_chapter_two_continues_after_saved_chapter_one -v -s`

Expected: FAIL on a true continuation/persistence issue if one exists.

- [ ] **Step 4: Make the minimum production fix required by the failure**

Allowed fix targets:
- `backend/app/services/writing_service.py`
- `backend/app/api/writing_routes.py`
- `backend/app/api/novel_routes.py`
- `backend/app/workflow_executor.py`

Examples of acceptable minimal fixes:
- missing novel context passed into the workflow
- chapter task result not persisted correctly
- chapter retrieval endpoint shape mismatch
- continuation path failing to use saved previous chapter context

Forbidden:
- broad workflow rewrites
- refactoring unrelated services
- changing prompt behavior “just because” without a failing test demanding it

- [ ] **Step 5: Re-run both main-flow tests**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py -v -s`

Expected: both tests PASS.

---

### Task 4: Verify the protected baseline still passes

**Files:**
- Modify if needed: whichever production file was changed in Task 3
- Test: `backend/tests/test_config_service.py`
- Test: `backend/tests/test_config_api.py`
- Test: `backend/tests/test_runtime_integrity.py`
- Test: `backend/tests/test_route_registration.py`
- Test: `backend/tests/test_service_routes.py`

- [ ] **Step 1: Run the backend regression suite that protects the recent fixes**

Run:
`python -m pytest backend/tests/test_main_flow_validation.py backend/tests/test_config_service.py backend/tests/test_config_api.py backend/tests/test_runtime_integrity.py backend/tests/test_route_registration.py backend/tests/test_service_routes.py -v`

Expected: all tests PASS.

- [ ] **Step 2: Run diagnostics on every changed backend file**

Use diagnostics on:
- `backend/tests/test_main_flow_validation.py`
- every modified production file

Expected: no new diagnostics in changed test/production files, or explicitly document any non-blocking pre-existing warning that was not caused by this work.

- [ ] **Step 3: Re-check backend health endpoint after test changes**

Run:
`python -c "from fastapi.testclient import TestClient; from app.main import app; c = TestClient(app); r = c.get('/api/health'); print(r.status_code); print(r.json()['status'])"`

Expected:
- `200`
- `healthy` or a deliberately understood status caused only by local optional services like Redis/Celery

---

### Task 5: Keep frontend build green while validating the API-first flow

**Files:**
- No frontend modifications expected unless the backend changes reveal a contract mismatch
- Modify only if required: `frontend/src/views/NovelLibrary.vue`
- Modify only if required: `frontend/src/views/WritingPanel.vue`

- [ ] **Step 1: Run frontend production build**

Run:
`npm run build`

Working directory:
`frontend`

Expected: PASS.

- [ ] **Step 2: Only if the build fails because of backend contract changes, patch the minimum frontend expectation mismatch**

Allowed:
- update payload field names
- update response extraction shape

Forbidden:
- redesigning views
- unrelated UI cleanup

- [ ] **Step 3: Re-run frontend build after any frontend patch**

Run:
`npm run build`

Expected: PASS.

---

### Task 6: Summarize evidence and hand off for the next phase

**Files:**
- Optional modify/create only if the project prefers durable records: `docs/plans/` or `docs/superpowers/plans/`

- [ ] **Step 1: Capture exact evidence for the validated main flow**

Record at minimum:
- sample novel creation succeeded
- chapter 1 task completed and persisted
- chapter 2 task completed and persisted
- chapter 2 was not a trivial replay of chapter 1
- backend regression suite passed
- frontend build passed

- [ ] **Step 2: Do not continue into “content quality hardening” inside this task batch**

Stop after proving “创作可用”. The next phase should separately target:
- AI-tone removal
- ending completeness
- continuity quality thresholds
- platform-specific review constraints

- [ ] **Step 3: If asked to continue, start a new plan for content-quality hardening**

That next plan should explicitly build on this validated main-flow baseline instead of re-solving creation/persistence again.
