# Semi-Automatic Dual-Platform Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add semi-automatic dual-platform routing to the main writing flow so chapter generation can either follow an explicitly chosen target platform (`fanqiao` / `qimao`) or recommend one automatically when no platform is specified, then route the chapter through the matching platform adaptation chain.

**Architecture:** Reuse the existing platform adaptation gates already implemented in `workflow_executor.py` and the existing style analysis in `StyleLearner`. Add a routing decision layer in the writing-service/API boundary: explicit platform wins; otherwise analyze available style context and content hints to recommend a default platform. Propagate both the resolved platform and the resolution source (`user_selected` vs `auto_recommended`) into the workflow result.

**Tech Stack:** Python, FastAPI routes, existing `WritingService`, `WritingWorkflowExecutor`, `StyleLearner`, pytest, async tests.

---

## File Structure / Responsibility Map

- **Modify:** `backend/app/services/writing_service.py`
  - Best place to resolve target platform before calling the workflow executor.
- **Modify:** `backend/app/api/writing_routes.py`
  - Ensure input payload supports `platform` and result payload exposes resolved routing metadata.
- **Modify if needed:** `backend/app/workflow_executor.py`
  - Only if result payload needs to carry platform metadata through the workflow response.
- **Reference/Modify if needed:** `backend/app/services/style_learner.py`
  - Reuse `match_platform` / `get_style_config`; extend only if platform recommendation rules need slight refinement.
- **Create:** `backend/tests/test_dual_platform_routing.py`
  - Dedicated regression surface for explicit routing, automatic recommendation, and result metadata.

Do **not** reimplement Fanqie/Qimao adaptation logic here. This phase is strictly about routing into those already-existing branches.

---

### Task 1: Add explicit platform selection with failing tests first

**Files:**
- Create: `backend/tests/test_dual_platform_routing.py`
- Modify: `backend/app/services/writing_service.py`

- [ ] **Step 1: Write a failing test where the caller explicitly requests `fanqiao` and the workflow receives that platform**

The test should assert:
- payload includes `platform="fanqiao"`
- service passes `style="fanqiao"` (or equivalent routing field) into the workflow executor
- result metadata records that platform was user-selected

- [ ] **Step 2: Add a second failing test for explicit `qimao` selection**

- [ ] **Step 3: Run the focused tests to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py -k "explicit" -v`

- [ ] **Step 4: Implement the minimum explicit routing logic**

Rules:
- if `platform` is present and valid, use it directly
- do not override with style matching
- preserve backward compatibility if only `style` is provided

- [ ] **Step 5: Re-run the explicit routing tests**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py -k "explicit" -v`

Expected: PASS.

---

### Task 2: Add automatic platform recommendation when no platform is specified

**Files:**
- Modify: `backend/tests/test_dual_platform_routing.py`
- Modify: `backend/app/services/writing_service.py`
- Reference: `backend/app/services/style_learner.py`

- [ ] **Step 1: Write a failing test where no platform is specified and the service auto-recommends `fanqiao` based on the text/style context**

Use either:
- a stubbed `StyleLearner.match_platform(...)`, or
- a realistic text sample whose features should clearly map to Fanqie.

- [ ] **Step 2: Write a second failing test for auto-recommending `qimao`**

- [ ] **Step 3: Run the focused auto-routing tests to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py -k "auto" -v`

- [ ] **Step 4: Implement the minimum recommendation logic**

Suggested resolution order:
1. explicit `platform` from request
2. known `style_context.style_id` if it is already a platform style
3. `StyleLearner.match_platform(...)` based on enriched outline / context
4. fallback = `default`

- [ ] **Step 5: Re-run the auto-routing tests**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py -k "auto" -v`

Expected: PASS.

---

### Task 3: Expose routing metadata in API/task results

**Files:**
- Modify: `backend/app/services/writing_service.py`
- Modify: `backend/app/api/writing_routes.py`
- Modify if needed: `backend/tests/test_dual_platform_routing.py`

- [ ] **Step 1: Write a failing test that requires the final result to expose routing metadata**

At minimum return:
- `platform`
- `platform_resolution` (`user_selected`, `auto_recommended`, or `default_fallback`)

- [ ] **Step 2: Run the focused metadata test to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py::test_platform_metadata_is_exposed_in_results -v`

- [ ] **Step 3: Implement the minimum metadata propagation**

The metadata should survive through:
- writing service return value
- task manager result payload
- API polling response

- [ ] **Step 4: Re-run the focused metadata test**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py::test_platform_metadata_is_exposed_in_results -v`

Expected: PASS.

---

### Task 4: Ensure the chosen platform actually reaches the right adaptation branch

**Files:**
- Modify: `backend/tests/test_dual_platform_routing.py`
- Modify if needed: `backend/app/workflow_executor.py`

- [ ] **Step 1: Write a failing workflow-level test that ensures `fanqiao` triggers Fanqie adaptation logic and `qimao` triggers Qimao adaptation logic**

Do not re-test the full adaptation quality here. Just verify routing branch selection.

- [ ] **Step 2: Run the focused branch-routing test to verify the red state**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py::test_platform_routing_enters_expected_adaptation_branch -v -s`

- [ ] **Step 3: Implement the minimum branch-selection fix if required**

Only touch the workflow if branch routing is not already faithfully driven by the resolved platform.

- [ ] **Step 4: Re-run the focused branch-routing test**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py::test_platform_routing_enters_expected_adaptation_branch -v -s`

Expected: PASS.

---

### Task 5: Run routing regressions and the protected suite

**Files:**
- Test: `backend/tests/test_dual_platform_routing.py`
- Test: `backend/tests/test_qimao_adaptation.py`
- Test: `backend/tests/test_fanqie_adaptation.py`
- Test: `backend/tests/test_publishability_guardrails.py`
- Test: `backend/tests/test_style_feedback.py`
- Test: `backend/tests/test_style_propagation.py`
- Test: `backend/tests/test_de_ai_polish.py`
- Test: `backend/tests/test_second_chapter_continuation.py`
- Test: `backend/tests/test_ending_completeness.py`

- [ ] **Step 1: Run dual-platform routing regressions**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py -v`

Expected: PASS.

- [ ] **Step 2: Run the broader protected suite**

Run:
`python -m pytest backend/tests/test_dual_platform_routing.py backend/tests/test_qimao_adaptation.py backend/tests/test_fanqie_adaptation.py backend/tests/test_publishability_guardrails.py backend/tests/test_style_feedback.py backend/tests/test_style_propagation.py backend/tests/test_de_ai_polish.py backend/tests/test_second_chapter_continuation.py backend/tests/test_ending_completeness.py -v`

Expected: PASS.

- [ ] **Step 3: Run diagnostics on changed files**

Use diagnostics on:
- `backend/app/services/writing_service.py`
- `backend/app/api/writing_routes.py`
- `backend/app/workflow_executor.py` if modified
- `backend/tests/test_dual_platform_routing.py`

Expected: no new blocking diagnostics introduced by this phase.

---

### Task 6: Capture evidence of semi-automatic routing and stop before export strategy work

**Files:**
- Optional notes only if useful; avoid unnecessary doc churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- one explicit Fanqie route example
- one explicit Qimao route example
- one auto-recommended route example
- proof that result payload now exposes platform + resolution source

- [ ] **Step 2: Stop after semi-automatic routing is verified**

Do not continue yet into:
- dual-export generation
- platform-specific artifact packaging
- dashboard UX / control panel work

- [ ] **Step 3: If asked to continue, write the next plan for export strategy or quality console productization**

That next phase should build on this routing layer rather than redoing routing logic.
