# Writing Page Export Entry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal usable export entry on the writing page so users can choose Fanqie, Qimao, or dual-platform export, trigger the backend export API, and view the returned variants directly in-page without disrupting the existing writing flow.

**Architecture:** Reuse the existing export button in `WritingPanel.vue` and convert it into an in-page modal workflow. Add a small frontend API helper for the backend chapter export endpoint, then wire the writing page to open a modal, let users choose the target (`fanqiao` / `qimao` / `both`), fetch the export results, and display them in a scrollable, labeled result area.

**Tech Stack:** Vue, Element Plus, existing writing page (`WritingPanel.vue`), frontend request helpers / axios layer, backend export API already implemented.

---

## File Structure / Responsibility Map

- **Modify:** `frontend/src/views/WritingPanel.vue`
  - Main place for export button behavior, export dialog state, target selection, loading state, and result rendering.
- **Modify if present:** frontend API/request helper file used by the writing page
  - Add a dedicated function for calling the backend chapter export endpoint.
- **Create if needed:** `frontend/src/api/export.js` or similar small request helper
  - Only if there is no clean existing request module to extend.

Do **not** build download, history, or dashboard features in this phase. This is strictly a minimal usable in-page export entry.

---

### Task 1: Add frontend API integration for chapter export

**Files:**
- Modify or create: frontend request helper file
- Test by manual/component-level verification via the writing page

- [ ] **Step 1: Write the failing UI/API expectation by identifying the current `exportChapter` path**

Confirm the current button path is placeholder or insufficient for the new backend export API.

- [ ] **Step 2: Add a small request helper for the new backend endpoint**

Expected request shape:
- chapter identity (`novel_id`, `chapter_num`)
- body with `target = fanqiao | qimao | both`

- [ ] **Step 3: Make the helper return normalized response data for the dialog**

The helper should hide transport details and return a clean object the page can render directly.

- [ ] **Step 4: Verify the helper is wired correctly (at least by invoking it from the page logic)**

Expected: the page can call the export API without breaking current writing actions.

---

### Task 2: Replace the current export button behavior with an export dialog

**Files:**
- Modify: `frontend/src/views/WritingPanel.vue`

- [ ] **Step 1: Add a failing UI expectation for opening an export dialog from the existing button**

This can be tested manually or by component-level reasoning if no test framework exists for Vue in the repo.

- [ ] **Step 2: Add dialog state and target selection state**

The dialog should at minimum include:
- target selector (`fanqiao`, `qimao`, `both`)
- confirm button
- cancel button

- [ ] **Step 3: Wire the existing “导出” button to open the dialog instead of any placeholder action**

- [ ] **Step 4: Verify the dialog opens cleanly and does not disrupt the writing page layout**

Expected: writing page remains stable, and export action becomes discoverable.

---

### Task 3: Fetch and render export results in the dialog

**Files:**
- Modify: `frontend/src/views/WritingPanel.vue`

- [ ] **Step 1: Add loading/error/result states for export**

Required states:
- idle
- loading
- error
- result loaded

- [ ] **Step 2: On confirm, call the export helper with the selected target and current chapter identity**

The request must use the chapter the user is currently editing/viewing.

- [ ] **Step 3: Render returned variants inside the dialog**

At minimum show:
- variant platform label
- title (if returned)
- content block / textarea / preview region

- [ ] **Step 4: Verify single-platform and dual-platform rendering**

Expected:
- `fanqiao` → one labeled result
- `qimao` → one labeled result
- `both` → two clearly separated labeled results

---

### Task 4: Add minimal UX safeguards so export does not feel broken

**Files:**
- Modify: `frontend/src/views/WritingPanel.vue`

- [ ] **Step 1: Prevent export when no novel/chapter is selected**

- [ ] **Step 2: Disable confirm button during export request**

- [ ] **Step 3: Show backend errors clearly in the dialog**

- [ ] **Step 4: Keep the export modal independent from save / AI writing actions**

Expected: exporting should not interfere with the current editing state.

---

### Task 5: Verify the writing page export entry and protected frontend baseline

**Files:**
- Modify: `frontend/src/views/WritingPanel.vue`
- Modify/create: frontend export request helper

- [ ] **Step 1: Run frontend build**

Run:
`npm run build`

Working directory:
`frontend`

Expected: PASS.

- [ ] **Step 2: Run diagnostics on changed frontend files**

Use diagnostics on changed `.vue` / `.js` / `.ts` files.

- [ ] **Step 3: Manually verify the minimal export flow in the writing page if possible**

At minimum verify:
- dialog opens
- target can be selected
- request triggers
- results render in-page

If full browser verification is unavailable in this step, note exactly what was verified via code/build/API reasoning.

---

### Task 6: Capture evidence of the frontend export entry and stop before dashboard work

**Files:**
- Optional notes only if useful; avoid extra churn otherwise

- [ ] **Step 1: Capture exact evidence of the improvement**

At minimum capture:
- writing page export entry exists
- one single-platform result rendering example
- one dual-platform result rendering example

- [ ] **Step 2: Stop after the minimal usable export entry is verified**

Do not continue yet into:
- download buttons
- export history
- quality console dashboard

- [ ] **Step 3: If asked to continue, write the next plan for download support or the quality console UI**

That next phase should build on this in-page export entry rather than redesigning it.
